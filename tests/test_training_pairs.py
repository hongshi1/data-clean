import json
from pathlib import Path

from tools.build_training_pairs import SPLIT_MAP, build, fold_for

ID_ONE = "TESTSYS-GN-01"
ID_TWO = "TESTSYS-GN-02"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _mini_corpus(root: Path) -> Path:
    corpus = root / "corpus"
    corpus.mkdir()
    _write_jsonl(
        corpus / "claims.jsonl",
        [
            {"claim_id": "C-1", "doc_id": "T1", "section": "3.2", "raw_text": f"系统应提供 {ID_ONE} 数据获取功能。"},
            {"claim_id": "C-2", "doc_id": "T1", "section": "3.2", "raw_text": "系统应提供数据转换功能。"},
            {"claim_id": "C-3", "doc_id": "T2", "section": "3.2", "raw_text": f"接口应支持 {ID_ONE} 协议。"},
        ],
    )
    _write_jsonl(
        corpus / "requirements.jsonl",
        [
            {"requirement_id": ID_ONE, "doc_id": "T1", "section": "3.1", "raw_text": f"1 | 数据获取 | {ID_ONE} | 新开发"},
            {"requirement_id": ID_TWO, "doc_id": "T1", "section": "3.1", "raw_text": f"2 | 数据转换 | {ID_TWO} | 新开发"},
            {"requirement_id": "REQ-NOLABEL-01", "doc_id": "T1", "section": "3.1", "raw_text": "3 | 数据备份 |  | 新开发"},
            {"requirement_id": "REQ-NOLABEL-02", "doc_id": "T1", "section": "3.1", "raw_text": "3 | 数据备份 |  | 新开发"},
        ],
    )
    _write_jsonl(corpus / "diagrams.jsonl", [{"diagram_id": "D-1", "doc_id": "T1"}])
    _write_jsonl(
        corpus / "diagram_nodes.jsonl",
        [
            {"node_id": "N-1", "diagram_id": "D-1", "text_raw": "数据获取", "type_candidate": "process"},
            {"node_id": "N-2", "diagram_id": "D-1", "text_raw": "数据转换", "type_candidate": "process"},
            {"node_id": "N-3", "diagram_id": "D-1", "text_raw": "数据获取", "type_candidate": "process"},
            {"node_id": "N-4", "diagram_id": "D-1", "text_raw": "数据获取", "type_candidate": "datastore"},
        ],
    )
    _write_jsonl(
        corpus / "tables.jsonl",
        [
            {
                "table_id": "TB-1",
                "doc_id": "T1",
                "section": "3.3",
                "rows": [
                    ["序号", "功能", "标识"],
                    ["1", "数据获取", ID_ONE],
                    ["2", "数据获取", ID_TWO],
                    ["3", "数据备份", ""],
                    ["3", "数据备份", ""],
                ],
            }
        ],
    )
    return corpus


def _endpoint_ids(row: dict) -> frozenset[str]:
    if "anchor" in row:
        return frozenset((row["anchor"]["occurrence_id"], row["candidate"]["occurrence_id"]))
    return frozenset((row["anchor_id"], row["candidate_id"]))


def test_explicit_identifier_positives_and_sibling_negatives(tmp_path: Path) -> None:
    corpus = _mini_corpus(tmp_path)
    out = tmp_path / "pairs_out"
    summary = build(corpus, out)

    pairs = _read_jsonl(out / "pairs.jsonl")
    excluded = _read_jsonl(out / "excluded.jsonl")
    positives = [pair for pair in pairs if pair["label"] == 1]
    negatives = [pair for pair in pairs if pair["label"] == 0]
    positive_ids = {_endpoint_ids(pair) for pair in positives}
    negative_ids = {_endpoint_ids(pair) for pair in negatives}
    excluded_ids = {_endpoint_ids(row) for row in excluded}

    # ── explicit identifier positives: cross-kind pairs inside doc T1 ──
    assert {pair["features"]["kind_pair"] for pair in positives} == {
        "claim+requirement",
        "claim+table_row",
        "requirement+table_row",
    }
    assert frozenset(("claim:C-1", f"requirement:{ID_ONE}")) in positive_ids
    assert frozenset(("claim:C-1", "table_row:TB-1:row=1")) in positive_ids
    assert frozenset((f"requirement:{ID_ONE}", "table_row:TB-1:row=1")) in positive_ids
    assert frozenset((f"requirement:{ID_TWO}", "table_row:TB-1:row=2")) in positive_ids
    assert len(positives) == 4
    for pair in positives:
        assert pair["features"]["shared_identifiers"]
        assert set(pair["features"]["shared_identifiers"]) <= {ID_ONE, ID_TWO}
        assert pair["label_basis"] == "explicit_identifier"
        assert pair["anchor"]["doc_id"] == pair["candidate"]["doc_id"] == "T1"

    # T2 reuses ID_ONE but must never be linked across documents.
    assert all("claim:C-3" not in ids for ids in positive_ids | negative_ids)

    # ── same-table adjacent sibling negative with disjoint identifiers ──
    assert frozenset(("table_row:TB-1:row=1", "table_row:TB-1:row=2")) in negative_ids
    assert next(pair for pair in negatives if "table_row:TB-1:row=1" in _endpoint_ids(pair))[
        "label_basis"
    ] == "sibling_distinct_identifier"

    # ── same-diagram sibling negatives (same type_candidate, different text) ──
    assert frozenset(("diagram_node:N-1", "diagram_node:N-2")) in negative_ids
    assert frozenset(("diagram_node:N-2", "diagram_node:N-3")) in negative_ids
    # Different type_candidate ⇒ never siblings.
    assert all("diagram_node:N-4" not in ids for ids in negative_ids | excluded_ids)

    # ── same-section requirement negative with distinct identifiers ──
    assert frozenset((f"requirement:{ID_ONE}", f"requirement:{ID_TWO}")) in negative_ids
    assert len(negatives) == 4

    # ── same normalized name without identifier distinction is excluded ──
    assert frozenset(("requirement:REQ-NOLABEL-01", "requirement:REQ-NOLABEL-02")) in excluded_ids
    assert frozenset(("table_row:TB-1:row=3", "table_row:TB-1:row=4")) in excluded_ids
    assert frozenset(("diagram_node:N-1", "diagram_node:N-3")) in excluded_ids
    assert all(row["reason"] == "unknown_identity" for row in excluded)
    assert len(excluded) == 3

    # ── fold split consistency ──
    for pair in pairs:
        assert pair["fold"] == fold_for("T1")
        assert pair["split"] == SPLIT_MAP[pair["fold"]]
        assert pair["anchor"]["doc_id"] == pair["candidate"]["doc_id"]

    # ── silver only: no gold fields anywhere ──
    for pair in pairs:
        assert "gold" not in pair
        assert pair["quality_tier"] == "silver"
    assert "gold" not in json.dumps(summary)

    # ── summary and manifest agree with the files on disk ──
    assert summary["counts"]["pairs"] == len(pairs)
    assert summary["counts"]["positive"] == len(positives)
    assert summary["counts"]["negative"] == len(negatives)
    assert summary["counts"]["excluded"] == len(excluded)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {"pairs.jsonl", "excluded.jsonl", "summary.json"}


def test_fold_is_deterministic_and_covers_all_splits() -> None:
    assert fold_for("T1") == fold_for("T1")
    assert 0 <= fold_for("T1") <= 3
    assert SPLIT_MAP == {0: "test", 1: "dev", 2: "train", 3: "train"}
