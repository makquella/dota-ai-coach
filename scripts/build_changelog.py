"""Build site/changelog.html («Что нового») from docs/release-notes/v*.md.

The notes are Russian above the `---` line and a one-paragraph English summary
below it («**In English:** …»). Only the few Markdown forms the notes use are
converted: `## heading`, a bold line as a subheading, `- ` bullets, paragraphs,
**bold**, `code` and bare https links. Everything else is escaped as text.

    python scripts/build_changelog.py          # write the page
    python scripts/build_changelog.py --check  # fail when the page is out of date (CI)
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "docs" / "release-notes"
PAGE = ROOT / "site" / "changelog.html"
RELEASES = "https://github.com/makquella/dota-ai-coach/releases/tag/"


def _version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", path.stem))


def _inline(text: str) -> str:
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"(?<![\w\"/])(https://[^\s<]*[^\s<.,;:)])", r'<a href="\1">\1</a>', out)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)


def markdown(text: str) -> str:
    """The notes' small Markdown subset to HTML."""
    blocks: list[str] = []
    items: list[str] = []
    para: list[str] = []

    def flush() -> None:
        if items:
            blocks.append("<ul>\n" + "\n".join(f"  <li>{i}</li>" for i in items) + "\n</ul>")
            items.clear()
        if para:
            blocks.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("## "):
            flush()  # «Что нового» — the page title says it already
        elif line.startswith("- "):
            if para:
                flush()
            items.append(_inline(line[2:]))
        elif re.fullmatch(r"\*\*[^*]+\*\*", line):
            flush()
            blocks.append(f"<h3>{_inline(line[2:-2])}</h3>")
        elif items:
            items[-1] += " " + _inline(line)  # a bullet continued on the next line
        else:
            para.append(line)
    flush()
    return "\n".join(blocks)


def release(path: Path) -> tuple[str, str, str]:
    """(version, Russian HTML, English HTML) of one notes file."""
    text = path.read_text(encoding="utf-8")
    ru, _, en = text.partition("\n---\n")
    en = re.sub(r"^\s*\*\*In English:\*\*\s*", "", en.strip())
    en = en[:1].upper() + en[1:]
    version = path.stem.lstrip("v")
    return version, markdown(ru), markdown(en) if en else ""


def _section(version: str, body: str, lang: str) -> str:
    title = "Версия" if lang == "ru" else "Version"
    link = "Скачать и подробности" if lang == "ru" else "Download and details"
    return (
        f'<section class="release" id="v{version}">\n'
        f'<h2><a href="#v{version}">{title} {version}</a></h2>\n'
        f"{body}\n"
        f'<p class="release-link"><a href="{RELEASES}v{version}" rel="noopener">{link}</a></p>\n'
        "</section>"
    )


def build() -> str:
    files = sorted(NOTES.glob("v*.md"), key=_version_key, reverse=True)
    releases = [release(path) for path in files]
    ru = "\n".join(_section(v, body, "ru") for v, body, _ in releases)
    en = "\n".join(_section(v, body, "en") for v, _, body in releases if body)
    template = (ROOT / "scripts" / "changelog.template.html").read_text(encoding="utf-8")
    return template.replace("<!-- RU -->", ru).replace("<!-- EN -->", en)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when the page is stale")
    args = parser.parse_args()
    page = build()
    if args.check:
        current = PAGE.read_text(encoding="utf-8") if PAGE.exists() else ""
        if current != page:
            print("site/changelog.html is out of date: run python scripts/build_changelog.py")
            return 1
        print("site/changelog.html is up to date")
        return 0
    PAGE.write_text(page, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
