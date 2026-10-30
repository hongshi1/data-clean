"""包内自检: 3条手工构造evidence样例跑fast档, 覆盖三态判定.

用法(独立运行, 无需研究仓库):
    cd srs_verify_package
    python -m srs_verify.smoke_test

预期: support / refute / not_in_evidence 各一条, 退出码0.
"""
from __future__ import annotations

import sys

from srs_verify import CascadeVerifier

#: 1) support: answer的项目唯一标识符出现在证据文本中(标识符通道命中)
SAMPLE_SUPPORT = {
    "question": "连接池配置用例的项目唯一标识符是什么？",
    "answer": "PZXQ-GN-LJCGL-LJCPZ",
    "evidence": [{"text": "3.2.5.1 连接池管理-连接池配置"
                          "（PZXQ-GN-LJCGL-LJCPZ）"}],
}

#: 2) refute: 同主体(连接超时时间)数值约束互斥(证据30秒 vs 答案60秒)
SAMPLE_REFUTE = {
    "question": "连接超时时间要求是多少？",
    "answer": "连接超时时间为60秒。",
    "evidence": [{"text": "连接池最大连接数为100，初始连接数为10，"
                          "连接超时时间为30秒。"}],
}

#: 3) not_in_evidence: 开放世界——证据只覆盖部分成员(YAML不可核对)
SAMPLE_NIE = {
    "question": "数据导入功能支持哪些数据格式？",
    "answer": "数据导入功能支持CSV、JSON、XML以及YAML格式。",
    "evidence": [{"text": "数据导入功能支持CSV、JSON格式文件的导入。"}],
}


def main() -> int:
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    cases = [
        ("support", SAMPLE_SUPPORT),
        ("refute", SAMPLE_REFUTE),
        ("not_in_evidence", SAMPLE_NIE),
    ]
    failed = False
    for expected, sample in cases:
        result = verifier.verify(sample["question"], sample["answer"],
                                 sample["evidence"])
        mark = "OK " if result.verdict == expected else "FAIL"
        failed = failed or result.verdict != expected
        print(f"[{mark}] 期望={expected:<16} 实际={result.verdict:<16}"
              f" refs={list(result.evidence_refs)}"
              f" latency={result.latency_ms:.1f}ms")
        print(f"       rationale: {result.rationale[:160]}")
    if failed:
        print("smoke test FAILED", file=sys.stderr)
        return 1
    print("smoke test PASSED (3/3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
