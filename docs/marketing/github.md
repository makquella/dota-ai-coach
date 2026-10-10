# Вітрина на GitHub

Люди знаходять проєкти на GitHub через пошук за темами й через добірки
«awesome-…». Зірки — це соціальний доказ для дописів («код відкритий,
його дивилися»). README вже оформлено: значки, посилання на сайт із `?ref=github`,
справжні скриншоти й звіт VirusTotal.

## 1. Налаштування репозиторію (5 хвилин, робите ви)

GitHub → репозиторій → праворуч «About» → ⚙:

- **Description:** `Free Dota 2 coach for Windows: advice over the game and out loud during the match, and a fact-checked post-match review. Official Valve GSI, no Overwolf.`
- **Website:** `https://luhovyimvp.dev/en/?ref=github`
- **Topics:** `dota2`, `dota-2`, `game-coach`, `esports`, `gamestate-integration`, `overlay`, `electron`, `fastapi`, `opendota`, `gaming-tools`, `windows`, `ai-coach`
- Позначки «Releases» і «Packages»: Releases залишити, Packages зняти.

Settings → General → **Social preview** → завантажити `site/assets/og.jpg`
(1200×630). Це картинка, яка показується, коли посилання на репозиторій
надсилають у Telegram, Discord чи Twitter.

## 2. Добірки awesome-… (робите ви, від свого акаунта)

1. Пошук GitHub: `awesome dota` і `awesome dota2`. Беріть добірки, де був
   коміт за останній рік і приймають pull request'и зі сторонніми
   інструментами. У кожній прочитайте CONTRIBUTING: формат рядка й порядок.
2. Форк → додати один рядок у потрібний розділ (зазвичай «Tools», «Overlays»,
   «Desktop apps») → pull request.

Рядок (підлаштуйте під формат списку):

```
- [Wardly](https://github.com/makquella/dota-ai-coach) - Free Windows coach: advice over the game and out loud during the match (official GSI), and a fact-checked post-match review. Open source.
```

Текст pull request'а:

```
Add Wardly, a free and open-source Dota 2 coach for Windows.

- Live advice over the game and by voice, from Valve's official Game State Integration (no memory reading).
- Post-match review: score by area, map of deaths, item timings against OpenDota, the same-role player of the match.
- MIT, no ads or accounts. Website: https://luhovyimvp.dev/en/

I'm the author; happy to change the wording or the section.
```

Чесно пишіть, що ви автор: у добірках це нормально, прихований самопіар — ні.

## 3. Пізніше, для англомовної хвилі

- **Show HN** (Hacker News), коли буде підпис інсталятора й перші відгуки.
  Заголовок: `Show HN: Wardly – a Dota 2 coach whose AI review can't make up numbers`.
  У тексті — як влаштовано: GSI → правила й планувальник → розбір → перевірка
  кожної цифри у відповіді моделі. Посилання — на репозиторій, сайт — усередині.
- **Release notes англійською** вже є в кожному релізі: GitHub показує
  їх підписникам репозиторію («Watch → Custom → Releases»).
