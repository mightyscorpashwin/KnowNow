import copy

from fixtures import SOURCE_URL, valid_page
from knownow.page_schema import PAGE_SCHEMA, validate_page


def test_valid_page_passes():
    assert validate_page(valid_page(), [SOURCE_URL]) == []


def test_source_url_match_ignores_locale_and_trailing_slash():
    page = valid_page("https://learn.microsoft.com/azure/architecture/guide/technology-choices/compute-decision-tree/")
    assert validate_page(page, [SOURCE_URL]) == []


def test_unfetched_source_is_rejected():
    page = valid_page("https://example.com/made-up")
    assert any("source not among fetched" in e for e in validate_page(page, [SOURCE_URL]))


def test_bad_quiz_and_table_are_reported():
    page = copy.deepcopy(valid_page())
    page["quiz"][0]["options"] = ["only", "three", "options"]
    page["quiz"][1]["answerIndex"] = 7
    page["comparison"]["rows"][0] = ["too", "short"]
    errors = validate_page(page, [SOURCE_URL])
    assert any("exactly 4 options" in e for e in errors)
    assert any("answerIndex out of range" in e for e in errors)
    assert any("row 1 has 2 cells" in e for e in errors)


def test_diagram_must_be_mermaid():
    page = valid_page()
    page["diagram"]["mermaid"] = "A -> B"
    assert any("diagram.mermaid" in e for e in validate_page(page, [SOURCE_URL]))


def test_missing_field():
    page = valid_page()
    del page["pitfalls"]
    assert validate_page(page, [SOURCE_URL]) == ["missing field: pitfalls"]


def _check_strict(node, path="$"):
    if node.get("type") == "object":
        assert node.get("additionalProperties") is False, path
        assert set(node["required"]) == set(node["properties"]), path
        for key, child in node["properties"].items():
            _check_strict(child, f"{path}.{key}")
    elif node.get("type") == "array":
        _check_strict(node["items"], f"{path}[]")


def test_schema_is_valid_for_strict_structured_outputs():
    _check_strict(PAGE_SCHEMA)
