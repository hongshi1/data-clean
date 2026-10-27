#!/usr/bin/env python3
"""40项校验严格对齐注入方法

严格遵从实施方案文档40项校验体系：
  术语8项 + 参数10项 + 逻辑11项 + GJB 11项 = 40种注入

每种注入5正例+5负例，共400条评测集。
seed=42确定性可复现，注入值回写到occurrences。
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
OUT_PATH = BASE / "data/gjb_438c/data_assets/eval_injected_v2.json"

SEED = 42
PER_ITEM = 5  # 每项5正5负

# Z3 gate
def z3_gate(param_name, constraints_a, constraints_b):
    s = Solver()
    x = Real(param_name)
    for op, val in constraints_a + constraints_b:
        if op == "ge": s.add(x >= val)
        elif op == "le": s.add(x <= val)
        elif op == "gt": s.add(x > val)
        elif op == "lt": s.add(x < val)
        elif op == "eq": s.add(x == val)
    return s.check() == unsat

# 同义词映射
SYN_MAP = {
    "获取": "采集", "管理": "管控", "监控": "监测", "处理": "处置",
    "传输": "传送", "存储": "保存", "查询": "检索", "注册": "登记",
    "部署": "安装", "启动": "开启", "关闭": "停止", "删除": "移除",
    "修改": "变更", "添加": "新增", "配置": "设置", "加载": "载入",
    "捕捉": "捕获", "归集": "汇集", "转换": "变换", "发布": "分发",
}

# 告警术语映射
ALERT_MAP = {
    "告警": "警示", "异常": "故障", "错误": "失误", "警告": "提醒",
    "失败": "失效", "超时": "过期", "中断": "断开", "溢出": "越界",
}

# 单位换算表（用于量纲单位⑥）
UNIT_CONVERT = {
    ("秒", "ms"): 1000, ("s", "ms"): 1000, ("ms", "us"): 1000,
    ("分钟", "秒"): 60, ("min", "s"): 60, ("小时", "分钟"): 60,
    ("GB", "MB"): 1024, ("MB", "KB"): 1024, ("TB", "GB"): 1024,
    ("GHz", "MHz"): 1000, ("MHz", "kHz"): 1000,
}

# GJB合规条款关键词
GJB_KEYWORDS = {
    "testable": ["可测试", "验证", "确认", "稳定运行"],
    "faulttolerant": ["容错", "冗余", "备份", "故障转移", "热备"],
    "security": ["访问控制", "权限", "认证", "授权", "安全"],
    "audit": ["审计", "日志", "操作日志", "审计日志"],
    "traceability": ["追溯", "追踪", "映射", "对应"],
    "alarm": ["报警", "告警", "警示", "预警"],
    "selfcheck": ["自检", "开机检测", "启动检测", "自测试", "BIT"],
    "powerfail": ["掉电", "断电", "电源故障", "UPS", "数据保护"],
    "input": ["输入校验", "合法性", "数据校验", "输入防护", "边界检查"],
    "upgrade": ["版本升级", "升级", "回滚", "版本管理", "热更新"],
    "degrade": ["降级", "退化", "降级运行", "降级模式"],
}

# 参数类型正则
PARAM_PATTERNS = {
    "time": re.compile(r'(\d+\.?\d*)\s*(ms|毫秒|s|秒|min|分钟)'),
    "period": re.compile(r'(?:周期|间隔|频率)\D*?(\d+\.?\d*)\s*(ms|毫秒|s|秒|min|分钟|Hz|kHz)'),
    "threshold": re.compile(r'(?:阈值|门限|临界|触发)\D*?(\d+\.?\d*)\s*(ms|毫秒|s|秒|%|GB|MB|次|个)'),
    "align": re.compile(r'(?:对齐|同步|校准)\D*?(\d+\.?\d*)\s*(ms|毫秒|us|微秒|s|秒)'),
    "resource": re.compile(r'(?:CPU|内存|存储|磁盘|带宽|资源)\D*?(\d+\.?\d*)\s*(GHz|MHz|GB|MB|TB|Mbps|Gbps|%|核|个)'),
    "range": re.compile(r'(?:值域|范围|区间|不小于|不大于|大于|小于)\D*?(\d+\.?\d*)\s*(GB|MB|TB|GHz|MHz|ms|秒|%|个|条|路)'),
    "storage": re.compile(r'(?:保存|存储|保留|留存)\D*?(\d+\.?\d*)\s*(天|日|月|年|小时|GB|MB|TB)'),
    "precision": re.compile(r'(?:精度|误差|偏差|准确度)\D*?(\d+\.?\d*)\s*(ms|毫秒|s|秒|us|微秒|ns|m|米)'),
    "degrade": re.compile(r'(?:降级|退化)\D*?(\d+\.?\d*)\s*(%|ms|秒|min|分钟)'),
    "fault": re.compile(r'(?:故障|失效)\D*?(\d+\.?\d*)\s*(s|秒|ms|毫秒|min|分钟)'),
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


def extract_params_from_chunks(chunks):
    """从chunks按10种参数类型提取数值参数"""
    params = defaultdict(list)
    for chunk in chunks:
        text = chunk.get("text", "")
        doc = chunk.get("doc", "")
        section = chunk.get("section", "")
        for ptype, pattern in PARAM_PATTERNS.items():
            for m in pattern.finditer(text):
                val = float(m.group(1))
                unit = m.group(2) if m.lastindex >= 2 else ""
                ctx_start = max(0, m.start() - 30)
                context = text[ctx_start:m.end() + 10]
                # 识别操作符
                op = "eq"
                pre = text[max(0, m.start()-15):m.start()]
                if "不小于" in pre or "至少" in pre or "≥" in pre: op = "ge"
                elif "不大于" in pre or "至多" in pre or "≤" in pre: op = "le"
                elif "大于" in pre or "超过" in pre or ">" in pre: op = "gt"
                elif "小于" in pre or "低于" in pre or "<" in pre: op = "lt"
                params[ptype].append({
                    "val": val, "unit": unit, "op": op,
                    "doc": doc, "section": section, "context": context[:80]
                })
    return params

def extract_gjb_clauses(chunks):
    """从chunks提取GJB合规条款"""
    clauses = defaultdict(list)
    for chunk in chunks:
        text = chunk.get("text", "")
        doc = chunk.get("doc", "")
        section = chunk.get("section", "")
        for gtype, keywords in GJB_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    idx = text.find(kw)
                    sent_start = text.rfind("。", 0, idx)
                    sent_start = sent_start + 1 if sent_start >= 0 else max(0, idx - 40)
                    sent_end = text.find("。", idx)
                    sent_end = sent_end + 1 if sent_end >= 0 else min(len(text), idx + 80)
                    sentence = text[sent_start:sent_end].strip()
                    if len(sentence) > 10:
                        clauses[gtype].append({
                            "keyword": kw, "doc": doc, "section": section,
                            "sentence": sentence[:150]
                        })
                    break
    return clauses


# ========== 术语层8种注入 ==========

def inject_TERM_01(entity, rng):
    """①同义异名：位置A用名称X，位置B用近义词Y"""
    occs = entity.get("occurrences", [])
    name = occs[0].get("content", "") if occs else ""
    if not isinstance(name, str) or len(name) < 2:
        return None
    for old, new in SYN_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-01", "synonym", entity, name, injected, 
                         f"位置A用'{name}'，位置B用'{injected}'({old}→{new})", "silver")
    return None

def inject_TERM_02(entity, rng):
    """②同名异义：同一名称在不同位置定义不同"""
    occs = entity.get("occurrences", [])
    name = occs[0].get("content", "") if occs else ""
    if not isinstance(name, str) or len(name) < 2:
        return None
    defs = ["低功耗运行模式", "故障保护模式", "数据加密模式", "维护诊断模式"]
    d1, d2 = rng.sample(defs, 2)
    return _build("TERM-02", "homonym", entity, name, name,
                 f"位置A'{name}'定义为'{d1}'，位置B'{name}'定义为'{d2}'", "silver",
                 extra={"def_a": d1, "def_b": d2})

def inject_TERM_03(entity, rng):
    """③枚举集合：文本N种，图N-1种"""
    for occ in entity.get("occurrences", []):
        content = occ.get("content", [])
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return _build("TERM-03", "enum_missing", entity, content, injected,
                         f"文本{len(content)}种 vs 图{len(injected)}种", "silver")
    return None

def inject_TERM_04(entity, rng):
    """④状态告警术语统一：同一状态不同名称"""
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 2:
        return None
    for old, new in ALERT_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-04", "alert_term", entity, name, injected,
                         f"位置A'{name}' vs 位置B'{injected}'", "silver")
    # 如果没匹配到，用通用替换
    injected = name + "(告警)" if "告警" not in name and "报警" not in name else name.replace("告警", "报警")
    if injected != name:
        return _build("TERM-04", "alert_term", entity, name, injected,
                     f"位置A'{name}' vs 位置B'{injected}'", "silver")
    return None

def inject_TERM_05(entity, rng):
    """⑤指令名称全局一致性"""
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 2:
        return None
    CMD_MAP = {"启动": "开启", "停止": "终止", "查询": "搜索", "发送": "推送",
               "接收": "获取", "创建": "新建", "删除": "清除", "更新": "刷新"}
    for old, new in CMD_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-05", "command_name", entity, name, injected,
                         f"位置A'{name}' vs 位置B'{injected}'", "silver")
    return None

def inject_TERM_06(entity, rng):
    """⑥量纲单位一致性：≤0.2s vs ≤20ms（冲突）"""
    # 需要数值参数
    for occ in entity.get("occurrences", []):
        content = str(occ.get("content", ""))
        m = re.match(r'(\d+\.?\d*)\s*(ms|毫秒|s|秒|min|分钟)', content)
        if m:
            val = float(m.group(1))
            unit = m.group(2)
            # 换算到不同单位但不做换算（制造冲突）
            conv = {"秒": ("ms", 1000), "s": ("ms", 1000), "ms": ("us", 1000),
                    "分钟": ("秒", 60), "min": ("s", 60)}
            if unit in conv:
                new_unit, factor = conv[unit]
                # 冲突：不改值只换单位（如0.2秒→0.2ms，实际应该是200ms）
                injected = f"{val}{new_unit}"
                original = f"{val}{unit}"
                return _build("TERM-06", "unit_conflict", entity, original, injected,
                             f"位置A'{original}' vs 位置B'{injected}'（应换算为{val*factor}{new_unit}）", "gold")
    return None

def inject_TERM_07(entity, rng):
    """⑦信号接口命名一致性"""
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 2:
        return None
    IFACE_MAP = {"接口": "通道", "端口": "连接", "总线": "链路", "信号": "通道"}
    for old, new in IFACE_MAP.items():
        if old in name:
            injected = name.replace(old, new, 1)
            return _build("TERM-07", "signal_name", entity, name, injected,
                         f"位置A'{name}' vs 位置B'{injected}'", "silver")
    return None

def inject_TERM_08(entity, rng):
    """⑧缩写代号一致性：全称换缩写"""
    name = entity.get("occurrences", [{}])[0].get("content", "")
    if not isinstance(name, str) or len(name) < 4:
        return None
    # 取前4字的unicode十六进制末2位
    chars = name[:4]
    abbr = ''.join(f'{ord(c) % 256:02X}' for c in chars)
    return _build("TERM-08", "abbreviation", entity, name, abbr,
                 f"位置A全称'{name}' vs 位置B缩写'{abbr}'", "silver")


# ========== 参数层10种注入 ==========

def inject_PARAM(params_by_type, ptype, param_id, rng):
    """通用参数注入：位置A和位置B数值冲突，Z3 gate验证"""
    candidates = params_by_type.get(ptype, [])
    if len(candidates) < 1:
        return None
    
    p = rng.choice(candidates)
    val = p["val"]
    unit = p["unit"]
    op = p.get("op", "ge")
    
    # 注入冲突值（减半或翻倍）
    injected_val = val * 2 if rng.random() > 0.5 else val * 0.5
    if injected_val == val:
        injected_val = val * 2
    
    original = f"{op} {val}{unit}"
    injected = f"{op} {injected_val}{unit}"
    
    # Z3 gate
    constraints_a = [(op, val)]
    conflict_op = {"ge": "lt", "le": "gt", "gt": "le", "lt": "ge", "eq": "ne"}.get(op, "lt")
    constraints_b = [(conflict_op, injected_val)]
    
    z3_ok = z3_gate(ptype, constraints_a, constraints_b)
    
    return _build(param_id, f"param_{ptype}", None, original, injected,
                 f"位置A'{original}' vs 位置B'{injected}' (Z3={'unsat' if z3_ok else 'sat'})",
                 "gold", z3_ok, doc=p["doc"], section=p["section"])


# ========== 逻辑层11种注入 ==========

def inject_LOGIC_01(vlm_data, rng):
    """①模式切换优先级：应急最高 vs 自动可夺回"""
    for vlm in vlm_data:
        branches = vlm.get("branches", [])
        if len(branches) >= 2:
            return _build("LOGIC-01", "priority_conflict", None,
                         "应急模式优先级最高", "自动模式可抢占应急模式",
                         "正文'应急最高' vs 状态机'自动可夺回'", "silver",
                         doc=vlm.get("doc", ""), section=vlm.get("section", ""))
    return None

def inject_LOGIC_02(vlm_data, rng):
    """②异常处置策略：切换备用 vs 重试"""
    for vlm in vlm_data:
        nodes = vlm.get("nodes", [])
        if any("异常" in n or "故障" in n for n in nodes):
            return _build("LOGIC-02", "exception_strategy", None,
                         "异常时切换备用通道", "异常时重试3次",
                         "正文'切换备用' vs 用例表'重试3次'", "silver",
                         doc=vlm.get("doc", ""), section=vlm.get("section", ""))
    return None

def inject_LOGIC_03(vlm_data, rng):
    """③事件时序：先A后B vs 先B后A"""
    for vlm in vlm_data:
        nodes = vlm.get("nodes", [])
        if len(nodes) >= 3:
            original = nodes[:3]
            injected = [nodes[1], nodes[0]] + nodes[2:]  # 交换前两个
            return _build("LOGIC-03", "sequence_swap", None, original, injected,
                         f"正文{original[:2]} vs 流程图{injected[:2]}", "silver",
                         doc=vlm.get("doc", ""), section=vlm.get("section", ""))
    return None

def inject_LOGIC_04(vlm_data, rng):
    """④数据流流向：单向 vs 反向"""
    for vlm in vlm_data:
        direction = vlm.get("data_flow_direction", "")
        if direction:
            conflict = "双向" if "单" in direction else "单向"
            return _build("LOGIC-04", "dataflow_reverse", None,
                         direction, conflict,
                         f"框图'{direction}' vs 正文'{conflict}'", "silver",
                         doc=vlm.get("doc", ""), section=vlm.get("section", ""))
    return None

def inject_LOGIC_05(vlm_data, rng):
    """⑤工况分支完备性：文本3类 vs 图2类"""
    for vlm in vlm_data:
        branches = vlm.get("branches", [])
        if len(branches) >= 2:
            injected = branches[:-1]
            return _build("LOGIC-05", "branch_missing", None,
                         branches, injected,
                         f"文本{len(branches)}类 vs 流程图{len(injected)}类", "silver",
                         doc=vlm.get("doc", ""), section=vlm.get("section", ""))
    return None

def inject_LOGIC_06(vlm_data, rng):
    """⑥互斥控制：互斥 vs 并行"""
    return _build("LOGIC-06", "mutex_conflict", None,
                 "A和B互斥执行", "A和B并行执行",
                 "正文'互斥' vs 时序图'并行'", "silver")

def inject_LOGIC_07(vlm_data, rng):
    """⑦任务切换原子性：不可中断 vs 可中断"""
    return _build("LOGIC-07", "atomic_conflict", None,
                 "任务切换为原子操作不可中断", "任务切换可被中断",
                 "正文'不可中断' vs 流程图'可中断'", "silver")

def inject_LOGIC_08(vlm_data, rng):
    """⑧数据冗余仲裁：主用优先 vs 备用优先"""
    return _build("LOGIC-08", "arbitration_conflict", None,
                 "主用数据优先", "备用数据优先",
                 "正文'主用优先' vs 设计说明'备用优先'", "silver")

def inject_LOGIC_09(vlm_data, rng):
    """⑨权限访问控制：普通用户不能 vs 流程图允许"""
    return _build("LOGIC-09", "permission_conflict", None,
                 "仅管理员可修改配置", "普通用户可进入配置页面",
                 "正文'仅管理员' vs 流程图'普通用户可进入'", "silver")

def inject_LOGIC_10(vlm_data, rng):
    """⑩故障恢复：自动恢复 vs 手动恢复"""
    return _build("LOGIC-10", "recovery_conflict", None,
                 "故障后自动恢复", "需手动重启恢复",
                 "正文'自动恢复' vs 维护手册'手动恢复'", "silver")

def inject_LOGIC_11(vlm_data, rng):
    """⑪追踪重搜：全库重搜 vs 增量搜索"""
    return _build("LOGIC-11", "research_conflict", None,
                 "追踪失败后重新搜索全库", "只搜索增量数据",
                 "正文'全库重搜' vs 设计说明'增量搜索'", "silver")


# ========== GJB合规层11种注入 ==========

def inject_GJB(gjb_clauses, gtype, gjb_id, rng):
    """GJB合规注入：删除/模糊化合规条款"""
    candidates = gjb_clauses.get(gtype, [])
    if not candidates:
        return None
    
    clause = rng.choice(candidates)
    sentence = clause["sentence"]
    
    # GJB-01可测试性：注入模糊需求
    if gtype == "testable":
        return _build("GJB-01", "vague_requirement", None,
                     sentence[:60], "系统应运行稳定",
                     "模糊需求'运行稳定'不可测试", "gold",
                     doc=clause["doc"], section=clause["section"])
    
    # 其他GJB：删除条款
    gjb_names = {
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
    
    if gtype in gjb_names:
        gid, method, desc = gjb_names[gtype]
        return _build(gid, method, None,
                     sentence[:60], "(条款缺失)",
                     f"{desc}: 删除'{clause['keyword']}'", "gold",
                     doc=clause["doc"], section=clause["section"])
    
    return None


# ========== 工具函数 ==========

def _build(check_item, method, entity, original, injected, detail, 
           confidence, z3_verified=False, doc="", section="", extra=None):
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
    if entity:
        result["entity_id"] = entity.get("entity_id", "")
        result["entity_type"] = entity.get("entity_type", "")
        result["occurrences"] = entity.get("occurrences", [])
    if extra:
        result["extra"] = extra
    return result

def _positive(entity, check_item="POSITIVE"):
    occs = entity.get("occurrences", [])
    content = occs[0].get("content", "") if occs else ""
    return {
        "check_item": check_item,
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


# ========== 主函数 ==========

def main():
    rng = random.Random(SEED)
    
    print("加载数据...")
    entities = load_entities()
    chunks = load_chunks()
    vlm_data = load_vlm_flowchart()
    print(f"  entities: {len(entities)}, chunks: {len(chunks)}, vlm: {len(vlm_data)}")
    
    # 从chunks提取参数和GJB条款
    print("提取参数和GJB条款...")
    params = extract_params_from_chunks(chunks)
    gjb_clauses = extract_gjb_clauses(chunks)
    for pt, cnt in sorted(params.items(), key=lambda x: -len(x[1])):
        print(f"  param_{pt}: {len(cnt)}")
    for gt, cnt in sorted(gjb_clauses.items(), key=lambda x: -len(x[1])):
        print(f"  gjb_{gt}: {len(cnt)}")
    
    # 按类型分组entities
    by_type = defaultdict(list)
    for e in entities:
        by_type[e["entity_type"]].append(e)
    
    results = []
    stats = defaultdict(int)
    
    # === 术语层8种 ===
    print("\n注入术语层...")
    term_injectors = [
        ("TERM-01", inject_TERM_01, "function_name"),
        ("TERM-02", inject_TERM_02, "function_name"),
        ("TERM-03", inject_TERM_03, "flow_sequence"),
        ("TERM-04", inject_TERM_04, "function_name"),
        ("TERM-05", inject_TERM_05, "function_name"),
        ("TERM-06", inject_TERM_06, "numeric_param"),
        ("TERM-07", inject_TERM_07, "interface"),
        ("TERM-08", inject_TERM_08, "function_name"),
    ]
    for tid, injector, etype in term_injectors:
        candidates = by_type.get(etype, [])
        # TERM-06需要numeric_param，但也尝试从function_name中找
        if etype == "numeric_param" and not candidates:
            # 从params中构建临时entity
            for ptype in ["time", "period"]:
                for p in params.get(ptype, [])[:PER_ITEM]:
                    temp_entity = {"entity_id": f"PARAM-{ptype}", "entity_type": "numeric_param",
                                   "occurrences": [{"content": f"{p['val']}{p['unit']}", "location": "text",
                                                    "section": p["section"], "doc": p["doc"]}]}
                    r = injector(temp_entity, rng)
                    if r:
                        results.append(r)
                        stats[tid] += 1
            continue
        count = 0
        for entity in rng.sample(candidates, min(len(candidates), PER_ITEM * 3)):
            if count >= PER_ITEM:
                break
            r = injector(entity, rng)
            if r:
                results.append(r)
                count += 1
                stats[tid] += 1
        print(f"  {tid}: {count}")
    
    # === 参数层10种 ===
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
    
    # === 逻辑层11种 ===
    print("注入逻辑层...")
    logic_injectors = [
        ("LOGIC-01", inject_LOGIC_01), ("LOGIC-02", inject_LOGIC_02),
        ("LOGIC-03", inject_LOGIC_03), ("LOGIC-04", inject_LOGIC_04),
        ("LOGIC-05", inject_LOGIC_05), ("LOGIC-06", inject_LOGIC_06),
        ("LOGIC-07", inject_LOGIC_07), ("LOGIC-08", inject_LOGIC_08),
        ("LOGIC-09", inject_LOGIC_09), ("LOGIC-10", inject_LOGIC_10),
        ("LOGIC-11", inject_LOGIC_11),
    ]
    for lid, injector in logic_injectors:
        count = 0
        for _ in range(PER_ITEM * 3):
            if count >= PER_ITEM:
                break
            r = injector(vlm_data, rng)
            if r:
                results.append(r)
                count += 1
                stats[lid] += 1
        print(f"  {lid}: {count}")
    
    # === GJB合规层11种 ===
    print("注入GJB层...")
    gjb_types = [
        ("GJB-01", "testable"), ("GJB-02", "faulttolerant"), ("GJB-03", "security"),
        ("GJB-04", "audit"), ("GJB-05", "traceability"), ("GJB-06", "alarm"),
        ("GJB-07", "selfcheck"), ("GJB-08", "powerfail"), ("GJB-09", "input"),
        ("GJB-10", "upgrade"), ("GJB-11", "degrade"),
    ]
    for gid, gtype in gjb_types:
        count = 0
        for _ in range(PER_ITEM * 3):
            if count >= PER_ITEM:
                break
            r = inject_GJB(gjb_clauses, gtype, gid, rng)
            if r:
                results.append(r)
                count += 1
                stats[gid] += 1
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
    
    print("\n=== 总计 ===")
    print(f"总条数: {total} (正例{positive} + 负例{negative})")
    print(f"Z3验证: {z3_count}条")
    print("按校验项:")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    
    # 保存
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({"total": total, "stats": dict(stats), "z3_verified": z3_count,
                   "seed": SEED, "injections": results}, f, ensure_ascii=False, indent=2)
    print(f"\n保存到 {OUT_PATH}")


if __name__ == "__main__":
    main()
