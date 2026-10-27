"""κ_P正文编译器单元测试: 用真实pair文本做金样本断言."""
from __future__ import annotations

import re

from algorithms.blackboard.prose_compiler import (ID_PAT, compile_prose,
                                                  prose_item_names)

# 真实文本: pair_dataset/sc1_usecase_capability/1_001/text.txt 首段
REAL_TEXT = (
    "数据获取针对各业务部门的海量多源异构数据资源、其他外部数据资源等，"
    "提供精准可靠、自动人工互补、便捷可扩展的数据引接汇聚工具手段，实现全域数据接入能力。"
    "通过采用离线数据报送、在线数据抽取、实时数据采集等方式，"
    "实现对数据中台结构化数据、半结构化数据、非结构化数据和流式数据资源的引接归集。"
    "数据归集根据数据结构、内容、时效性的区别，提供不同的数据归集手段，"
    "包括结构化数据归集、半结构化数据归集、非结构化数据归集、流式数据归集。"
)

CONSTRAINT_TEXT = "系统存储容量不低于256GB，磁盘剩余空间不少于100GB，响应时间不大于500ms。"

REF_TEXT = "具体处理流程如图3所示，参数定义见表34，详见3.2.1.2节。"


def test_enumeration_extracts_gjb_capability_list():
    c = compile_prose(REAL_TEXT, subject_hint="所有功能标识")
    items = prose_item_names(c)
    # "包括"后的四大归集功能必须完整提出(sc1检测的核心观察面)
    for expect in ("结构化数据归集", "半结构化数据归集",
                   "非结构化数据归集", "流式数据归集"):
        assert expect in items
    # "采用"后的三种采集方式
    for expect in ("离线数据报送", "在线数据抽取", "实时数据采集"):
        assert expect in items
    # 枚举项干净: 无"等"残渣/无逗号/无句号
    assert all("等" not in it and "，" not in it and "," not in it
               and "。" not in it for it in items)


def test_constraints_extract_op_value_unit():
    c = compile_prose(CONSTRAINT_TEXT)
    assert len(c["constraints"]) == 3
    storage = next(k for k in c["constraints"] if "存储" in k["param_hint"])
    assert storage["op"] == "ge" and storage["value"] == 256 and storage["unit"] == "GB"
    disk = next(k for k in c["constraints"] if "磁盘" in k["param_hint"])
    assert disk["op"] == "ge" and disk["value"] == 100
    rt = next(k for k in c["constraints"] if "响应" in k["param_hint"])
    # "不大于" = le (修复: 旧版会误解析为"大于"gt)
    assert rt["op"] == "le" and rt["value"] == 500 and rt["unit"] == "ms"


def test_references_and_roles():
    c = compile_prose(REF_TEXT)
    kinds = {(r["kind"], r["target"]) for r in c["references"]}
    assert ("figure", "3") in kinds
    assert ("table", "34") in kinds
    assert ("section", "3.2.1.2") in kinds
    # 句角色: 引用句
    assert 0 in c["sentence_roles"]


def test_behavior_verb_object():
    c = compile_prose(REAL_TEXT, subject_hint="所有功能标识")
    assert c["behaviors"], "至少提取出一个(动词,宾语)"
    first = c["behaviors"][0]
    assert first["verb"] in ("提供", "实现", "支持", "采用")
    assert first["object"]
    assert first["subject_hint"] == "所有功能标识"


def test_id_regex_fixes_8char_prefix_limit():
    """回归: 旧ID正则[A-Z]{2,8}前缀对长ID提取出截断错误ID — 05_method_roadmap缺陷#6."""
    old = re.compile(r'[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}')
    long_id = "ZZSJHQZHFW-GN-SJHQ-JGHSJGJ"
    text = f"功能标识为{long_id}的子功能"
    m_old = old.search(text)
    # 旧版要么漏检, 要么提取出截断的错误ID(丢前缀)
    assert m_old is None or m_old.group(0) != long_id
    m = ID_PAT.search(text)
    assert m is not None and m.group(0) == long_id
    # 普通长度ID不受影响
    assert ID_PAT.search("PZXQ-GN-FWYXKZ") is not None


def test_compile_prose_empty_and_idempotent():
    assert compile_prose("")["n_sentences"] == 0
    c1 = compile_prose(REAL_TEXT)
    c2 = compile_prose(REAL_TEXT)
    assert c1 == c2  # 确定性
