#!/usr/bin/env python3
"""40种注入方法（严格对齐14_strict_40_items_design.md）

术语层8种 TERM-01~08 (字符级·silver)
参数层10种 PARAM-01~10 (数值级·gold·全部Z3 gate)
逻辑层11种 LOGIC-01~11 (序列级·silver)
GJB层11种 GJB-01~11 (内容缺失·gold)

seed=42可复现，注入值回写occurrences
"""
import json
import random
from pathlib import Path
from z3 import Real, Solver, unsat

BASE = Path(__file__).resolve().parent.parent
ENTITIES_PATH = BASE / "data/gjb_438c/data_assets/eval_entities.json"
OUT_PATH = BASE / "data/gjb_438c/data_assets/eval_injected.json"
SEED = 42

# T1错字映射表
CHAR_MAP = {
    '数':'发','据':'局','获':'或','取':'趣','服':'付','务':'雾','界':'介','面':'免',
    '开':'闩','发':'友','集':'及','成':'城','框':'狂','架':'加','转':'传','换':'涣',
    '接':'按','口':'叩','管':'官','理':'李','控':'空','制':'致','监':'简','测':'侧',
    '配':'陪','置':'直','注':'驻','册':'测','登':'灯','录':'绿','启':'起','停':'亭',
    '运':'云','行':'形','状':'妆','态':'太','异':'易','常':'长','告':'高','警':'井',
    '信':'新','号':'耗','模':'摸','式':'饰','切':'窃','优':'忧','先':'仙','级':'极',
    '权':'全','限':'线','访':'防','问':'闻','结':'洁','构':'购','化':'花','归':'龟',
    '流':'琉','非':'飞','半':'办','插':'播','入':'人','删':'珊','除':'出','修':'休',
    '改':'该','查':'茶','询':'寻','统':'桶','计':'记','存':'村','储':'厨','安':'按',
    '全':'权','通':'痛','道':'导','链':'连','路':'露','网':'纲','络':'洛','交':'胶',
}

SYN_MAP = {
    "获取":"采集","管理":"管控","监控":"监测","处理":"处置","传输":"传送",
    "存储":"保存","查询":"检索","注册":"登记","部署":"安装","启动":"开启",
    "关闭":"停止","删除":"移除","修改":"变更","添加":"新增","配置":"设置",
    "加载":"载入","发送":"发出","接收":"收取","解析":"分析","转换":"变换",
}

ALERT_MAP = {
    "告警":"警示","异常":"故障","错误":"失误","警告":"提醒","失败":"异常",
    "超时":"过期","中断":"断开","溢出":"越界","崩溃":"宕机","死锁":"卡死",
}

TRANS_MAP = {
    "数据获取":"DataAcquisition","数据转换":"DataConversion","界面集成":"UIIntegration",
    "服务集成":"ServiceIntegration","运行支撑":"RuntimeSupport","软件部署":"SoftwareDeployment",
    "数据访问":"DataAccess","传输服务":"TransportService","界面监控":"UIMonitoring",
}


def z3_gate(param_name, constraints_a, constraints_b):
    """Z3求解器验证约束矛盾（unsat=真矛盾）"""
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


def make_result(method, check_item, original, injected, entity, occ, detail, confidence, z3_verified=False):
    """构建注入结果"""
    return {
        "method": method,
        "check_item": check_item,
        "label": "inconsistent",
        "original": original,
        "injected": injected,
        "inject_location": occ.get("location", ""),
        "detail": detail,
        "confidence": confidence,
        "z3_verified": z3_verified,
        "seed": SEED,
        "entity_id": entity["entity_id"],
        "entity_type": entity["entity_type"],
        "occurrences": entity["occurrences"],
        "doc": entity["occurrences"][0].get("doc", ""),
        "pair_id": entity["occurrences"][0].get("pair_id", ""),
    }


# ========== 术语层8种 ==========

def inject_TERM_01(entity, rng):
    """同义异名：位置A名称X，位置B近义词Y"""
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if not isinstance(name, str) or len(name) < 2:
            continue
        for old, new in SYN_MAP.items():
            if old in name:
                injected = name.replace(old, new, 1)
                return make_result("TERM-01_synonym", "TERM-01", name, injected, entity, occ, f"{old}→{new}", "silver")
    return None

def inject_TERM_02(entity, rng):
    """同名异义：同名在不同位置定义不同概念"""
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if not isinstance(name, str) or len(name) < 2:
            continue
        injected = name + "（故障保护模式）"
        original = name + "（低功耗运行模式）"
        return make_result("TERM-02_homonym", "TERM-02", original, injected, entity, occ, "same name, different definition", "silver")
    return None

def inject_TERM_03(entity, rng):
    """枚举集合：文本N种，图N-1种"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("TERM-03_enum_missing", "TERM-03", content, injected, entity, occ, f"remove last: {content[-1]}", "silver")
    return None

def inject_TERM_04(entity, rng):
    """状态告警术语：同状态换术语"""
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if not isinstance(name, str) or len(name) < 2:
            continue
        for old, new in ALERT_MAP.items():
            if old in name:
                injected = name.replace(old, new, 1)
                return make_result("TERM-04_alert_term", "TERM-04", name, injected, entity, occ, f"{old}→{new}", "silver")
    return None

def inject_TERM_05(entity, rng):
    """指令名称：同指令不同名称"""
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if not isinstance(name, str) or len(name) < 2:
            continue
        for old, new in SYN_MAP.items():
            if old in name:
                injected = name.replace(old, new, 1)
                return make_result("TERM-05_command_name", "TERM-05", name, injected, entity, occ, f"command: {old}→{new}", "silver")
    # 如果没有同义词匹配，用错字
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if isinstance(name, str) and len(name) >= 2:
            pos = rng.randint(0, len(name) - 1)
            old_c = name[pos]
            new_c = CHAR_MAP.get(old_c, chr(ord(old_c) + 1))
            injected = name[:pos] + new_c + name[pos+1:]
            return make_result("TERM-05_command_name", "TERM-05", name, injected, entity, occ, f"char replace pos={pos}", "silver")
    return None

def inject_TERM_06(entity, rng):
    """量纲单位：≤0.2s vs ≤20ms（冲突非等效）"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, str) and content.replace('.', '').isdigit():
            unit = occ.get("unit", "")
            op = occ.get("op", "eq")
            UNIT_MAP = {"秒":"ms", "s":"ms", "分钟":"秒", "GB":"MB", "MB":"KB", "GHz":"MHz"}
            new_unit = UNIT_MAP.get(unit)
            if new_unit:
                original = f"{op} {content}{unit}"
                injected = f"{op} {content}{new_unit}"
                return make_result("TERM-06_unit_conflict", "TERM-06", original, injected, entity, occ, f"{unit}→{new_unit} (no conversion)", "gold")
    return None

def inject_TERM_07(entity, rng):
    """信号接口命名：同接口不同命名"""
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if not isinstance(name, str) or len(name) < 2:
            continue
        for old, new in SYN_MAP.items():
            if old in name:
                injected = name.replace(old, new, 1)
                return make_result("TERM-07_iface_name", "TERM-07", name, injected, entity, occ, f"interface: {old}→{new}", "silver")
    # fallback: 错字
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if isinstance(name, str) and len(name) >= 2:
            pos = rng.randint(0, len(name) - 1)
            new_c = CHAR_MAP.get(name[pos], chr(ord(name[pos]) + 1))
            injected = name[:pos] + new_c + name[pos+1:]
            return make_result("TERM-07_iface_name", "TERM-07", name, injected, entity, occ, "char replace", "silver")
    return None

def inject_TERM_08(entity, rng):
    """缩写代号：全称换缩写"""
    for occ in entity["occurrences"]:
        name = occ.get("content", "")
        if not isinstance(name, str) or len(name) < 4:
            continue
        chars = name[:4]
        abbr = ''.join(f'{ord(c) % 256:02X}' for c in chars)
        return make_result("TERM-08_abbreviation", "TERM-08", name, abbr, entity, occ, f"unicode abbr: {abbr}", "silver")
    return None


# ========== 参数层10种（全部Z3 gate） ==========

def inject_param_generic(entity, rng, param_id, param_type, confidence="gold"):
    """参数层通用注入：制造数值约束矛盾，Z3 gate验证"""
    for occ in entity["occurrences"]:
        try:
            val = float(occ["content"])
            op = occ.get("op", "ge")
            
            # 操作符方向自适应
            if op in ("ge", "gt"):
                injected_val = val * 0.5
                conflict_op = "lt"
            elif op in ("le", "lt"):
                injected_val = val * 2
                conflict_op = "gt"
            else:  # eq
                injected_val = val * 2
                conflict_op = "gt"
                op = "ge"  # 把eq当作ge处理
            
            original_constraints = [(op, val)]
            injected_constraints = [(conflict_op, injected_val)]
            
            if z3_gate(entity.get("param_name", param_type), original_constraints, injected_constraints):
                original = f"{op} {val}"
                injected = f"{conflict_op} {injected_val}"
                return make_result(
                    f"{param_id}_{param_type}", param_id,
                    original, injected, entity, occ,
                    f"{op} {val} vs {conflict_op} {injected_val} (Z3 unsat)",
                    confidence, z3_verified=True
                )
        except (ValueError, TypeError):
            continue
    return None

def inject_PARAM_01(entity, rng): return inject_param_generic(entity, rng, "PARAM-01", "time")
def inject_PARAM_02(entity, rng): return inject_param_generic(entity, rng, "PARAM-02", "period")
def inject_PARAM_03(entity, rng): return inject_param_generic(entity, rng, "PARAM-03", "threshold")
def inject_PARAM_04(entity, rng): return inject_param_generic(entity, rng, "PARAM-04", "align")
def inject_PARAM_05(entity, rng): return inject_param_generic(entity, rng, "PARAM-05", "resource")
def inject_PARAM_06(entity, rng): return inject_param_generic(entity, rng, "PARAM-06", "range")
def inject_PARAM_07(entity, rng): return inject_param_generic(entity, rng, "PARAM-07", "storage")
def inject_PARAM_08(entity, rng): return inject_param_generic(entity, rng, "PARAM-08", "precision")
def inject_PARAM_09(entity, rng): return inject_param_generic(entity, rng, "PARAM-09", "degrade")
def inject_PARAM_10(entity, rng): return inject_param_generic(entity, rng, "PARAM-10", "fault")


# ========== 逻辑层11种 ==========

def inject_LOGIC_01(entity, rng):
    """模式切换优先级：应急最高 vs 自动可夺回"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.insert(0, "自动模式优先（可抢占应急）")
            return make_result("LOGIC-01_mode_priority", "LOGIC-01", content, injected, entity, occ, "auto can preempt emergency", "silver")
    return None

def inject_LOGIC_02(entity, rng):
    """异常处置策略：切换备用 vs 重试"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("异常时重试3次（不切换备用）")
            return make_result("LOGIC-02_exception_strategy", "LOGIC-02", content, injected, entity, occ, "retry instead of switch", "silver")
    return None

def inject_LOGIC_03(entity, rng):
    """事件时序：交换前两个步骤"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = list(content)
            injected[0], injected[1] = injected[1], injected[0]
            return make_result("LOGIC-03_step_swap", "LOGIC-03", content, injected, entity, occ, "swap step 0,1", "silver")
    return None

def inject_LOGIC_04(entity, rng):
    """数据流流向：单向 vs 双向"""
    for occ in entity["occurrences"]:
        direction = occ.get("data_flow_direction", "")
        if direction:
            injected = "双向" if "单" in direction else "单向"
            return make_result("LOGIC-04_data_flow", "LOGIC-04", direction, injected, entity, occ, f"{direction}→{injected}", "silver")
    return None

def inject_LOGIC_05(entity, rng):
    """工况分支完备：删除最后一个分支"""
    for occ in entity["occurrences"]:
        branches = occ.get("branches", [])
        if isinstance(branches, list) and len(branches) >= 2:
            injected = branches[:-1]
            return make_result("LOGIC-05_branch_missing", "LOGIC-05", branches, injected, entity, occ, f"remove branch: {branches[-1]}", "silver")
    return None

def inject_LOGIC_06(entity, rng):
    """互斥控制：互斥 vs 并行"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("A和B并行执行（非互斥）")
            return make_result("LOGIC-06_mutex", "LOGIC-06", content, injected, entity, occ, "parallel instead of mutex", "silver")
    return None

def inject_LOGIC_07(entity, rng):
    """任务切换原子性：不可中断 vs 可中断"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("任务切换可被中断（非原子）")
            return make_result("LOGIC-07_atomicity", "LOGIC-07", content, injected, entity, occ, "interruptible switch", "silver")
    return None

def inject_LOGIC_08(entity, rng):
    """数据冗余仲裁：主用优先 vs 备用优先"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("备用数据优先（非主用）")
            return make_result("LOGIC-08_arbitration", "LOGIC-08", content, injected, entity, occ, "standby priority", "silver")
    return None

def inject_LOGIC_09(entity, rng):
    """权限访问控制：仅管理员 vs 普通用户可进入"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("普通用户可进入修改（权限放宽）")
            return make_result("LOGIC-09_permission", "LOGIC-09", content, injected, entity, occ, "normal user can modify", "silver")
    return None

def inject_LOGIC_10(entity, rng):
    """故障恢复：自动恢复 vs 手动恢复"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("需手动重启恢复（非自动）")
            return make_result("LOGIC-10_recovery", "LOGIC-10", content, injected, entity, occ, "manual recovery", "silver")
    return None

def inject_LOGIC_11(entity, rng):
    """追踪重搜：全库重搜 vs 增量搜索"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("只搜索增量数据（非全库）")
            return make_result("LOGIC-11_research", "LOGIC-11", content, injected, entity, occ, "incremental search", "silver")
    return None


# ========== GJB层11种（内容缺失/模糊） ==========

def inject_GJB_01(entity, rng):
    """可测试性：注入模糊需求"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, str) and len(content) >= 2:
            injected = "系统应运行稳定"
            return make_result("GJB-01_testability", "GJB-01", content, injected, entity, occ, "vague requirement", "gold")
        elif isinstance(content, list) and len(content) >= 2:
            injected = list(content)
            injected.append("系统应运行稳定（无量化指标）")
            return make_result("GJB-01_testability", "GJB-01", content, injected, entity, occ, "vague requirement", "gold")
    return None

def inject_GJB_02(entity, rng):
    """故障容错完备：缺失容错条款"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-02_fault_tolerance", "GJB-02", content, injected, entity, occ, f"remove: {content[-1]}", "gold")
    return None

def inject_GJB_03(entity, rng):
    """安全访问控制：缺失安全条款"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-03_security", "GJB-03", content, injected, entity, occ, "remove security clause", "gold")
    return None

def inject_GJB_04(entity, rng):
    """审计日志：缺失审计条款"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-04_audit", "GJB-04", content, injected, entity, occ, "remove audit clause", "gold")
    return None

def inject_GJB_05(entity, rng):
    """需求可追溯：追溯链断裂"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-05_traceability", "GJB-05", content, injected, entity, occ, "break traceability", "gold")
    return None

def inject_GJB_06(entity, rng):
    """异常报警要素：缺失报警级别"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-06_alarm", "GJB-06", content, injected, entity, occ, "remove alarm element", "gold")
    return None

def inject_GJB_07(entity, rng):
    """软件自检：缺失自检条款"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-07_selfcheck", "GJB-07", content, injected, entity, occ, "remove self-check", "gold")
    return None

def inject_GJB_08(entity, rng):
    """掉电数据保护：缺失保护条款"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-08_powerfail", "GJB-08", content, injected, entity, occ, "remove power-fail protection", "gold")
    return None

def inject_GJB_09(entity, rng):
    """输入数据防护：缺失防护条款"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-09_input_protection", "GJB-09", content, injected, entity, occ, "remove input protection", "gold")
    return None

def inject_GJB_10(entity, rng):
    """版本升级安全：缺失回退机制"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-10_upgrade", "GJB-10", content, injected, entity, occ, "remove rollback", "gold")
    return None

def inject_GJB_11(entity, rng):
    """降级运行：缺失降级模式"""
    for occ in entity["occurrences"]:
        content = occ.get("content", "")
        if isinstance(content, list) and len(content) >= 3:
            injected = content[:-1]
            return make_result("GJB-11_degrade", "GJB-11", content, injected, entity, occ, "remove degrade mode", "gold")
    return None


# ========== 注入注册表 ==========

INJECTORS = {
    # 术语层8种
    "TERM-01": (inject_TERM_01, "function_name"),
    "TERM-02": (inject_TERM_02, "function_name"),
    "TERM-03": (inject_TERM_03, "flow_sequence"),
    "TERM-04": (inject_TERM_04, "function_name"),
    "TERM-05": (inject_TERM_05, "function_name"),
    "TERM-06": (inject_TERM_06, "numeric_param"),
    "TERM-07": (inject_TERM_07, "function_name"),
    "TERM-08": (inject_TERM_08, "function_name"),
    # 参数层10种（全部Z3 gate）
    "PARAM-01": (inject_PARAM_01, "numeric_param"),
    "PARAM-02": (inject_PARAM_02, "numeric_param"),
    "PARAM-03": (inject_PARAM_03, "numeric_param"),
    "PARAM-04": (inject_PARAM_04, "numeric_param"),
    "PARAM-05": (inject_PARAM_05, "numeric_param"),
    "PARAM-06": (inject_PARAM_06, "numeric_param"),
    "PARAM-07": (inject_PARAM_07, "numeric_param"),
    "PARAM-08": (inject_PARAM_08, "numeric_param"),
    "PARAM-09": (inject_PARAM_09, "numeric_param"),
    "PARAM-10": (inject_PARAM_10, "numeric_param"),
    # 逻辑层11种
    "LOGIC-01": (inject_LOGIC_01, "flow_sequence"),
    "LOGIC-02": (inject_LOGIC_02, "flow_sequence"),
    "LOGIC-03": (inject_LOGIC_03, "flow_sequence"),
    "LOGIC-04": (inject_LOGIC_04, "flow_sequence"),
    "LOGIC-05": (inject_LOGIC_05, "flow_sequence"),
    "LOGIC-06": (inject_LOGIC_06, "flow_sequence"),
    "LOGIC-07": (inject_LOGIC_07, "flow_sequence"),
    "LOGIC-08": (inject_LOGIC_08, "flow_sequence"),
    "LOGIC-09": (inject_LOGIC_09, "flow_sequence"),
    "LOGIC-10": (inject_LOGIC_10, "flow_sequence"),
    "LOGIC-11": (inject_LOGIC_11, "flow_sequence"),
    # GJB层11种
    "GJB-01": (inject_GJB_01, "table_header"),
    "GJB-02": (inject_GJB_02, "table_header"),
    "GJB-03": (inject_GJB_03, "table_header"),
    "GJB-04": (inject_GJB_04, "table_header"),
    "GJB-05": (inject_GJB_05, "table_header"),
    "GJB-06": (inject_GJB_06, "table_header"),
    "GJB-07": (inject_GJB_07, "table_header"),
    "GJB-08": (inject_GJB_08, "table_header"),
    "GJB-09": (inject_GJB_09, "table_header"),
    "GJB-10": (inject_GJB_10, "table_header"),
    "GJB-11": (inject_GJB_11, "table_header"),
}

# 参数层也尝试从function_name和interface中提取数值
PARAM_FALLBACK_TYPES = ["numeric_param", "function_name", "interface"]


def make_positive(entity):
    """构造正例（一致）"""
    content = entity["occurrences"][0].get("content", "")
    return {
        "method": "positive",
        "check_item": "POSITIVE",
        "label": "consistent",
        "original": content,
        "injected": content,
        "inject_location": "",
        "detail": "no injection, original data",
        "confidence": "gold",
        "z3_verified": False,
        "seed": SEED,
        "entity_id": entity["entity_id"],
        "entity_type": entity["entity_type"],
        "occurrences": entity["occurrences"],
        "doc": entity["occurrences"][0].get("doc", ""),
        "pair_id": entity["occurrences"][0].get("pair_id", ""),
    }


def main():
    print("加载检测对象...")
    with open(ENTITIES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    entities = data["entities"]
    print(f"  共 {len(entities)} 个检测对象")
    
    by_type = {}
    for e in entities:
        t = e["entity_type"]
        by_type.setdefault(t, []).append(e)
    
    print("按类型:")
    for t, es in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"  {t}: {len(es)}")
    
    rng = random.Random(SEED)
    results = []
    method_stats = {}
    
    for method_id, (injector, required_type) in INJECTORS.items():
        # 获取候选实体
        candidates = by_type.get(required_type, [])

        # PARAM精确匹配: PARAM-01优先选param_type=time的实体(修复标签造假)
        if method_id.startswith("PARAM") and required_type == "numeric_param":
            ptype_map = {
                "PARAM-01": "time", "PARAM-02": "period", "PARAM-03": "threshold",
                "PARAM-04": "align", "PARAM-05": "resource", "PARAM-06": "range",
                "PARAM-07": "storage", "PARAM-08": "precision",
                "PARAM-09": "degrade", "PARAM-10": "fault",
            }
            want_type = ptype_map.get(method_id, "")
            typed = [e for e in candidates if e.get("param_type") == want_type]
            if typed:
                candidates = typed
            # 该类型无实体则回落到全部numeric_param(如实报告)

        # 参数层如果没有numeric_param，尝试其他类型
        if not candidates and method_id.startswith("PARAM"):
            for ft in PARAM_FALLBACK_TYPES[1:]:
                candidates = by_type.get(ft, [])
                if candidates:
                    break
        
        if not candidates:
            print(f"  {method_id}: 0条 (无{required_type}实体)")
            continue
        
        success = 0
        target = 5
        sampled = rng.sample(candidates, min(len(candidates), target * 3))
        
        for entity in sampled:
            if success >= target:
                break
            result = injector(entity, rng)
            if result:
                results.append(result)
                success += 1
                method_stats[method_id] = method_stats.get(method_id, 0) + 1
        
        if success == 0:
            print(f"  {method_id}: 0条 (注入失败)")
    
    # 正例
    pos_count = 0
    for entity in rng.sample(entities, min(len(entities), 50)):
        results.append(make_positive(entity))
        pos_count += 1
    
    # 统计
    neg_count = len(results) - pos_count
    z3_count = sum(1 for r in results if r.get("z3_verified"))
    
    print("\n注入统计:")
    print(f"  正例: {pos_count}")
    print(f"  负例: {neg_count}")
    print(f"  Z3验证: {z3_count}条")
    print(f"  方法数: {len(method_stats)}/40")
    print("  按方法:")
    for m in sorted(method_stats.keys()):
        print(f"    {m}: {method_stats[m]}")
    
    # 保存
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(results),
            "stats": {"positive": pos_count, "negative": neg_count},
            "method_stats": method_stats,
            "z3_verified": z3_count,
            "seed": SEED,
            "injections": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n保存到 {OUT_PATH}")


if __name__ == "__main__":
    main()
