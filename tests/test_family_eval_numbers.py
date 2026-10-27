"""family_eval_full 论文数字快照: 锁定表1矩阵(任务对齐v2).

数据: family_evalset_v1(896条) | 我方: v4.2通道+v12
运行: family_eval_full_afe91565_20261014_112510
有意重跑后同步本快照(tools/eval_family.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RUN_DIR = "family_eval_full_afe91565_20261014_112510"
OURS_KEY = "Ours(v4.2+channel)"
DISPATCH_KEY = "Family-dispatch(Z3/LCS/Set/EditLex/GJB)"


def _load() -> dict:
    run_dir = Path(__file__).resolve().parent.parent / "data/gjb_438c/runs" / RUN_DIR
    return json.loads((run_dir / "result.json").read_text(encoding="utf-8"))


def test_table1_ours() -> None:
    t1 = _load()["table1_family_matrix"]
    ours = t1[OURS_KEY]
    assert ours["overall"] == 0.894
    assert ours["A"] == 0.940 and ours["D"] == 0.975 and ours["F"] == 0.993
    assert ours["C"] == 0.824 and ours["E"] == 0.806 and ours["B"] == 0.642


def test_table1_baseline_matrix() -> None:
    t1 = _load()["table1_family_matrix"]
    # Z3分派的A族: 形式化盲区(TPR≈0.03 → bAcc≈0.51)
    assert t1[DISPATCH_KEY]["A"] == 0.513
    # E族零样本NLI意外强(通用矛盾模式)
    assert t1["Erlangshen ZS"]["E"] == 1.000
    # 次优总体
    others = [row["overall"] for name, row in t1.items() if name != OURS_KEY]
    assert max(others) == 0.604


def test_nontask_refs_excluded() -> None:
    """TF-IDF/BGE必须不在方法矩阵里(任务对齐)."""
    t1 = _load()["table1_family_matrix"]
    assert not any("TF-IDF" in k or "BGE" in k for k in t1)
    refs = _load()["surface_refs_nontask"]
    assert "TF-IDF(参考,非同任务)" in refs


def test_bootstrap_ci() -> None:
    lo, hi = _load()["bootstrap_ci"]
    assert lo == 0.873 and hi == 0.914


def test_mcnemar() -> None:
    mcn = _load()["mcnemar_vs_family_baseline"]
    for f in ("A", "C", "D", "F"):
        assert mcn[f]["p"] < 0.001, f"族{f}应显著"
    assert mcn["B"]["p"] > 0.05 and mcn["E"]["p"] > 0.05
