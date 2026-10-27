"""The evaluator run metadata must identify the exact evaluated snapshot."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))


def test_aee_run_config_uses_current_snapshot_metadata() -> None:
    from tools.eval_aee import dataset_fingerprint

    path = BASE / "data/gjb_438c/answer_evidence_evalset_v1.json"
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    fingerprint = dataset_fingerprint(path, entries)

    assert fingerprint["n"] == len(entries) == 1443
    assert fingerprint["path"] == "data/gjb_438c/answer_evidence_evalset_v1.json"
    assert len(fingerprint["sha256"]) == 64
    assert fingerprint["labels"] == {
        "not_in_evidence": 125,
        "refute": 535,
        "support": 783,
    }


def test_verifier_exceptions_are_not_relabelled_as_nie() -> None:
    """A broken detector must fail the run, not silently improve NIE counts."""
    source = (BASE / "tools/eval_aee.py").read_text(encoding="utf-8")
    assert "except Exception" not in source
