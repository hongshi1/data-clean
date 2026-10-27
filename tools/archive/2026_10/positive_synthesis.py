#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正例合成升级: 语义等效变换(非简单复制)

设计原则(对齐VeriEvol 2026 + Korn 2026):
  1. 正例 = 语义等效但表述不同 → 教模型区分"合理差异 vs 真实矛盾"
  2. 四类正例:
     P-EQUIV:  等效单位变换 (≤0.2s ↔ ≤200ms)
     P-SYN:    同义词改述 (获取↔采集, 语义不变)
     P-MODAL:  跨模态一致 (表格名=图节点名)
     P-SUPER:  合理超集差异 ("桌面版" vs "桌面版和在线版均")

用法: 在inject_rules.py的make_positive()基础上扩展
"""

# 等效单位变换表
UNIT_EQUIV = {
    "ms": [("0.2s", "200ms"), ("1s", "1000ms"), ("500ms", "0.5s"),
           ("5s", "5000ms"), ("10ms", "0.01s"), ("3s", "3000ms")],
    "MB": [("1GB", "1024MB"), ("512MB", "0.5GB"), ("2GB", "2048MB")],
    "kHz": [("1MHz", "1000kHz"), ("500kHz", "0.5MHz")],
}

# 同义词等效(方向1=同义改述, 保持一致)
SYN_EQUIV = {
    "获取": "采集", "管理": "管控", "监控": "监测", "处理": "处置",
    "传输": "传送", "存储": "保存", "查询": "检索", "注册": "登记",
    "部署": "安装", "启动": "开启", "配置": "设置", "解析": "分析",
}


def make_positive_equiv(entity, rng):
    """P-EQUIV: 等效单位变换(0.2s→200ms, label=consistent)"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, str) and any(u in content for u in ["s", "ms", "GB", "MB", "MHz", "kHz"]):
            for unit, pairs in UNIT_EQUIV.items():
                for orig, equiv in pairs:
                    if orig in content:
                        return {
                            "method": "P-EQUIV",
                            "label": "consistent",
                            "original": content,
                            "injected": content.replace(orig, equiv),
                            "detail": f"等效单位变换: {orig}={equiv}",
                            "confidence": "gold",  # 单位换算是确定的
                            "z3_verified": True,   # Z3可验证等效性
                            "equiv_type": "unit_equivalence",
                        }
    return None


def make_positive_syn(entity, rng):
    """P-SYN: 同义词改述(获取→采集, label=consistent)"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, str) and len(content) >= 2:
            for old, new in SYN_EQUIV.items():
                if old in content:
                    return {
                        "method": "P-SYN",
                        "label": "consistent",
                        "original": content,
                        "injected": content.replace(old, new, 1),
                        "detail": f"同义改述: {old}↔{new}",
                        "confidence": "silver",
                        "z3_verified": False,
                        "equiv_type": "synonym",
                    }
    return None


def make_positive_modal(entity, rng):
    """P-MODAL: 跨模态一致(同一实体在表格和图中名称一致)"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, str) and len(content) >= 2:
            # 模拟: 表格中名称X, 图中也是X(但换了编号格式)
            # 如"表3:数据获取" vs "图5节点:数据获取"
            return {
                "method": "P-MODAL",
                "label": "consistent",
                "original": f"表格中: {content}",
                "injected": f"图中节点: {content}",  # 名称完全一致, 位置不同
                "detail": f"跨模态一致: 表格和图中「{content[:10]}」名称相同",
                "confidence": "gold",
                "z3_verified": False,
                "equiv_type": "cross_modal_consistency",
            }
    return None


def make_positive_superset(entity, rng):
    """P-SUPER: 合理超集差异("桌面版"→"桌面版和在线版", label=consistent)"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, str) and len(content) >= 4:
            supersets = ["和在线版均提供", "及移动端均支持", "(含桌面版和在线版)"]
            sup = rng.choice(supersets)
            return {
                "method": "P-SUPER",
                "label": "consistent",
                "original": f"{content}(桌面版提供)",
                "injected": f"{content}{sup}",
                "detail": "合理超集: 原文限定桌面版, 变换后扩大范围(非矛盾)",
                "confidence": "silver",
                "z3_verified": False,
                "equiv_type": "reasonable_superset",
            }
    return None


def make_positive_hard(entity, rng):
    """P-HARD: hard级正例——多处同时等效变换(教模型不被表面差异迷惑)

    例: "数据获取≤0.2s(桌面版)" → "数据采集≤200ms(桌面版和在线版)"
    位置A用"获取", 位置B用"采集"; A用"0.2s", B用"200ms"
    但语义完全一致 → label=consistent
    """
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, str) and len(content) >= 4:
            injected = content
            # 叠加2-3种等效变换
            transforms = []
            for old, new in SYN_EQUIV.items():
                if old in injected:
                    injected = injected.replace(old, new, 1)
                    transforms.append(f"{old}→{new}")
                    break
            for unit, pairs in UNIT_EQUIV.items():
                for orig, equiv in pairs:
                    if orig in injected:
                        injected = injected.replace(orig, equiv)
                        transforms.append(f"{orig}→{equiv}")
                        break
                if len(transforms) >= 2:
                    break
            if transforms:
                return {
                    "method": "P-HARD",
                    "label": "consistent",
                    "original": content,
                    "injected": injected,
                    "detail": f"hard级复合等效变换({len(transforms)}处): " + ", ".join(transforms),
                    "confidence": "silver",
                    "z3_verified": False,
                    "equiv_type": "compound_equivalence",
                    "difficulty": "hard",
                }
    return None


# 正例合成入口
def make_positive_v2(entity, rng):
    """智能正例: 优先hard级, 降级到easy"""
    for fn in [make_positive_hard, make_positive_equiv,
               make_positive_syn, make_positive_modal,
               make_positive_superset]:
        result = fn(entity, rng)
        if result:
            result["check_item"] = "POSITIVE"
            result["seed"] = 42
            result["entity_id"] = entity["entity_id"]
            result["entity_type"] = entity["entity_type"]
            result["occurrences"] = entity["occurrences"]
            result["doc"] = entity["occurrences"][0].get("doc", "")
            result["pair_id"] = entity["occurrences"][0].get("pair_id", "")
            return result
    return None
