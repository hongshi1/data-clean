from algorithms.domain import (
    CandidateLink,
    Claim,
    EntityCandidate,
    Item,
    ObservationAlignment,
    Occurrence,
    ParserObservation,
    QualityContract,
    SourceRef,
    SourceVersion,
    Value,
)


def test_source_and_claim_preserve_raw_and_normalized_values() -> None:
    version = SourceVersion("doc-1", "v1", "sha256:abc")
    source = SourceRef(version.version_id, "table_row", row_id="r7")
    occurrence = Occurrence(
        "occ-1",
        source,
        raw_value="0.2秒",
        normalized_value="200ms",
    )
    claim = Claim(
        "claim-1",
        subject="接口X",
        predicate="响应时间",
        value=Value("0.2秒", typed_value=200, unit="ms"),
        occurrence_refs=(occurrence.occurrence_id,),
    )

    assert claim.value is not None
    assert claim.value.raw_text == "0.2秒"
    assert claim.value.typed_value == 200
    assert occurrence.source_ref.source_type == "table_row"


def test_item_is_not_an_entity_candidate() -> None:
    candidate = EntityCandidate("ent-1", "interface", "接口X")
    link = CandidateLink("occ-1", "occ-2", "same_identity", 0.95)
    item = Item("item-1", entity_key=candidate.candidate_id,
                occurrence_refs=("occ-1", "occ-2"),
                accepted_links=(link,), completeness="complete")

    assert item.entity_key == candidate.candidate_id
    assert item.accepted_links[0].relation == "same_identity"


def test_quality_contract_requires_explicit_evidence_obligations() -> None:
    contract = QualityContract(
        quality_type="interface_value_conflict",
        target_schema="ClaimPair",
        evidence_obligations=("identity_alignment", "scope_match", "value_parse"),
        abstain_policy="missing obligation -> insufficient",
    )

    assert len(contract.evidence_obligations) == 3
    assert "scope_match" in contract.evidence_obligations


def test_parser_observation_preserves_method_and_parent_lineage() -> None:
    ref = SourceRef("v1", "image_element", page=2, region_id="r4")
    observation = ParserObservation(
        "obs-1",
        "v1",
        "diagram_edge",
        '{"via":"geo","connector_id":"c3"}',
        ref,
        status="partial",
        method_kind="heuristic",
        method_id="geo_snap_v1",
        parent_observation_ids=("raw-1",),
    )

    assert observation.status == "partial"
    assert observation.method_kind == "heuristic"
    assert observation.parent_observation_ids == ("raw-1",)


def test_parser_alignment_can_remain_unmatched_or_ambiguous() -> None:
    alignment = ObservationAlignment(
        "mineru-image-1",
        "visio-embed-2",
        "figure_alignment",
        evidence_refs=("caption-1",),
        status="ambiguous",
    )

    assert alignment.status == "ambiguous"
    assert alignment.alignment_type == "figure_alignment"
