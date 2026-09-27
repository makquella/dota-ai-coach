# Сайт Dota AI Coach

Статический лендинг без сборки: `index.html`, `styles.css`, `app.js` и `assets/`
(шрифт Inter, скриншоты приложения на двух языках, иконка, превью для соцсетей).
Всё грузится с того же домена — ни CDN, ни трекеров.

- Язык: русский по умолчанию, английский — по языку браузера или переключателю
  RU/EN (запоминается в `localStorage`). Русские тексты — в HTML, английские —
  в `app.js` (`EN`).
- Кнопки «Скачать» ведут прямо на установщик последнего релиза GitHub
  (`api.github.com/repos/makquella/dota-ai-coach/releases/latest`), а если API
  недоступен — на страницу релизов. Для посетителей репозиторий должен быть
  публичным.
- Карточка подсказки в первом экране показывает настоящие тексты советов
  приложения.

## Посмотреть локально

```bash
cd site && python3 -m http.server 8080
# http://localhost:8080
```

## Свой домен

Подойдёт любой статический хостинг — достаточно выложить содержимое папки
`site/` в корень сайта.

- **GitHub Pages.** Settings → Pages → Source: *GitHub Actions*, затем
  Actions → *Website* → Run workflow (`.github/workflows/pages.yml`). Для своего
  домена укажите его в Settings → Pages → Custom domain и добавьте у регистратора
  DNS-запись `CNAME` на `makquella.github.io` (для корня домена — записи `A` на
  адреса GitHub Pages).
- **Cloudflare Pages / Netlify / Vercel.** Новый проект из репозитория, команда
  сборки — пустая, папка публикации — `site`, затем подключить домен в панели.
- **Свой сервер (nginx).** `root /var/www/dota-ai-coach;` и скопировать туда
  содержимое `site/`.

После подключения домена поменяйте в `index.html` `og:image` на полный адрес
(`https://ваш-домен/assets/og.jpg`) — так превью ссылки надёжнее показывается в
Telegram, Discord и VK.

## Обновить скриншоты

Скриншоты в `assets/shots/{ru,en}/` сняты с настоящего приложения на демо-данных
(2x, JPEG). Если интерфейс поменяется, их стоит переснять тем же способом и
сохранить под теми же именами.

## Hero and item pictures

The hero scene and the «В игре» cards load hero portraits and item icons from Valve's CDN (`cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/...`, the same files dota2.com and OpenDota show) at view time; `app.js` fills every `.pic[data-hero]` / `.pic[data-item]`, and without a picture the initials show. Dota 2 and its artwork are Valve's.
