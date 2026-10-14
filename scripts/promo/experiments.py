"""Manual Ukrainian male voice comparisons, delivered only to the owner's chat."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import random
import urllib.parse
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from . import send, voice

CATALOG_API = "https://api.elevenlabs.io"
TELEGRAM_API = "https://api.telegram.org"
VARIANTS = {
    "A": (0, 0.5, 1.0, "природна подача"),
    "B": (0, 0.0, 1.04, "енергійна подача"),
    "C": (1, 0.5, 1.0, "другий голос"),
    "D": (2, 0.5, 1.0, "третій голос"),
}


def _api(path: str, *, body: dict[str, Any] | None = None) -> Any:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY is required for voice experiments")
    return voice.api_request(
        CATALOG_API + path, body, key, method="GET" if body is None else "POST"
    )


def modern_model(models: list[dict[str, Any]]) -> str:
    usable = {m["model_id"] for m in models if m.get("can_do_text_to_speech")}
    for name in ("eleven_v4", "eleven_v3"):
        if name in usable:
            return name
    raise SystemExit("The account has neither eleven_v4 nor eleven_v3 TTS; no legacy fallback")


def native_male(row: dict[str, Any]) -> bool:
    labels = row.get("labels") or {}
    gender = str(row.get("gender") or labels.get("gender") or "").lower()
    language = str(row.get("language") or labels.get("language") or row.get("locale") or "").lower()
    # Multilingual capability alone does not make an English voice Ukrainian.
    return gender == "male" and language in {"uk", "uk-ua", "ukrainian", "українська"}


def descriptor(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "voice_id": row["voice_id"],
        "name": row.get("name") or row["voice_id"],
        "language": "uk",
        "gender": "male",
        "public_owner_id": row.get("public_owner_id") or row.get("public_user_id"),
    }


def catalog() -> dict[str, Any]:
    models = _api("/v1/models")
    model = modern_model(models)
    owned = _api("/v2/voices?page_size=100")
    rows = [r for r in owned.get("voices", []) if native_male(r)]
    if len(rows) < 3:
        for language in ("uk", "ukrainian"):
            query = urllib.parse.urlencode(
                {"language": language, "gender": "male", "page_size": 50}
            )
            shared = _api("/v1/shared-voices?" + query)
            rows.extend(r for r in shared.get("voices", []) if native_male(r))
            if len({r["voice_id"] for r in rows}) >= 3:
                break
    unique = {r["voice_id"]: descriptor(r) for r in rows}
    voices = sorted(unique.values(), key=lambda r: (r["name"].casefold(), r["voice_id"]))
    result = {
        "model": model,
        "v4_available": model == "eleven_v4",
        "model_ids": [m["model_id"] for m in models],
        "voices": voices,
    }
    print(f"Models verified: {model}; native Ukrainian male candidates: {len(voices)}")
    return result


def ensure_voice(selected: dict[str, Any]) -> None:
    """Import a public library voice when it is not already in the account."""
    owned = _api("/v2/voices?page_size=100")
    if any(row["voice_id"] == selected["voice_id"] for row in owned.get("voices", [])):
        return
    owner = selected.get("public_owner_id")
    if not owner:
        raise SystemExit(f"Voice {selected['name']} is unavailable in this account")
    _api(
        f"/v1/voices/add/{urllib.parse.quote(owner, safe='')}/{selected['voice_id']}",
        body={"new_name": selected["name"]},
    )


def preview_caption(profile: dict[str, Any], seconds: float) -> str:
    return (
        f"<b>Порівняння голосів · {profile['variant']}/4</b>\n"
        f"{html.escape(profile['name'])} · {html.escape(profile['delivery'])}\n"
        f"{profile['model']} · українська · чоловічий голос\n"
        f"stability {profile['stability']} · speed {profile['speed']} · {seconds:.1f} с\n"
        "Один сценарій про Phantom Lancer. Напиши, яка літера звучить краще."
    )


def send_preview(folder: Path, item: dict[str, Any], profile: dict[str, Any]) -> int:
    # A comparison is not a publishing-queue entry. No R2 upload or publishing
    # callbacks: the ordinary scheduled approval flow is unchanged.
    bot, chat = send._env("TELEGRAM_BOT_TOKEN"), send._env("TELEGRAM_CHAT_ID")
    fields = {
        "chat_id": chat,
        "caption": preview_caption(profile, item["seconds"]),
        "parse_mode": "HTML",
        "supports_streaming": "true",
        "width": "1080",
        "height": "1920",
        "duration": str(round(item["seconds"])),
    }
    body, kind = send.multipart(
        fields,
        {
            "video": (
                f"wardly-voice-{profile['variant']}.mp4",
                "video/mp4",
                (folder / "video.mp4").read_bytes(),
            )
        },
    )
    sent = send._request(
        f"{TELEGRAM_API}/bot{bot}/sendVideo",
        data=body,
        method="POST",
        headers={"Content-Type": kind},
    )
    message = int(sent["result"]["message_id"])
    print(f"Voice {profile['variant']} delivered to approval chat (message {message})")
    return message


def build(
    out: Path, variant: str, today: date, selected_catalog: dict[str, Any], *, deliver: bool
) -> dict[str, Any]:
    from . import draft_demo, package, script

    index, stability, speed, delivery = VARIANTS[variant]
    candidates = selected_catalog["voices"]
    if len(candidates) < 3:
        raise SystemExit(f"Need three native Ukrainian male voices; found {len(candidates)}")
    selected = candidates[index]
    ensure_voice(selected)
    profile = {
        **selected,
        "variant": variant,
        "delivery": delivery,
        "model": selected_catalog["model"],
        "stability": stability,
        "speed": speed,
        "continuous": True,
    }
    os.environ.update(
        {
            "ELEVENLABS_MODEL": profile["model"],
            "ELEVENLABS_VOICE_ID": profile["voice_id"],
            "ELEVENLABS_LANGUAGE": "uk",
            "ELEVENLABS_STABILITY": str(stability),
            "ELEVENLABS_SPEED": str(speed),
            "ELEVENLABS_CONTINUOUS": "true",
        }
    )
    found = draft_demo.card("Phantom Lancer")
    if found is None:
        raise SystemExit("Phantom Lancer has no verified draft card")
    item = script.draft(found, random.Random(1), package.backend_version())
    result = package.make(out, today, "draft", True, False, item=item)
    result["voice_config"] = profile
    result["id"] = hashlib.sha256(
        (result["id"] + json.dumps(profile, sort_keys=True)).encode()
    ).hexdigest()[:16]
    if not result["quality"]["ok"]:
        raise SystemExit("Preview failed quality: " + "; ".join(result["quality"]["errors"]))
    (out / "package.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if deliver:
        result["telegram_message_id"] = send_preview(out, result, profile)
        (out / "delivery.json").write_text(
            json.dumps({"variant": variant, "message_id": result["telegram_message_id"]}),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=["catalog", *VARIANTS], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(UTC).date())
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    selected_catalog = json.loads(args.catalog.read_text()) if args.catalog else catalog()
    (args.out / "voice-catalog.json").write_text(
        json.dumps(selected_catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.variant != "catalog":
        build(args.out.resolve(), args.variant, args.date, selected_catalog, deliver=args.send)


if __name__ == "__main__":
    main()
