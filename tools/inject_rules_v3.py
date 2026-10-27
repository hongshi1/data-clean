#!/usr/bin/env python3
"""40项校验严格对齐注入方法 (v3 — 全部修复)

严格遵从实施方案文档40项校验体系：
  术语8项 + 参数10项 + 逻辑11项 + GJB 11项 = 40种注入

修复内容:
  P0: Z3 gate操作符方向匹配
  P0: TERM-02同名异义occurrences增加definition
  P1: GJB层构造真实缺失条款(两位置对比)
  P1: LOGIC-06~11从chunks提取真实约束
  P2: TERM-06量纲单位从params提取
  P2: TERM-07信号接口扩大映射
  P2: PARAM-04/08/09/10放宽正则
  P2: GJB-11降级运行补充关键词
"""
import json
import re
import random
from pathlib import Path
from collections import defaultdict
from z3 import Real, Solver, unsat

BASE = Path(__file__).resolve().parent.parent
ENTITIES_PATH = BASE / "data/gjb_438c/data_assets/eval_entities.json"
CHUNKS_PATH = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
VLM_FLOWCHART = BASE / "data/gjb_438c/data_assets/vlm_flowchart_extract.jsonl"
OUT_PATH = BASE / "data/gjb_438c/data_assets/eval_injected_v3.json"

SEED = 42
PER_ITEM = 5


def z3_gate(param_name, constraints_a, constraints_b):
    s = Solver()
    x = Real(param_name)
    for op, val in constraints_a + constraints_b:
        if op == "ge":
            s.add(x >= val)
        elif op == "le":
            s.add(x <= val)
        elif op == "gt":
            s.add(x > val)
        elif op == "lt":
            s.add(x < val)
        elif op == "eq":
            s.add(x == val)
    return s.check() == unsat


SYN_MAP = {
    "获取": "采集", "管理": "管控", "监控": "监测", "处理": "处置",
    "传输": "传送", "存储": "保存", "查询": "检索", "注册": "登记",
    "部署": "安装", "启动": "开启", "关闭": "停止", "删除": "移除",
    "修改": "变更", "添加": "新增", "配置": "设置", "加载": "载入",
    "捕捉": "捕获", "归集": "汇集", "转换": "变换", "发布": "分发",
}

ALERT_MAP = {
    "告警": "警示", "异常": "故障", "错误": "失误", "警告": "提醒",
    "失败": "失效", "超时": "过期", "中断": "断开", "溢出": "越界",
}

CMD_MAP = {"启动": "开启", "停止": "终止", "查询": "搜索", "发送": "推送",
           "接收": "获取", "创建": "新建", "删除": "清除", "更新": "刷新",
           "加载": "装入", "执行": "运行", "连接": "链接", "断开": "分离"}

IFACE_MAP = {"接口": "通道", "端口": "连接", "总线": "链路", "信号": "通道",
             "服务": "功能", "模块": "组件", "组件": "部件", "通道": "链路"}

GJB_KEYWORDS = {
    "testable": ["可测试", "验证方法", "确认方法", "稳定运行", "性能良好", "正常运行"],
    "faulttolerant": ["容错", "冗余", "备份", "故障转移", "热备", "冷备", "主备"],
    "security": ["访问控制", "权限控制", "身份认证", "授权", "安全防护", "角色"],
    "audit": ["审计日志", "操作日志", "日志记录", "审计追踪", "操作审计"],
    "traceability": ["追溯", "追踪关系", "映射关系", "需求对应", "测试对应"],
    "alarm": ["报警", "告警", "警示", "预警", "故障告警", "异常报警"],
    "selfcheck": ["自检", "开机检测", "启动检测", "自测试", "BIT", "开机自检"],
    "powerfail": ["掉电", "断电", "电源故障", "UPS", "掉电保护", "断电保护"],
    "input": ["输入校验", "合法性校验", "数据校验", "输入防护", "边界检查", "输入验证"],
    "upgrade": ["版本升级", "软件升级", "回滚", "版本回退", "热更新", "在线升级"],
    "degrade": ["降级", "退化", "降级运行", "降级模式", "最低功能", "功能降级", "性能降级", "降级处理"],
}

PARAM_PATTERNS = {
    "time": re.compile(r'(\d+\.?\d*)\s*(ms|毫秒|s|秒|min|分钟)'),
    "period": re.compile(r'(?:周期|间隔|频率|定时)\D{0,10}(\d+\.?\d*)\s*(ms|毫秒|s|秒|min|分钟|Hz|kHz)'),
    "threshold": re.compile(r'(?:阈值|门限|临界|触发|启动条件|判定条件)\D{0,15}(\d+\.?\d*)\s*(ms|毫秒|s|秒|%|GB|MB|次|个|度|倍)'),
    "align": re.compile(r'(?:对齐|同步|校准)\D{0,15}(\d+\.?\d*)\s*(ms|毫秒|us|微秒|s|秒|ns|纳秒|%|个)'),
    "resource": re.compile(r'(?:CPU|内存|存储|磁盘|带宽|资源占用)\D{0,10}(\d+\.?\d*)\s*(GHz|MHz|GB|MB|TB|Mbps|Gbps|%|核|个)'),
    "range": re.compile(r'(?:值域|范围|区间|不小于|不大于|大于|小于|至少|至多)\D{0,10}(\d+\.?\d*)\s*(GB|MB|TB|GHz|MHz|ms|秒|%|个|条|路|度)'),
    "storage": re.compile(r'(?:保存|存储|保留|留存|备份保留)\D{0,10}(\d+\.?\d*)\s*(天|日|月|年|小时|hour|h|GB|MB|TB)'),
    "precision": re.compile(r'(?:精度|误差|偏差|准确度|精确度)\D{0,120}?(\d+(?:\.\d+)?)\s*(ms|毫秒|s|秒|us|微秒|ns|nm|m|米|%|位|字节|byte|bit|MHz|kHz|GHz)', re.S),
    "degrade": re.compile(r'(?:降级|退化|最低|最小功能|功能降级|性能降级)\D{0,20}(\d+\.?\d*)\s*(%|ms|秒|min|分钟|GB|MB|个|倍|级)'),
    "fault": re.compile(r'(?:故障|失效|超时|判定|隔离)\D{0,20}(\d+\.?\d*)\s*(s|秒|ms|毫秒|min|分钟|次|个|%)'),
}

LOGIC_KEYWORDS = {
    "mutex": ["互斥", "不能同时", "单独执行", "排他"],
    "atomic": ["原子", "不可中断", "完整执行", "全部完成"],
    "arbitration": ["仲裁", "优先", "主用", "备用", "主备"],
    "permission": ["权限", "管理员", "普通用户", "授权", "角色"],
    "recovery": ["恢复", "自动恢复", "手动恢复", "重启", "回退"],
    "research": ["重新搜索", "重搜", "全量", "增量", "重新查找"],
}


def load_entities():
    with open(ENTITIES_PATH) as f:
        return json.load(f)["entities"]

def load_chunks():
    with open(CHUNKS_PATH) as f:
        return json.load(f)

def load_vlm_flowchart():
    results = []
    if VLM_FLOWCHART.exists():
        with open(VLM_FLOWCHART) as f:
            for line in f:
                results.append(json.loads(line))
    return results


def _clean_text(text):
    t = re.sub(r'<[^>]+>', '', text)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def _extract_sentence(text, keyword, max_len=120):
    idx = text.find(keyword)
    if idx < 0:
        return None
    s = text.rfind('。', 0, idx)
    start = s + 1 if s >= 0 else max(0, idx - 50)
    e = text.find('。', idx)
    end = e + 1 if e >= 0 else min(len(text), idx + 80)
    sent = text[start:end].strip()
    sent = _clean_text(sent)
    if len(sent) < 10 or len(sent) > max_len:
        return None
    return sent

def extract_params_from_chunks(chunks):
    params = defaultdict(list)
    seen = set()
    for chunk in chunks:
        text = chunk.get("text", "")
        doc = chunk.get("doc", "")
        section = chunk.get("section", "")
        for ptype, pattern in PARAM_PATTERNS.items():
            for m in pattern.finditer(text):
                val = float(m.group(1))
                unit = m.group(2) if m.lastindex >= 2 else ""
                key = (ptype, val, unit, doc, section)
                if key in seen:
                    continue
                seen.add(key)
                op = "eq"
                pre = text[max(0, m.start()-15):m.start()]
                if "不小于" in pre or "至少" in pre or "≥" in pre:
                    op = "ge"
                elif "不大于" in pre or "至多" in pre or "≤" in pre:
                    op = "le"
                elif "大于" in pre or "超过" in pre or ">" in pre:
                    op = "gt"
                elif "小于" in pre or "低于" in pre or "<" in pre:
                    op = "lt"
                ctx = _clean_text(text[max(0, m.start()-30):m.end()+10])
                params[ptype].append({
                    "val": val, "unit": unit, "op": op,
                    "doc": doc, "section": section, "context": ctx[:100]
                })
    return params

def extract_gjb_clauses(chunks):
    clauses = defaultdict(list)
    seen = set()
    for chunk in chunks:
        text = chunk.get("text", "")
        doc = chunk.get("doc", "")
        section = chunk.get("section", "")
        for gtype, keywords in GJB_KEYWORDS.items():
            for kw in keywords:
                sent = _extract_sentence(text, kw)
                if sent:
                    key = (gtype, sent[:50])
                    if key not in seen:
                        seen.add(key)
                        clauses[gtype].append({
                            "keyword": kw, "doc": doc, "section": section, "sentence": sent
                        })
    return clauses

def extract_logic_constraints(chunks):
    constraints = defaultdict(list)
    seen = set()
    for chunk in chunks:
        text = chunk.get("text", "")
        doc = chunk.get("doc", "")
        section = chunk.get("section", "")
        for ltype, keywords in LOGIC_KEYWORDS.items():
            for kw in keywords:
                sent = _extract_sentence(text, kw)
                if sent:
                    key = (ltype, sent[:50])
                    if key not in seen:
                        seen.add(key)
                        constraints[ltype].append({
                            "keyword": kw, "doc": doc, "section": section, "sentence": sent
                        })
    return constraints


# ========== 术语层8种 ==========

def inject_TERM_01(entity, rng):
    occs = entity.get("occurrences", [])
    name = occs[0].get("content", "") if occs else ""
    if not isinstance(name, str) or len(name) < 2:
        return None
    for old, new in SYN_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-01", "synonym", entity, name, injected,
                         f"位置A'{name}' vs 位置B'{injected}'({old}→{new})", "silver")
    return None

def inject_TERM_02(entity, rng):
    """②同名异义：同一名称在不同位置定义不同概念"""
    occs = entity.get("occurrences", [])
    name = occs[0].get("content", "") if occs else ""
    if not isinstance(name, str) or len(name) < 2:
        return None
    DEFS = [
        ("低功耗运行模式", "故障保护模式"),
        ("数据加密模式", "维护诊断模式"),
        ("用户安全模式", "系统保护模式"),
        ("安全防护模式", "安全保密模式"),
    ]
    d1, d2 = rng.choice(DEFS)
    new_occs = []
    for i, occ in enumerate(occs[:4]):
        new_occ = dict(occ)
        new_occ["definition"] = d1 if i == 0 else d2
        new_occ["content"] = f"{name}（{d1 if i == 0 else d2}）"
        new_occs.append(new_occ)
    return _build("TERM-02", "homonym", entity, f"{name}（{d1}）", f"{name}（{d2}）",
                 f"位置A'{name}'定义为'{d1}'，位置B'{name}'定义为'{d2}'", "silver",
                 occurrences_override=new_occs)

def inject_TERM_03(entity, rng):
    for occ in entity.get("occurrences", []):
        content = occ.get("content", [])
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return _build("TERM-03", "enum_missing", entity, content, injected,
                         f"文本{len(content)}种 vs 图{len(injected)}种", "silver")
    return None

def inject_TERM_04(entity, rng):
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 2:
        return None
    for old, new in ALERT_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-04", "alert_term", entity, name, injected,
                         f"位置A'{name}' vs 位置B'{injected}'", "silver")
    injected = name.replace("告警", "报警") if "告警" in name else None
    if not injected and "报警" in name:
        injected = name.replace("报警", "告警")
    if injected and injected != name:
        return _build("TERM-04", "alert_term", entity, name, injected,
                     f"位置A'{name}' vs 位置B'{injected}'", "silver")
    return None

def inject_TERM_05(entity, rng):
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 2:
        return None
    for old, new in CMD_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-05", "command_name", entity, name, injected,
                         f"位置A'{name}' vs 位置B'{injected}'", "silver")
    return None

def inject_TERM_06_from_params(params, rng):
    """⑥量纲单位一致性：≤0.2s vs ≤20ms（冲突）"""
    for ptype in ["time", "period"]:
        candidates = params.get(ptype, [])
        for p in candidates:
            val = p["val"]
            unit = p["unit"]
            conv = {"秒": ("ms", 1000), "s": ("ms", 1000), "ms": ("us", 1000),
                    "分钟": ("秒", 60), "min": ("s", 60)}
            if unit in conv:
                new_unit, factor = conv[unit]
                original = f"{val}{unit}"
                injected = f"{val}{new_unit}"
                correct = f"{val*factor}{new_unit}"
                occs = [
                    {"location": "text", "section": p["section"], "content": original, "doc": p["doc"]},
                    {"location": "table", "section": p["section"], "content": injected, "doc": p["doc"]},
                ]
                return _build("TERM-06", "unit_conflict", None, original, injected,
                             f"位置A'{original}' vs 位置B'{injected}'（正确应换算为'{correct}'）", "gold",
                             occurrences_override=occs, doc=p["doc"], section=p["section"])
    return None

def inject_TERM_07(entity, rng):
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 2:
        return None
    for old, new in IFACE_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-07", "signal_name", entity, name, injected,
                         f"位置A'{name}' vs 位置B'{injected}'", "silver")
    pos = rng.randint(0, len(name) - 1)
    old_c = name[pos]
    new_c = chr(ord(old_c) + 1) if ord(old_c) < 0x9FFF else chr(ord(old_c) - 1)
    injected = name[:pos] + new_c + name[pos+1:]
    return _build("TERM-07", "signal_name", entity, name, injected,
                 f"位置A'{name}' vs 位置B'{injected}'", "silver")

def inject_TERM_08(entity, rng):
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 4:
        return None
    chars = name[:4]
    abbr = ''.join(f'{ord(c) % 26 + 65}' for c in chars)
    return _build("TERM-08", "abbreviation", entity, name, abbr,
                 f"位置A全称'{name}' vs 位置B缩写'{abbr}'", "silver")


# ========== 参数层10种 (Z3 gate修复) ==========

def inject_PARAM(params_by_type, ptype, param_id, rng):
    """参数注入：根据操作符方向选择注入值，确保Z3验证通过"""
    candidates = params_by_type.get(ptype, [])
    if not candidates:
        return None
    p = rng.choice(candidates)
    val = p["val"]
    unit = p["unit"]
    op = p.get("op", "ge")
    
    conflict_map = {"ge": "lt", "le": "gt", "gt": "le", "lt": "ge", "eq": "lt"}
    conflict_op = conflict_map.get(op, "lt")
    
    if op in ("ge", "gt"):
        injected_val = val * 0.5
    elif op in ("le", "lt"):
        injected_val = val * 2
    else:
        injected_val = val * 2
        op = "le"
        conflict_op = "gt"
    
    constraints_a = [(op, val)]
    constraints_b = [(conflict_op, injected_val)]
    z3_ok = z3_gate(ptype, constraints_a, constraints_b)
    
    op_sym = {"ge": "≥", "le": "≤", "gt": ">", "lt": "<", "eq": "="}
    original = f"{op_sym.get(op, op)}{val}{unit}"
    injected = f"{op_sym.get(conflict_op, conflict_op)}{injected_val}{unit}"
    
    occs = [
        {"location": "text", "section": p["section"], "content": original, "doc": p["doc"]},
        {"location": "table", "section": p["section"], "content": injected, "doc": p["doc"]},
    ]
    
    return _build(param_id, f"param_{ptype}", None, original, injected,
                 f"位置A'{original}' vs 位置B'{injected}' (Z3={'unsat' if z3_ok else 'sat'})",
                 "gold", z3_ok, occurrences_override=occs, doc=p["doc"], section=p["section"])


# ========== 逻辑层11种 ==========

def inject_LOGIC_01(vlm_data, rng):
    for vlm in vlm_data:
        branches = vlm.get("branches", [])
        if len(branches) >= 2:
            doc = vlm.get("doc", "")
            sec = vlm.get("section", "")
            occs = [
                {"location": "text", "section": sec, "content": "应急模式优先级最高", "doc": doc},
                {"location": "image", "section": sec, "content": f"状态机允许{branches[0]}→{branches[1]}转移", "doc": doc},
            ]
            return _build("LOGIC-01", "priority_conflict", None,
                         "应急模式优先级最高", "自动模式可抢占应急模式",
                         "正文'应急最高' vs 状态机'自动可夺回'", "silver",
                         occurrences_override=occs, doc=doc, section=sec)
    return None

def inject_LOGIC_02(vlm_data, rng):
    for vlm in vlm_data:
        nodes = vlm.get("nodes", [])
        if any("异常" in n or "故障" in n for n in nodes):
            doc = vlm.get("doc", "")
            sec = vlm.get("section", "")
            occs = [
                {"location": "text", "section": sec, "content": "异常时切换备用通道", "doc": doc},
                {"location": "image", "section": sec, "content": "异常时重试3次", "doc": doc},
            ]
            return _build("LOGIC-02", "exception_strategy", None,
                         "异常时切换备用通道", "异常时重试3次",
                         "正文'切换备用' vs 用例表'重试3次'", "silver",
                         occurrences_override=occs, doc=doc, section=sec)
    return None

def inject_LOGIC_03(vlm_data, rng):
    for vlm in vlm_data:
        nodes = vlm.get("nodes", [])
        if len(nodes) >= 3:
            doc = vlm.get("doc", "")
            sec = vlm.get("section", "")
            original = nodes[:3]
            injected = [nodes[1], nodes[0]] + nodes[2:]
            occs = [
                {"location": "text", "section": sec, "content": " → ".join(original), "doc": doc},
                {"location": "image", "section": sec, "content": " → ".join(injected), "doc": doc},
            ]
            return _build("LOGIC-03", "sequence_swap", None, original, injected,
                         f"正文{original[:2]} vs 流程图{injected[:2]}", "silver",
                         occurrences_override=occs, doc=doc, section=sec)
    return None

def inject_LOGIC_04(vlm_data, rng):
    for vlm in vlm_data:
        direction = vlm.get("data_flow_direction", "")
        if direction:
            doc = vlm.get("doc", "")
            sec = vlm.get("section", "")
            conflict = "双向" if "单" in direction else "单向"
            occs = [
                {"location": "image", "section": sec, "content": direction, "doc": doc},
                {"location": "text", "section": sec, "content": conflict, "doc": doc},
            ]
            return _build("LOGIC-04", "dataflow_reverse", None,
                         direction, conflict,
                         f"框图'{direction}' vs 正文'{conflict}'", "silver",
                         occurrences_override=occs, doc=doc, section=sec)
    return None

def inject_LOGIC_05(vlm_data, rng):
    for vlm in vlm_data:
        branches = vlm.get("branches", [])
        if len(branches) >= 2:
            doc = vlm.get("doc", "")
            sec = vlm.get("section", "")
            injected = branches[:-1]
            occs = [
                {"location": "text", "section": sec, "content": branches, "doc": doc},
                {"location": "image", "section": sec, "content": injected, "doc": doc},
            ]
            return _build("LOGIC-05", "branch_missing", None,
                         branches, injected,
                         f"文本{len(branches)}类 vs 流程图{len(injected)}类", "silver",
                         occurrences_override=occs, doc=doc, section=sec)
    return None

def inject_LOGIC_from_chunks(logic_constraints, ltype, logic_id, conflict_desc, rng):
    """从chunks提取真实逻辑约束，构造矛盾"""
    candidates = logic_constraints.get(ltype, [])
    if not candidates:
        return None
    c = rng.choice(candidates)
    sent = c["sentence"]
    doc = c["doc"]
    sec = c["section"]
    CONFLICTS = {
        "mutex": "A和B可同时并行执行",
        "atomic": "任务切换可被中断",
        "arbitration": "备用数据优先于主用数据",
        "permission": "普通用户可直接修改配置",
        "recovery": "需手动重启恢复",
        "research": "仅搜索增量数据",
    }
    conflict = CONFLICTS.get(ltype, "与原文矛盾的描述")
    occs = [
        {"location": "text", "section": sec, "content": sent, "doc": doc},
        {"location": "table", "section": sec, "content": conflict, "doc": doc},
    ]
    return _build(logic_id, f"logic_{ltype}", None, sent, conflict,
                 f"正文'{sent[:40]}' vs 设计说明'{conflict}'", "silver",
                 occurrences_override=occs, doc=doc, section=sec)


# ========== GJB合规层11种 ==========

def inject_GJB_v2(gjb_clauses, gtype, gjb_id, rng):
    """GJB合规注入：构造两位置对比（位置A有条款，位置B缺失）"""
    candidates = gjb_clauses.get(gtype, [])
    if not candidates:
        return None
    c = rng.choice(candidates)
    sent = c["sentence"]
    doc = c["doc"]
    sec = c["section"]
    kw = c["keyword"]
    
    VAGUE_REQS = ["系统应运行稳定", "系统性能良好", "系统正常工作",
                  "系统应保持稳定", "系统应可靠运行"]
    
    if gtype == "testable":
        vague = rng.choice(VAGUE_REQS)
        occs = [
            {"location": "text", "section": sec, "content": sent, "doc": doc},
            {"location": "table", "section": sec, "content": vague, "doc": doc},
        ]
        return _build("GJB-01", "vague_requirement", None,
                     sent, vague,
                     f"模糊需求'{vague}'不可测试（原文：{sent[:40]}）", "gold",
                     occurrences_override=occs, doc=doc, section=sec)
    
    GJB_INFO = {
        "faulttolerant": ("GJB-02", "faulttolerant_missing", "故障容错条款缺失"),
        "security": ("GJB-03", "security_missing", "安全访问控制条款缺失"),
        "audit": ("GJB-04", "audit_missing", "审计日志条款缺失"),
        "traceability": ("GJB-05", "trace_broken", "需求可追溯性断裂"),
        "alarm": ("GJB-06", "alarm_missing", "异常报警要素缺失"),
        "selfcheck": ("GJB-07", "selfcheck_missing", "软件自检条款缺失"),
        "powerfail": ("GJB-08", "powerfail_missing", "掉电数据保护条款缺失"),
        "input": ("GJB-09", "input_missing", "输入数据防护条款缺失"),
        "upgrade": ("GJB-10", "upgrade_missing", "版本升级安全条款缺失"),
        "degrade": ("GJB-11", "degrade_missing", "降级运行条款缺失"),
    }
    
    if gtype in GJB_INFO:
        gid, method, desc = GJB_INFO[gtype]
        occs = [
            {"location": "text", "section": sec, "content": sent, "doc": doc},
            {"location": "table", "section": sec, "content": f"（该条款缺失：{desc}）", "doc": doc},
        ]
        return _build(gid, method, None,
                     sent, "（条款缺失）",
                     f"{desc}：位置A有'{kw}'相关条款，位置B缺失", "gold",
                     occurrences_override=occs, doc=doc, section=sec)
    return None


# ========== 工具函数 ==========

def _build(check_item, method, entity, original, injected, detail,
           confidence, z3_verified=False, doc="", section="", extra=None,
           occurrences_override=None):
    result = {
        "check_item": check_item,
        "method": method,
        "original": original,
        "injected": injected,
        "detail": detail,
        "label": "inconsistent",
        "confidence": confidence,
        "z3_verified": z3_verified,
        "doc": doc,
        "section": section,
        "seed": SEED,
    }
    if occurrences_override:
        result["occurrences"] = occurrences_override
    elif entity:
        result["entity_id"] = entity.get("entity_id", "")
        result["entity_type"] = entity.get("entity_type", "")
        result["occurrences"] = entity.get("occurrences", [])
    if extra:
        result["extra"] = extra
    return result

def _positive(entity):
    occs = entity.get("occurrences", [])
    content = occs[0].get("content", "") if occs else ""
    return {
        "check_item": "POSITIVE",
        "method": "positive",
        "original": content,
        "injected": content,
        "detail": "no injection",
        "label": "consistent",
        "confidence": "gold",
        "z3_verified": False,
        "entity_id": entity.get("entity_id", ""),
        "entity_type": entity.get("entity_type", ""),
        "occurrences": occs,
        "doc": occs[0].get("doc", "") if occs else "",
        "section": occs[0].get("section", "") if occs else "",
        "seed": SEED,
    }


def main():
    rng = random.Random(SEED)
    
    print("加载数据...")
    entities = load_entities()
    chunks = load_chunks()
    vlm_data = load_vlm_flowchart()
    print(f"  entities: {len(entities)}, chunks: {len(chunks)}, vlm: {len(vlm_data)}")
    
    print("提取参数/GJB条款/逻辑约束...")
    params = extract_params_from_chunks(chunks)
    gjb_clauses = extract_gjb_clauses(chunks)
    logic_constraints = extract_logic_constraints(chunks)
    for pt, cnt in sorted(params.items(), key=lambda x: -len(x[1])):
        print(f"  param_{pt}: {len(cnt)}")
    for gt, cnt in sorted(gjb_clauses.items(), key=lambda x: -len(x[1])):
        print(f"  gjb_{gt}: {len(cnt)}")
    for lt, cnt in sorted(logic_constraints.items(), key=lambda x: -len(x[1])):
        print(f"  logic_{lt}: {len(cnt)}")
    
    by_type = defaultdict(list)
    for e in entities:
        by_type[e["entity_type"]].append(e)
    
    results = []
    stats = defaultdict(int)
    
    # === 术语层 ===
    print("\n注入术语层...")
    term_injectors = [
        ("TERM-01", inject_TERM_01, "function_name"),
        ("TERM-02", inject_TERM_02, "function_name"),
        ("TERM-03", inject_TERM_03, "flow_sequence"),
        ("TERM-04", inject_TERM_04, "function_name"),
        ("TERM-05", inject_TERM_05, "function_name"),
        ("TERM-08", inject_TERM_08, "function_name"),
    ]
    for tid, injector, etype in term_injectors:
        candidates = by_type.get(etype, [])
        rng.shuffle(candidates)
        count = 0
        for entity in candidates:  # 全量遍历(修复: 抽样不命中词表实体)
            if count >= PER_ITEM:

                break
            r = injector(entity, rng)
            if r:
                results.append(r)
                count += 1
                stats[tid] += 1
        print(f"  {tid}: {count}")
    
    # TERM-06 from params
    count = 0
    rng.shuffle(params.get("time", []))
    rng.shuffle(params.get("period", []))
    for _ in range(len(params.get("time", [])) + len(params.get("period", []))):
        if count >= PER_ITEM:

            break
        r = inject_TERM_06_from_params(params, rng)
        if r:
            results.append(r)
            count += 1
            stats["TERM-06"] += 1
    print(f"  TERM-06: {count}")

    # TERM-07 from interface entities (canonical_name字段 — content是dict)
    count = 0
    iface_candidates = by_type.get("interface", [])
    rng.shuffle(iface_candidates)
    for entity in iface_candidates:
        if count >= PER_ITEM:

            break
        name = entity.get("canonical_name", "")
        if not isinstance(name, str) or len(name) < 2:
            continue
        for old, new in IFACE_MAP.items():
            if old in name:
                injected = name.replace(old, new, 1)
                occs = [
                    {"location": "table", "section": entity["occurrences"][0].get("section", ""),
                     "content": name, "doc": entity["occurrences"][0].get("doc", "")},
                    {"location": "text", "section": entity["occurrences"][0].get("section", ""),
                     "content": injected, "doc": entity["occurrences"][0].get("doc", "")},
                ]
                results.append(_build("TERM-07", "signal_name", entity, name, injected,
                                      f"位置A'{name}' vs 位置B'{injected}'", "silver",
                                      occurrences_override=occs,
                                      doc=entity["occurrences"][0].get("doc", ""),
                                      section=entity["occurrences"][0].get("section", "")))
                count += 1
                stats["TERM-07"] += 1
                break
    print(f"  TERM-07: {count}")
    
    # === 参数层 ===
    print("注入参数层...")
    param_types = [
        ("PARAM-01", "time"), ("PARAM-02", "period"), ("PARAM-03", "threshold"),
        ("PARAM-04", "align"), ("PARAM-05", "resource"), ("PARAM-06", "range"),
        ("PARAM-07", "storage"), ("PARAM-08", "precision"),
        ("PARAM-09", "degrade"), ("PARAM-10", "fault"),
    ]
    for pid, ptype in param_types:
        count = 0
        for _ in range(PER_ITEM * 2):
            if count >= PER_ITEM:

                break
            r = inject_PARAM(params, ptype, pid, rng)
            if r:
                results.append(r)
                count += 1
                stats[pid] += 1
        print(f"  {pid}({ptype}): {count}")
    
    # === 逻辑层 ===
    print("注入逻辑层...")
    # LOGIC-01~05 from VLM (全量遍历按doc去重)
    vlm_injectors = [
        ("LOGIC-01", inject_LOGIC_01), ("LOGIC-02", inject_LOGIC_02),
        ("LOGIC-03", inject_LOGIC_03), ("LOGIC-04", inject_LOGIC_04),
        ("LOGIC-05", inject_LOGIC_05),
    ]
    for lid, injector in vlm_injectors:
        count = 0
        seen_docs = set()
        for vlm in vlm_data:
            if count >= PER_ITEM:

                break
            doc = vlm.get("doc", "")
            if doc in seen_docs:

                continue
            r = injector([vlm], rng)
            if r:
                results.append(r)
                count += 1
                stats[lid] += 1
                seen_docs.add(doc)
        print(f"  {lid}: {count}")

    # LOGIC-06~11 from chunks (全量遍历+detail去重)
    logic_chunk_injectors = [
        ("LOGIC-06", "mutex"), ("LOGIC-07", "atomic"), ("LOGIC-08", "arbitration"),
        ("LOGIC-09", "permission"), ("LOGIC-10", "recovery"), ("LOGIC-11", "research"),
    ]
    for lid, ltype in logic_chunk_injectors:
        count = 0
        seen = set()
        for c in logic_constraints.get(ltype, []):
            if count >= PER_ITEM:

                break
            r = inject_LOGIC_from_chunks({ltype: [c]}, ltype, lid, "", rng)
            if r and r["detail"] not in seen:
                results.append(r)
                count += 1
                stats[lid] += 1
                seen.add(r["detail"])
        print(f"  {lid}({ltype}): {count}")

    # === GJB合规层 ===
    print("注入GJB层...")
    gjb_types = [
        ("GJB-01", "testable"), ("GJB-02", "faulttolerant"), ("GJB-03", "security"),
        ("GJB-04", "audit"), ("GJB-05", "traceability"), ("GJB-06", "alarm"),
        ("GJB-07", "selfcheck"), ("GJB-08", "powerfail"), ("GJB-09", "input"),
        ("GJB-10", "upgrade"), ("GJB-11", "degrade"),
    ]
    for gid, gtype in gjb_types:
        count = 0
        seen = set()
        for c in gjb_clauses.get(gtype, []):
            if count >= PER_ITEM:

                break
            r = inject_GJB_v2({gtype: [c]}, gtype, gid, rng)
            if r:
                key = (c.get("keyword", ""), c.get("sentence", "")[:60])
                if key in seen:
                    continue
                results.append(r)
                count += 1
                stats[gid] += 1
                seen.add(key)
        print(f"  {gid}({gtype}): {count}")
    
    # === 正例 ===
    print("生成正例...")
    for entity in rng.sample(entities, min(len(entities), 40)):
        results.append(_positive(entity))
        stats["positive"] += 1
    
    # === 统计 ===
    total = len(results)
    negative = sum(1 for r in results if r["label"] == "inconsistent")
    positive = sum(1 for r in results if r["label"] == "consistent")
    z3_count = sum(1 for r in results if r.get("z3_verified"))
    has_occs = sum(1 for r in results if r.get("occurrences"))
    
    print("\n=== 总计 ===")
    print(f"总条数: {total} (正例{positive} + 负例{negative})")
    print(f"Z3验证: {z3_count}条")
    print(f"有occurrences: {has_occs}条")
    print("按校验项:")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({"total": total, "stats": dict(stats), "z3_verified": z3_count,
                   "seed": SEED, "injections": results}, f, ensure_ascii=False, indent=2)
    print(f"\n保存到 {OUT_PATH}")


if __name__ == "__main__":
    main()
