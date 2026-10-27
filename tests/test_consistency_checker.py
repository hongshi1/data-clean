"""Task 1 v4.1 领域等价约定回归测试: 锁定域约定判定语义.

锁定的论文级声明:
  - 同值异表面(单位归一/算子族/引号恒等/集合重排) = consistent
  - 值突变/操作符族冲突/集合差/同义异名 = inconsistent
  - T1负向句式("没有「X」")的值不参与匹配
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.consistency.checker import ConsistencyChecker, normalize_unit

_C = ConsistencyChecker()

# (premise, hypothesis, expected_verdict, expected_channel, desc)
CASES = [
    # 领域等价约定: 单位归一(200G = 204800MB)
    ("可用空间不少于200G", "可用空间≥204800MB", "consistent", "numeric", "单位归一+同族算子"),
    ("可用空间200G以上", "可用空间204800MB以上", "consistent", "numeric", "后缀式单位归一"),
    # 领域等价约定: 算子族(不少于 ↔ ≥)
    ("支持节点不少于19种", "支持节点≥19种", "consistent", "numeric", "同族算子(ge)"),
    ("获取的数据资源不少于19种", "获取的数据资源不高于19种", "inconsistent", "numeric", "跨族算子(ge vs le)"),
    # 值突变
    ("可用空间200G以上", "可用空间100G以上", "inconsistent", "numeric", "同参数不同值"),
    ("「响应时间」不超过500ms", "「响应时间」不大于300ms", "inconsistent", "numeric", "同参数不同值(引号内)"),
    # 操作符族冲突(同值)
    ("「响应时间」不超过500ms", "「响应时间」不小于500ms", "inconsistent", "numeric", "le vs ge同值"),
    # 复合单位(字/秒, 以单位串为族)
    ("处理速度不低于1000字/秒", "处理速度大于等于1000字/秒", "consistent", "numeric", "复合单位+不低于/大于等于"),
    # eq族: 为 ↔ =
    ("宽度为120px", "宽度=120px", "consistent", "numeric", "eq族(为/=)"),
    # TERM-01: 同义异名
    ("支持「获取」功能", "支持「采集」功能", "inconsistent", "term", "K1同义异名"),
    # 枚举集合
    ("包括：数据获取、数据转换、数据组织", "包括：数据获取、数据转换", "inconsistent", "enum", "枚举集合缺失"),
    ("图中涉及元素：数据获取、数据转换", "图中涉及元素：数据转换、数据获取", "consistent", "enum", "无序语境重排(领域约定)"),
    # 引号恒等(表面归一)
    ("表11的描述包含「用户响应时间不小于3秒」", "表12的描述中包含「用户响应时间不小于3秒」", "consistent", "numeric", "TERM-02数值优先命中"),
    ("表11包含「选择目标库、表创建模式」", "表12中包含「选择目标库、表创建模式」", "consistent", "quote", "ENUM-02引号恒等"),
    # 图元素(存在性)
    ("该图中包含以下元素：用户、文电处理服务、网络资源定位", "该图中包含以下元素：用户、文电处理服务", "inconsistent", "enum", "图元素缺失"),
    ("该图中包含以下元素：用户、文电处理服务", "该图中包含以下元素：文电处理服务、用户", "consistent", "enum", "图元素重排"),
    # T1负向句式: 负向引用的值不参与匹配
    ("甲表中没有「获取的数据资源不少于19种」，对应内容为「获取的数据资源不少于38种」",
     "乙规定：获取的数据资源不少于19种", "inconsistent", "numeric", "T1负向句式取正向值38"),
    ("甲表中包含「可用空间200G以上」", "乙表中包含「可用空间204800MB以上」", "consistent", "numeric", "T1一致(单位归一)"),
]


def test_kd_cases() -> None:
    for prem, hyp, exp_verdict, exp_channel, desc in CASES:
        r = _C.check(prem, hyp)
        assert r.verdict == exp_verdict, f"[{desc}] verdict={r.verdict} 期望={exp_verdict}\nP={prem}\nH={hyp}"
        assert r.channel == exp_channel, f"[{desc}] channel={r.channel} 期望={exp_channel}"


def test_normalize_unit_families() -> None:
    # 时间族归一
    assert normalize_unit("1", "s") == (1000.0, "time")
    assert normalize_unit("1000", "ms") == (1000.0, "time")
    # 存储族归一
    assert normalize_unit("200", "G")[0] == 200 * 1073741824.0
    assert abs(normalize_unit("204800", "MB")[0] - normalize_unit("200", "G")[0]) < 0.01
    # 未知复合单位fallback: 以单位串为族名
    assert normalize_unit("1000", "字/秒") == (1000.0, "字/秒")
    # 无单位
    assert normalize_unit("19", "") == (19.0, "count")


def test_batch_consistency() -> None:
    pairs = [("可用空间不少于200G", "可用空间≥204800MB"),
             ("宽度为120px", "宽度=120px")]
    results = _C.check_batch(pairs)
    assert [r.verdict for r in results] == ["consistent", "consistent"]
    assert all(r.channel == "numeric" for r in results)


def test_numbered_order_channel() -> None:
    """v4.3编号条目通道: B族修复的回归锁.

    形态1(编号随条目走的对调): P"2、主...3、备" ↔ H"3、备...2、主" → inconsistent
    形态2(同编号不同内容): 编号错位 → inconsistent
    健全化规则: 同编号同序同内容 → 通道让位(None), 不判consistent(局部证据)
    """
    # 形态1: 编号对调(真实ORDER_CONFLICT形态)
    r = _C._check_numbered(
        "功能表规定，2、主达梦库同步异常、PZXQ-A、记录X、沿用、3、备达梦库同步异常、PZXQ-B、记录Y",
        "功能表规定，3、备达梦库同步异常、PZXQ-B、记录Y、沿用、2、主达梦库同步异常、PZXQ-A、记录X")
    assert r is not None and r.verdict == "inconsistent" and r.channel == "numbered"
    # 形态2: 同编号不同内容
    r2 = _C._check_numbered("功能表规定，1、数据获取，2、数据转换",
                            "功能表规定，1、数据获取，2、数据引接")
    assert r2 is not None and r2.verdict == "inconsistent"
    # 健全化: 全一致 → None(让位, 不证明全pair等价)
    r3 = _C._check_numbered("功能表规定，1、数据获取、PZXQ-A，2、数据转换、PZXQ-B",
                            "功能表规定，1、数据获取、PZXQ-A，2、数据转换、PZXQ-B")
    assert r3 is None
    # 无编号条目不触发; 数值对不触发
    assert _C._check_numbered("包括：A、B、C", "包括：B、A、C") is None
    assert _C._check_numbered("支持节点不少于19种", "支持节点≥19种") is None
