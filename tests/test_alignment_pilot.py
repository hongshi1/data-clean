from tools.build_alignment_pilot import fold_for, set_pilot_fields


def test_pilot_rows_have_unassigned_gold_and_stable_document_fold() -> None:
    row = {
        "source": {"asset_type": "claim", "asset_id": "claim:c1", "doc_id": "04"},
        "target": {"asset_type": "table_row", "asset_id": "table_row:t1:row=1", "doc_id": "04"},
        "tier": "P2",
    }
    result = set_pilot_fields(row, "same_table_sibling_row", "L3")

    assert result["gold"]["relation"] is None
    assert result["status"] == "pending_annotation"
    assert result["split"]["fold"] == fold_for("04")
    assert result["split"]["name"] in {"train", "dev", "test"}
