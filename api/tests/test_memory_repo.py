from knownow.catalog import Target
from knownow.memory_repo import InMemoryRepository
from knownow.page_schema import validate_page
from knownow.sample_pages import AZURE_COMPUTE, COMPUTE_SOURCE, demo_page


def test_sample_and_demo_pages_pass_checks():
    assert validate_page(AZURE_COMPUTE, [COMPUTE_SOURCE]) == []
    t = Target("legacy", "Legacy", "cobol", "COBOL", "overview", "Overview", "cobol")
    assert validate_page(demo_page(t), [COMPUTE_SOURCE]) == []


def test_review_flow_publishes_only_after_approval():
    repo = InMemoryRepository()
    assert {p["pageId"] for p in repo.published_pages("cloud")} == {"azure--compute"}

    draft = {
        "id": "azure--storage--draft", "pageId": "azure--storage", "topicId": "cloud", "subtopicId": "azure",
        "areaId": "storage", "areaName": "Storage", "status": "draft", "content": {"title": "Storage"},
        "checks": {"passed": True, "problems": []}, "generation": {"generatedAt": "2026-11-02T00:00:00Z"},
    }
    repo.save_draft(draft)
    assert [d["pageId"] for d in repo.list_drafts()] == ["azure--storage"]
    assert "azure--storage" not in {p["pageId"] for p in repo.published_pages("cloud")}

    repo.approve("cloud", "azure--storage", "rev@contoso.com")
    assert repo.list_drafts() == []
    page = repo.get_page("cloud", "azure--storage")
    assert page["status"] == "approved" and page["review"]["by"] == "rev@contoso.com"


def test_reject_keeps_draft_hidden():
    repo = InMemoryRepository()
    repo.save_draft({
        "id": "azure--overview--draft", "pageId": "azure--overview", "topicId": "cloud", "subtopicId": "azure",
        "areaId": "overview", "areaName": "Overview", "status": "draft", "content": {"title": "x"},
        "checks": {"passed": True, "problems": []}, "generation": {"generatedAt": "2026-11-02T00:00:00Z"},
    })
    repo.reject("cloud", "azure--overview", "rev@contoso.com", "Too vague")
    drafts = repo.list_drafts()
    assert drafts[0]["status"] == "rejected"
    assert repo.get_page("cloud", "azure--overview") is None
