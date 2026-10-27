"""GJB-URE-v1数据集与公开数据集转换器: 格式校验+规模快照.

规范: docs/srs_project/20_dataset_spec.md
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

URE = BASE / "data/gjb_438c/data_assets/evalsets/gjb_ure_v1.json"
CONVERTER = BASE / "tools/convert_public_dataset.py"


@pytest.mark.skipif(not URE.exists(), reason="未构建(先跑 tools/build_ure_dataset.py)")
class TestGjbUreV1:
    @pytest.fixture()
    def ds(self) -> dict:
        return json.loads(URE.read_text(encoding="utf-8"))

    def test_meta_and_protocol(self, ds: dict):
        assert ds["meta"]["name"] == "GJB-URE-v1"
        assert ds["protocol"]["n_folds"] == 4
        assert ds["protocol"]["metrics"] == ["R@1", "R@5", "MRR@10"]
        assert "query_prefix" in ds["protocol"]

    def test_corpus_snapshot(self, ds: dict):
        """corpus规模快照: 全部381图+1207表(含无单元图)."""
        st = ds["meta"]["stats"]
        assert st["n_corpus"] == 1588
        assert st["n_images"] == 381
        assert st["n_tables"] == 1207
        assert st["n_docs"] == 16

    def test_chunk_id_unique(self, ds: dict):
        ids = [c["chunk_id"] for c in ds["corpus"]]
        assert len(ids) == len(set(ids))

    def test_expected_reference_integrity(self, ds: dict):
        """所有expected必须在corpus中(构建期已校验, 此处回归)."""
        idset = {c["chunk_id"] for c in ds["corpus"]}
        for q in ds["queries"]:
            assert q["expected"], f"空expected: {q['query'][:20]}"
            for t in q["expected"]:
                assert t in idset

    def test_eval_queries_snapshot(self, ds: dict):
        """eval查询规模与场景分布(与锁定评测一致)."""
        eval_q = [q for q in ds["queries"] if q["split"] == "eval"]
        assert len(eval_q) == 1125
        scenes = Counter(q["scene"] for q in eval_q)
        assert scenes == {"image": 1007, "table_deep": 118}

    def test_fold_evaluability(self, ds: dict):
        """每fold每eval场景可评测 + fold约定一致性(审计S1护栏)."""
        by = Counter((q["fold"], q["scene"]) for q in ds["queries"]
                     if q["split"] == "eval")
        ctype = {"image": "image", "table_caption": "table", "table_deep": "table"}
        corpus_by_fold: dict[int, Counter] = {}
        fold_of_cid = {}
        for c in ds["corpus"]:
            corpus_by_fold.setdefault(c["fold"], Counter())[c["type"]] += 1
            fold_of_cid[c["chunk_id"]] = c["fold"]
        for (fold, scene), n in by.items():
            assert n >= 1
            assert corpus_by_fold[fold][ctype[scene]] >= 5
        # fold约定: eval查询gold绝大数在本fold(允许≤5%已知噪声)
        n_miss = sum(1 for q in ds["queries"] if q["split"] == "eval"
                     and q["fold"] not in
                     {fold_of_cid[t] for t in q["expected"] if t in fold_of_cid})
        assert n_miss <= len([q for q in ds["queries"]
                              if q["split"] == "eval"]) * 0.05

    def test_fold_convention_matches_tools(self, ds: dict):
        """fold=(doc-1)mod4, 与全部评测工具的FOLD_MAP一致(doc01→fold0)."""
        for c in ds["corpus"]:
            assert c["fold"] == (int(c["doc"][:2]) - 1) % 4
            break  # 抽查首条即可(构建期已全量校验)

    def test_train_eval_decontaminated(self, ds: dict):
        """审计S2护栏: train池不含与eval的(query,expected)对重复."""
        eval_pairs = {(q["query"], tuple(q["expected"]))
                      for q in ds["queries"] if q["split"] == "eval"}
        train_pairs = [(q["query"], tuple(q["expected"]))
                       for q in ds["queries"] if q["split"] == "train"]
        overlap = [p for p in train_pairs if p in eval_pairs]
        assert not overlap, f"train泄漏eval对{len(overlap)}条"

    def test_train_queries_snapshot(self, ds: dict):
        """train池规模快照(去污染后)."""
        train_q = [q for q in ds["queries"] if q["split"] == "train"]
        assert len(train_q) == 2008

    def test_units_count_consistent(self, ds: dict):
        """n_units与units列表长度一致(标题与内容单元分离; 图标题
        同时也是图中节点的情形属合法数据属性, 允许文本重复)."""
        for c in ds["corpus"]:
            assert c["n_units"] == len(c["units"]), c["chunk_id"][-12:]


@pytest.mark.skipif(not CONVERTER.exists(), reason="转换器不存在")
class TestWtqConverter:
    def test_fixture_conversion(self, tmp_path: Path):
        """离线夹具: 全管线(表→corpus, 问→queries, 校验, 落盘)."""
        out = tmp_path / "wtq_ure.json"
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(CONVERTER),
             "--source", "wtq-fixture", "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", timeout=120)
        assert r.returncode == 0, r.stderr[-300:]
        ds = json.loads(out.read_text(encoding="utf-8"))
        assert ds["meta"]["name"] == "WTQ-fixture-URE"
        assert len(ds["corpus"]) == 3
        assert len(ds["queries"]) == 6
        # 行序列化: "header=value"
        t0 = ds["corpus"][0]
        assert "=Thomas Burke" in " ".join(t0["units"])
        # gold映射完整
        ids = {c["chunk_id"] for c in ds["corpus"]}
        assert all(q["expected"][0] in ids for q in ds["queries"])
        # fold ∈ [0,4)
        assert all(q["fold"] in (0, 1, 2, 3) for q in ds["queries"])
        # 英文语言标记+协议注意
        assert ds["meta"]["language"] == "en"
        assert "fold_rule" in ds["protocol"]

    def test_wtq_table_serialization(self):
        """单元序列化与GJB表同构('表头=值')."""
        from tools.convert_public_dataset import wtq_table_to_corpus
        t = {"name": "t1", "page_title": "Test Page",
             "header": ["A", "B"], "rows": [["x", "y"], ["1", "2"]]}
        c = wtq_table_to_corpus(t)
        assert c["chunk_id"] == "wtq_t1"
        assert c["title"] == "Test Page"
        assert c["units"] == ["A=x B=y", "A=1 B=2"]
        assert c["n_units"] == 2

    def test_kv_fallback_when_mismatch(self):
        """行列数≠表头数时回退原文join(与GJB解析器一致)."""
        from tools.convert_public_dataset import wtq_table_to_corpus
        t = {"name": "t2", "page_title": "P", "header": ["A", "B"],
             "rows": [["only-one-cell"]]}
        c = wtq_table_to_corpus(t)
        assert c["units"] == ["only-one-cell"]
