"""时序数据处理算子集合 (Data-Juicer custom operators).

包含三个面向焊接场景的时序算子:
  - TimeSeriesAnomalyFilter:   基于IsolationForest的时序异常检测Filter
  - TimeSeriesStatsMapper:     焊接段统计特征Mapper
  - CrossModalConflictFilter:  图像(CLIP)+时序+文本标签 跨模态冲突检测Filter

设计依据:
  - 继承 data_juicer.ops.base_op 中的 Filter / Mapper 基类
  - 通过 @OPERATORS.register_module 注册, 可在YAML中通过 custom_operator_paths 引用
  - 数据格式遵循 Data-Juicer 约定: JSONL记录含 text / images / meta{csv_path, defect_label}
  - CSV列: Date,Time,Part No,Pressure,CO2 Weld Flow,Feed,
           Primary Weld Current,Wire Consumed,Secondary Weld Voltage,Remarks
"""
import csv
import math
import os

from data_juicer.ops.base_op import OPERATORS, Filter, Mapper
from data_juicer.utils.constant import Fields

# CSV列名常量
COL_CURRENT = "Primary Weld Current"
COL_VOLTAGE = "Secondary Weld Voltage"
COL_PRESSURE = "Pressure"
COL_CO2 = "CO2 Weld Flow"

# 焊接段判定阈值: 电流>10A 视为有效焊接区间
WELD_CURRENT_THRESHOLD = 10.0


def _read_csv_series(csv_path):
    """读取CSV并返回四路时序信号列表; 失败返回None."""
    if not csv_path or not os.path.isfile(csv_path):
        return None
    currents, voltages, pressures, co2_flows = [], [], [], []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                currents.append(float(row.get(COL_CURRENT, 0)))
                voltages.append(float(row.get(COL_VOLTAGE, 0)))
                pressures.append(float(row.get(COL_PRESSURE, 0)))
                co2_flows.append(float(row.get(COL_CO2, 0)))
            except (ValueError, KeyError):
                continue
    if not currents:
        return None
    return currents, voltages, pressures, co2_flows


def _stats(values):
    """计算一维序列的统计量."""
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "max": 0.0, "min": 0.0, "count": 0}
    mean = sum(values) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in values) / n) if n > 1 else 0.0
    return {
        "mean": round(mean, 3),
        "std": round(std, 3),
        "max": round(max(values), 3),
        "min": round(min(values), 3),
        "count": n,
    }


# =============================================================================
# a) TimeSeriesAnomalyFilter —— 时序异常检测Filter
# =============================================================================
@OPERATORS.register_module("time_series_anomaly_filter")
class TimeSeriesAnomalyFilter(Filter):
    """基于IsolationForest的时序异常检测Filter.

    处理流程:
      1. 读取meta.csv_path指向的CSV, 提取 [电流/电压/气压/CO2] 四路时序
      2. 将每个时间点视为一个样本, 用IsolationForest检测异常时间点
      3. anomaly_score = 异常时间点占比 (0~1, 越大越异常)
      4. 同时计算各路信号的统计特征(mean/std/max/min)
      5. process_single: 保留 anomaly_score < threshold 的样本
    """

    def __init__(self, threshold=0.5, contamination=0.1, random_state=42, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold = threshold
        self.contamination = contamination
        self.random_state = random_state

    def compute_stats_single(self, sample):
        meta = sample.get("meta", {})
        csv_path = meta.get("csv_path", "")
        stats = sample.get(Fields.stats, {})
        if "ts_anomaly_score" in stats:
            return sample

        series = _read_csv_series(csv_path)
        if series is None:
            stats["ts_anomaly_score"] = 1.0
            stats["ts_anomaly_reason"] = "无法读取时序CSV"
            stats["ts_signal_stats"] = {}
            sample[Fields.stats] = stats
            return sample

        currents, voltages, pressures, co2_flows = series
        n = len(currents)

        # 统计特征
        stats["ts_signal_stats"] = {
            "current": _stats(currents),
            "voltage": _stats(voltages),
            "pressure": _stats(pressures),
            "co2_flow": _stats(co2_flows),
        }

        # IsolationForest异常检测: 每个时间点是一个4维样本
        anomaly_ratio = 0.0
        reason = ""
        if n >= 4:
            try:
                import numpy as np
                from sklearn.ensemble import IsolationForest

                X = np.column_stack([currents, voltages, pressures, co2_flows])
                clf = IsolationForest(
                    n_estimators=80,
                    contamination=self.contamination,
                    random_state=self.random_state,
                )
                preds = clf.fit_predict(X)  # 1=正常, -1=异常
                anomaly_count = int((preds == -1).sum())
                anomaly_ratio = round(anomaly_count / n, 4)
                reason = f"IsolationForest检测: {anomaly_count}/{n} 时间点异常"
            except Exception as e:
                reason = f"IsolationForest失败: {e}"
                anomaly_ratio = 0.0
        else:
            reason = f"时间点不足({n}<4), 跳过异常检测"
            anomaly_ratio = 0.0

        stats["ts_anomaly_score"] = anomaly_ratio
        stats["ts_anomaly_reason"] = reason
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        stats = sample.get(Fields.stats, {})
        score = stats.get("ts_anomaly_score", 0.0)
        return score < self.threshold


# =============================================================================
# b) TimeSeriesStatsMapper —— 焊接段统计特征Mapper
# =============================================================================
@OPERATORS.register_module("time_series_stats_mapper")
class TimeSeriesStatsMapper(Mapper):
    """焊接段(current>10A)统计特征Mapper.

    处理流程:
      1. 读取meta.csv_path指向的CSV
      2. 筛选焊接段 (Primary Weld Current > 10A)
      3. 计算: CO2均值 / 压力均值 / 电流std / 电压std
      4. 将结果写入 sample['meta']['ts_stats']
    """

    def __init__(self, current_threshold=WELD_CURRENT_THRESHOLD, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_threshold = current_threshold

    def process_single(self, sample):
        meta = sample.get("meta", {})
        csv_path = meta.get("csv_path", "")
        series = _read_csv_series(csv_path)

        if series is None:
            meta["ts_stats"] = {
                "weld_segment_count": 0,
                "co2_mean": None,
                "pressure_mean": None,
                "current_std": None,
                "voltage_std": None,
                "error": "无法读取时序CSV",
            }
            sample["meta"] = meta
            return sample

        currents, voltages, pressures, co2_flows = series
        # 焊接段掩码: 电流 > 阈值
        weld_mask = [c > self.current_threshold for c in currents]
        weld_count = sum(weld_mask)

        if weld_count == 0:
            meta["ts_stats"] = {
                "weld_segment_count": 0,
                "co2_mean": None,
                "pressure_mean": None,
                "current_std": None,
                "voltage_std": None,
                "error": "无有效焊接段(电流均<=10A)",
            }
            sample["meta"] = meta
            return sample

        weld_co2 = [co2_flows[i] for i in range(len(weld_mask)) if weld_mask[i]]
        weld_pressure = [pressures[i] for i in range(len(weld_mask)) if weld_mask[i]]
        weld_current = [currents[i] for i in range(len(weld_mask)) if weld_mask[i]]
        weld_voltage = [voltages[i] for i in range(len(weld_mask)) if weld_mask[i]]

        meta["ts_stats"] = {
            "weld_segment_count": weld_count,
            "total_samples": len(currents),
            "weld_ratio": round(weld_count / len(currents), 4),
            "co2_mean": round(sum(weld_co2) / weld_count, 3),
            "pressure_mean": round(sum(weld_pressure) / weld_count, 3),
            "current_std": _stats(weld_current)["std"],
            "voltage_std": _stats(weld_voltage)["std"],
            "current_mean": _stats(weld_current)["mean"],
            "voltage_mean": _stats(weld_voltage)["mean"],
        }
        sample["meta"] = meta
        return sample


# =============================================================================
# c) CrossModalConflictFilter —— 跨模态冲突检测Filter
# =============================================================================
# CLIP模型缓存于类属性, 避免每条样本重复加载
_CLIP_CACHE = {"model": None, "processor": None, "loaded": False}

# 缺陷类型 -> CLIP候选文本(用于零样本图像分类)
DEFECT_PROMPTS = {
    "裂纹": ["a photo of a cracked weld seam with cracks", "焊接裂纹缺陷照片"],
    "熔合不良": ["a photo of a weld with poor fusion incomplete fusion", "焊接熔合不良缺陷照片"],
    "正常": ["a photo of a good quality weld seam", "正常焊接焊缝照片"],
    "烧穿": ["a photo of a weld burn-through hole", "焊接烧穿穿孔缺陷照片"],
}


def _load_clip(hf_clip="openai/clip-vit-base-patch32"):
    if not _CLIP_CACHE["loaded"]:
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            _CLIP_CACHE["model"] = CLIPModel.from_pretrained(hf_clip)
            _CLIP_CACHE["processor"] = CLIPProcessor.from_pretrained(hf_clip)
            _CLIP_CACHE["loaded"] = True
        except Exception as e:
            _CLIP_CACHE["error"] = str(e)
            _CLIP_CACHE["loaded"] = True
    return _CLIP_CACHE.get("model"), _CLIP_CACHE.get("processor")


@OPERATORS.register_module("cross_modal_conflict_filter")
class CrossModalConflictFilter(Filter):
    """图像(CLIP)+时序+文本标签 跨模态冲突检测Filter.

    处理流程:
      1. CLIP零样本分类: 用候选缺陷文本对图像打分, 取最高分作为"图像预测缺陷类型"
      2. 时序异常: 复用IsolationForest得到时序异常分(anomaly_ratio)
      3. 冲突判定:
         - 图像预测类型 != 标签 -> 图像-标签冲突
         - 时序异常分高 但标签为"正常" -> 时序-标签冲突
         - 时序正常 但标签为缺陷(裂纹/烧穿/熔合不良) -> 时序-标签冲突
      4. process_single: 无冲突则保留(True), 有冲突则丢弃(False)
    """

    def __init__(self, hf_clip="openai/clip-vit-base-patch32",
                 clip_score_threshold=0.2, ts_anomaly_threshold=0.3,
                 contamination=0.1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hf_clip = hf_clip
        self.clip_score_threshold = clip_score_threshold
        self.ts_anomaly_threshold = ts_anomaly_threshold
        self.contamination = contamination

    @staticmethod
    def _clip_classify(image_path, hf_clip):
        """用CLIP对图像做零样本分类, 返回 (预测缺陷类型, 各类型分数dict)."""
        model, processor = _load_clip(hf_clip)
        if model is None or not image_path or not os.path.isfile(image_path):
            return None, {}
        try:
            import torch
            from PIL import Image

            image = Image.open(image_path).convert("RGB")
            prompts = []
            label_list = []
            for label, texts in DEFECT_PROMPTS.items():
                for t in texts:
                    prompts.append(t)
                    label_list.append(label)
            inputs = processor(text=prompts, images=image, return_tensors="pt",
                               padding=True, truncation=True)
            with torch.no_grad():
                outputs = model(**inputs)
                # logits_per_image shape: [1, num_prompts]
                probs = outputs.logits_per_image.softmax(dim=-1)[0]
            # 聚合: 每个标签取其候选文本的最大概率
            label_scores = {}
            for i, label in enumerate(label_list):
                p = float(probs[i])
                if label not in label_scores or p > label_scores[label]:
                    label_scores[label] = round(p, 4)
            pred_label = max(label_scores, key=label_scores.get)
            return pred_label, label_scores
        except Exception as e:
            return None, {"error": str(e)}

    def _ts_anomaly(self, csv_path):
        """计算时序异常比例."""
        series = _read_csv_series(csv_path)
        if series is None:
            return 1.0, "无法读取时序CSV"
        currents, voltages, pressures, co2_flows = series
        n = len(currents)
        if n < 4:
            return 0.0, f"时间点不足({n})"
        try:
            import numpy as np
            from sklearn.ensemble import IsolationForest

            X = np.column_stack([currents, voltages, pressures, co2_flows])
            clf = IsolationForest(n_estimators=80, contamination=self.contamination,
                                  random_state=42)
            preds = clf.fit_predict(X)
            anomaly_count = int((preds == -1).sum())
            return round(anomaly_count / n, 4), f"{anomaly_count}/{n}异常"
        except Exception as e:
            return 0.0, f"IsolationForest失败: {e}"

    @staticmethod
    def _detect_conflict(pred_label, clip_scores, ts_score, ts_reason, defect_label):
        """综合判定跨模态冲突, 返回 (是否冲突, 原因列表)."""
        label = str(defect_label).strip()
        reasons = []

        # 1. 图像-标签冲突
        if pred_label is not None and pred_label != label:
            score = clip_scores.get(pred_label, 0)
            if score >= 0.2:
                reasons.append(
                    f"图像-标签冲突: CLIP判为[{pred_label}](p={score})，标签为[{label}]"
                )

        # 2. 时序-标签冲突
        is_defect = label in ("裂纹", "烧穿", "熔合不良")
        is_normal = label == "正常"
        if is_normal and ts_score > 0.3:
            reasons.append(f"时序-标签冲突: 标签为正常但时序异常比例高({ts_score})")
        if is_defect and ts_score < 0.02:
            reasons.append(f"时序-标签冲突: 标签为缺陷[{label}]但时序几乎无异常({ts_score})")

        return len(reasons) > 0, reasons

    def compute_stats_single(self, sample):
        meta = sample.get("meta", {})
        csv_path = meta.get("csv_path", "")
        defect_label = meta.get("defect_label", "")
        images = sample.get("images", []) or []
        image_path = images[0] if images else ""

        stats = sample.get(Fields.stats, {})
        if "cross_modal_conflict" in stats:
            return sample

        # 图像侧
        pred_label, clip_scores = self._clip_classify(image_path, self.hf_clip)
        # 时序侧
        ts_score, ts_reason = self._ts_anomaly(csv_path)
        # 冲突判定
        conflict, reasons = self._detect_conflict(
            pred_label, clip_scores, ts_score, ts_reason, defect_label)

        stats["clip_pred_label"] = pred_label
        stats["clip_label_scores"] = clip_scores
        stats["ts_anomaly_score"] = ts_score
        stats["ts_anomaly_reason"] = ts_reason
        stats["cross_modal_conflict"] = conflict
        stats["cross_modal_conflict_reasons"] = reasons
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        stats = sample.get(Fields.stats, {})
        return not stats.get("cross_modal_conflict", False)
