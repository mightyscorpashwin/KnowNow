from knownow.catalog import catalog_documents, iter_targets, load_catalog


def test_catalog_has_five_topics_with_unique_ids():
    topics = load_catalog()["topics"]
    assert [t["id"] for t in topics] == ["cloud", "ai", "devops", "backend", "legacy"]
    for t in topics:
        sub_ids = [s["id"] for s in t["subtopics"]]
        assert len(sub_ids) == len(set(sub_ids)), t["id"]
        for s in t["subtopics"]:
            area_ids = [a["id"] for a in s["areas"]]
            assert area_ids and len(area_ids) == len(set(area_ids)), s["id"]


def test_documents_carry_partition_key():
    docs = catalog_documents()
    assert all(d["topicId"] == d["id"] and d["type"] == "topic" for d in docs)


def test_scheduled_targets_only_enabled_subtopics():
    targets = iter_targets(load_catalog()["topics"])
    assert targets and {t.subtopic_id for t in targets} == {"azure"}
    assert targets[0].page_id == "azure--overview"


def test_explicit_subtopic_overrides_generate_flag():
    targets = iter_targets(load_catalog()["topics"], topic_id="legacy", subtopic_id="cobol")
    assert [t.page_id for t in targets] == ["cobol--overview"]


def test_single_area():
    targets = iter_targets(load_catalog()["topics"], subtopic_id="azure", area_id="compute")
    assert len(targets) == 1 and "compute" in targets[0].query.lower()
