"""医疗多模态数据冲突检测算子集合 (Data-Juicer custom operators).

包含5个面向 MedTVT 医疗场景的算子:
  - MedtvtDataMapper (Mapper):           解析 meta 中的 labs/diagnosis, 增补结构化特征
  - MedicalLabRangeFilter (Filter):      L1 单指标正常范围检测 (基于知识库 L1_lab_ranges)
  - LabDiagnosisConflictFilter (Filter): L2 血检异常 vs 诊断标签冲突 (与1444结果对齐)
  - CrossLabConsistencyFilter (Filter):  L3 多指标协同一致性检测
  - DiagnosisConsistencyFilter (Filter): 诊断标签间互斥性检查 (No Finding + 其他诊断)

设计依据:
  - 继承 data_juicer.ops.base_op 中的 Filter / Mapper 基类
  - 通过 @OPERATORS.register_module 注册, 可在YAML中通过 custom_operator_paths 引用
  - 所有 Filter 的 process_single 恒返回 True (仅标记不丢弃, 体检报告模式)
  - 冲突信息全部写入 sample[Fields.stats] 供报告导出
  - 知识库从外部 medical_kb.json 加载, 可配置
"""
import json
import os
import sys

# 注入 data-juicer 源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "data-juicer"))

from data_juicer.ops.base_op import OPERATORS, Filter, Mapper
from data_juicer.utils.constant import Fields

DEFAULT_KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "knowledge", "medical_kb.json")

# 严重度排序, 用于取最大严重度
_SEV_ORDER = {"MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _load_kb(kb_path):
    """加载医学知识库 JSON."""
    if not kb_path or not os.path.isfile(kb_path):
        raise FileNotFoundError(f"医学知识库不存在: {kb_path}")
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _cmp(val, op, thr):
    """通用数值比较."""
    if val is None:
        return False
    try:
        v = float(val)
        t = float(thr)
    except (TypeError, ValueError):
        return False
    if op == ">":
        return v > t
    if op == ">=":
        return v >= t
    if op == "<":
        return v < t
    if op == "<=":
        return v <= t
    if op == "==":
        return v == t
    return False


def _sev_level(level):
    return _SEV_ORDER.get(level, 0)


# =============================================================================
# 1) MedtvtDataMapper —— 解析 meta 中的 labs/diagnosis
# =============================================================================
@OPERATORS.register_module("medtvt_data_mapper")
class MedtvtDataMapper(Mapper):
    """解析 meta 中的 labs/diagnosis, 增补结构化特征.

    处理流程:
      1. 读取 meta.labs (dict: itemid->数值)
      2. 读取 meta.diagnosis (dict: 标签->1/0/-1)
      3. 增补 meta.parsed 标记, 记录关键指标摘要 (供后续算子/报告使用)
    """

    def __init__(self, key_lab_itemids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_lab_itemids = key_lab_itemids or [
            "50893", "51237", "50931", "50971", "50820"
        ]

    def process_single(self, sample):
        meta = sample.get("meta", {})
        labs = meta.get("labs", {}) or {}
        diagnosis = meta.get("diagnosis", {}) or {}

        # 关键指标摘要 (itemid->数值)
        key_labs = {iid: labs[iid] for iid in self.key_lab_itemids if iid in labs}
        # 诊断阳性标签列表
        positive_dx = [lbl for lbl, v in diagnosis.items() if v == 1]
        uncertain_dx = [lbl for lbl, v in diagnosis.items() if v == -1]
        no_finding = diagnosis.get("No Finding", 0) == 1

        meta["parsed"] = {
            "key_labs": key_labs,
            "positive_dx": positive_dx,
            "uncertain_dx": uncertain_dx,
            "no_finding": no_finding,
            "lab_count": len(labs),
            "lab_missing_key": [iid for iid in self.key_lab_itemids if iid not in labs],
        }
        sample["meta"] = meta
        return sample


# =============================================================================
# 2) MedicalLabRangeFilter —— L1 单指标正常范围检测
# =============================================================================
@OPERATORS.register_module("medical_lab_range_filter")
class MedicalLabRangeFilter(Filter):
    """L1: 单指标正常范围检测.

    遍历知识库 L1_lab_ranges, 检测 meta.labs 中每个指标是否越界,
    记录异常项及严重度. 写入 stats: lab_abnormal_list / lab_abnormal_count /
    lab_abnormal_max_severity.
    """

    def __init__(self, knowledge_base_path=DEFAULT_KB_PATH, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kb = _load_kb(knowledge_base_path)
        self.lab_ranges = self.kb.get("L1_lab_ranges", {})

    def _check_item(self, itemid, val):
        """检测单指标, 返回 (是否异常, 异常方向, 严重度, 详情dict) 或 (False, ...)."""
        rule = self.lab_ranges.get(itemid)
        if not rule:
            return False, None, None, None
        try:
            v = float(val)
        except (TypeError, ValueError):
            return False, None, None, None
        lo = rule.get("normal_low")
        hi = rule.get("normal_high")
        direction = rule.get("abnormal_dir", "both")
        if v < lo and direction in ("both", "low"):
            sev = self._severity(rule, v, "low")
            return True, "low", sev, {
                "itemid": itemid, "name": rule.get("name_cn", itemid),
                "value": v, "normal_low": lo, "normal_high": hi,
                "unit": rule.get("unit", ""), "direction": "low", "severity": sev,
            }
        if v > hi and direction in ("both", "high"):
            sev = self._severity(rule, v, "high")
            return True, "high", sev, {
                "itemid": itemid, "name": rule.get("name_cn", itemid),
                "value": v, "normal_low": lo, "normal_high": hi,
                "unit": rule.get("unit", ""), "direction": "high", "severity": sev,
            }
        return False, None, None, None

    @staticmethod
    def _severity(rule, val, direction):
        """根据 severity_high/severity_low 阶梯取最高命中严重度."""
        key = "severity_high" if direction == "high" else "severity_low"
        tiers = rule.get(key, [])
        if not tiers:
            return "HIGH" if direction == "high" else "MEDIUM"
        hit = None
        for t in tiers:
            if val >= t["threshold"]:
                if hit is None or _sev_level(t["level"]) > _sev_level(hit):
                    hit = t["level"]
            elif val <= t["threshold"] and direction == "low":
                if hit is None or _sev_level(t["level"]) > _sev_level(hit):
                    hit = t["level"]
        return hit or "MEDIUM"

    def compute_stats_single(self, sample, context=False):
        stats = sample.get(Fields.stats, {})
        if "lab_abnormal_count" in stats:
            return sample
        meta = sample.get("meta", {})
        labs = meta.get("labs", {}) or {}
        abnormal_list = []
        for iid, val in labs.items():
            is_abn, direction, sev, detail = self._check_item(iid, val)
            if is_abn:
                abnormal_list.append(detail)
        max_sev = None
        for d in abnormal_list:
            s = d.get("severity")
            if s and (max_sev is None or _sev_level(s) > _sev_level(max_sev)):
                max_sev = s
        stats["lab_abnormal_list"] = abnormal_list
        stats["lab_abnormal_count"] = len(abnormal_list)
        stats["lab_abnormal_max_severity"] = max_sev
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        # 仅标记不丢弃 (体检报告模式)
        return True


# =============================================================================
# 3) LabDiagnosisConflictFilter —— L2 血检异常 vs 诊断标签冲突
# =============================================================================
@OPERATORS.register_module("lab_diagnosis_conflict_filter")
class LabDiagnosisConflictFilter(Filter):
    """L2: 血检异常 vs 诊断标签冲突.

    依据知识库 L2_lab_diagnosis_rules: 指标超过严重阈值且诊断=No Finding(1) -> 冲突.
    阈值与 medical_conflict_results.json 的1444冲突对齐:
      乳酸>5.0 / 肌酐>2.0 / 血糖>300 / 钾>6.0 / pH<7.20
    写入 stats: lab_diag_conflict / lab_diag_conflict_list / lab_diag_conflict_count.
    """

    def __init__(self, knowledge_base_path=DEFAULT_KB_PATH, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kb = _load_kb(knowledge_base_path)
        self.rules = self.kb.get("L2_lab_diagnosis_rules", [])

    def compute_stats_single(self, sample, context=False):
        stats = sample.get(Fields.stats, {})
        if "lab_diag_conflict" in stats:
            return sample
        meta = sample.get("meta", {})
        labs = meta.get("labs", {}) or {}
        diagnosis = meta.get("diagnosis", {}) or {}

        conflicts = []
        for rule in self.rules:
            iid = rule["itemid"]
            val = labs.get(iid)
            if val is None:
                continue
            is_abn = _cmp(val, rule["op"], rule["threshold"])
            if not is_abn:
                continue
            # 冲突条件: 指标异常 但 诊断标签命中 conflict_if (默认 No Finding=1)
            conflict_label = rule.get("conflict_if", "No Finding")
            if diagnosis.get(conflict_label, 0) == 1:
                detail = rule.get("detail_template", "").format(val=round(float(val), 3))
                conflicts.append({
                    "type": rule["conflict_type"],
                    "itemid": iid,
                    "lab_name": rule.get("name_cn", iid),
                    "lab_value": round(float(val), 3),
                    "op": rule["op"],
                    "threshold": rule["threshold"],
                    "diagnosis": conflict_label,
                    "severity": rule["severity"],
                    "detail": detail,
                })
        stats["lab_diag_conflict"] = len(conflicts) > 0
        stats["lab_diag_conflict_list"] = conflicts
        stats["lab_diag_conflict_count"] = len(conflicts)
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True


# =============================================================================
# 4) CrossLabConsistencyFilter —— L3 多指标协同一致性
# =============================================================================
@OPERATORS.register_module("cross_lab_consistency_filter")
class CrossLabConsistencyFilter(Filter):
    """L3: 多指标协同一致性检测.

    依据知识库 L3_cross_lab_rules: 多指标组合同时满足条件 -> 提示综合征.
    写入 stats: cross_lab_conflict / cross_lab_conflict_list / cross_lab_conflict_count.
    """

    def __init__(self, knowledge_base_path=DEFAULT_KB_PATH, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kb = _load_kb(knowledge_base_path)
        self.rules = self.kb.get("L3_cross_lab_rules", [])

    def compute_stats_single(self, sample, context=False):
        stats = sample.get(Fields.stats, {})
        if "cross_lab_conflict" in stats:
            return sample
        meta = sample.get("meta", {})
        labs = meta.get("labs", {}) or {}

        hits = []
        for rule in self.rules:
            conditions = rule.get("conditions", [])
            if not conditions:
                continue
            all_met = True
            met_values = {}
            for cond in conditions:
                val = labs.get(cond["itemid"])
                if val is None or not _cmp(val, cond["op"], cond["val"]):
                    all_met = False
                    break
                met_values[cond["itemid"]] = round(float(val), 3)
            if all_met:
                hits.append({
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "conditions": conditions,
                    "matched_values": met_values,
                    "description": rule.get("description", ""),
                })
        stats["cross_lab_conflict"] = len(hits) > 0
        stats["cross_lab_conflict_list"] = hits
        stats["cross_lab_conflict_count"] = len(hits)
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True


# =============================================================================
# 5) DiagnosisConsistencyFilter —— 诊断标签间一致性
# =============================================================================
@OPERATORS.register_module("diagnosis_consistency_filter")
class DiagnosisConsistencyFilter(Filter):
    """诊断标签间互斥性检查.

    规则:
      - No Finding=1 且 其他任一诊断=1 -> 互斥冲突 (No Finding 与阳性诊断矛盾)
      - No Finding=1 且 其他诊断=-1 (不确定) -> 潜在冲突
    写入 stats: diag_consistency_conflict / diag_conflict_reason / diag_conflict_list.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compute_stats_single(self, sample, context=False):
        stats = sample.get(Fields.stats, {})
        if "diag_consistency_conflict" in stats:
            return sample
        meta = sample.get("meta", {})
        diagnosis = meta.get("diagnosis", {}) or {}

        no_finding = diagnosis.get("No Finding", 0) == 1
        reasons = []
        conflict_list = []
        if no_finding:
            for lbl, v in diagnosis.items():
                if lbl == "No Finding":
                    continue
                if v == 1:
                    reasons.append(f"No Finding 与 {lbl}=阳性 互斥")
                    conflict_list.append({
                        "type": "诊断互斥",
                        "labels": ["No Finding", lbl],
                        "values": {"No Finding": 1, lbl: 1},
                        "severity": "HIGH",
                    })
                elif v == -1:
                    reasons.append(f"No Finding 与 {lbl}=不确定 潜在冲突")
                    conflict_list.append({
                        "type": "诊断潜在冲突",
                        "labels": ["No Finding", lbl],
                        "values": {"No Finding": 1, lbl: -1},
                        "severity": "MEDIUM",
                    })
        # 编码异常: 同一标签非 {1,0,-1}
        for lbl, v in diagnosis.items():
            if v not in (1, 0, -1):
                reasons.append(f"{lbl} 编码异常={v}")
                conflict_list.append({
                    "type": "编码异常", "label": lbl, "value": v, "severity": "LOW",
                })
        stats["diag_consistency_conflict"] = len(reasons) > 0
        stats["diag_conflict_reason"] = reasons
        stats["diag_conflict_list"] = conflict_list
        stats["diag_conflict_count"] = len(conflict_list)
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True
