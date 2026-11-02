"""The fixed KnowNow page format, as a JSON schema for the LLM and as checks
run on every draft before it reaches a reviewer."""
from __future__ import annotations

from urllib.parse import urlsplit

MERMAID_STARTS = (
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram",
    "erDiagram", "mindmap", "timeline", "quadrantChart", "block-beta", "architecture-beta",
)

LIMITS = {
    "summary": 400,
    "overview": 2500,
    "keyConcepts": (4, 10),
    "comparisonRows": (2, 10),
    "whenToUse": (2, 8),
    "pitfalls": (3, 8),
    "quiz": (3, 6),
    "sources": (1, 10),
}

_string = {"type": "string"}

PAGE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "summary", "overview", "diagram", "keyConcepts", "comparison",
        "whenToUse", "pitfalls", "quiz", "sources",
    ],
    "properties": {
        "title": _string,
        "summary": {**_string, "description": "One or two sentences a reader can skim."},
        "overview": {**_string, "description": "3-5 short paragraphs of markdown."},
        "diagram": {
            "type": "object",
            "additionalProperties": False,
            "required": ["caption", "mermaid"],
            "properties": {
                "caption": _string,
                "mermaid": {**_string, "description": "Mermaid source, e.g. starting with 'flowchart LR'."},
            },
        },
        "keyConcepts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["term", "explanation"],
                "properties": {"term": _string, "explanation": _string},
            },
        },
        "comparison": {
            "type": "object",
            "additionalProperties": False,
            "required": ["caption", "columns", "rows"],
            "properties": {
                "caption": _string,
                "columns": {"type": "array", "items": _string},
                "rows": {"type": "array", "items": {"type": "array", "items": _string}},
            },
        },
        "whenToUse": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["option", "useWhen"],
                "properties": {"option": _string, "useWhen": _string},
            },
        },
        "pitfalls": {"type": "array", "items": _string},
        "quiz": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "options", "answerIndex", "explanation"],
                "properties": {
                    "question": _string,
                    "options": {"type": "array", "items": _string},
                    "answerIndex": {"type": "integer"},
                    "explanation": _string,
                },
            },
        },
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "url"],
                "properties": {"title": _string, "url": _string},
            },
        },
    },
}


def _norm_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    # Learn URLs may or may not carry a locale segment (/en-us/)
    segs = [s for s in path.split("/") if s]
    if segs and len(segs[0]) == 5 and segs[0][2] == "-":
        segs = segs[1:]
    return f"{parts.netloc.lower()}/{'/'.join(segs).lower()}"


def _count(errors: list[str], name: str, items: list, bounds: tuple[int, int]) -> None:
    lo, hi = bounds
    if not lo <= len(items) <= hi:
        errors.append(f"{name}: expected {lo}-{hi} items, got {len(items)}")


def validate_page(page: dict, allowed_source_urls: list[str]) -> list[str]:
    """Return a list of problems; an empty list means the draft is acceptable."""
    errors: list[str] = []
    for key in PAGE_SCHEMA["required"]:
        if key not in page:
            errors.append(f"missing field: {key}")
    if errors:
        return errors

    if not page["title"].strip():
        errors.append("title is empty")
    if len(page["summary"]) > LIMITS["summary"]:
        errors.append(f"summary longer than {LIMITS['summary']} characters")
    if not page["overview"].strip():
        errors.append("overview is empty")
    if len(page["overview"]) > LIMITS["overview"]:
        errors.append(f"overview longer than {LIMITS['overview']} characters")

    mermaid = page["diagram"]["mermaid"].strip()
    if not mermaid.startswith(MERMAID_STARTS):
        errors.append("diagram.mermaid must start with a Mermaid diagram type such as 'flowchart'")

    _count(errors, "keyConcepts", page["keyConcepts"], LIMITS["keyConcepts"])
    _count(errors, "whenToUse", page["whenToUse"], LIMITS["whenToUse"])
    _count(errors, "pitfalls", page["pitfalls"], LIMITS["pitfalls"])
    _count(errors, "quiz", page["quiz"], LIMITS["quiz"])
    _count(errors, "sources", page["sources"], LIMITS["sources"])

    table = page["comparison"]
    width = len(table["columns"])
    if width < 2:
        errors.append("comparison needs at least 2 columns")
    _count(errors, "comparison.rows", table["rows"], LIMITS["comparisonRows"])
    for i, row in enumerate(table["rows"]):
        if len(row) != width:
            errors.append(f"comparison row {i + 1} has {len(row)} cells, expected {width}")

    for i, q in enumerate(page["quiz"]):
        if len(q["options"]) != 4:
            errors.append(f"quiz {i + 1}: needs exactly 4 options")
        if not 0 <= q["answerIndex"] < len(q["options"]):
            errors.append(f"quiz {i + 1}: answerIndex out of range")

    allowed = {_norm_url(u) for u in allowed_source_urls if u}
    for src in page["sources"]:
        if _norm_url(src["url"]) not in allowed:
            errors.append(f"source not among fetched pages: {src['url']}")
    return errors
