"""The topic catalogue bundled with the app, and helpers to walk it."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("catalog.json")


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def page_id(subtopic_id: str, area_id: str) -> str:
    return f"{subtopic_id}--{area_id}"


@dataclass(frozen=True)
class Target:
    """One page the content job can generate."""

    topic_id: str
    topic_name: str
    subtopic_id: str
    subtopic_name: str
    area_id: str
    area_name: str
    query: str

    @property
    def page_id(self) -> str:
        return page_id(self.subtopic_id, self.area_id)

    def to_dict(self) -> dict:
        return {
            "topicId": self.topic_id,
            "topicName": self.topic_name,
            "subtopicId": self.subtopic_id,
            "subtopicName": self.subtopic_name,
            "areaId": self.area_id,
            "areaName": self.area_name,
            "query": self.query,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Target":
        return cls(
            topic_id=d["topicId"],
            topic_name=d["topicName"],
            subtopic_id=d["subtopicId"],
            subtopic_name=d["subtopicName"],
            area_id=d["areaId"],
            area_name=d["areaName"],
            query=d["query"],
        )


def catalog_documents(catalog: dict | None = None) -> list[dict]:
    """One Cosmos DB document per topic (partition key /topicId)."""
    catalog = catalog or load_catalog()
    return [
        {**topic, "id": topic["id"], "topicId": topic["id"], "type": "topic"}
        for topic in catalog["topics"]
    ]


def iter_targets(
    topics: list[dict],
    topic_id: str | None = None,
    subtopic_id: str | None = None,
    area_id: str | None = None,
    include_disabled: bool = False,
) -> list[Target]:
    """Pages to generate. A scheduled run uses only sub-topics marked
    ``generate: true``; an admin can ask for any sub-topic explicitly."""
    targets: list[Target] = []
    for topic in topics:
        if topic_id and topic["id"] != topic_id:
            continue
        for sub in topic.get("subtopics", []):
            if subtopic_id and sub["id"] != subtopic_id:
                continue
            if not sub.get("generate") and not (include_disabled or subtopic_id):
                continue
            for area in sub.get("areas", []):
                if area_id and area["id"] != area_id:
                    continue
                targets.append(
                    Target(
                        topic_id=topic["id"],
                        topic_name=topic["name"],
                        subtopic_id=sub["id"],
                        subtopic_name=sub["name"],
                        area_id=area["id"],
                        area_name=area["name"],
                        query=area.get("query") or f"{sub['name']} {area['name']}",
                    )
                )
    return targets
