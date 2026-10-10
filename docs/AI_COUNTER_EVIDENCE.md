# Перевірка лічильників в AI-розборі

F04, перший slice у 0.53.13. Раніше число могло бути дозволене з будь-якого поля JSON: 160 last hits дозволяли «160 kills», а числа 0–12 завжди проходили перевірку. Тепер кількісні твердження про kills/deaths/assists гравця прив'язано до власних підсумкових лічильників в `analysis.headline`.

## Дані й межа

`coach_evidence.py` будує `CounterEvidence` для трьох невід'ємних integer totals. Bool, відсутній/невалідний лічильник не перетворюються на нуль. Compact match facts містять `match_totals` і refs `{source: analysis.headline, field, observed_at: null, precision: reported_total, value}`. Джерело вказує на детермінований розбір, а не приписує окремому upstream-постачальнику точність, якої merged analysis не зберігає. Час фактичного спостереження в headline невідомий: `observed_at` залишається null, не видається за timestamp кінця матчу.

`FactChecker` перевіряє UK/EN числові noun phrases «200 вбивств», «kills: 200», «смерті: їх було 2» і K/D/A triples за конкретними полями. Значення nested scoreboard, lane, findings, last hits чи інших метрик не дозволяють total гравця. Хибне речення видаляється; порожня/надто пошкоджена відповідь отримує звичайний один retry, потім `unverified`. Модель не вибирає значення evidence: metadata формує backend після перевірки.

Ці refs підтверджують reported match totals. Числові combat assertions з іншим named hero, time/minute/lane/rate scope відхиляються консервативно: підсумковий лічильник не доводить такого твердження. Це може прибрати коректне формулювання, доки не з'явиться ledger з окремими subject/time slices. Prompt описує цю межу.

`next_game`, `plan` і block `fix` залишаються goal slots: майбутня ціль «не більше 2 смертей» не мусить збігатися з минулим total. Там зберігається попередня загальна перевірка numbers/times/names. У вільних match Q&A quantified combat statements проходять сувору перевірку; числові майбутні цілі слід залишати в goal slots, Q&A може дати якісну пораду.

## Cache і UI

`COACH_VERSION` підвищено з 1 до 2. Нові cache entries записують verification version. Legacy match review не показується при pending, error, waiting чи AI off; stored copy зберігається до звичайної регенерації. Сучасний stale review зберігає попередню поведінку, коли надходять нові дані, і позначається stale. Career verification policy не змінено.

Збережені match questions проходять перевірку речення за реченням під час читання без provider call: відповідь із хибним реченням повертається з очищеним текстом, повністю неперевірювана відповідь не показується. Вихідний cache під час читання не видаляється. Нові відповіді зберігають refs; повернений view отримує refs поточного розбору. Під час наступного ask нова історія збирається з перевіреного view.

У match review та answers елемент, що розгортається, «Дані для перевірки K/D/A» показує totals і межу їхньої точності обома мовами. Він використовує DOM/textContent, підтримує legacy відсутність metadata й відкидає malformed rows. Public share payload лишається попереднім field-by-field: refs, запитання та source internals не публікуються.

## Перевірки й наступний slice

`test_coach_evidence.py`: metric swap за дозволеного числа, small-count bypass, comma punctuation, UK/EN, K/D/A reorder, unknown vs zero, unsupported subjects/scopes, real HTTP/SQLite generation/retry/history, legacy cache upgrade/offline view. Scripted provider є зовнішнім fixture; внутрішні checker/service/storage працюють реально. Новий evidence module проходить strict mypy й оголошений clean у blocking baseline; старі 226 errors не розширено.

Electron smoke створює справжній disclosure DOM із bundled renderer script, відкриває його обома мовами й перевіряє zero, malformed values/source і legacy відсутність refs. Загальний source/Windows smoke перевіряє застосунок, preload та IPC.

## GPM/XPM у 0.53.26

`MatchRateBindings` окремо перевіряє match-wide GPM і XPM гравця.
`match_rates` і `match_rates_evidence` формуються лише з `analysis.headline`;
порожній ledger зберігається в compact facts. Rate evidence має той самий source,
своє field, `observed_at: null`, `precision: reported_match_rate` і вихідне
число. Підтримуються finite nonnegative integer/float до JS safe-integer
межі; bool, рядки й відсутні значення залишаються unknown. Нуль залишається
вимірюванням. Quantified noun phrases GPM/XPM, gold/experience per minute і
«золота/досвіду за хвилину» мають точно збігатися зі своїм полем, зокрема дробова
частина. Округлена, інша чи nested метрика не підтверджує такого твердження.

Назви одиниць «per minute» / «за хвилину» не вважаються часовим відрізком.
Інші time/lane/team/hero scopes потребують окремого evidence й відхиляються.
Future goal slots зберігають попередню загальну перевірку. Модель не формує refs:
після deterministic перевірки backend додає `rate_evidence` до review/answer;
UI disclosure показує лише validated rows обома мовами, зокрема zero й decimal.
Combat-only legacy disclosure зберігає попередній текст.

`COACH_VERSION` тепер 3. Match review з verification version 2 приховується до
звичайної регенерації, зокрема offline/AI-off view; вихідний cache зберігається.
Policy version бере участь у загальному digest і може спричинити звичайне оновлення
career cache, але career field binding тут не додано. Saved Q&A під час читання
перевіряється наново речення за реченням без provider call і без видалення збереженого;
returned refs відповідають поточному розбору. Share payload, як і раніше, не
публікує запитань чи внутрішнього evidence.

Нові functional checks використовують справжні HTTP, SQLite, generation/retry і
cache upgrade із зовнішнім scripted provider. Parser checks покривають metric swap,
small-number bypass, unsupported subject/time scope, UK/EN units і decimal,
unknown/zero/invalid rate. Source/Windows Electron smoke відкриває справжній
disclosure DOM двома мовами, перевіряє combined/legacy UI та malformed rates.

Це обмежений детермінований parser, не повна семантична перевірка AI. Spelled-out counts, довільні дієслівні/coreference конструкції та суперечності без підтримуваної числової noun phrase тут не доводяться. Farm/item/findings refs, часові claims, інші метрики й career ще потребують власних bindings. F04 залишається відкритим до наступних slices; немає твердження, що кожне AI-твердження тепер доведено.

## Match farm totals in 0.53.31

`MatchFarmBindings` checks last hits/LH and denies/DN against their own
`analysis.headline` fields. `match_farm` and `match_farm_evidence` preserve an
explicit empty ledger when unknown; root fields use the same validated values.
Only nonnegative integer totals through JS MAX_SAFE_INTEGER are evidence. Bool,
strings, fractional values and missing/invalid counters stay unknown; zero is
known. Refs have `precision: reported_total` and `observed_at: null`.

Supported UK/EN numeric noun phrases include last hits, LH, denies/DN,
добивання/добиті кріпи and денаї. Each count must match its own total exactly.
Nested lane/team values cannot license a match total. Removing the metric
name "last hits" before scope checks avoids treating "last" in the name as a
time slice. At exactly 10:00, a separate `match_farm_at_10` ledger licenses
player samples and a narrowly parsed numeric comparison against its named
opponent; each count is checked against its own subject/field. A valid, unique
minute-10 `analysis.lane.points` sample takes priority. Without a lane sample,
LH alone may use `analysis.peers.me` / `analysis.peers.peers[0].metrics` for the
same-role enemy comparison; this does not invent a physical lane or DN sample.
Integral float peer counts are retained exactly as integers. Duplicate/invalid
sample times stay unknown. Total/10-minute and player/opponent swaps are
rejected. Supported comparison forms include “36 last hits versus 65 for
Anti-Mage at 10:00” and the Ukrainian equivalents already used in review text.
Other timestamps, lane-exclusive counts, last-N-minutes, unnamed/different
subjects, standalone enemy claims and per-minute scopes remain rejected.
Future goal slots keep the existing generic number policy. This small parser
does not prove spelled-out counts, arbitrary verbs/coreference, item/build or
finding causes, other time slices or career claims. F04 stays partial.

Backend adds `farm_evidence` and `farm_slice_evidence` after checking, including
stored Q&A. Sample refs carry their actual source, player/opponent subject,
hero, `observed_at: 600` (game-relative seconds, not a wall-clock timestamp) and
`precision: reported_sample`. UI labels these samples separately at 10:00;
samples do not prove event causes or why a lane was lost. Reads scrub
old answers without provider calls or deleting their stored copy. COACH_VERSION
is 4: v3 match reviews are hidden through pending/offline/AI-off states until
normal regeneration; storage is retained. The shared digest also invalidates
career cache normally, without changing its verification policy. Analysis/trim
versions and live behavior are unchanged. Share payload keeps excluding refs
and questions. UK/EN disclosure validates field/source/precision/value and uses
textContent; older combat-only and rate-only disclosures retain their copy.

Functional tests exercise real HTTP/service/SQLite review generation, question
retry/rejection, future goals and offline cache upgrades with external scripted
providers. Parser cases include metric swaps, small numbers, unsupported scope,
UK/EN labels, unknown/zero, total/sample/subject/field swaps and invalid values.
Source/Windows Electron smoke opens actual farm/sample/combined disclosure DOM and rejects malformed rows in both
languages. No live or paid AI calls are made.

## Safe sample compaction in 0.53.35

Malformed NaN/Infinity in a minute-10 sample previously reached `_prune` through
raw `match_farm_at_10` and legacy lane/peer fields, even though evidence validation
rejected it. `farm_slice_facts` now rebuilds the ledger only from validated refs;
legacy lane counters and peer LH-at-10 metrics use the same bounded measurements.
Unknown inputs cannot crash this farm preparation or reappear in the number
inventory. Integral peer floats remain exact counts; fractional/nonfinite values,
strings, bool and out-of-range counters remain unknown. Zero, source, subject
and time survive compaction and reconstruct the same refs. Duplicate samples
still cannot fall back to peer evidence accidentally. Other metric types and
malformed whole analysis structures remain separate boundaries.

Eighteen deterministic compaction scenarios exercise lane/peer invalid inputs
(including the reproduced exceptions), strict JSON serialization, legacy-field
absence, unknown-vs-zero and evidence roundtrip. Existing real HTTP/SQLite
review/question/cache tests continue. COACH_VERSION stays 4: verification policy
is unchanged; changed compact facts naturally change their digest. Analysis/trim
versions and live behavior stay the same.

## First three finding groups in 0.53.38

Vision, LH10 and early-death findings now have source measurements and recording
coverage, plus semantic checks and UK/EN disclosure. See [FINDING_EVIDENCE.md](FINDING_EVIDENCE.md).
ANALYSIS_VERSION is 21 and COACH_VERSION is 5; the older version descriptions above
record their original patch behavior. F04's first-three-findings acceptance is
prepared. This does not claim arbitrary prose, causality or career verification.
