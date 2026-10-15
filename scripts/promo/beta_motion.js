// Narration time owns all motion. No CSS timers, random state or fake gameplay.
const sections = [...document.querySelectorAll('.scene')];
const allWords = captions.flatMap(c => c.words);
const clamp = n => Math.min(1, Math.max(0, n));
const ease = n => 1 - Math.pow(1 - clamp(n), 3);
const findWord = (scene, fragment, fallback = 0) => {
  const span = timeline[scene];
  const word = allWords.find(w => w.s >= span.start && w.s < span.end && w.w.toLowerCase().includes(fragment));
  return word ? word.s - span.start : fallback;
};
const reviewAt = findWord(1, language === 'uk' ? 'розбір' : 'post-match', 2);
const heroAt = language === 'uk'
  ? ['джагернаута', 'терорблейда'].map(x => findWord(2, x, 1.2))
  : ['juggernaut', 'terrorblade'].map(x => findWord(2, x, 1.2));
const questionAt = language === 'uk'
  ? ['допомогло', 'запізнилося', 'хибною'].map(x => findWord(4, x))
  : ['helped', 'late', 'wrong'].map(x => findWord(4, x));
const ctaAt = findWord(6, language === 'uk' ? 'напиши' : 'comment', .7);
const escape = s => s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const emphasis = /wardly|sven|свені|mmr|бета|beta|хибною|wrong|запізнилося|late/i;
window.renderAt = async t => {
  const active = Math.max(0, timeline.findIndex(s => t >= s.start && t < s.end));
  const local = Math.max(0, t - timeline[active].start);
  document.body.dataset.scene = active;
  sections.forEach((el, i) => {
    el.style.visibility = i === active ? 'visible' : 'hidden';
    el.style.opacity = i === active ? 1 : 0;
    el.style.transform = `translateY(${i === 0 ? 0 : (1 - ease(local / .16)) * 16}px)`;
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
  if (active === 0) current.querySelector('.hook-heroes').style.transform = `translateY(${-local * 3}px) scale(${1 + local * .012})`;
  if (active === 1) {
    const second = local >= reviewAt;
    for (const name of ['title', 'screen']) {
      current.querySelector(`.live-${name}`).style.visibility = second ? 'hidden' : 'visible';
      current.querySelector(`.review-${name}`).style.visibility = second ? 'visible' : 'hidden';
    }
    current.querySelector('.game-context').style.transform = `scale(${1 + Math.min(local, reviewAt) * .012})`;
    current.querySelector('.review-screen img').style.transform = `translateY(${-Math.max(0, local - reviewAt) * 5}px)`;
  }
  if (active === 2) {
    const selected = heroAt.findLastIndex(at => local >= at);
    current.querySelectorAll('.hero-card').forEach((card, i) => {
      card.classList.toggle('selected', selected === i);
      card.style.transform = `translateY(${selected === i ? -10 : 0}px)`;
    });
  }
  if (active === 3) current.querySelector('.review-detail img').style.transform = `translateY(${-local * 7}px)`;
  if (active === 4) {
    const selected = Math.max(0, questionAt.findLastIndex(at => local >= at));
    current.querySelectorAll('.question').forEach((q, i) => {
      q.classList.toggle('selected', selected === i);
      q.style.transform = `translateX(${selected === i ? 10 * ease((local - questionAt[i]) / .14) : 0}px)`;
    });
  }
  if (active === 5) current.querySelectorAll('.goal').forEach((g, i) => {
    g.style.opacity = .55 + .45 * ease((local - i * .1) / .3);
    g.style.transform = `translateX(${(1 - ease((local - i * .1) / .3)) * 18}px)`;
  });
  if (active === 6) {
    const hit = ease((local - ctaAt) / .18);
    current.querySelector('.comment-card').style.transform = `scale(${.96 + hit * .04})`;
  }
  const cue = captions.find(c => t >= c.start && t < c.end);
  const box = document.querySelector('.captions');
  box.style.display = cue && active !== 6 ? 'block' : 'none';
  box.innerHTML = cue ? cue.words.map(w => `<span class="${emphasis.test(w.w) ? 'emphasis' : ''}">${escape(w.w)}</span>`).join(' ') : '';
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
  const elements = [...document.querySelectorAll('[data-safe]')].filter(visible);
  const errors = elements.flatMap(el => {
    const r = el.getBoundingClientRect();
    const result = [];
    if (r.left < 78 || r.top < 196 || r.right > 910 || r.bottom > 1450) result.push({text:el.textContent,box:[r.left,r.top,r.right,r.bottom]});
    if (el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 2) result.push({text:el.textContent,overflow:true});
    return result;
  });
  elements.forEach((a, i) => elements.slice(i + 1).forEach(b => {
    if (a.contains(b) || b.contains(a)) return;
    const x = a.getBoundingClientRect(), y = b.getBoundingClientRect();
    if (Math.min(x.right, y.right) - Math.max(x.left, y.left) > 8 && Math.min(x.bottom, y.bottom) - Math.max(x.top, y.top) > 8) errors.push({overlap:[a.textContent,b.textContent]});
  }));
  const caption = document.querySelector('.captions');
  if (visible(caption) && caption.clientHeight > 145) errors.push({captions:'more than two lines'});
  if (document.querySelectorAll('[data-brand]').length !== 1) errors.push({branding:'duplicate logo'});
  return errors;
};
window.renderAt(0);
