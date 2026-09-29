# Витрина на GitHub

Люди находят проекты на GitHub через поиск по темам и через подборки
«awesome-…». Звёзды — это социальное доказательство для постов («код открыт,
его смотрели»). README уже оформлен: значки, ссылки на сайт с `?ref=github`,
настоящие скриншоты и отчёт VirusTotal.

## 1. Настройки репозитория (5 минут, делаете вы)

GitHub → репозиторий → справа «About» → ⚙:

- **Description:** `Free Dota 2 coach for Windows: advice over the game and out loud during the match, and a fact-checked post-match review. Official Valve GSI, no Overwolf.`
- **Website:** `https://luhovyimvp.dev/en/?ref=github`
- **Topics:** `dota2`, `dota-2`, `game-coach`, `esports`, `gamestate-integration`, `overlay`, `electron`, `fastapi`, `opendota`, `gaming-tools`, `windows`, `ai-coach`
- Галочки «Releases» и «Packages»: Releases оставить, Packages снять.

Settings → General → **Social preview** → загрузить `site/assets/og.jpg`
(1200×630). Это картинка, которая показывается, когда ссылку на репозиторий
присылают в Telegram, Discord или Twitter.

## 2. Подборки awesome-… (делаете вы, от своего аккаунта)

1. Поиск GitHub: `awesome dota` и `awesome dota2`. Берите подборки, где был
   коммит за последний год и принимают pull request’ы со сторонними
   инструментами. В каждой прочитайте CONTRIBUTING: формат строки и порядок.
2. Форк → добавить одну строку в нужный раздел (обычно «Tools», «Overlays»,
   «Desktop apps») → pull request.

Строка (подстройте под формат списка):

```
- [Wardly](https://github.com/makquella/dota-ai-coach) - Free Windows coach: advice over the game and out loud during the match (official GSI), and a fact-checked post-match review. Open source.
```

Текст pull request’а:

```
Add Wardly, a free and open-source Dota 2 coach for Windows.

- Live advice over the game and by voice, from Valve's official Game State Integration (no memory reading).
- Post-match review: score by area, map of deaths, item timings against OpenDota, the same-role player of the match.
- MIT, no ads or accounts. Website: https://luhovyimvp.dev/en/

I'm the author; happy to change the wording or the section.
```

Честно пишите, что вы автор: в подборках это нормально, скрытый самопиар — нет.

## 3. Позже, для англоязычной волны

- **Show HN** (Hacker News), когда будет подпись установщика и первые отзывы.
  Заголовок: `Show HN: Wardly – a Dota 2 coach whose AI review can't make up numbers`.
  В тексте — как устроено: GSI → правила и планировщик → разбор → проверка
  каждой цифры в ответе модели. Ссылка — на репозиторий, сайт — внутри.
- **Release notes на английском** уже есть в каждом релизе: GitHub показывает
  их подписчикам репозитория («Watch → Custom → Releases»).
