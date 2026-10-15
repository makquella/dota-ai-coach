// Every transform and picture is derived from narration time, never CSS timers.
const sections = [...document.querySelectorAll('.scene')];
const allWords = captions.flatMap(c => c.words);
const clamp = n => Math.min(1, Math.max(0, n));
const ease = n => 1 - Math.pow(1 - clamp(n), 3);
const findWord = (scene, fragment, fallback = 0) => {
  const span = timeline[scene];
  const word = allWords.find(w => w.s >= span.start && w.s < span.end && w.w.toLowerCase().includes(fragment));
  return word ? word.s - span.start : fallback;
};
const reviewAt = findWord(1, language === 'uk' ? 'розбір' : 'post-match', 2.7);
const heroAt = language === 'uk'
  ? ['свені', 'джагернауті', 'терорблейді'].map(x => findWord(2, x, 3))
  : ['sven', 'juggernaut', 'terrorblade'].map(x => findWord(2, x, 3));
const questionAt = language === 'uk'
  ? ['запізнилося', 'відволікало', 'неправильною'].map(x => findWord(4, x))
  : ['late', 'distracted', 'wrong'].map(x => findWord(4, x));
const goalAt = language === 'uk'
  ? ['точнішими', 'вчаснішими', 'кориснішими'].map(x => findWord(5, x))
  : ['accurate', 'timely', 'useful'].map(x => findWord(5, x));
const ctaAt = findWord(6, language === 'uk' ? 'напиши' : 'comment', 1);
const escape = s => s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
window.renderAt = async t => {
  const active = Math.max(0, timeline.findIndex(s => t >= s.start && t < s.end));
  const local = Math.max(0, t - timeline[active].start);
  document.body.dataset.scene = active;
  sections.forEach((el, i) => {
    el.style.visibility = i === active ? 'visible' : 'hidden';
    // Open with a fully visible hook. Later cuts have a quick, restrained settle.
    const enter = i === 0 ? 1 : ease(local / .23);
    el.style.opacity = i === active ? 1 : 0;
    el.style.transform = `translateY(${(1 - enter) * 24}px)`;
  });
  const current = sections[active];
  const decoding = [];
  current.querySelectorAll('[data-hero]').forEach(img => {
    const frames = motion[img.dataset.hero];
    if (frames?.length) {
      const frame = Math.floor(t * 20) % frames.length;
      if (img.dataset.frame !== String(frame)) {
        img.src = frames[frame];
        img.dataset.frame = String(frame);
        decoding.push(img.decode());
      }
    }
  });
  if (active === 0) {
    current.querySelector('.hook-heroes').style.transform = `translateY(${-local * 6}px) scale(${1 + local * .018})`;
  }
  if (active === 1) {
    const second = local >= reviewAt;
    for (const name of ['title', 'screen']) {
      current.querySelector(`.live-${name}`).style.visibility = second ? 'hidden' : 'visible';
      current.querySelector(`.review-${name}`).style.visibility = second ? 'visible' : 'hidden';
    }
    current.querySelector('.live-screen img').style.transform = `scale(${1 + Math.min(local, reviewAt) * .008})`;
    current.querySelector('.review-screen img').style.transform = `translateY(${-Math.max(0, local - reviewAt) * 13}px)`;
  }
  if (active === 2) {
    const selected = heroAt.findLastIndex(at => local >= at);
    current.querySelectorAll('.hero-card').forEach((card, i) => {
      card.classList.toggle('selected', selected === i);
      const start = ease((local - i * .09) / .34);
      card.style.transform = `translateY(${(1 - start) * 48 + (selected === i ? -14 : 0)}px)`;
      card.style.opacity = .25 + .75 * start;
    });
  }
  if (active === 4) {
    const selected = Math.max(0, questionAt.findLastIndex(at => local >= at));
    current.querySelectorAll('.question').forEach((q, i) => {
      q.classList.toggle('selected', selected === i);
      q.style.transform = `translateX(${selected === i ? 12 * ease((local - questionAt[i]) / .15) : 0}px)`;
    });
  }
  if (active === 5) {
    current.querySelectorAll('.goal').forEach((g, i) => {
      const on = local >= goalAt[i];
      g.classList.toggle('selected', on);
      g.querySelector('span').style.opacity = on ? 1 : .2;
      g.style.transform = `translateX(${on ? 8 * ease((local - goalAt[i]) / .22) : 0}px)`;
    });
  }
  if (active === 6) {
    const hit = ease((local - ctaAt) / .22);
    const card = current.querySelector('.comment-card');
    card.style.transform = `scale(${.93 + hit * .07}) rotate(${-.9 + hit * .9}deg)`;
    card.style.filter = `saturate(${.55 + hit * .45})`;
  }
  const cue = captions.find(c => t >= c.start && t < c.end);
  const box = document.querySelector('.captions');
  // The opening headline IS its caption. On the final card the same words
  // are composed as the invitation + comment CTA, avoiding a second copy.
  box.classList.toggle('hook', active === 0);
  box.style.display = cue && active !== 6 ? 'block' : 'none';
  box.innerHTML = cue ? cue.words.map((w, i) => {
    const next = cue.words[i + 1]?.s ?? cue.end;
    const on = t >= w.s && t < next && w.w.length > 2;
    return `<span class="${on ? 'active' : ''}">${escape(w.w)}</span>`;
  }).join(' ') : '';
  await Promise.all(decoding);
};
window.layoutErrors = () => {
  const visible = el => {
    for (let x = el; x; x = x.parentElement) {
      const style = getComputedStyle(x);
      if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) === 0) return false;
    }
    return true;
  };
  const errors = [...document.querySelectorAll('[data-safe]')].flatMap(el => {
    if (!visible(el)) return [];
    const r = el.getBoundingClientRect();
    const result = [];
    if (r.left < 78 || r.top < 196 || r.right > 910 || r.bottom > 1450) result.push({text:el.textContent,box:[r.left,r.top,r.right,r.bottom]});
    if (el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 2) result.push({text:el.textContent,overflow:true});
    return result;
  });
  const caption = document.querySelector('.captions');
  if (visible(caption) && caption.clientHeight > (caption.classList.contains('hook') ? 225 : 155)) errors.push({captions:'more than two lines'});
  if (document.querySelectorAll('[data-brand]').length !== 1) errors.push({branding:'duplicate logo'});
  return errors;
};
window.renderAt(0);
