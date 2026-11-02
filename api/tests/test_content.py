import json

from fixtures import SOURCE_URL, valid_page
from knownow.catalog import Target
from knownow.content import generate_draft, pick_urls
from knownow.learn_mcp import SearchHit
from knownow.page_schema import validate_page

TARGET = Target("cloud", "Cloud", "azure", "Microsoft Azure", "compute", "Compute", "azure compute")


class FakeDocs:
    def __init__(self):
        self.fetched = []

    def search(self, query):
        return [
            SearchHit("Choose a compute service", SOURCE_URL + "#section", "excerpt"),
            SearchHit("Duplicate", SOURCE_URL, "dup"),
            SearchHit("Elsewhere", "https://example.com/x", "ignored"),
        ]

    def fetch(self, url):
        self.fetched.append(url)
        return "Full page text about Azure compute."


def test_pick_urls_dedupes_and_keeps_learn_only():
    hits = FakeDocs().search("q")
    assert [h.url for h in pick_urls(hits)] == [SOURCE_URL]


def test_generate_draft_happy_path():
    docs = FakeDocs()
    calls = []

    def chat(messages):
        calls.append(messages)
        return json.dumps(valid_page())

    draft = generate_draft(TARGET, docs, chat, validate_page, "content")
    assert draft["id"] == "azure--compute--draft" and draft["topicId"] == "cloud"
    assert draft["status"] == "draft" and draft["checks"]["passed"]
    assert docs.fetched == [SOURCE_URL]
    assert len(calls) == 1 and SOURCE_URL in calls[0][1]["content"]


def test_generate_draft_retries_with_feedback():
    bad = valid_page()
    bad["pitfalls"] = []
    replies = [json.dumps(bad), json.dumps(valid_page())]
    seen = []

    def chat(messages):
        seen.append(messages)
        return replies.pop(0)

    draft = generate_draft(TARGET, FakeDocs(), chat, validate_page, "content")
    assert draft["checks"]["passed"]
    assert "pitfalls" in seen[1][-1]["content"]


def test_generate_draft_records_failed_checks_after_retries():
    bad = valid_page()
    bad["quiz"] = []
    draft = generate_draft(TARGET, FakeDocs(), lambda m: json.dumps(bad), validate_page, "content")
    assert not draft["checks"]["passed"] and draft["checks"]["problems"]
