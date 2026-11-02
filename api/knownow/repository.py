"""Cosmos DB access. Pages live in the 'pages' container (partition /topicId):
  <subtopic>--<area>          the published page (status 'approved')
  <subtopic>--<area>--draft   the latest draft awaiting review
"""
from __future__ import annotations

from datetime import datetime, timezone

from .catalog import catalog_documents

DRAFT_SUFFIX = "--draft"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if not k.startswith("_")}


class Repository:
    def __init__(self, endpoint: str, database: str) -> None:
        from azure.cosmos import CosmosClient
        from azure.identity import DefaultAzureCredential

        client = CosmosClient(endpoint, credential=DefaultAzureCredential())
        db = client.get_database_client(database)
        self.catalog = db.get_container_client("catalog")
        self.pages = db.get_container_client("pages")

    # -- catalogue -----------------------------------------------------------
    def list_topics(self) -> list[dict]:
        items = self.catalog.query_items(
            "SELECT * FROM c WHERE c.type = 'topic'", enable_cross_partition_query=True
        )
        return sorted((_strip(i) for i in items), key=lambda t: t.get("order", 99))

    def ensure_catalog(self) -> list[dict]:
        """Load the bundled catalogue into Cosmos DB on first use."""
        topics = self.list_topics()
        if not topics:
            topics = self.sync_catalog()
        return topics

    def sync_catalog(self) -> list[dict]:
        docs = catalog_documents()
        for doc in docs:
            self.catalog.upsert_item(doc)
        return docs

    def get_topic(self, topic_id: str) -> dict | None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        try:
            return _strip(self.catalog.read_item(topic_id, partition_key=topic_id))
        except CosmosResourceNotFoundError:
            return None

    # -- pages ---------------------------------------------------------------
    def published_pages(self, topic_id: str, subtopic_id: str | None = None) -> list[dict]:
        query = "SELECT * FROM c WHERE c.status = 'approved'"
        params: list[dict] = []
        if subtopic_id:
            query += " AND c.subtopicId = @sub"
            params.append({"name": "@sub", "value": subtopic_id})
        items = self.pages.query_items(query, parameters=params, partition_key=topic_id)
        return [_strip(i) for i in items]

    def get_page(self, topic_id: str, doc_id: str) -> dict | None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        try:
            return _strip(self.pages.read_item(doc_id, partition_key=topic_id))
        except CosmosResourceNotFoundError:
            return None

    def save_draft(self, draft: dict) -> dict:
        return _strip(self.pages.upsert_item(draft))

    def list_drafts(self) -> list[dict]:
        items = self.pages.query_items(
            "SELECT c.id, c.pageId, c.topicId, c.subtopicId, c.areaName, c.status, c.checks, "
            "c.generation.generatedAt AS generatedAt, c.content.title AS title "
            "FROM c WHERE c.status IN ('draft', 'rejected')",
            enable_cross_partition_query=True,
        )
        return sorted((_strip(i) for i in items), key=lambda d: d.get("generatedAt", ""), reverse=True)

    def approve(self, topic_id: str, page_id: str, reviewer: str) -> dict:
        draft = self.get_page(topic_id, page_id + DRAFT_SUFFIX)
        if draft is None:
            raise KeyError(page_id)
        published = {
            **draft,
            "id": page_id,
            "status": "approved",
            "review": {"by": reviewer, "at": _now(), "decision": "approved"},
        }
        self.pages.upsert_item(published)
        self.pages.delete_item(page_id + DRAFT_SUFFIX, partition_key=topic_id)
        return published

    def reject(self, topic_id: str, page_id: str, reviewer: str, comment: str) -> dict:
        draft = self.get_page(topic_id, page_id + DRAFT_SUFFIX)
        if draft is None:
            raise KeyError(page_id)
        draft["status"] = "rejected"
        draft["review"] = {"by": reviewer, "at": _now(), "decision": "rejected", "comment": comment}
        return _strip(self.pages.upsert_item(draft))
