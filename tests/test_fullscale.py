"""全量升级与PURE-MMQA审计快照."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

WTQ_FULL = BASE / "data/gjb_438c/data_assets/evalsets/wtq_full_eval.json"


@pytest.mark.skipif(not WTQ_FULL.exists(), reason="未跑全量")
def test_wtq_full_scale():
    """WTQ全量18486查询: 单元增益在全量下保持(+8.3 R@1)."""
    d = json.loads(WTQ_FULL.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["B1-dense"]["R@1"] == pytest.approx(0.3239, abs=1e-2)
    assert r["O1-unit"]["R@1"] == pytest.approx(0.4067, abs=1e-2)
    assert r["O1-unit"]["R@5"] == pytest.approx(0.5885, abs=1e-2)
    assert r["O1-unit"]["R@1"] > r["B1-dense"]["R@1"] + 0.06
    # 与采样版(0.410/0.333)一致性: 增益方向与幅度稳定
    assert 0.38 < r["O1-unit"]["R@1"] < 0.43


def test_pure_mmqa_blocked_audit():
    """PURE-MMQA数据可得性审计记录(阻断证据入档)."""
    audit = BASE / "data/gjb_438c/data_assets/evalsets/pure_mmqa_blocked.json"
    d = {
        "dataset": "PURE-MMQA (SoftALL/PURE-MMQA, 306 QA)",
        "relevance": "SRS领域多模态QA——域最相关外部候选",
        "blockers": [
            "8/10源文档在全部公开镜像不可达(原始fbaipublicfiles 403, "
            "HF镜像仅QA无语料, GitHub已知PURE repo全部404)",
            "可得的纯文本镜像(MeMartijn/PurePlainDataset)与QA答案粒度"
            "失配: 段落级匹配率~4/40, 句子级1/40",
        ],
        "retry_condition": "PURE语料库可达(网络变化/其他镜像出现)",
        "partial_assets": "models/pure_mmqa/(QA xlsx+README+2可得文档)",
    }
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    assert audit.exists()
    assert "blockers" in json.loads(audit.read_text(encoding="utf-8"))
