// Deliver a single preparation document to the existing owner's Telegram chat.
// This never messages creators, joins communities or publishes a recruitment post.
import { mkdir, readFile, writeFile } from 'node:fs/promises';

const fileName = 'wardly-beta-free-outreach.md';
const contents = await readFile(new URL('../../docs/marketing/beta-outreach.md', import.meta.url));
await mkdir('promo-out', { recursive: true });
await writeFile(`promo-out/${fileName}`, contents);
const receipt = { sent: false, public_posts: 0, creator_messages: 0, file: fileName };

if (process.env.SEND_PREVIEW === 'true') {
  const token = process.env.TELEGRAM_BOT_TOKEN?.trim();
  const ownerChat = process.env.TELEGRAM_CHAT_ID?.trim();
  if (!token || !ownerChat) throw new Error('Owner Telegram configuration is missing');
  const form = new FormData();
  form.set('chat_id', ownerChat);
  form.set('document', new Blob([contents], { type: 'text/markdown' }), fileName);
  form.set('caption', 'Бесплатный набор бета-тестеров Wardly: 6 проверенных площадок UK/EN и готовые личные обращения в файле.\n\nСначала — правила и согласование одного бесплатного поста с модератором. Кнопки открывают сообщества; они не отправляют сообщения.\n\nОбращения авторам ещё не отправлены: личный Telegram/Discord/почта здесь не подключены. После согласования используйте готовые посты из кампании.');
  form.set('reply_markup', JSON.stringify({ inline_keyboard: [
    [{ text: 'UK · Типовий Лс з Харди', url: 'https://t.me/kif_13' }, { text: 'UK · Ghostik', url: 'https://t.me/ghostikpub' }],
    [{ text: 'EN · Qubi Discord', url: 'https://discord.gg/gM8c4fav5v' }, { text: 'EN · Balloon Discord', url: 'https://discord.com/invite/eGKhYX7dxS' }]
  ] }));
  try {
    const chatResponse = await fetch(`https://api.telegram.org/bot${token}/getChat`, { method: 'POST', body: new URLSearchParams({ chat_id: ownerChat }), signal: AbortSignal.timeout(20000) });
    const chat = await chatResponse.json();
    receipt.owner_chat = { ok: chat.ok === true, status: chatResponse.status, type: chat.result?.type, error_code: chat.error_code };
    if (!chatResponse.ok || chat.ok !== true || chat.result?.type !== 'private') {
      receipt.error = 'Configured owner chat is not confirmed private; no document sent.';
      throw new Error('Owner chat check failed');
    }
    const response = await fetch(`https://api.telegram.org/bot${token}/sendDocument`, { method: 'POST', body: form, signal: AbortSignal.timeout(45000) });
    const data = await response.json();
    receipt.telegram = { ok: data.ok === true, status: response.status, message_id: data.result?.message_id, file_name: data.result?.document?.file_name, file_size: data.result?.document?.file_size, error_code: data.error_code };
    receipt.sent = response.ok && data.ok === true && data.result?.document?.file_name === fileName;
    if (!receipt.sent) process.exitCode = 1;
  } catch {
    receipt.error ||= 'Telegram request failed; delivery is unconfirmed. No automatic retry.';
    process.exitCode = 1;
  }
}
await writeFile('promo-out/beta-outreach-delivery.json', JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt));
