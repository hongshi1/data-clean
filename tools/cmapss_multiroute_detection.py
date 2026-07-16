#!/usr/bin/env python3
"""
NASA C-MAPSS真实涡扇发动机数据 · 多路并行不一致性检测
数据: NASA C-MAPSS FD001 (涡扇发动机退化仿真, 真实传感器数据)
模态: 时序(21传感器通道) + 标签(退化/故障)
路线: E(规则驱动) + A(分段式IsolationForest+冲突矩阵) + 退化趋势分析 + 物理约束
"""

import numpy as np
import os
import json
from sklearn.ensemble import IsolationForest
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "nasa_cmapss")

# 21个传感器名称（NASA C-MAPSS标准）
SENSORS = [
    "T2_总温", "T24_低压涡轮温度", "T30_高压涡轮温度", "T50_排气温度",
    "P2_入口压力", "P15_旁路压力", "P30_高压压缩机出口压力",
    "Nf_物理转速", "Nc_核心机转速", "epr_发动机压比",
    "Ps30_静压", "phi_流量比", "NRf_校正转速", "NRc_校正核心转速",
    "BPR_旁路比", "farB_燃油空气比", "htBleed_引气",
    "Nf_dmd_转速需求", "PCNf_rNf_转速比",
    "W31_冷却流量", "W32_冷却流量"
]

# 传感器正常范围（基于FD001数据集统计，海平面工况）
# 来源: Saxena et al. 2008 + 学术文献经验值
SENSOR_RANGES = {
    0:  (518.0, 519.5),    # T2: 海平面总温基本恒定
    1:  (641.0, 644.5),    # T24
    2:  (1585, 1595),      # T30
    3:  (1395, 1410),      # T50
    4:  (14.5, 14.7),      # P2
    5:  (21.5, 21.7),      # P15
    6:  (550, 560),        # P30
    7:  (2380, 2395),      # Nf
    8:  (9000, 9100),      # Nc
    9:  (1.25, 1.35),      # epr
    10: (47.0, 48.0),      # Ps30
    11: (520, 525),        # phi
    12: (2380, 2395),      # NRf
    13: (8100, 8200),      # NRc
    14: (8.3, 8.5),        # BPR
    15: (0.02, 0.04),      # farB
    16: (390, 395),        # htBleed
    17: (2380, 2395),      # Nf_dmd
    18: (99.5, 100.5),     # PCNf_rNf
    19: (38.5, 39.7),      # W31
    20: (23.2, 23.6),      # W32
}

# 关键退化传感器（学术文献确认：这些传感器在退化过程中有明显趋势）
DEGRADATION_SENSORS = [1, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 19, 20]
# 退化方向: +1=上升退化, -1=下降退化
DEGRADATION_DIR = {
    1: +1,   # T24: 退化时温度↑
    3: +1,   # T50: 排气温度↑（最经典的退化指标）
    5: -1,   # P15: 压力↓
    6: -1,   # P30: 高压压缩机出口压力↓（HPC退化直接指标）
    7: +1,   # Nf: 转速↑
    8: -1,   # Nc: 核心机转速↓
    10: -1,  # Ps30: 静压↓
    11: -1,  # phi: 流量↓
    12: +1,  # NRf
    13: -1,  # NRc
    14: -1,  # BPR: 旁路比↓
    15: +1,  # farB
    16: +1,  # htBleed: 引气↑
    19: +1,  # W31
    20: +1,  # W32
}


def load_cmapss(filepath):
    """加载C-MAPSS数据，返回{unit: {sensor: [values], cycle: [...]}}"""
    units_data = defaultdict(lambda: {"cycles": [], "sensors": defaultdict(list), "ops": defaultdict(list)})
    
    with open(filepath) as f:
        for line in f:
            cols = line.split()
            if len(cols) < 26:
                continue
            unit = int(cols[0])
            cycle = int(cols[1])
            units_data[unit]["cycles"].append(cycle)
            for i in range(3):  # 操作设置
                units_data[unit]["ops"][i].append(float(cols[2 + i]))
            for i in range(21):  # 传感器
                units_data[unit]["sensors"][i].append(float(cols[5 + i]))
    
    return dict(units_data)


# ============================================================
# 路线E：规则驱动（传感器通道范围检查）
# ============================================================
def route_E_rules(unit_data, unit_id):
    """逐传感器范围检查"""
    conflicts = []
    for sidx in range(21):
        vals = np.array(unit_data["sensors"][sidx])
        lo, hi = SENSOR_RANGES[sidx]
        out_ratio = ((vals < lo) | (vals > hi)).sum() / len(vals)
        
        if out_ratio > 0.1:
            severity = "HIGH" if out_ratio > 0.3 else "MEDIUM"
            conflicts.append({
                "route": "E",
                "unit": unit_id,
                "sensor": SENSORS[sidx],
                "sensor_idx": sidx,
                "type": "传感器越限",
                "out_of_range_ratio": round(float(out_ratio), 3),
                "normal_range": f"[{lo}, {hi}]",
                "actual_range": f"[{vals.min():.2f}, {vals.max():.2f}]",
                "severity": severity,
            })
    return conflicts


# ============================================================
# 路线A：分段式（IsolationForest时序异常检测）
# ============================================================
def route_A_isolation_forest(unit_data, unit_id):
    """IsolationForest时序异常检测"""
    # 构建21维特征矩阵
    matrix = np.column_stack([unit_data["sensors"][i] for i in range(21)])
    
    clf = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    preds = clf.fit_predict(matrix)
    anomaly_mask = preds == -1
    scores = clf.score_samples(matrix)
    
    # 定位异常段（连续异常点）
    anomaly_indices = np.where(anomaly_mask)[0]
    segments = []
    if len(anomaly_indices) > 0:
        start = anomaly_indices[0]
        prev = anomaly_indices[0]
        for idx in anomaly_indices[1:]:
            if idx - prev > 5:  # 间隔>5个循环=新异常段
                segments.append((int(start), int(prev)))
                start = idx
            prev = idx
        segments.append((int(start), int(prev)))
    
    return {
        "anomaly_ratio": round(float(anomaly_mask.sum() / len(preds)), 4),
        "anomaly_count": int(anomaly_mask.sum()),
        "total_cycles": len(preds),
        "score_mean": round(float(scores.mean()), 4),
        "score_min": round(float(scores.min()), 4),
        "anomaly_segments": [(s, e) for s, e in segments],
        "segment_count": len(segments),
    }


# ============================================================
# 退化趋势分析（C-MAPSS特有）
# ============================================================
def degradation_analysis(unit_data, unit_id):
    """检测退化传感器趋势"""
    cycles = np.array(unit_data["cycles"])
    degradations = []
    
    for sidx in DEGRADATION_SENSORS:
        vals = np.array(unit_data["sensors"][sidx])
        if len(vals) < 20:
            continue
        
        # 用前20%和后20%的均值差判断退化趋势
        n = len(vals)
        early_mean = vals[:max(1, n//5)].mean()
        late_mean = vals[-max(1, n//5):].mean()
        change = late_mean - early_mean
        change_ratio = change / (abs(early_mean) + 1e-8)
        
        expected_dir = DEGRADATION_DIR.get(sidx, 0)
        actual_dir = 1 if change > 0 else (-1 if change < 0 else 0)
        
        if expected_dir != 0 and actual_dir == expected_dir and abs(change_ratio) > 0.001:
            degradations.append({
                "sensor": SENSORS[sidx],
                "sensor_idx": sidx,
                "early_mean": round(float(early_mean), 3),
                "late_mean": round(float(late_mean), 3),
                "change": round(float(change), 3),
                "change_ratio": round(float(change_ratio), 5),
                "direction": "↑" if actual_dir > 0 else "↓",
                "expected": "↑" if expected_dir > 0 else "↓",
                "match": True,
            })
        elif expected_dir != 0 and actual_dir != expected_dir and abs(change_ratio) > 0.001:
            degradations.append({
                "sensor": SENSORS[sidx],
                "sensor_idx": sidx,
                "change_ratio": round(float(change_ratio), 5),
                "direction": "↑" if actual_dir > 0 else "↓",
                "expected": "↑" if expected_dir > 0 else "↓",
                "match": False,
                "note": "退化方向与预期不符——物理约束违反候选",
            })
    
    return degradations


# ============================================================
# 多传感器物理约束检查（路线E的L3层）
# ============================================================
def physics_constraints(unit_data, unit_id):
    """检查多传感器物理耦合关系"""
    conflicts = []
    s = unit_data["sensors"]
    n = len(s[0])
    
    # 约束1: T50(排气温度)↑ 应伴随 P30(高压压缩机出口压力)↓
    # 热力学: HPC退化→压缩效率↓→排气温度↑+出口压力↓
    t50 = np.array(s[3])  # T50
    p30 = np.array(s[6])  # P30
    n_half = n // 2
    t50_trend = t50[-n_half:].mean() - t50[:n_half].mean()
    p30_trend = p30[-n_half:].mean() - p30[:n_half].mean()
    
    if t50_trend > 0.5 and p30_trend > 0:  # 温度↑但压力也↑→物理异常
        conflicts.append({
            "route": "E-L3",
            "unit": unit_id,
            "type": "物理约束违反: HPC退化热力学耦合",
            "description": f"T50(排气温度)↑{t50_trend:.2f} 但 P30(压缩机出口压力)↑{p30_trend:.2f}——应↓",
            "physics": "HPC退化→压缩效率↓→排气温度↑+出口压力↓(热力学第一定律)",
            "severity": "HIGH",
        })
    
    # 约束2: Nf(物理转速)与Nf_dmd(转速需求)应接近
    nf = np.array(s[7])
    nf_dmd = np.array(s[17])
    nf_diff = np.abs(nf - nf_dmd)
    if nf_diff.mean() > 10:  # 转速偏差>10rpm
        conflicts.append({
            "route": "E-L3",
            "unit": unit_id,
            "type": "物理约束违反: 转速跟踪偏差",
            "description": f"Nf(实际转速)与Nf_dmd(需求转速)平均偏差={nf_diff.mean():.2f}",
            "physics": "控制器应保持实际转速跟踪需求转速",
            "severity": "MEDIUM",
        })
    
    # 约束3: epr(发动机压比)应在合理范围且稳定
    epr = np.array(s[9])
    if epr.std() > 0.1:
        conflicts.append({
            "route": "E-L3",
            "unit": unit_id,
            "type": "物理约束违反: 压比波动",
            "description": f"epr(发动机压比)标准差={epr.std():.4f}，波动过大",
            "physics": "稳态工况下压比应稳定",
            "severity": "MEDIUM",
        })
    
    return conflicts


# ============================================================
# 冲突矩阵（时序异常 × 退化标签）
# ============================================================
def conflict_matrix(ts_result, deg_count, unit_id, total_cycles):
    """时序异常段 × 退化状态 冲突矩阵"""
    conflicts = []
    anomaly_ratio = ts_result["anomaly_ratio"]
    
    # 退化阶段判断: 后1/3为退化阶段
    deg_start = total_cycles * 2 // 3
    deg_end = total_cycles
    early_end = total_cycles // 3
    
    # 检查异常段是否集中在退化阶段
    late_anomaly = 0
    early_anomaly = 0
    for seg_start, seg_end in ts_result["anomaly_segments"]:
        if seg_start >= deg_start:
            late_anomaly += 1
        elif seg_end <= early_end:
            early_anomaly += 1
    
    # 冲突1: 早期异常（正常阶段出现异常→可能传感器故障）
    if early_anomaly > 0 and late_anomaly == 0:
        conflicts.append({
            "route": "A",
            "unit": unit_id,
            "type": "时序↔退化阶段冲突",
            "description": f"异常仅在早期(正常阶段)出现({early_anomaly}段)，退化阶段无异常",
            "severity": "MEDIUM",
            "evidence": f"早期异常{early_anomaly}段 vs 晚期异常{late_anomaly}段",
        })
    
    # 冲突2: 无退化趋势但时序异常率高
    if deg_count == 0 and anomaly_ratio > 0.1:
        conflicts.append({
            "route": "A",
            "unit": unit_id,
            "type": "时序异常↔退化标签否定",
            "description": f"时序异常率={anomaly_ratio:.1%}但无退化趋势检出",
            "severity": "LOW",
            "evidence": f"IsolationForest检出{ts_result['anomaly_count']}/{ts_result['total_cycles']}个异常但退化趋势分析未检出退化",
        })
    
    # 冲突3: 有退化趋势但时序无异常
    if deg_count > 3 and anomaly_ratio < 0.05:
        conflicts.append({
            "route": "A",
            "unit": unit_id,
            "type": "退化标签↔时序否定",
            "description": f"退化趋势检出{deg_count}个传感器但时序异常率仅{anomaly_ratio:.1%}",
            "severity": "MEDIUM",
            "evidence": f"退化趋势分析检出退化但IsolationForest未检出异常",
        })
    
    return conflicts


# ============================================================
# 主检测流程
# ============================================================
def main():
    filepath = os.path.join(DATA_DIR, "train_FD001.txt")
    print("=" * 90)
    print("NASA C-MAPSS真实涡扇发动机数据 · 多路并行不一致性检测")
    print(f"数据集: C-MAPSS FD001 (涡扇发动机退化仿真, NASA Saxena et al. 2008)")
    print(f"检测路线: E(规则+物理约束) + A(IsolationForest+冲突矩阵) + 退化趋势分析")
    print("=" * 90)
    
    # 加载数据
    units_data = load_cmapss(filepath)
    print(f"\n加载数据: {len(units_data)}台发动机, {sum(len(v['cycles']) for v in units_data.values())}行\n")
    
    all_results = []
    
    for unit_id in sorted(units_data.keys()):
        unit_data = units_data[unit_id]
        total_cycles = len(unit_data["cycles"])
        
        result = {
            "unit": unit_id,
            "total_cycles": total_cycles,
        }
        
        # ===== 路线E: 规则驱动 =====
        e_conflicts = route_E_rules(unit_data, unit_id)
        # 路线E-L3: 物理约束
        physics_conflicts = physics_constraints(unit_data, unit_id)
        all_e = e_conflicts + physics_conflicts
        result["route_E"] = {
            "conflicts": len(e_conflicts),
            "physics_conflicts": len(physics_conflicts),
            "total": len(all_e),
        }
        
        # ===== 路线A: 分段式 =====
        ts_result = route_A_isolation_forest(unit_data, unit_id)
        result["route_A_ts"] = {
            "anomaly_ratio": ts_result["anomaly_ratio"],
            "anomaly_count": ts_result["anomaly_count"],
            "segments": ts_result["segment_count"],
        }
        
        # ===== 退化趋势分析 =====
        degradations = degradation_analysis(unit_data, unit_id)
        matched_deg = [d for d in degradations if d.get("match")]
        mismatched_deg = [d for d in degradations if not d.get("match")]
        result["degradation"] = {
            "matched_sensors": len(matched_deg),
            "mismatched_sensors": len(mismatched_deg),
        }
        
        # ===== 冲突矩阵 =====
        a_conflicts = conflict_matrix(ts_result, len(matched_deg), unit_id, total_cycles)
        result["route_A"] = {
            "conflicts": len(a_conflicts),
        }
        
        # ===== 融合 =====
        total_conflicts = len(all_e) + len(a_conflicts)
        result["fusion"] = {
            "total": total_conflicts,
            "E": len(all_e),
            "A": len(a_conflicts),
        }
        
        all_results.append(result)
        
        # 打印前10台和最后几台
        if unit_id <= 10 or unit_id >= len(units_data) - 2:
            print(f"  发动机{unit_id:>2} | 循环数={total_cycles:>3} | "
                  f"异常率={ts_result['anomaly_ratio']:.1%}({ts_result['anomaly_count']}个,{ts_result['segment_count']}段) | "
                  f"退化传感器={len(matched_deg):>2} | "
                  f"物理违反={len(physics_conflicts)} | "
                  f"冲突={total_conflicts}")
        elif unit_id == 11:
            print(f"  ...")
    
    # ===== 汇总统计 =====
    print(f"\n{'=' * 90}")
    print("汇总统计")
    print(f"{'=' * 90}")
    
    total_units = len(all_results)
    total_e = sum(r["route_E"]["total"] for r in all_results)
    total_a = sum(r["route_A"]["conflicts"] for r in all_results)
    total_physics = sum(r["route_E"]["physics_conflicts"] for r in all_results)
    total_deg = sum(r["degradation"]["matched_sensors"] for r in all_results)
    total_mismatch = sum(r["degradation"]["mismatched_sensors"] for r in all_results)
    total_all = sum(r["fusion"]["total"] for r in all_results)
    
    print(f"\n  发动机总数:     {total_units}台")
    print(f"  数据总行数:     {sum(len(units_data[u]['cycles']) for u in units_data)}行")
    print(f"  传感器通道数:   21个/台")
    print(f"\n  路线E(规则):    {total_e}条冲突 (其中物理约束违反={total_physics})")
    print(f"  路线A(分段式):  {total_a}条冲突")
    print(f"  融合总计:       {total_all}条冲突")
    print(f"\n  退化趋势检出:   {total_deg}个传感器×发动机组合有退化趋势")
    print(f"  方向不一致:     {total_mismatch}个传感器退化方向与预期不符(物理约束违反候选)")
    
    # 逐发动机冲突分布
    print(f"\n  各发动机冲突分布:")
    for r in all_results:
        bar = "█" * min(r["fusion"]["total"], 30)
        print(f"    发动机{r['unit']:>2}: 循环{r['total_cycles']:>3} | 冲突{r['fusion']['total']:>2}条 "
              f"(E={r['route_E']['total']} A={r['route_A']['conflicts']}) {bar}")
    
    # 物理约束违反详情
    print(f"\n  物理约束违反详情:")
    for r in all_results:
        unit_id = r["unit"]
        unit_data = units_data[unit_id]
        p_conflicts = physics_constraints(unit_data, unit_id)
        for pc in p_conflicts:
            print(f"    发动机{unit_id:>2} [{pc['severity']}] {pc['type']}")
            print(f"           {pc['description']}")
    
    # 保存结果
    output_path = os.path.join(DATA_DIR, "cmapss_detection_results.json")
    # 补充完整信息到结果
    for r, unit_id in zip(all_results, sorted(units_data.keys())):
        unit_data = units_data[unit_id]
        r["route_E_details"] = route_E_rules(unit_data, unit_id)
        r["physics_details"] = physics_constraints(unit_data, unit_id)
        r["route_A_details"] = route_A_isolation_forest(unit_data, unit_id)
        r["degradation_details"] = degradation_analysis(unit_data, unit_id)
        r["conflict_matrix"] = conflict_matrix(
            route_A_isolation_forest(unit_data, unit_id),
            len([d for d in degradation_analysis(unit_data, unit_id) if d.get("match")]),
            unit_id, len(unit_data["cycles"])
        )
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  详细结果已保存: {output_path}")


if __name__ == "__main__":
    main()
