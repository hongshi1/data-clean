from tools.build_evidence_graph import (
    make_entities,
    make_items,
    node_id,
    overlap,
    requirement_candidates,
)


def test_overlap_is_deterministic_and_empty_safe() -> None:
    assert overlap("数据结构转换", "数据结构转换功能") > 0
    assert overlap("", "数据") == 0


def test_identifier_match_is_identity_candidate_but_semantic_match_is_not() -> None:
    requirements = [
        {
            "requirement_id": "ABC-REQ-001",
            "doc_id": "01",
            "section": "3.2.1",
            "raw_text": "功能A ABC-REQ-001",
            "features": {"requirement_ids": ["ABC-REQ-001"]},
        }
    ]
    claims = [
        {
            "claim_id": "c1",
            "doc_id": "01",
            "section": "3.2.1",
            "raw_text": "功能A ABC-REQ-001",
        },
        {
            "claim_id": "c2",
            "doc_id": "01",
            "section": "3.2.1",
            "raw_text": "功能A的相关处理",
        },
    ]

    links, stats = requirement_candidates(requirements, claims, [], [], embedding=False)
    by_target = {link["target_id"]: link for link in links}

    assert stats["enabled"] is False
    assert by_target["claims:c1"]["relation_type"] == "same_identity"
    assert by_target["claims:c1"]["status"] == "accepted"
    assert by_target["claims:c2"]["relation_type"] != "same_identity"


def test_entity_and_item_keep_candidate_status() -> None:
    requirement = {
        "requirement_id": "ABC-REQ-001",
        "doc_id": "01",
        "raw_text": "功能A",
    }
    requirement_node = node_id("requirements", requirement)
    link = {
        "link_id": "link-1",
        "source_id": requirement_node,
        "target_id": "claims:c1",
        "status": "accepted",
    }

    entities = make_entities([requirement], [link])
    items = make_items(entities, [link])

    assert entities[0]["quality_tier"] == "candidate"
    assert items[0]["quality_tier"] == "candidate"
    assert items[0]["accepted_link_ids"] == ["link-1"]
