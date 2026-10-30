"""06号跨文档泛化评测集契约测试 + ×5扩充文档(05/07/08/10)与合并集.

构造性sound标签的机械验证(与tools/build_crossdoc_evalset.py的构造期
断言相互独立——本文件从落盘JSONL重新线性化证据再复核):
  1) 30条完整性: 字段/证据非空/sound_label合法/label_proof非空/10-10-10;
  2) R对的污染值确实在其证据中(值级归一化子串验证, 跨行污染R须含
     真值绑定语句+污染源语句两枚token);
  3) N对的内容确实不在证据中(标记词/主体行缺席);
  4) S对的断言值在证据中;
  5) 评测脚本能跑(tools/eval_crossdoc.run_evaluation在小fixture上
     deterministic-only配置端到端落盘);
  6) 构造确定性: 同输入重跑build_evalset逐字节一致;
  7) 扩充文档(05/07/08/10)逐文档同口径复核 + 合并集150条形态;
  8) eval_crossdoc5(×5评测工具)小fixture冒烟(b3与零样本mDeBERTa).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import linearize_context  # noqa: E402
from algorithms.consistency.egt_synthesis import (  # noqa: E402
    _vnorm,
    evidence_from_dict,
)

EVALSET = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"
SOURCE = (BASE / "data/gjb_438c/mineru_standard"
          / "06运行支撑服务软件需求规格说明-终稿/office"
          / "06运行支撑服务软件需求规格说明-终稿_content_list.json")

#: ×5扩充: 05/07/08/10各30条 + 合并集150条
NEW_DOC_NUMBERS = ("05", "07", "08", "10")
MERGED_EVALSET = BASE / "data/gjb_438c/qa_frozen/crossdoc5_evalset_v1.jsonl"

pytestmark = pytest.mark.skipif(
    not EVALSET.exists(),
    reason="crossdoc06评测集未构建(先跑 python tools/build_crossdoc_evalset.py)")


def _load() -> list[dict]:
    return [json.loads(line) for line in
            EVALSET.read_text(encoding="utf-8").splitlines() if line.strip()]


def _evidence_norm(row: dict) -> str:
    """模块真实看到的线性化证据语句文本(值级归一化)."""
    statements = linearize_context(tuple(
        evidence_from_dict(ev) for ev in row["evidence"]))
    return _vnorm("；".join(s.text for s in statements))


# ── 1) 完整性 ─────────────────────────────────────────────


def test_30_rows_integrity():
    rows = _load()
    assert len(rows) == 30
    counts = Counter(r["sound_label"] for r in rows)
    assert counts == {"support": 10, "refute": 10, "not_in_evidence": 10}
    ids = [r["instance_id"] for r in rows]
    assert len(set(ids)) == 30
    freezes = {r["context_freeze_id"] for r in rows}
    assert len(freezes) == 1
    assert next(iter(freezes)).startswith("crossdoc06-frozen-v1-")
    for row in rows:
        for key in ("instance_id", "question", "answer", "context_freeze_id",
                    "evidence", "sound_label", "label_proof", "family",
                    "operator", "check_tokens"):
            assert row.get(key), f"{row['instance_id']}缺字段 {key}"
        assert row["sound_label"] in ("support", "refute", "not_in_evidence")
        assert len(row["question"]) >= 6
        assert len(row["answer"]) >= 10
        assert len(row["evidence"]) >= 2, "seed块+邻近块至少2块"
        for ev in row["evidence"]:
            assert ev["text"].strip(), f"{row['instance_id']}空证据块"
            assert ev["evidence_id"]
            assert ev["source_ref"]["doc_id"].startswith("06")
            assert ev["completeness"] == "open"
            assert ev["completeness_proof"]
        assert isinstance(row["check_tokens"]["in_evidence"], list)
        assert isinstance(row["check_tokens"]["not_in_evidence"], list)


# ── 2) R对: 污染值确实在证据中 ──────────────────────────────


def test_refute_pollution_in_evidence():
    refute_rows = [r for r in _load() if r["sound_label"] == "refute"]
    assert len(refute_rows) == 10
    for row in refute_rows:
        env = _evidence_norm(row)
        tokens = row["check_tokens"]["in_evidence"]
        assert tokens, f"{row['instance_id']}R对无in_evidence token"
        for token in tokens:
            assert _vnorm(token) in env, (
                f"{row['instance_id']}污染/真值token不在证据中: {token}")
        assert "构造性R" in row["label_proof"]
        if row["operator"].endswith(("_add", "_swap")):
            # 跨行污染R: 真值绑定语句+污染源语句两枚token(测跨行join)
            assert len(tokens) >= 2, (
                f"{row['instance_id']}跨行污染R应含真值+污染源两枚token")
            assert "污染" in row["label_proof"]


# ── 3) N对: 内容确实不在证据中 ─────────────────────────────


def test_nie_content_absent_from_evidence():
    nie_rows = [r for r in _load() if r["sound_label"] == "not_in_evidence"]
    assert len(nie_rows) == 10
    for row in nie_rows:
        env = _evidence_norm(row)
        tokens = row["check_tokens"]["not_in_evidence"]
        assert tokens, f"{row['instance_id']}N对无not_in_evidence token"
        for token in tokens:
            assert _vnorm(token) not in env, (
                f"{row['instance_id']}N内容出现在证据中: {token}")
        assert "构造性N" in row["label_proof"]


# ── 4) S对: 断言值在证据中 ─────────────────────────────────


def test_support_assertions_in_evidence():
    support_rows = [r for r in _load() if r["sound_label"] == "support"]
    assert len(support_rows) == 10
    for row in support_rows:
        env = _evidence_norm(row)
        tokens = row["check_tokens"]["in_evidence"]
        assert tokens, f"{row['instance_id']}S对无in_evidence token"
        for token in tokens:
            assert _vnorm(token) in env, (
                f"{row['instance_id']}S断言token不在证据中: {token}")
        assert "构造性S" in row["label_proof"]


# ── 5) 评测脚本能跑(小fixture, deterministic-only) ────────────

FIXTURE_TABLE = (
    '<table><thead><tr><th><p>序号</p></th><th><p>Usecase名称</p></th>'
    '<th><p>项目唯一标识符</p></th><th><p>方式名称</p></th>'
    '<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th></tr></thead>'
    '<tbody>'
    '<tr><td><p>1</p></td><td><p>数据查询</p></td>'
    '<td><p>PZXQ-GN-CXSJ</p></td><td><p>平板、桌面</p></td>'
    '<td><p>运行阶段</p></td><td><p>4.1.1</p></td></tr>'
    '<tr><td><p>2</p></td><td><p>数据删除</p></td>'
    '<td><p>PZXQ-GN-SCSJ</p></td><td><p>桌面</p></td>'
    '<td><p>开发阶段、运行阶段</p></td><td><p>4.1.2</p></td></tr>'
    '</tbody></table>')


def _fixture_ev(instance_id: str, idx: int, text: str) -> dict:
    return {
        "evidence_id": f"{instance_id}-ev-{idx:06d}",
        "text": text,
        "source_type": "table",
        "source_ref": {"doc_id": "06fixture", "section": "3.2 CSCI能力需求",
                       "page": 1, "block_id": f"block-{idx:06d}"},
        "scope_id": f"06fixture:block-{idx:06d}",
        "completeness": "open",
        "completeness_proof": "Only this source block was frozen.",
        "extraction_method": "fixture",
        "extraction_confidence": 1.0,
    }


def _fixture_row(instance_id: str, question: str, answer: str,
                 label: str, operator: str, in_ev: list[str],
                 not_ev: list[str]) -> dict:
    return {
        "instance_id": instance_id,
        "question": question,
        "answer": answer,
        "context_freeze_id": "fixture-frozen-v1",
        "evidence": [_fixture_ev(instance_id, 30, FIXTURE_TABLE)],
        "sound_label": label,
        "label_proof": f"fixture构造{label}",
        "family": "capability_device",
        "operator": operator,
        "check_tokens": {"in_evidence": in_ev, "not_in_evidence": not_ev},
    }


def test_eval_runs_on_small_fixture(tmp_path):
    from tools.eval_crossdoc import run_evaluation
    rows = [
        _fixture_row(
            "FIX-001", "数据查询功能支持在哪些设备上使用？",
            "数据查询功能支持在平板、桌面设备上使用。", "support",
            "s_device_narrative", ["数据查询的方式名称：平板、桌面"], []),
        _fixture_row(
            "FIX-002", "数据删除功能支持在哪些设备上使用？",
            "数据删除功能支持在桌面、平板设备上使用。", "refute",
            "r_device_member_add",
            ["数据删除的方式名称：桌面", "数据查询的方式名称：平板、桌面"],
            []),
        _fixture_row(
            "FIX-003", "数据删除功能有什么特点？",
            "数据删除功能经过完整的单元测试验证，确保一致的用户体验。",
            "not_in_evidence", "n_effect_claim",
            ["数据删除的方式名称：桌面"], ["单元测试"]),
    ]
    path = tmp_path / "fixture_evalset.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    result, run_path = run_evaluation(
        evalset_path=path, out_root=tmp_path / "runs",
        configs=("deterministic",), reference_run="no_such_reference_run")
    metrics = result["configs"]["deterministic"]["metrics"]
    assert metrics["n"] == 3
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert set(metrics["per_class"]) == {
        "support", "refute", "not_in_evidence"}
    assert result["configs"]["deterministic"]["llm_stats"]["invocations"] == 0
    assert result["generalization_gap"]["available"] is False
    assert (run_path / "result.json").exists()
    assert (run_path / "report.md").exists()


# ── 6) 构造确定性 ─────────────────────────────────────────


def test_build_is_deterministic():
    pytest.importorskip("tools.build_crossdoc_evalset")
    from tools.build_crossdoc_evalset import build_evalset
    assert SOURCE.exists()
    rows_a, stats_a = build_evalset(SOURCE)
    rows_b, stats_b = build_evalset(SOURCE)
    assert stats_a["context_freeze_id"] == stats_b["context_freeze_id"]
    assert rows_a == rows_b
    assert len(rows_a) == 30


# ── 7) ×5扩充文档(05/07/08/10)与合并集 ──────────────────────


def _doc_evalset_path(doc: str) -> Path:
    return BASE / f"data/gjb_438c/qa_frozen/crossdoc{doc}_evalset_v1.jsonl"


def _load_doc(doc: str) -> list[dict]:
    return [json.loads(line) for line in
            _doc_evalset_path(doc).read_text(encoding="utf-8").splitlines()
            if line.strip()]


_new_docs = [pytest.param(doc, marks=pytest.mark.skipif(
    not _doc_evalset_path(doc).exists(),
    reason=f"crossdoc{doc}评测集未构建(先跑 python "
           f"tools/build_crossdoc_evalset.py)")) for doc in NEW_DOC_NUMBERS]


@pytest.mark.parametrize("doc", _new_docs)
def test_newdoc_30_rows_integrity(doc: str):
    rows = _load_doc(doc)
    assert len(rows) == 30
    counts = Counter(r["sound_label"] for r in rows)
    assert counts == {"support": 10, "refute": 10, "not_in_evidence": 10}
    ids = [r["instance_id"] for r in rows]
    assert len(set(ids)) == 30
    assert all(i.startswith(f"C{doc}QA-") for i in ids)
    freezes = {r["context_freeze_id"] for r in rows}
    assert len(freezes) == 1
    assert next(iter(freezes)).startswith(f"crossdoc{doc}-frozen-v1-")
    for row in rows:
        for key in ("instance_id", "question", "answer", "context_freeze_id",
                    "evidence", "sound_label", "label_proof", "family",
                    "operator", "check_tokens"):
            assert row.get(key), f"{row['instance_id']}缺字段 {key}"
        assert row["sound_label"] in ("support", "refute", "not_in_evidence")
        assert len(row["question"]) >= 6
        assert len(row["answer"]) >= 10
        assert len(row["evidence"]) >= 2, "seed块+邻近块至少2块"
        for ev in row["evidence"]:
            assert ev["text"].strip(), f"{row['instance_id']}空证据块"
            assert ev["evidence_id"]
            assert ev["source_ref"]["doc_id"].startswith(doc)
            assert ev["completeness"] == "open"
            assert ev["completeness_proof"]
        assert isinstance(row["check_tokens"]["in_evidence"], list)
        assert isinstance(row["check_tokens"]["not_in_evidence"], list)


@pytest.mark.parametrize("doc", _new_docs)
def test_newdoc_refute_pollution_in_evidence(doc: str):
    refute_rows = [r for r in _load_doc(doc) if r["sound_label"] == "refute"]
    assert len(refute_rows) == 10
    for row in refute_rows:
        env = _evidence_norm(row)
        tokens = row["check_tokens"]["in_evidence"]
        assert tokens, f"{row['instance_id']}R对无in_evidence token"
        for token in tokens:
            assert _vnorm(token) in env, (
                f"{row['instance_id']}污染/真值token不在证据中: {token}")
        assert "构造性R" in row["label_proof"]
        if row["operator"].endswith(("_add", "_swap")):
            # 跨行污染R: 真值绑定语句+污染源语句两枚token(测跨行join)
            assert len(tokens) >= 2, (
                f"{row['instance_id']}跨行污染R应含真值+污染源两枚token")
            assert "污染" in row["label_proof"]


@pytest.mark.parametrize("doc", _new_docs)
def test_newdoc_nie_content_absent_from_evidence(doc: str):
    nie_rows = [r for r in _load_doc(doc)
                if r["sound_label"] == "not_in_evidence"]
    assert len(nie_rows) == 10
    for row in nie_rows:
        env = _evidence_norm(row)
        tokens = row["check_tokens"]["not_in_evidence"]
        assert tokens, f"{row['instance_id']}N对无not_in_evidence token"
        for token in tokens:
            assert _vnorm(token) not in env, (
                f"{row['instance_id']}N内容出现在证据中: {token}")
        assert "构造性N" in row["label_proof"]


@pytest.mark.parametrize("doc", _new_docs)
def test_newdoc_support_assertions_in_evidence(doc: str):
    support_rows = [r for r in _load_doc(doc)
                    if r["sound_label"] == "support"]
    assert len(support_rows) == 10
    for row in support_rows:
        env = _evidence_norm(row)
        tokens = row["check_tokens"]["in_evidence"]
        assert tokens, f"{row['instance_id']}S对无in_evidence token"
        for token in tokens:
            assert _vnorm(token) in env, (
                f"{row['instance_id']}S断言token不在证据中: {token}")
        assert "构造性S" in row["label_proof"]


@pytest.mark.skipif(
    not MERGED_EVALSET.exists(),
    reason="crossdoc5合并集未构建(先跑 python tools/build_crossdoc_evalset.py)")
def test_merged_150_rows_shape():
    rows = [json.loads(line) for line in
            MERGED_EVALSET.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    assert len(rows) == 150
    counts = Counter(r["sound_label"] for r in rows)
    assert counts == {"support": 50, "refute": 50, "not_in_evidence": 50}
    ids = [r["instance_id"] for r in rows]
    assert len(set(ids)) == 150
    by_doc = Counter(i[:5] for i in ids)
    assert by_doc == {f"C{d}QA": 30 for d in (*NEW_DOC_NUMBERS, "06")}
    # 合并集=5个单文档集的逐字节拼接
    for doc in ("05", "06", "07", "08", "10"):
        doc_rows = [r for r in rows if r["instance_id"].startswith(f"C{doc}QA")]
        on_disk = _doc_evalset_path(doc).read_text(encoding="utf-8")
        rebuilt = "".join(json.dumps(r, ensure_ascii=False) + "\n"
                          for r in doc_rows)
        assert rebuilt == on_disk, f"合并集{doc}号子集与单文档文件不一致"


@pytest.mark.parametrize("doc", _new_docs)
def test_newdoc_build_is_deterministic_and_matches_disk(doc: str):
    """同输入重跑逐字节一致, 且与落盘文件逐字节一致(冻结性)."""
    pytest.importorskip("tools.build_crossdoc_evalset")
    from tools.build_crossdoc_evalset import build_evalset, load_source_blocks
    source = load_source_blocks(doc)
    rows_a, stats_a = build_evalset(source)
    rows_b, stats_b = build_evalset(source)
    assert stats_a["context_freeze_id"] == stats_b["context_freeze_id"]
    assert rows_a == rows_b
    assert len(rows_a) == 30
    rebuilt = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_a)
    assert rebuilt == _doc_evalset_path(doc).read_text(encoding="utf-8")


def test_06_rebuild_matches_disk():
    """06号重生成与现有冻结集逐字节一致(参数化无漂移)."""
    pytest.importorskip("tools.build_crossdoc_evalset")
    from tools.build_crossdoc_evalset import build_evalset
    rows, _stats = build_evalset(SOURCE)
    rebuilt = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    assert rebuilt == EVALSET.read_text(encoding="utf-8")


# ── 8) ×5评测工具冒烟 ──────────────────────────────────────


@pytest.mark.skipif(
    not MERGED_EVALSET.exists(),
    reason="crossdoc5合并集未构建(先跑 python tools/build_crossdoc_evalset.py)")
def test_eval_crossdoc5_benchmark_shape():
    from tools.eval_crossdoc5 import doc_of, validate_benchmark_shape
    rows = [json.loads(line) for line in
            MERGED_EVALSET.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    counts = validate_benchmark_shape(rows)
    assert counts == {"05": 30, "06": 30, "07": 30, "08": 30, "10": 30}
    assert doc_of(rows[0]) in NEW_DOC_NUMBERS + ("06",)


def test_eval_crossdoc5_runs_on_small_fixture(tmp_path):
    from tools.eval_crossdoc5 import run_evaluation
    rows = [
        _fixture_row(
            "FIX-001", "数据查询功能支持在哪些设备上使用？",
            "数据查询功能支持在平板、桌面设备上使用。", "support",
            "s_device_narrative", ["数据查询的方式名称：平板、桌面"], []),
        _fixture_row(
            "FIX-002", "数据删除功能支持在哪些设备上使用？",
            "数据删除功能支持在桌面、平板设备上使用。", "refute",
            "r_device_member_add",
            ["数据删除的方式名称：桌面", "数据查询的方式名称：平板、桌面"],
            []),
        _fixture_row(
            "FIX-003", "数据删除功能有什么特点？",
            "数据删除功能经过完整的单元测试验证，确保一致的用户体验。",
            "not_in_evidence", "n_effect_claim",
            ["数据删除的方式名称：桌面"], ["单元测试"]),
    ]
    path = tmp_path / "fixture_evalset5.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    result, run_path = run_evaluation(
        evalset_path=path, out_root=tmp_path / "runs",
        configs=("b3_deterministic",),
        reference_run="no_such_reference_run")
    metrics = result["configs"]["b3_deterministic"]["metrics"]
    assert metrics["n"] == 3
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert set(metrics["per_class"]) == {
        "support", "refute", "not_in_evidence"}
    assert result["configs"]["b3_deterministic"]["llm_stats"][
        "invocations"] == 0
    assert result["doc06_reproduction"]["available"] is False
    assert (run_path / "result.json").exists()
    assert (run_path / "report.md").exists()


@pytest.mark.skipif(
    not (BASE / "models/nli/mdeberta-v3-base-xnli-multilingual-nli-2mil7"
         / "config.json").exists(),
    reason="mDeBERTa基座模型未下载(models/nli/)")
def test_eval_crossdoc5_zeroshot_runs_on_small_fixture(tmp_path):
    from tools.eval_crossdoc5 import run_evaluation
    rows = [
        _fixture_row(
            "FIX-001", "数据查询功能支持在哪些设备上使用？",
            "数据查询功能支持在平板、桌面设备上使用。", "support",
            "s_device_narrative", ["数据查询的方式名称：平板、桌面"], []),
        _fixture_row(
            "FIX-002", "数据删除功能支持在哪些设备上使用？",
            "数据删除功能支持在桌面、平板设备上使用。", "refute",
            "r_device_member_add",
            ["数据删除的方式名称：桌面", "数据查询的方式名称：平板、桌面"],
            []),
        _fixture_row(
            "FIX-003", "数据删除功能有什么特点？",
            "数据删除功能经过完整的单元测试验证，确保一致的用户体验。",
            "not_in_evidence", "n_effect_claim",
            ["数据删除的方式名称：桌面"], ["单元测试"]),
    ]
    path = tmp_path / "fixture_evalset5zs.jsonl"
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    result, run_path = run_evaluation(
        evalset_path=path, out_root=tmp_path / "runs",
        configs=("mdeberta_zeroshot",),
        reference_run="no_such_reference_run")
    entry = result["configs"]["mdeberta_zeroshot"]
    metrics = entry["metrics"]
    assert metrics["n"] == 3
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert entry["zeroshot_stats"]["mode"] in ("cpu", "gpu", "cuda")
    assert entry["zeroshot_stats"]["n_pairs"] == 3
    assert (run_path / "result.json").exists()
    assert (run_path / "report.md").exists()


@pytest.mark.skipif(
    not (BASE / "models/embedding/bge-large-zh-v1.5/config.json").exists(),
    reason="BGE嵌入模型未下载(models/embedding/)")
def test_eval_crossdoc5_bge_runs_on_small_fixture():
    """BGE中心法(public_baselines接口)小fixture冒烟: 合成fit池注入."""
    from tools.eval_crossdoc5 import run_bge_centroid
    rows = [
        _fixture_row(
            "FIX-001", "数据查询功能支持在哪些设备上使用？",
            "数据查询功能支持在平板、桌面设备上使用。", "support",
            "s_device_narrative", ["数据查询的方式名称：平板、桌面"], []),
        _fixture_row(
            "FIX-002", "数据删除功能支持在哪些设备上使用？",
            "数据删除功能支持在桌面、平板设备上使用。", "refute",
            "r_device_member_add",
            ["数据删除的方式名称：桌面", "数据查询的方式名称：平板、桌面"],
            []),
        _fixture_row(
            "FIX-003", "数据删除功能有什么特点？",
            "数据删除功能经过完整的单元测试验证，确保一致的用户体验。",
            "not_in_evidence", "n_effect_claim",
            ["数据删除的方式名称：桌面"], ["单元测试"]),
    ]
    fit_pool = []
    for label, texts in (
            ("support", [("用户在平板终端可以使用查询功能。", "查询功能支持在平板上使用。"),
                         ("清单为桌面、平板。", "设备包括桌面和平板。")]),
            ("refute", [("清单只有桌面。", "设备包括平板。"),
                        ("方式名称为桌面。", "方式名称为平板。")]),
            ("not_in_evidence", [("清单为桌面、平板。", "功能经过单元测试验证。"),
                                 ("接口采用消息机制。", "接口采用加密传输。")])):
        for premise, hypothesis in texts:
            fit_pool.append({"premise": premise, "hypothesis": hypothesis,
                             "label": label})
    outcomes, stats = run_bge_centroid(rows, fit_pool=fit_pool)
    assert set(outcomes) == {"FIX-001", "FIX-002", "FIX-003"}
    assert all(o["verdict"] in ("support", "refute", "not_in_evidence")
               for o in outcomes.values())
    assert stats["mode"] in ("cpu", "gpu", "cuda")
    assert stats["fit_pool"]["n_fit_pairs"] == len(fit_pool)
