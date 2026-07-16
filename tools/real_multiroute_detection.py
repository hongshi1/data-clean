#!/usr/bin/env python3
"""
真实数据多路并行不一致性检测演示
数据: H4R Welding Dataset (真实工业焊接数据)
模态: 时序(6通道传感器) + 图像(焊缝照片) + 标签(缺陷类型)
路线: E(规则) + A(分段式IsolationForest+冲突矩阵) + B(CLIP向量级)
"""

import csv
import math
import json
import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
from sklearn.ensemble import IsolationForest

# ============================================================
# 数据加载
# ============================================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "h4r_welding")

SAMPLES = {
    "crack": {
        "csv": "crack_sample.csv",
        "img": "crack_img.jpg",
        "label": "裂纹(crack)",
        "label_en": "crack",
    },
    "good": {
        "csv": "good_sample.csv",
        "img": "good_img.jpg",
        "label": "正常(good)",
        "label_en": "good",
    },
    "fusion": {
        "csv": "fusion_sample.csv",
        "img": "fusion_img.jpg",
        "label": "熔合(fusion)",
        "label_en": "fusion",
    },
    "weld": {
        "csv": "weld_sample.csv",
        "img": "weld_img1.jpg",
        "label": "焊接(weld)",
        "label_en": "weld",
    },
}

# 传感器通道
CHANNELS = ["Pressure", "CO2 Weld Flow", "Feed", "Primary Weld Current", "Wire Consumed", "Secondary Weld Voltage"]
# 简称
CH_SHORT = {"Pressure": "压力", "CO2 Weld Flow": "CO2流量", "Feed": "送丝",
            "Primary Weld Current": "焊接电流", "Wire Consumed": "焊丝消耗", "Secondary Weld Voltage": "焊接电压"}


def load_welding_csv(filepath):
    """加载焊接CSV，返回各通道时序数据"""
    data = {ch: [] for ch in CHANNELS}
    timestamps = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for ch in CHANNELS:
                try:
                    data[ch].append(float(row.get(ch, 0)))
                except (ValueError, TypeError):
                    data[ch].append(0.0)
            timestamps.append(row.get("Time", ""))
    return data, timestamps


def compute_stats(values):
    """计算统计量"""
    arr = np.array(values)
    return {
        "mean": round(float(arr.mean()), 4),
        "std": round(float(arr.std()), 4),
        "max": round(float(arr.max()), 4),
        "min": round(float(arr.min()), 4),
        "count": len(arr),
    }


# ============================================================
# 路线E：规则驱动（传感器通道范围检查）
# ============================================================
# 焊接传感器正常范围（基于工业经验，类比航发ISO 10816）
SENSOR_RANGES = {
    "Pressure":           {"normal": (3.0, 4.0),   "unit": "bar",   "severity_high": {"<2.5": "HIGH", ">4.5": "HIGH"}},
    "CO2 Weld Flow":      {"normal": (-0.5, 0.5),  "unit": "L/min", "severity_high": {"<-1.0": "HIGH", ">1.0": "HIGH"}},
    "Primary Weld Current":{"normal": (0, 300),    "unit": "A",     "severity_high": {">350": "HIGH"}},
    "Secondary Weld Voltage":{"normal": (0, 35),   "unit": "V",     "severity_high": {">40": "HIGH"}},
    "Feed":               {"normal": (-1.0, 2.0),  "unit": "m/min", "severity_high": {">3.0": "HIGH"}},
    "Wire Consumed":      {"normal": (0, 50),      "unit": "mm",    "severity_high": {">60": "HIGH"}},
}

def route_E_rules(data):
    """路线E：逐通道范围检查"""
    conflicts = []
    for ch in CHANNELS:
        lo, hi = SENSOR_RANGES[ch]["normal"]
        vals = np.array(data[ch])
        out_of_range = ((vals < lo) | (vals > hi)).sum()
        ratio = out_of_range / len(vals) if len(vals) > 0 else 0
        if ratio > 0.1:  # 超过10%的时间点超出范围
            severity = "HIGH" if ratio > 0.3 else "MEDIUM"
            conflicts.append({
                "route": "E",
                "channel": ch,
                "channel_cn": CH_SHORT[ch],
                "type": "传感器越限",
                "out_of_range_ratio": round(ratio, 3),
                "out_of_range_count": int(out_of_range),
                "total_count": len(vals),
                "normal_range": f"[{lo}, {hi}]",
                "actual_max": round(float(vals.max()), 3),
                "actual_min": round(float(vals.min()), 3),
                "severity": severity,
            })
    return conflicts


# ============================================================
# 路线A：分段式（IsolationForest时序异常 + 冲突矩阵）
# ============================================================
def route_A_isolation_forest(data, label):
    """路线A-1: IsolationForest时序异常检测"""
    # 构建特征矩阵：每个时间点是一个样本，6通道为特征
    matrix = np.column_stack([data[ch] for ch in CHANNELS])
    
    # IsolationForest检测异常
    clf = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
    predictions = clf.fit_predict(matrix)
    # -1 = 异常, 1 = 正常
    anomaly_mask = predictions == -1
    anomaly_ratio = anomaly_mask.sum() / len(predictions)
    anomaly_score = clf.score_samples(matrix)  # 越负越异常
    
    return {
        "anomaly_ratio": round(float(anomaly_ratio), 4),
        "anomaly_count": int(anomaly_mask.sum()),
        "total_count": len(predictions),
        "mean_score": round(float(anomaly_score.mean()), 4),
        "min_score": round(float(anomaly_score.min()), 4),
        "anomaly_indices": np.where(anomaly_mask)[0].tolist()[:20],  # 前20个异常点
    }


def route_A_conflict_matrix(ts_result, label):
    """路线A-3: 时序异常 × 缺陷标签 冲突矩阵"""
    anomaly_ratio = ts_result["anomaly_ratio"]
    
    # 缺陷标签四态（类比医疗CheXpert四态）
    # 焊接场景：标签直接给出缺陷类型
    # 如果标签是"good"（正常），但时序检测到异常→冲突
    # 如果标签是缺陷类型，但时序没异常→冲突
    
    conflicts = []
    
    if label == "good":
        # 标签说正常，但时序有异常
        if anomaly_ratio > 0.1:
            severity = "HIGH" if anomaly_ratio > 0.25 else "MEDIUM"
            conflicts.append({
                "route": "A",
                "type": "时序↔标签否定",
                "description": f"标签='正常' 但时序异常率={anomaly_ratio:.1%}",
                "severity": severity,
                "evidence": f"IsolationForest检出{ts_result['anomaly_count']}/{ts_result['total_count']}个异常点",
            })
    else:
        # 标签说有缺陷，但时序没异常
        if anomaly_ratio < 0.05:
            conflicts.append({
                "route": "A",
                "type": "标签↔时序",
                "description": f"标签='{label}' 但时序异常率仅={anomaly_ratio:.1%}",
                "severity": "MEDIUM",
                "evidence": f"时序几乎无异常，但标签标注有缺陷",
            })
    
    return conflicts


# ============================================================
# 路线A补充：逐通道异常检测（定位到哪个通道异常）
# ============================================================
def route_A_per_channel(data):
    """逐通道IsolationForest，定位异常通道"""
    channel_results = {}
    for ch in CHANNELS:
        vals = np.array(data[ch]).reshape(-1, 1)
        clf = IsolationForest(n_estimators=50, contamination=0.15, random_state=42)
        preds = clf.fit_predict(vals)
        ratio = (preds == -1).sum() / len(preds)
        scores = clf.score_samples(vals)
        channel_results[ch] = {
            "anomaly_ratio": round(float(ratio), 4),
            "score_mean": round(float(scores.mean()), 4),
            "score_min": round(float(scores.min()), 4),
        }
    return channel_results


# ============================================================
# 边界带降级（类比医疗场景）
# ============================================================
def apply_boundary_degradation(conflicts, anomaly_ratio):
    """异常率在边界带[0.08, 0.12]内时降级"""
    BOUNDARY_LOW, BOUNDARY_HIGH = 0.08, 0.12
    in_boundary = BOUNDARY_LOW <= anomaly_ratio <= BOUNDARY_HIGH
    
    for c in conflicts:
        if in_boundary and c.get("severity") == "HIGH":
            c["severity"] = "MEDIUM"
            c["degraded"] = True
            c["note"] = f"异常率{anomaly_ratio:.1%}在边界带[{BOUNDARY_LOW:.0%},{BOUNDARY_HIGH:.0%}]内，降级处理"
    
    return conflicts


# ============================================================
# 主检测流程
# ============================================================
def detect_sample(sample_name, sample_info):
    """对单个样本跑多路并行检测"""
    csv_path = os.path.join(DATA_DIR, sample_info["csv"])
    
    if not os.path.isfile(csv_path):
        return {"sample": sample_name, "error": f"CSV不存在: {csv_path}"}
    
    # 加载数据
    data, timestamps = load_welding_csv(csv_path)
    label = sample_info["label_en"]
    
    result = {
        "sample": sample_name,
        "label": sample_info["label"],
        "csv_file": sample_info["csv"],
        "data_points": len(timestamps),
        "channels": len(CHANNELS),
    }
    
    # ===== 路线E：规则驱动 =====
    route_e_conflicts = route_E_rules(data)
    result["route_E"] = {
        "method": "规则驱动(传感器范围检查)",
        "conflicts": route_e_conflicts,
        "conflict_count": len(route_e_conflicts),
    }
    
    # ===== 路线A：分段式 =====
    # A-1: 时序异常检测
    ts_result = route_A_isolation_forest(data, label)
    result["route_A_ts"] = ts_result
    
    # A-2: 逐通道异常
    ch_results = route_A_per_channel(data)
    result["route_A_channels"] = ch_results
    
    # A-3: 冲突矩阵
    route_a_conflicts = route_A_conflict_matrix(ts_result, label)
    # 边界带降级
    route_a_conflicts = apply_boundary_degradation(route_a_conflicts, ts_result["anomaly_ratio"])
    result["route_A"] = {
        "method": "分段式(IsolationForest+冲突矩阵)",
        "ts_anomaly_ratio": ts_result["anomaly_ratio"],
        "conflicts": route_a_conflicts,
        "conflict_count": len(route_a_conflicts),
    }
    
    # ===== 通道统计 =====
    result["channel_stats"] = {ch: compute_stats(data[ch]) for ch in CHANNELS}
    
    # ===== 融合 =====
    all_conflicts = route_e_conflicts + route_a_conflicts
    result["fusion"] = {
        "total_conflicts": len(all_conflicts),
        "by_route": {
            "E": len(route_e_conflicts),
            "A": len(route_a_conflicts),
        },
        "by_severity": {
            "HIGH": sum(1 for c in all_conflicts if c.get("severity") == "HIGH"),
            "MEDIUM": sum(1 for c in all_conflicts if c.get("severity") == "MEDIUM"),
            "LOW": sum(1 for c in all_conflicts if c.get("severity") == "LOW"),
        },
    }
    
    return result


def main():
    print("=" * 80)
    print("真实数据多路并行不一致性检测")
    print(f"数据集: H4R Welding Dataset (真实工业焊接数据)")
    print(f"模态: 时序(6通道传感器) + 图像(焊缝照片) + 标签(缺陷类型)")
    print(f"检测路线: E(规则驱动) + A(分段式IsolationForest+冲突矩阵)")
    print("=" * 80)
    print()
    
    all_results = []
    
    for name, info in SAMPLES.items():
        result = detect_sample(name, info)
        all_results.append(result)
        
        print(f"{'─' * 70}")
        print(f"样本: {name} | 标签: {info['label']} | 数据点: {result.get('data_points', 'N/A')}")
        print(f"{'─' * 70}")
        
        if "error" in result:
            print(f"  ❌ {result['error']}")
            continue
        
        # 通道统计
        print(f"\n  📊 传感器通道统计:")
        print(f"  {'通道':<12} {'均值':>8} {'标准差':>8} {'最大':>8} {'最小':>8}")
        for ch in CHANNELS:
            s = result["channel_stats"][ch]
            print(f"  {CH_SHORT[ch]:<10} {s['mean']:>8.3f} {s['std']:>8.3f} {s['max']:>8.3f} {s['min']:>8.3f}")
        
        # 路线A时序异常
        ts = result["route_A_ts"]
        print(f"\n  🔍 路线A - IsolationForest时序异常检测:")
        print(f"     异常率: {ts['anomaly_ratio']:.1%} ({ts['anomaly_count']}/{ts['total_count']}个异常点)")
        print(f"     异常分数: 均值={ts['mean_score']:.4f}, 最低={ts['min_score']:.4f}")
        
        # 逐通道异常
        print(f"\n  📈 逐通道异常率:")
        for ch in CHANNELS:
            cr = result["route_A_channels"][ch]
            bar = "█" * int(cr["anomaly_ratio"] * 50)
            print(f"     {CH_SHORT[ch]:<10} {cr['anomaly_ratio']:.1%} {bar}")
        
        # 路线E规则
        print(f"\n  📋 路线E - 规则驱动(传感器范围检查):")
        if result["route_E"]["conflict_count"] == 0:
            print(f"     ✅ 无越限冲突")
        else:
            for c in result["route_E"]["conflicts"]:
                print(f"     🔴 [{c['severity']}] {c['channel_cn']} 越限率={c['out_of_range_ratio']:.1%} "
                      f"(正常范围{c['normal_range']}, 实际[{c['actual_min']:.2f}, {c['actual_max']:.2f}])")
        
        # 路线A冲突
        print(f"\n  🔀 路线A - 冲突矩阵(时序异常×缺陷标签):")
        if result["route_A"]["conflict_count"] == 0:
            print(f"     ✅ 无冲突")
        else:
            for c in result["route_A"]["conflicts"]:
                degraded = " [边界带降级]" if c.get("degraded") else ""
                print(f"     🔴 [{c['severity']}] {c['type']}: {c['description']}{degraded}")
                print(f"        证据: {c['evidence']}")
        
        # 融合结果
        f = result["fusion"]
        print(f"\n  🎯 融合结果: 共{f['total_conflicts']}条冲突 "
              f"(HIGH={f['by_severity']['HIGH']}, MEDIUM={f['by_severity']['MEDIUM']}, LOW={f['by_severity']['LOW']})")
        print()
    
    # 汇总统计
    print("=" * 80)
    print("汇总统计")
    print("=" * 80)
    
    total_conflicts = sum(r.get("fusion", {}).get("total_conflicts", 0) for r in all_results)
    high_conflicts = sum(r.get("fusion", {}).get("by_severity", {}).get("HIGH", 0) for r in all_results)
    med_conflicts = sum(r.get("fusion", {}).get("by_severity", {}).get("MEDIUM", 0) for r in all_results)
    
    print(f"\n  样本总数: {len(all_results)}")
    print(f"  冲突总数: {total_conflicts}")
    print(f"  HIGH: {high_conflicts}, MEDIUM: {med_conflicts}")
    print(f"\n  各样本冲突分布:")
    for r in all_results:
        f = r.get("fusion", {})
        print(f"    {r['sample']:<10} ({r['label']:<12}): {f.get('total_conflicts', 0)}条冲突")
    
    # 保存结果
    output_path = os.path.join(DATA_DIR, "real_detection_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  详细结果已保存: {output_path}")


if __name__ == "__main__":
    main()
