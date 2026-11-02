"""Generate one draft page: search Learn, fetch pages, draft with the LLM,
check the draft, and save it for review."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Protocol

from .catalog import Target
from .drafting import PROMPT_VERSION, SourceDoc, build_messages, draft_page
from .learn_mcp import SearchHit

log = logging.getLogger(__name__)

MAX_PAGES_FETCHED = 3
MAX_CHARS_PER_SOURCE = 12000
MAX_ATTEMPTS = 2


class DocsSource(Protocol):
    def search(self, query: str) -> list[SearchHit]: ...
    def fetch(self, url: str) -> str: ...


def pick_urls(hits: list[SearchHit], limit: int = MAX_PAGES_FETCHED) -> list[SearchHit]:
    """Distinct pages in search order, Microsoft Learn only."""
    seen: set[str] = set()
    picked: list[SearchHit] = []
    for hit in hits:
        base = hit.url.split("#")[0]
        if not base.startswith("https://learn.microsoft.com/") or base in seen:
            continue
        seen.add(base)
        picked.append(SearchHit(title=hit.title, url=base, content=hit.content))
        if len(picked) == limit:
            break
    return picked


def collect_sources(docs: DocsSource, target: Target) -> list[SourceDoc]:
    hits = docs.search(target.query)
    sources: list[SourceDoc] = []
    for hit in pick_urls(hits):
        try:
            text = docs.fetch(hit.url)
        except Exception as exc:  # fall back to the search excerpt
            log.warning("Fetch failed for %s: %s", hit.url, exc)
            text = hit.content
        if text:
            sources.append(SourceDoc(title=hit.title or hit.url, url=hit.url, text=text[:MAX_CHARS_PER_SOURCE]))
    return sources


def generate_draft(
    target: Target,
    docs: DocsSource,
    chat: Callable[[list[dict]], str],
    validate: Callable[[dict, list[str]], list[str]],
    model_label: str,
) -> dict:
    """Return a page document ready to save as a draft. Raises if no sources."""
    sources = collect_sources(docs, target)
    if not sources:
        raise RuntimeError(f"No Microsoft Learn sources found for '{target.query}'")
    urls = [s.url for s in sources]

    feedback: list[str] | None = None
    page: dict = {}
    errors: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        page = draft_page(chat, build_messages(target, sources, feedback))
        errors = validate(page, urls)
        if not errors:
            break
        log.info("Draft %s attempt %d failed checks: %s", target.page_id, attempt, errors)
        feedback = errors

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"{target.page_id}--draft",
        "pageId": target.page_id,
        "topicId": target.topic_id,
        "subtopicId": target.subtopic_id,
        "areaId": target.area_id,
        "areaName": target.area_name,
        "status": "draft",
        "content": page,
        "checks": {"passed": not errors, "problems": errors},
        "generation": {
            "generatedAt": now,
            "model": model_label,
            "promptVersion": PROMPT_VERSION,
            "query": target.query,
            "fetchedSources": [{"title": s.title, "url": s.url} for s in sources],
        },
    }
