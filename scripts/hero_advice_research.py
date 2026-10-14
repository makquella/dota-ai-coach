"""Validate and render source-backed hero advice research; never run live rules.

Usage: python scripts/hero_advice_research.py validate
       python scripts/hero_advice_research.py render [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hero_advice_research"
DOCS = ROOT / "docs" / "hero-advice"
READINESS = {"existing", "raw_extension", "new_observation", "manual_or_replay"}
READINESS_ORDER = {
    name: i
    for i, name in enumerate(("existing", "raw_extension", "new_observation", "manual_or_replay"))
}
PHASES = {"lane", "farm", "pressure", "fight", "reset"}


def digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe source path: {relative}")
    return root / path


def field(payload: Any, path: str) -> Any:
    for part in path.split("/"):
        payload = payload[int(part)] if isinstance(payload, list) else payload[part]
    return payload


def validate(root: Path) -> list[dict[str, Any]]:
    manifest = read(root / "manifest.json")
    signals = read(root / "signals.json")
    patch = read(root / "sources" / "patch.json")
    if patch["patch_number"] != manifest["patch"]:
        raise ValueError("patch mismatch")
    catalogs: list[dict[str, Any]] = []
    all_ids: set[str] = set()
    for key in manifest["heroes"]:
        item = read(root / "catalogs" / f"{key}.json")
        hero = item["hero"]
        snapshot = read(source_path(root, item["source"]))
        if digest(snapshot["hero"]) != snapshot["snapshot_sha256"]:
            raise ValueError(f"{key}: source checksum mismatch")
        if (
            hero["key"] != key
            or snapshot["hero"]["key"] != key
            or hero["id"] != snapshot["hero"]["id"]
            or snapshot["patch"] != manifest["patch"]
        ):
            raise ValueError(f"{key}: hero or patch mismatch")
        facts: dict[str, Any] = {}
        for fact in item["mechanics"]:
            fact_id = fact["id"]
            if fact_id in facts:
                raise ValueError(f"{key}: duplicate fact {fact_id}")
            actual = field(snapshot["hero"], fact["field"])
            if "equals" in fact and actual != fact["equals"]:
                raise ValueError(f"{key}: fact {fact_id} differs from source")
            if "contains" in fact and fact["contains"] not in str(actual):
                raise ValueError(f"{key}: fact {fact_id} quotation missing")
            if "equals" not in fact and not fact.get("contains"):
                raise ValueError(f"{key}: fact {fact_id} has no verifiable claim")
            facts[fact_id] = fact
        phases = set()
        for advice in item["advice"]:
            aid = advice["id"]
            if aid in all_ids:
                raise ValueError(f"duplicate advice {aid}")
            all_ids.add(aid)
            if advice["phase"] not in PHASES or advice["readiness"] not in READINESS:
                raise ValueError(f"{aid}: invalid phase/readiness")
            phases.add(advice["phase"])
            for required in (
                "title",
                "benefit",
                "trigger",
                "conditions",
                "suppress_if",
                "cancel_if",
                "timing",
                "repeat",
                "cost",
                "requires",
                "evidence",
                "scenarios",
            ):
                if not advice.get(required):
                    raise ValueError(f"{aid}: missing {required}")
            if any(e not in facts for e in advice["evidence"]):
                raise ValueError(f"{aid}: unknown evidence")
            for signal in advice["requires"]:
                if signal not in signals:
                    raise ValueError(f"{aid}: unknown signal {signal}")
                if (
                    READINESS_ORDER[signals[signal]["status"]]
                    > READINESS_ORDER[advice["readiness"]]
                ):
                    raise ValueError(f"{aid}: live readiness overclaims {signal}")
            for text_type in ("action", "reason"):
                if set(advice[text_type]) != {"uk", "en"} or not all(advice[text_type].values()):
                    raise ValueError(f"{aid}: missing translation")
                limit = 100 if text_type == "action" else 180
                if any(len(text) > limit for text in advice[text_type].values()):
                    raise ValueError(f"{aid}: {text_type} exceeds overlay limit")
            if set(advice["scenarios"]) != {"positive", "negative", "unknown"}:
                raise ValueError(f"{aid}: missing counterexample")
            if not all(advice["scenarios"].values()) or advice["level"] not in {
                "practical",
                "advanced",
            }:
                raise ValueError(f"{aid}: empty scenario or invalid audience level")
            if advice.get("status") != "research_candidate":
                raise ValueError(f"{aid}: research must not claim release approval")
        if phases != PHASES:
            raise ValueError(f"{key}: missing game phase {PHASES - phases}")
        if not item.get("open_checks") or not item.get("first_implementation"):
            raise ValueError(f"{key}: no explicit verification/implementation plan")
        catalogs.append(item)
    return catalogs


def render_hero(item: dict[str, Any], root: Path) -> str:
    snapshot = read(source_path(root, item["source"]))
    hero = item["hero"]
    lines = [
        f"# {hero['name']}: игровые приёмы и live-подсказки",
        "",
        f"Патч источника: **{snapshot['patch']}**. Дата сбора: {snapshot['retrieved_at'][:10]}.",
        f"Роли исследования: {', '.join(hero['roles'])}. Целевая аудитория: 0–4к MMR.",
        "",
        "Статус: завершённый кабинетный анализ и каталог кандидатов. Механические",
        "утверждения проверяются по снимку Valve; игровые условия требуют описанных",
        "ниже проверок. Эти кандидаты ещё не включены в приложение. Контрпримеры",
        "спроектированы для будущей проверки и не выдаются за просмотренные реплеи.",
        "",
        f"Источник: [Valve hero data]({snapshot['url']}); [патч]({snapshot['patch_url']}).",
        "",
        "## Как герой получает преимущество",
        "",
        item["identity"],
        "",
        "## Проверенные механические основания",
        "",
    ]
    for fact in item["mechanics"]:
        lines.append(f"- **{fact['id']}** — {fact['statement']} (`{fact['field']}`).")
    lines += ["", "## Каталог возможных подсказок", ""]
    for advice in item["advice"]:
        lines += [
            f"### {advice['id']} — {advice['title']}",
            "",
            f"Фаза: {advice['phase']}; сложность: {advice['level']}; данные: {advice['readiness']}.",
            "",
            f"- **Польза:** {advice['benefit']}",
            f"- **Когда рассматривать:** {advice['trigger']}",
            f"- **Условия:** {'; '.join(advice['conditions'])}.",
            f"- **Цена:** {advice['cost']}",
            f"- **Не показывать:** {'; '.join(advice['suppress_if'])}.",
            f"- **Отменить:** {'; '.join(advice['cancel_if'])}.",
            f"- **Момент:** {advice['timing']} **Повтор:** {advice['repeat']}",
            f"- **Сигналы:** {', '.join(advice['requires'])}. Основания: {', '.join(advice['evidence'])}.",
            "",
            f"> {advice['action']['uk']}",
            f"> {advice['reason']['uk']}",
            "",
            f"EN: {advice['action']['en']} — {advice['reason']['en']}",
            "",
            f"- Полезный показ: {advice['scenarios']['positive']}",
            f"- Контрпример: {advice['scenarios']['negative']}",
            f"- Неизвестные данные: {advice['scenarios']['unknown']}",
            "",
        ]
    lines += ["## Что проверить до реализации", ""]
    lines.extend(f"- {check}" for check in item["open_checks"])
    lines += ["", "## Первая очередь реализации", ""]
    lines.extend(f"- {step}" for step in item["first_implementation"])
    return "\n".join(lines) + "\n"


def render(root: Path, docs: Path, *, check: bool) -> list[str]:
    catalogs = validate(root)
    signals = read(root / "signals.json")
    manifest = read(root / "manifest.json")
    outputs = {f"{c['hero']['key']}.md": render_hero(c, root) for c in catalogs}
    lines = [
        "# Исследование игровых подсказок: первая пятёрка",
        "",
        f"Источники Valve собраны {manifest['date']}; последний патч списка — {manifest['patch']}.",
        "",
        "Каталоги охватывают линию, фарм, давление, бой и восстановление. Билды исключены.",
        "Проверка ниже подтверждает целостность источников, ссылок, переводов и условий",
        "каталога; она не заменяет игровую проверку в лобби и на записях.",
        "",
        "| Герой | Кандидаты | Механические основания |",
        "|---|---:|---:|",
    ]
    for c in catalogs:
        lines.append(
            f"| [{c['hero']['name']}]({c['hero']['key']}.md) | {len(c['advice'])} | {len(c['mechanics'])} |"
        )
    lines += ["", "## Сигналы и работа с неизвестными данными", ""]
    for key, value in signals.items():
        lines.append(f"- **{key}** ({value['status']}): {value['description']}")
    lines += [
        "",
        "`existing` означает наличие источника при корректном текущем payload, а не",
        "безусловную доступность на каждом tick. `raw_extension` — поле есть в реальном",
        "семпле, но нужно сохранить и проверить в контракте. `new_observation` — нужны",
        "новые наблюдения/трекер. `manual_or_replay` — точная команда заблокирована до",
        "подтверждённого источника; послеигровая информация не используется как live-факт.",
        "",
        "## Воспроизводимость",
        "",
        "```bash",
        "python scripts/hero_advice_research.py validate",
        "python scripts/hero_advice_research.py render --check",
        "```",
        "",
        "Тексты карточек подготовлены на украинском и английском. Каталоги — данные",
        "исследования, которые live-пайплайн не загружает. Источники привязаны к патчу",
        "и контрольной сумме; числовые утверждения и цитаты сверяются автоматически.",
        "Пустой список facets в этих снимках не разрешает придумывать модификаторы.",
        "",
        "Подробный порядок реализации и границы сделанной проверки — [IMPLEMENTATION.md](IMPLEMENTATION.md).",
    ]
    outputs["README.md"] = "\n".join(lines) + "\n"
    changed = []
    for name, body in outputs.items():
        path = docs / name
        if not path.exists() or path.read_text(encoding="utf-8") != body:
            changed.append(name)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--docs", type=Path, default=DOCS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        catalogs = validate(args.data)
        if args.command == "render":
            changed = render(args.data, args.docs, check=args.check)
            if args.check and changed:
                raise ValueError(f"stale research docs: {', '.join(changed)}")
        print(
            f"{len(catalogs)} heroes, {sum(len(c['advice']) for c in catalogs)} candidates, "
            f"{sum(len(c['mechanics']) for c in catalogs)} source-backed facts: valid"
        )
    except (ValueError, KeyError, IndexError, TypeError, OSError) as exc:
        print(f"research check failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
