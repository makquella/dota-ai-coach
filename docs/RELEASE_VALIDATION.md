# Перевірка commit перед випуском

F15 у 0.53.10 робить поточний CI reusable: `ci.yml` приймає обов'язковий `source_sha` при `workflow_call`. Звичайні push/PR перевірки зберігають попередні job names і запускають Windows packaging. Кожен checkout використовує повний SHA, і `verify_source.py` підтверджує HEAD і відсутність змін tracked source. Для PR це GitHub test-merge SHA; для push — SHA події.

## Release workflow

1. Read-only `source` job бере snapshot SHA події, читає version і перевіряє відповідність tag. Manual release дозволено лише на main і з іще не наявним version tag, як раніше. В output передається фактичний commit HEAD, тому annotated tag розв'язується до commit.
2. Read-only `validation` викликає той самий `ci.yml` для цього SHA. Проходять locked dependency checks, Ruff/format, blocking type gate, повний pytest, frontend syntax/unit tests і site generators. Немає `secrets: inherit`; signing credentials не передаються validation.
3. Windows job залежить від успішних `source` **і** `validation`, checkout того самого SHA і ще раз перевіряє source перед збиранням. Він робить власний Windows build із попередньою signing configuration, signature check і backend/app/installer smoke. У reusable call передається `skip_windows: true`, щоб ця сама unsigned package-збірка не виконувалася вдруге. У звичайному PR Windows job не пропускається.
4. Перед публікацією й кожним retry перевіряються той самий HEAD, незмінений tracked source і поточний remote tag. Для annotated tag використовується peeled commit. Тег іншого commit і зниклий push tag дають відмову. Лише manual release може створити відсутній тег, з явним `--target RELEASE_SHA`.

Зміна main під час очікування/збирання не змінює вибраного release commit. Failure чи skip спільної validation не запускає Windows publish job: збережено default success gate, без `always()` або `continue-on-error` на validation. Artifacts, signing і release notes зберігають наявний формат.

## Перевірки й межі

`scripts/verify_source.py` приймає лише full lowercase SHA, без branch/tag/short SHA, і запускає Git через argv з явним cwd. Його CLI перевіряється на справжніх тимчасових репозиторіях і local bare origin: інший HEAD, dirty/staged source, lightweight/annotated tags, movement/deletion, manual missing tag. Workflow contract перевіряє dependencies, readonly permissions і передавання одного SHA. Actionlint перевіряє GitHub Actions expressions і reusable-call schema.

Протокол перевіряє source і стан tag у моменти перевірок; GitHub не надає атомарної операції «перевірити ref і опублікувати release», тому захист від одночасної зміни tag також залежить від repository tag protections. Перевірка source не є підписаною provenance для кожного байта installer. Signing, dependency integrity і Windows smoke залишаються окремими необхідними перевірками.

Під час розробки цього виправлення release/tag/publish не запускалися. PR CI перевіряє новий checkout guard і звичайну Windows-збірку; коректність release dependency graph і tag guards перевіряється без публікації. Випуск, як і раніше, запускається наявним tag/manual workflow, коли вибрана версія готова до випуску.
