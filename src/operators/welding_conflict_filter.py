import csv
import math
import os

from data_juicer.ops.base_op import OPERATORS, Filter
from data_juicer.utils.constant import Fields, StatsKeys


@OPERATORS.register_module("welding_conflict_filter")
class WeldingConflictFilter(Filter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def _read_csv_stats(csv_path):
        if not csv_path or not os.path.isfile(csv_path):
            return None

        currents = []
        voltages = []
        pressures = []
        co2_flows = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cur = float(row.get("Primary Weld Current", 0))
                    vol = float(row.get("Secondary Weld Voltage", 0))
                    prs = float(row.get("Pressure", 0))
                    co2 = float(row.get("CO2 Weld Flow", 0))
                    currents.append(cur)
                    voltages.append(vol)
                    pressures.append(prs)
                    co2_flows.append(co2)
                except (ValueError, KeyError):
                    continue

        if not currents:
            return None

        n = len(currents)
        mean_cur = sum(currents) / n
        max_cur = max(currents)
        min_cur = min(currents)
        std_cur = math.sqrt(sum((x - mean_cur) ** 2 for x in currents) / n) if n > 1 else 0

        mean_vol = sum(voltages) / n
        max_vol = max(voltages)
        min_vol = min(voltages)
        std_vol = math.sqrt(sum((x - mean_vol) ** 2 for x in voltages) / n) if n > 1 else 0

        return {
            "current_mean": round(mean_cur, 2),
            "current_max": round(max_cur, 2),
            "current_min": round(min_cur, 2),
            "current_std": round(std_cur, 2),
            "voltage_mean": round(mean_vol, 2),
            "voltage_max": round(max_vol, 2),
            "voltage_min": round(min_vol, 2),
            "voltage_std": round(std_vol, 2),
            "pressure_mean": round(sum(pressures) / n, 2),
            "co2_flow_mean": round(sum(co2_flows) / n, 2),
            "sample_count": n,
        }

    @staticmethod
    def _check_conflict(stats, label):
        if stats is None:
            return True, "无法读取传感器数据"

        c_max = stats["current_max"]
        c_mean = stats["current_mean"]
        c_std = stats["current_std"]
        v_max = stats["voltage_max"]
        label = str(label).strip().lower()

        if "烧穿" in label:
            if c_max < 150:
                return True, f"标签为烧穿，但电流最大值仅{c_max}A，远低于典型阈值150A"
            if v_max < 40:
                return True, f"标签为烧穿，但电压最大值仅{v_max}V，偏低"
            return False, "传感器数据与烧穿标签一致（电流/电压偏高）"

        elif "裂纹" in label:
            if c_std < 50:
                return True, f"标签为裂纹，但电流标准差仅{c_std}A，波动不足，与裂纹典型特征不符"
            if c_max < 150:
                return True, f"标签为裂纹，但电流最大值仅{c_max}A，偏低"
            return False, "传感器数据与裂纹标签一致（电流波动大）"

        elif "熔合" in label or "融合" in label:
            if c_mean > 150:
                return True, f"标签为熔合不良，但电流均值{c_mean}A偏高，热量充足不应出现熔合不良"
            if c_max > 220:
                return True, f"标签为熔合不良，但电流峰值{c_max}A过高，与热量不足矛盾"
            return False, "传感器数据与熔合不良标签一致（电流偏低）"

        elif "正常" in label or "good" in label:
            if c_max > 250:
                return True, f"标签为正常，但电流峰值{c_max}A过高，存在异常"
            if c_std > 120:
                return True, f"标签为正常，但电流标准差{c_std}A过大，波动异常"
            return False, "传感器数据与正常标签一致"

        return False, f"未知标签'{label}'，跳过冲突检测"

    def compute_stats_single(self, sample):
        meta = sample.get("meta", {})
        csv_path = meta.get("csv_path", "")
        stats = sample.get(Fields.stats, {})
        if "welding_sensor_stats" in stats:
            return sample

        sensor_stats = self._read_csv_stats(csv_path)
        label = meta.get("defect_label", "")
        is_conflict, reason = self._check_conflict(sensor_stats, label)

        stats["welding_sensor_stats"] = sensor_stats or {}
        stats["welding_conflict"] = is_conflict
        stats["welding_conflict_reason"] = reason
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True

