"""Contract tests for the isolated frozen-QA dual annotator."""
from __future__ import annotations

import json
from pathlib import Path

from tools import annotate_frozen_qa_dual_llm as pipeline


def row() -> dict:
    return {
        "instance_id": "qa-1",
        "question": "响应时间是多少？",
        "answer": "响应时间为200ms。",
        "gold": "must-not-leak",
        "mutation": {"operator": "bad"},
        "evidence": [{
            "evidence_id": "ev-1", "text": "响应时间为200ms。",
            "source_ref": {"doc_id": "d", "section": "3.2"},
            "scope_id": "d:3.2", "completeness": "open",
        }],
    }


def valid_output(verdict="support") -> dict:
    return {"overall_verdict": verdict, "claims": [{
        "claim_id": "c1", "claim_text": "响应时间为200ms。", "verdict": verdict,
        "evidence_refs": ["ev-1"], "check_items": ["explicit value"],
        "rationale": "直接陈述。", "confidence": 0.9,
    }], "diagnostics": {"note": "independent"}}


def test_prompt_excludes_private_fields_and_enforces_open_absence_rule():
    prompt = pipeline.build_prompt(row(), "dual_qa_kimi")
    assert "must-not-leak" not in prompt
    assert "mutation" not in prompt
    assert "open" in prompt and "not_in_evidence" in prompt
    assert "explicit contradiction" in prompt


def test_mocked_llm_json_is_strict_and_provider_is_independent(monkeypatch):
    calls = []

    def fake(prompt, system=None, prefer=None, cache=None, allow_fallback=None):
        calls.append((prefer, cache, prompt))
        assert allow_fallback is False
        return valid_output("support" if prefer == "kimi" else "refute"), pipeline.EXPECTED_MODELS[prefer]

    monkeypatch.setattr(pipeline, "llm_json", fake)
    kimi = pipeline.annotate_row(row(), "dual_qa_kimi", "kimi")
    glm = pipeline.annotate_row(row(), "dual_qa_glm", "glm")
    assert kimi["status"] == glm["status"] == "ok"
    assert [call[:2] for call in calls] == [("kimi", True), ("glm", True)]
    assert all("gold" not in call[2] and "mutation" not in call[2] for call in calls)


def test_invalid_output_abstains_without_guessing(monkeypatch):
    monkeypatch.setattr(pipeline, "llm_json", lambda **kwargs: ({"overall_verdict": "support"}, "x"))
    result = pipeline.annotate_row(row(), "dual_qa_kimi", "kimi")
    assert result["status"] == "error"
    assert result["overall_verdict"] is None
    assert result["diagnostics"]["abstain"] is True


def test_unknown_evidence_reference_abstains(monkeypatch):
    invalid = valid_output()
    invalid["claims"][0]["evidence_refs"] = ["not-in-freeze"]
    monkeypatch.setattr(pipeline, "llm_json", lambda *args, **kwargs: (invalid, "x"))
    result = pipeline.annotate_row(row(), "dual_qa_kimi", "kimi")
    assert result["status"] == "error"
    assert result["overall_verdict"] is None
    assert any("unknown evidence_id" in error
               for error in result["diagnostics"]["errors"])


def test_provider_fallback_identity_is_rejected(monkeypatch):
    monkeypatch.setattr(
        pipeline, "llm_json",
        lambda *args, **kwargs: (valid_output(), pipeline.EXPECTED_MODELS["glm"]),
    )
    result = pipeline.annotate_row(row(), "dual_qa_kimi", "kimi")
    assert result["status"] == "error"
    assert any("provider identity mismatch" in error
               for error in result["diagnostics"]["errors"])


def test_comparison_has_kappa_disagreements_and_no_gold():
    data = {"kimi": {"qa-1": {"status": "ok", "overall_verdict": "support"}}, "glm": {"qa-1": {"status": "ok", "overall_verdict": "refute"}}}
    report = pipeline.compare_annotations(data)
    assert report["disagreements"]
    assert report["cohen_kappa"] == 0.0
    assert report["gold_label"] is None


def test_dry_run_writes_separate_raw_and_comparison_files(tmp_path: Path, monkeypatch, capsys):
    input_path = tmp_path / "input.jsonl"
    input_path.write_text(json.dumps(row(), ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["annotate", "--input", str(input_path), "--output-root", str(tmp_path / "runs"), "--limit", "1", "--dry-run"])
    pipeline.main()
    run_path = Path(capsys.readouterr().out.strip())
    assert (run_path / "raw_kimi.jsonl").exists()
    assert (run_path / "raw_glm.jsonl").exists()
    assert (run_path / "comparison_report.json").exists()


def test_load_existing_annotations_supports_resume(tmp_path: Path):
    path = tmp_path / "raw_kimi.jsonl"
    path.write_text(json.dumps({"instance_id": "qa-1", "status": "ok"}) + "\n",
                    encoding="utf-8")
    loaded = pipeline.load_existing_annotations(path)
    assert loaded == {"qa-1": {"instance_id": "qa-1", "status": "ok"}}


def test_write_annotations_replaces_partial_or_duplicate_output(tmp_path: Path):
    path = tmp_path / "raw_kimi.jsonl"
    path.write_text('{"instance_id":"qa-1"}\n{"instance_id":"qa-1"}\n',
                    encoding="utf-8")
    rows = [{"instance_id": "qa-1"}, {"instance_id": "qa-2"}]
    values = {
        "qa-1": {"instance_id": "qa-1", "status": "ok"},
        "qa-2": {"instance_id": "qa-2", "status": "error"},
    }
    pipeline.write_annotations(path, rows, values)
    actual = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [item["instance_id"] for item in actual] == ["qa-1", "qa-2"]
