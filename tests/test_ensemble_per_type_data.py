from __future__ import annotations
import pytest
pytest.importorskip("ensemble_per_type_eval", reason="ensemble_per_type_eval.py已归档")
"""ensemble_per_type_eval数据构建快照回归 — 真实金标+变异+对称构造的规模与类型数锁定.

论文数字: 3062条/39类型(真实296+变异1383+对称1383) 与 b_wavg_bacc权重(来自v16保存配置).
仅测数据构建(纯CPU无模型加载); 逐类型分数快照在 runs/ensemble_per_type.json.
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

from ensemble_per_type_eval import build_eval_data  # noqa: E402

V16_RESULTS = BASE / "data/gjb_438c/runs/ensemble_v16_results.json"
PER_TYPE_RESULTS = BASE / "data/gjb_438c/runs/ensemble_per_type.json"


def test_build_eval_data_snapshot():
    combined, counts = build_eval_data()
    assert counts == {"real": 296, "mutation": 1383, "symmetric": 1383}
    assert len(combined) == 3062
    types = {x["type"] for x in combined}
    assert len(types) == 39
    # 对称构造全为consistent, 变异全为inconsistent
    assert all(x["label"] == "consistent" for x in combined if x["origin"] == "symmetric")
    assert all(x["label"] == "inconsistent" for x in combined if x["origin"] == "mutation")
    # 真实金标两类齐全(162不一致+134一致)
    labels = [x["label"] for x in combined if x["origin"] == "real"]
    assert labels.count("inconsistent") == 162 and labels.count("consistent") == 134


def test_v16_weights_and_saved_results():
    v16 = json.loads(V16_RESULTS.read_text(encoding="utf-8"))
    w = v16["weights"]["b_wavg_bacc"]
    assert sorted(w) == ["svm", "v12", "v13", "v15"]
    assert abs(sum(w.values()) - 1.0) < 0.001
    assert v16["best"]["strategy"] == "b_wavg_bacc"

    r = json.loads(PER_TYPE_RESULTS.read_text(encoding="utf-8"))
    assert r["ensemble_config"]["strategy"] == "b_wavg_bacc"
    assert r["data"]["n_types"] == 39 and r["data"]["n_total"] == 3062
    assert set(r["per_type"]) == {x["type"] for x in build_eval_data()[0]}
    # 关键结果数字锁定(论文快照): v13在逐类型评测上占优, 集成权重稀释了v13
    assert r["pooled"]["ens"]["bAcc"] == 0.5595
    assert r["pooled"]["v13"]["bAcc"] == 0.6871
    assert r["macro_bAcc"] == {"ens": 0.5267, "v12": 0.5024, "v13": 0.6566}
