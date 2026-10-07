# Проверка commit перед выпуском

F15 в 0.53.10 делает текущий CI reusable: `ci.yml` принимает обязательный `source_sha` при `workflow_call`. Обычные push/PR проверки сохраняют прежние job names и запускают Windows packaging. Каждая checkout использует полный SHA, и `verify_source.py` подтверждает HEAD и отсутствие изменений tracked source. Для PR это GitHub test-merge SHA; для push — SHA события.

## Release workflow

1. Read-only `source` job берёт snapshot SHA события, читает version и проверяет соответствие tag. Manual release разрешён только на main и с ещё несуществующим version tag, как раньше. В output передаётся фактический commit HEAD, поэтому annotated tag разрешается до commit.
2. Read-only `validation` вызывает тот же `ci.yml` для этого SHA. Проходят locked dependency checks, Ruff/format, blocking type gate, полный pytest, frontend syntax/unit tests и site generators. Нет `secrets: inherit`; signing credentials не передаются validation.
3. Windows job зависит от успешных `source` **и** `validation`, checkout того же SHA и ещё раз проверяет source перед сборкой. Он делает собственный Windows build с прежней signing configuration, signature check и backend/app/installer smoke. В reusable call передаётся `skip_windows: true`, чтобы эта же unsigned package-сборка не выполнялась второй раз. В обычном PR Windows job не пропускается.
4. Перед публикацией и каждой retry проверяется тот же HEAD, неизменённый tracked source и текущий remote tag. Для annotated tag используется peeled commit. Тег другого commit и исчезнувший push tag дают отказ. Только manual release может создать отсутствующий тег, с явным `--target RELEASE_SHA`.

Изменение main за время ожидания/сборки не меняет выбранный release commit. Failure или skip общей validation не запускает Windows publish job: сохранён default success gate, без `always()` или `continue-on-error` на validation. Artifacts, signing и release notes сохраняют существующий формат.

## Проверки и границы

`scripts/verify_source.py` принимает только full lowercase SHA, без branch/tag/short SHA, и запускает Git через argv с явным cwd. Его CLI проверяется на настоящих временных репозиториях и local bare origin: другой HEAD, dirty/staged source, lightweight/annotated tags, movement/deletion, manual missing tag. Workflow contract проверяет dependencies, readonly permissions и передачу одного SHA. Actionlint проверяет GitHub Actions expressions и reusable-call schema.

Протокол проверяет source и состояние tag в моменты проверок; GitHub не предоставляет атомарную операцию «проверить ref и опубликовать release», поэтому защита от одновременного изменения tag также зависит от repository tag protections. Проверка source не является подписанной provenance для каждого байта installer. Signing, dependency integrity и Windows smoke остаются отдельными необходимыми проверками.

При разработке этого исправления release/tag/publish не запускались. PR CI проверяет новый checkout guard и обычную Windows-сборку; корректность release dependency graph и tag guards проверяется без публикации. Выпуск по-прежнему запускается существующим tag/manual workflow, когда выбранная версия готова к выпуску.
