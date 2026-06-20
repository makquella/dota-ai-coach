"""
rag.py — keyword-based retrieval from local Markdown knowledge base.

Scoring weights:
  - base:       token overlap with the full query
  - hero bonus: +5 if the paragraph mentions the current hero (strong signal)
  - gs bonus:   +2 if the paragraph mentions game_state keywords (medium signal)
  - penalty:    -3 if the paragraph mentions a different hero (noise reduction)
"""

from pathlib import Path
from app.config import KNOWLEDGE_BASE_DIR, RAG_TOP_K

# Heroes tracked in the knowledge base (lowercase, space-separated)
_KNOWN_HEROES = {"anti-mage", "juggernaut", "luna"}


def _normalise_item_name(item: str) -> str:
    return " ".join(item.lower().split())


def _paragraph_contradicts_owned_items(paragraph: str, owned_items: list[str]) -> bool:
    """Skip context that says the hero is still before an item the request already owns."""
    paragraph_lower = " ".join(paragraph.lower().split())
    owned_item_names = {_normalise_item_name(item) for item in owned_items}

    for item in owned_item_names:
        if not item:
            continue
        if f"before {item}" in paragraph_lower or f"until {item}" in paragraph_lower:
            return True
        if item in paragraph_lower and "until your spike" in paragraph_lower:
            return True
    return False


def _load_paragraphs(kb_dir: Path) -> list[str]:
    """Read all .md files and split into non-empty paragraphs."""
    paragraphs: list[str] = []
    for md_file in sorted(kb_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        for para in text.split("\n\n"):
            stripped = para.strip()
            if stripped:
                paragraphs.append(stripped)
    return paragraphs


def _score(
    paragraph: str,
    query_tokens: set[str],
    hero_words: set[str],
    gs_words: set[str],
) -> float:
    """Score a paragraph against the query with hero/game_state bonuses."""
    para_lower = paragraph.lower()
    para_tokens = set(para_lower.split())

    base = len(query_tokens & para_tokens)

    # Strong bonus for paragraphs that mention the current hero
    hero_bonus = 5 if hero_words & para_tokens else 0

    # Medium bonus for paragraphs that mention game_state keywords
    gs_bonus = 2 if gs_words & para_tokens else 0

    # Penalty if paragraph is about a *different* known hero
    other_heroes = _KNOWN_HEROES - hero_words
    penalty = -3 if any(h in para_lower for h in other_heroes) else 0

    return base + hero_bonus + gs_bonus + penalty


def retrieve_context(
    query: str,
    hero: str = "",
    game_state: str = "",
    owned_items: list[str] | None = None,
    top_k: int = RAG_TOP_K,
) -> list[str]:
    """
    Return the top_k most relevant paragraphs from the knowledge base.

    hero and game_state are used to adjust scores beyond plain token overlap.
    """
    paragraphs = _load_paragraphs(KNOWLEDGE_BASE_DIR)
    owned_items = owned_items or []
    paragraphs = [
        para for para in paragraphs
        if not _paragraph_contradicts_owned_items(para, owned_items)
    ]
    if not paragraphs:
        return []

    query_tokens = set(query.lower().split())
    hero_words = set(hero.lower().split())
    # Split game_state on underscores too (e.g. "enemy_pressure_mid" → {"enemy","pressure","mid"})
    gs_words = set(game_state.lower().replace("_", " ").split())

    scored = [
        (para, _score(para, query_tokens, hero_words, gs_words))
        for para in paragraphs
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    # Only keep paragraphs with a positive final score
    top = [para for para, score in scored[:top_k] if score > 0]
    return top
