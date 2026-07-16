"""NLMCXR 胸片报告冲突检测算子集合 (Data-Juicer custom operators).

包含4个面向 NLMCXR 胸片场景的算子:
  - NlmcxrDataMapper (Mapper):              解析 text/images, 存入 meta.report / meta.image_path
  - XrayImageAnalysisFilter (Filter):       TorchXRayVision DenseNet121 X光片疾病推理 (6种疾病)
  - ReportNerFilter (Filter):               报告文本NER (正则+否定/不确定检测, 三态标注)
  - ImageReportConflictFilter (Filter):     图片-报告三态冲突矩阵

设计依据:
  - 继承 data_juicer.ops.base_op 中的 Filter / Mapper 基类
  - 通过 @OPERATORS.register_module 注册, 可在YAML中通过 custom_operator_paths 引用
  - 所有 Filter 的 process_single 恒返回 True (仅标记不丢弃, 体检报告模式)
  - 冲突信息全部写入 sample[Fields.stats] 供报告导出
  - TorchXRayVision 模型在 Filter.__init__ 中加载一次 (类属性缓存), CPU运行

核心逻辑对齐 professional_v3_20.json:
  - 6种疾病: Atelectasis / Consolidation / Edema / Cardiomegaly / Pneumothorax / Pleural Effusion
  - 图片侧: raw output > 0.5 判断阳性 (不用sigmoid, 不用官方op_threshs)
  - 报告侧: 正则匹配关键词, 30字符窗口否定/不确定检测, 三态 (positive/negative/uncertain/unmentioned)
  - 冲突矩阵: 图片↔报告否定(HIGH/MEDIUM/LOW) / 图片↔报告不确定(LOW) /
              图片↔报告结论(MEDIUM) / 报告↔图片(MEDIUM) / 报告内部(MEDIUM)
"""
import os
import re
import sys

# 注入 data-juicer 源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "data-juicer"))

from data_juicer.ops.base_op import OPERATORS, Filter, Mapper
from data_juicer.utils.constant import Fields

# =============================================================================
# 常量定义
# =============================================================================

# 6种目标疾病 (固定顺序, 对齐 v3)
DISEASES = [
    "Atelectasis",
    "Consolidation",
    "Edema",
    "Cardiomegaly",
    "Pneumothorax",
    "Pleural Effusion",
]

# 模型病理学名称 -> 目标疾病名映射
_MODEL_NAME_MAP = {
    "Atelectasis": "Atelectasis",
    "Consolidation": "Consolidation",
    "Edema": "Edema",
    "Cardiomegaly": "Cardiomegaly",
    "Pneumothorax": "Pneumothorax",
    "Effusion": "Pleural Effusion",
}

# 报告NER关键词 (小写匹配)
REPORT_KEYWORDS = {
    "Atelectasis": ["atelectasis"],
    "Consolidation": ["consolidation", "airspace disease"],
    "Edema": ["edema"],
    "Cardiomegaly": ["cardiomegaly"],
    "Pneumothorax": ["pneumothorax"],
    "Pleural Effusion": ["effusion", "pleural fluid"],
}

# 否定词 (30字符窗口内, 词级匹配)
_NEG_PATTERN = re.compile(r"\b(no|without|not|absence|nor|cannot)\b")

# 不确定标记 (30字符窗口内, 子串匹配)
_UNC_MARKERS = [
    "may represent",
    "possible",
    "cannot exclude",
    "suggest",
    "may be",
    "could represent",
    "could be",
]

# "正常"表述短语 (子串匹配, 对齐 v3 report_normal 逻辑)
_NORMAL_PHRASES = [
    "clear",
    "no acute",
    "no active",
    "unremarkable",
    "within normal",
    "negative chest",
    "heart size normal",
    "no evidence of acute",
]

# 阳性阈值: raw output > 0.5
POSITIVE_THRESHOLD = 0.5

# 否定冲突严重度阈值 (基于 raw output)
_SEV_HIGH = 0.7
_SEV_MEDIUM = 0.55


# =============================================================================
# 1) NlmcxrDataMapper —— 解析 text/images 存入 meta
# =============================================================================
@OPERATORS.register_module("nlmcxr_data_mapper")
class NlmcxrDataMapper(Mapper):
    """解析 sample 的 text(报告)和 images(图片路径), 存入 meta.

    处理流程:
      1. 读取 sample['text'] 作为报告原文
      2. 读取 sample['images'][0] 作为图片路径
      3. 写入 meta.report / meta.image_path 供后续算子使用
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process_single(self, sample):
        meta = sample.get("meta", {})
        meta["report"] = sample.get("text", "")
        images = sample.get("images", []) or []
        meta["image_path"] = images[0] if images else ""
        sample["meta"] = meta
        return sample


# =============================================================================
# 2) XrayImageAnalysisFilter —— TorchXRayVision X光片疾病推理
# =============================================================================
@OPERATORS.register_module("xray_image_analysis_filter")
class XrayImageAnalysisFilter(Filter):
    """TorchXRayVision DenseNet121 X光片疾病推理 Filter.

    处理流程:
      1. 加载 TorchXRayVision DenseNet121 (weights='densenet121-res224-mimic_ch'), CPU运行
      2. 图片预处理: PIL加载→灰度→xrv.datasets.normalize→resize(224)
      3. 推理: model(img_tensor) → raw output (不用sigmoid)
      4. 对6种疾病用 raw output > 0.5 判断阳性
      5. 写入 stats.xray_predictions = {disease: {"prob": float, "positive": bool}}
    """

    # 类属性缓存模型 (只加载一次)
    _model = None
    _disease_indices = None

    def __init__(self, weights="densenet121-res224-mimic_ch", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if XrayImageAnalysisFilter._model is None:
            self._load_model(weights)

    @classmethod
    def _load_model(cls, weights):
        """加载 TorchXRayVision 模型 (CPU), 建立疾病索引映射."""
        import torch  # noqa: F401
        import torchxrayvision as xrv

        model = xrv.models.DenseNet(weights=weights)
        model.eval()
        cls._model = model

        # 建立疾病名 -> 模型输出索引映射
        pathologies = list(model.pathologies)
        indices = {}
        for model_name, disease in _MODEL_NAME_MAP.items():
            if model_name in pathologies:
                indices[disease] = pathologies.index(model_name)
        cls._disease_indices = indices

    @staticmethod
    def _preprocess_image(image_path):
        """图片预处理: PIL→灰度→normalize→resize(224)→tensor.

        返回 torch.Tensor shape (1, 224, 224), 或 None(失败).
        """
        if not image_path or not os.path.isfile(image_path):
            return None
        try:
            import numpy as np
            import torch
            from PIL import Image
            from skimage.transform import resize
            import torchxrayvision as xrv

            img = Image.open(image_path).convert("L")
            img_np = np.array(img)
            img_norm = xrv.datasets.normalize(img_np, 255)
            img_resized = resize(img_norm, (224, 224), mode="constant")
            img_tensor = torch.from_numpy(img_resized).unsqueeze(0)  # (1, 224, 224)
            return img_tensor
        except Exception:
            return None

    def compute_stats_single(self, sample, context=False):
        stats = sample.get(Fields.stats, {})
        if "xray_predictions" in stats:
            return sample

        meta = sample.get("meta", {})
        image_path = meta.get("image_path", "")

        predictions = {}
        img_tensor = self._preprocess_image(image_path)
        if img_tensor is not None:
            import torch

            with torch.no_grad():
                raw_out = self._model(img_tensor)
            raw_np = raw_out.detach().numpy()[0]
            for disease in DISEASES:
                idx = self._disease_indices.get(disease)
                if idx is not None and idx < len(raw_np):
                    prob = round(float(raw_np[idx]), 3)
                    positive = float(raw_np[idx]) > POSITIVE_THRESHOLD
                else:
                    prob = 0.0
                    positive = False
                predictions[disease] = {"prob": prob, "positive": positive}
        else:
            for disease in DISEASES:
                predictions[disease] = {"prob": 0.0, "positive": False}

        stats["xray_predictions"] = predictions
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True


# =============================================================================
# 3) ReportNerFilter —— 报告文本NER (三态标注)
# =============================================================================
@OPERATORS.register_module("report_ner_filter")
class ReportNerFilter(Filter):
    """报告文本NER: 正则匹配+否定/不确定检测, 三态标注.

    处理流程:
      1. 对6种疾病用正则匹配关键词 (大小写不敏感)
      2. 否定检测: 检查关键词前30字符是否有 no/without/not/absence/nor/cannot
      3. 不确定检测: 检查关键词前30字符是否有 may represent/possible/cannot exclude/suggest等
      4. 三态标注: positive(优先) > uncertain > negative > unmentioned
      5. 检测"正常"表述: clear/no acute/normal/unremarkable等 -> report_normal
      6. 写入 stats.report_findings / stats.report_normal
    """

    def __init__(self, window=30, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window

    def _classify_occurrence(self, context_before):
        """判断单次出现的状态: negative / uncertain / positive."""
        if _NEG_PATTERN.search(context_before):
            return "negative"
        if any(u in context_before for u in _UNC_MARKERS):
            return "uncertain"
        return "positive"

    def _ner_disease(self, report_lower, disease):
        """对单个疾病做NER, 返回 state."""
        keywords = REPORT_KEYWORDS.get(disease, [])
        states = []
        for kw in keywords:
            for m in re.finditer(re.escape(kw), report_lower):
                ctx = report_lower[max(0, m.start() - self.window): m.start()]
                states.append(self._classify_occurrence(ctx))
        if "positive" in states:
            return "positive"
        if "uncertain" in states:
            return "uncertain"
        if "negative" in states:
            return "negative"
        return "unmentioned"

    @staticmethod
    def _detect_normal(report_lower):
        """检测报告是否含"正常"表述."""
        return any(p in report_lower for p in _NORMAL_PHRASES)

    def compute_stats_single(self, sample, context=False):
        stats = sample.get(Fields.stats, {})
        if "report_findings" in stats:
            return sample

        meta = sample.get("meta", {})
        report = meta.get("report", "") or sample.get("text", "")
        report_lower = report.lower()

        findings = {}
        for disease in DISEASES:
            findings[disease] = {"state": self._ner_disease(report_lower, disease)}

        stats["report_findings"] = findings
        stats["report_normal"] = self._detect_normal(report_lower)
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True


# =============================================================================
# 4) ImageReportConflictFilter —— 图片-报告三态冲突矩阵
# =============================================================================
@OPERATORS.register_module("image_report_conflict_filter")
class ImageReportConflictFilter(Filter):
    """图片-报告三态冲突矩阵 Filter.

    处理流程 (对每个疾病):
      - 图片阳性 + 报告否定   → 图片↔报告否定 (severity: raw>=0.7 HIGH, >=0.55 MEDIUM, else LOW)
      - 图片阳性 + 报告不确定  → 图片↔报告不确定 (LOW)
      - 图片阳性 + 报告unmentioned + 报告称正常 → 图片↔报告结论 (MEDIUM)
      - 报告阳性 + 图片阴性    → 报告↔图片 (MEDIUM)
      - 报告阳性 + 报告称正常  → 报告内部 (MEDIUM, 聚合所有阳性疾病)
    写入 stats.conflicts / stats.conflict_count.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _negation_severity(raw):
        """否定冲突严重度: raw>=0.7 HIGH, >=0.55 MEDIUM, else LOW."""
        if raw >= _SEV_HIGH:
            return "HIGH"
        if raw >= _SEV_MEDIUM:
            return "MEDIUM"
        return "LOW"

    def compute_stats_single(self, sample, context=False):
        stats = sample.get(Fields.stats, {})
        if "conflicts" in stats:
            return sample

        xray_pred = stats.get("xray_predictions", {})
        report_findings = stats.get("report_findings", {})
        report_normal = stats.get("report_normal", False)

        conflicts = []
        positive_report_diseases = []

        for disease in DISEASES:
            img = xray_pred.get(disease, {})
            img_pos = img.get("positive", False)
            raw = img.get("prob", 0.0)
            rstate = report_findings.get(disease, {}).get("state", "unmentioned")

            if rstate == "positive":
                positive_report_diseases.append(disease)

            # 图片阳性 + 报告否定 → 图片↔报告否定
            if img_pos and rstate == "negative":
                sev = self._negation_severity(raw)
                conflicts.append({
                    "disease": disease,
                    "type": "图片↔报告否定",
                    "severity": sev,
                    "detail": f"图片{disease}(raw={raw:.3f}>0.5) 但报告否定",
                })
            # 图片阳性 + 报告不确定 → 图片↔报告不确定
            elif img_pos and rstate == "uncertain":
                conflicts.append({
                    "disease": disease,
                    "type": "图片↔报告不确定",
                    "severity": "LOW",
                    "detail": f"图片{disease}(raw={raw:.3f}) 报告不确定",
                })
            # 图片阳性 + 报告unmentioned + 报告称正常 → 图片↔报告结论
            elif img_pos and rstate == "unmentioned" and report_normal:
                conflicts.append({
                    "disease": disease,
                    "type": "图片↔报告结论",
                    "severity": "MEDIUM",
                    "detail": f"图片{disease}(raw={raw:.3f}) 但报告称正常",
                })
            # 报告阳性 + 图片阴性 → 报告↔图片
            elif not img_pos and rstate == "positive":
                conflicts.append({
                    "disease": disease,
                    "type": "报告↔图片",
                    "severity": "MEDIUM",
                    "detail": f"报告阳性{disease} 但图片未检出(raw={raw:.3f}<0.5)",
                })

        # 报告内部冲突: 报告阳性 + 报告称正常
        if report_normal and positive_report_diseases:
            diseases_str = ", ".join(positive_report_diseases)
            conflicts.append({
                "disease": diseases_str,
                "type": "报告内部",
                "severity": "MEDIUM",
                "detail": f"报告阳性({diseases_str}) 但结论称正常",
            })

        stats["conflicts"] = conflicts
        stats["conflict_count"] = len(conflicts)
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True
