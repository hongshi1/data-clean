"""srs_verify分发包验证(在仓库内跑).

覆盖:
1. 包import成功(srs_verify_package目录, 不经安装)
2. 等价性: 包版CascadeVerifier vs 仓库版, fast档跑91QA的
   20条固定抽样(seed=42), verdict逐条一致
3. SCENES路径存在(包内configs资产齐备)
4. smoke三态样例(support/refute/NIE)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PKG = BASE / "srs_verify_package"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.verifier import (  # noqa: E402
    CascadeVerifier as RepoVerifier,
)
from srs_verify import (  # noqa: E402
    SCENES as PkgScenes,
    CascadeVerifier as PkgVerifier,
)

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SAMPLE_N = 20
SEED = 42

#: 三态smoke样例(与包内srs_verify/smoke_test.py同一组, 期望确定性判定)
SMOKE_CASES = [
    ("support", "连接池配置用例的项目唯一标识符是什么？",
     "PZXQ-GN-LJCGL-LJCPZ",
     [{"text": "3.2.5.1 连接池管理-连接池配置（PZXQ-GN-LJCGL-LJCPZ）"}]),
    ("refute", "连接超时时间要求是多少？",
     "连接超时时间为60秒。",
     [{"text": "连接池最大连接数为100，初始连接数为10，"
               "连接超时时间为30秒。"}]),
    ("not_in_evidence", "数据导入功能支持哪些数据格式？",
     "数据导入功能支持CSV、JSON、XML以及YAML格式。",
     [{"text": "数据导入功能支持CSV、JSON格式文件的导入。"}]),
]


def _load_frozen_rows() -> list[dict]:
    lines = QA_FROZEN.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    assert len(rows) == 91, f"91QA冻结语料行数异常: {len(rows)}"
    return rows


def _sample_rows() -> list[dict]:
    return random.Random(SEED).sample(_load_frozen_rows(), SAMPLE_N)


def test_package_imports():
    import srs_verify

    assert srs_verify.__version__
    for name in ("CascadeVerifier", "VerdictResult", "PRESETS", "SCENES",
                 "ClaimResult", "QAInput", "RetrievedEvidence", "SourceRef"):
        assert hasattr(srs_verify, name), f"公共API缺失: {name}"
    assert set(srs_verify.PRESETS) == {"fast", "standard", "full"}


def test_equivalence_20_sample_fast():
    """包版vs仓库版: fast档, 20条seed=42抽样, verdict逐条一致."""
    rows = _sample_rows()
    repo = RepoVerifier(preset="fast", scene="srs_scene1")
    repo_results = [repo.verify_record(dict(row)) for row in rows]
    pkg = PkgVerifier(preset="fast", scene="srs_scene1")
    pkg_results = [pkg.verify_record(dict(row)) for row in rows]
    mismatches = [
        (row["instance_id"], r.verdict, p.verdict)
        for row, r, p in zip(rows, repo_results, pkg_results)
        if r.verdict != p.verdict
    ]
    assert not mismatches, f"verdict不一致: {mismatches}"
    assert len(repo_results) == SAMPLE_N


def test_package_scenes_assets_exist():
    for lexicon_rel, pack_rel in PkgScenes.values():
        lexicon = PKG / "srs_verify" / lexicon_rel
        pack = PKG / "srs_verify" / pack_rel
        assert lexicon.exists(), f"词典缺失: {lexicon}"
        assert pack.exists(), f"规则包缺失: {pack}"
        pack_data = json.loads(pack.read_text(encoding="utf-8"))
        library = PKG / "srs_verify" / pack_data["gjb_rule_library_path"]
        assert library.exists(), f"GJB规则库缺失: {library}"


def test_package_smoke_three_verdicts():
    verifier = PkgVerifier(preset="fast", scene="srs_scene1")
    for expected, question, answer, evidence in SMOKE_CASES:
        result = verifier.verify(question, answer, evidence)
        assert result.verdict == expected, (
            f"{question!r}: 期望{expected}, 实际{result.verdict}")
