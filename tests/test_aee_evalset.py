"""answer_evidence_evalset_v1 冻结快照(新定位统一评测集)."""
from __future__ import annotations

import json
import sys
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = Path(__file__).resolve().parent.parent
DATA = json.loads((BASE / "data/gjb_438c/answer_evidence_evalset_v1.json").read_text(encoding="utf-8"))
E = DATA["entries"]


def test_total() -> None:
    assert len(E) == 1443


def test_three_state_labels() -> None:
    from collections import Counter
    labels = Counter(e["gold"]["label"] for e in E)
    assert dict(labels) == {"support": 783, "refute": 535, "not_in_evidence": 125}


def test_no_train_leakage() -> None:
    """29对family_train泄漏已剔除: 构建器跳过计数."""
    train_path = BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl"
    train = [json.loads(line) for line in train_path.read_text(encoding="utf-8").splitlines()]
    import re

    def nk(s: str) -> str:
        return re.sub(r"[\s「」《》]", "", str(s))
    keys = {(nk(x.get("pair", x).get("premise", "")), nk(x.get("pair", x).get("hypothesis", ""))) for x in train}
    n = 0
    for e in E:
        if e["provenance"].startswith("family/"):
            ev0 = e["evidence"][0]["claims"][0] if e["evidence"][0]["claims"] else ""
            if (nk(ev0), nk(e["answer"]["text"])) in keys:
                n += 1
    assert n == 0


def test_schema() -> None:
    for e in E:
        assert e["gold"]["label"] in ("support", "refute", "not_in_evidence")
        assert e["answer"]["text"]
        for ev in e["evidence"]:
            assert ev["evidence_type"] in ("text", "table", "figure")
        assert e["modality_combo"]
        # verify()校验一个answer；证据来源不是互相比较的两端。
        assert len(e["evidence"]) == 1
        assert "+" not in e["modality_combo"]


def test_world_assumption_coverage() -> None:
    """三态全覆盖: NIE条目存在(图侧VLM缺失)且refute含表侧闭世界."""
    nie = [e for e in E if e["gold"]["label"] == "not_in_evidence"]
    assert len(nie) >= 100  # A1图侧125
    fig_nie = [e for e in nie if any(ev["evidence_type"] == "figure" for ev in e["evidence"])]
    assert len(fig_nie) >= 80


def test_eval_run_fingerprint_matches_snapshot() -> None:
    from tools.eval_aee import dataset_fingerprint

    path = BASE / "data/gjb_438c/answer_evidence_evalset_v1.json"
    fingerprint = dataset_fingerprint(path, E)
    assert fingerprint["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert fingerprint["n"] == 1443
    assert fingerprint["labels"] == {
        "not_in_evidence": 125,
        "refute": 535,
        "support": 783,
    }
