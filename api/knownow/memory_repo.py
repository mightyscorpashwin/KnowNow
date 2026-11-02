"""In-memory stand-in for the Cosmos DB repository, used by the demo server."""
from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone

from .catalog import catalog_documents, page_id
from .repository import DRAFT_SUFFIX
from .sample_pages import AZURE_COMPUTE, COMPUTE_SOURCE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryRepository:
    def __init__(self, seed_sample: bool = True) -> None:
        self._lock = threading.Lock()
        self._topics: dict[str, dict] = {}
        self._pages: dict[tuple[str, str], dict] = {}
        if seed_sample:
            self.sync_catalog()
            pid = page_id("azure", "compute")
            self._pages[("cloud", pid)] = {
                "id": pid,
                "pageId": pid,
                "topicId": "cloud",
                "subtopicId": "azure",
                "areaId": "compute",
                "areaName": "Compute",
                "status": "approved",
                "content": copy.deepcopy(AZURE_COMPUTE),
                "checks": {"passed": True, "problems": []},
                "generation": {
                    "generatedAt": _now(),
                    "model": "sample",
                    "promptVersion": "sample",
                    "query": "azure compute",
                    "fetchedSources": [{"title": "Choose an Azure compute service", "url": COMPUTE_SOURCE}],
                },
                "review": {"by": "sample.reviewer@contoso.com", "at": _now(), "decision": "approved"},
            }

    # catalogue
    def list_topics(self) -> list[dict]:
        return sorted(copy.deepcopy(list(self._topics.values())), key=lambda t: t.get("order", 99))

    def ensure_catalog(self) -> list[dict]:
        return self.list_topics() or self.sync_catalog()

    def sync_catalog(self) -> list[dict]:
        docs = catalog_documents()
        with self._lock:
            self._topics = {d["id"]: d for d in docs}
        return copy.deepcopy(docs)

    def get_topic(self, topic_id: str) -> dict | None:
        t = self._topics.get(topic_id)
        return copy.deepcopy(t) if t else None

    # pages
    def published_pages(self, topic_id: str, subtopic_id: str | None = None) -> list[dict]:
        return [
            copy.deepcopy(p)
            for (tid, _), p in self._pages.items()
            if tid == topic_id and p["status"] == "approved" and (not subtopic_id or p["subtopicId"] == subtopic_id)
        ]

    def get_page(self, topic_id: str, doc_id: str) -> dict | None:
        p = self._pages.get((topic_id, doc_id))
        return copy.deepcopy(p) if p else None

    def save_draft(self, draft: dict) -> dict:
        with self._lock:
            self._pages[(draft["topicId"], draft["id"])] = copy.deepcopy(draft)
        return draft

    def list_drafts(self) -> list[dict]:
        rows = []
        for p in self._pages.values():
            if p["status"] in ("draft", "rejected"):
                rows.append(
                    {
                        "id": p["id"],
                        "pageId": p["pageId"],
                        "topicId": p["topicId"],
                        "subtopicId": p["subtopicId"],
                        "areaName": p["areaName"],
                        "status": p["status"],
                        "checks": p["checks"],
                        "generatedAt": p["generation"]["generatedAt"],
                        "title": p["content"].get("title"),
                    }
                )
        return sorted(rows, key=lambda d: d["generatedAt"], reverse=True)

    def approve(self, topic_id: str, pid: str, reviewer: str) -> dict:
        with self._lock:
            draft = self._pages.pop((topic_id, pid + DRAFT_SUFFIX), None)
            if draft is None:
                raise KeyError(pid)
            published = {
                **draft,
                "id": pid,
                "status": "approved",
                "review": {"by": reviewer, "at": _now(), "decision": "approved"},
            }
            self._pages[(topic_id, pid)] = published
        return copy.deepcopy(published)

    def reject(self, topic_id: str, pid: str, reviewer: str, comment: str) -> dict:
        with self._lock:
            draft = self._pages.get((topic_id, pid + DRAFT_SUFFIX))
            if draft is None:
                raise KeyError(pid)
            draft["status"] = "rejected"
            draft["review"] = {"by": reviewer, "at": _now(), "decision": "rejected", "comment": comment}
        return copy.deepcopy(draft)
