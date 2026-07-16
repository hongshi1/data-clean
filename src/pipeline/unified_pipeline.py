#!/usr/bin/env python3
"""
统一多模态冲突检测Pipeline
Phase 1: 信息抽取(TorchXRayVision/NER/值提取)
Phase 2: LLM推理(Ollama Qwen2判断一致性)
Phase 3: 实体级解释

支持三种数据集: NLMCXR(图片+报告) / MedTVT(血检+标签) / H4R(时序+图片+标签+文本)
"""
import json, os, sys, re, io, base64, requests
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "data-juicer"))

import pandas as pd
import numpy as np

# ============================================================
# Phase 1: 信息抽取 (各模态独立)
# ============================================================

# --- NLMCXR: TorchXRayVision + 报告NER ---
def init_xrv_model():
    """初始化TorchXRayVision (惰性加载)"""
    if not hasattr(init_xrv_model, '_model'):
        import torch, torchxrayvision as xrv
        from skimage.transform import resize
        model = xrv.models.DenseNet(weights="densenet121-res224-mimic_ch")
        model.eval()
        init_xrv_model._model = model
        init_xrv_model._resize = resize
        init_xrv_model._torch = torch
    return init_xrv_model._model, init_xrv_model._resize, init_xrv_model._torch

def extract_image_info(image_bytes):
    """TorchXRayVision: X光片 → 6种疾病概率"""
    from PIL import Image
    model, resize, torch = init_xrv_model()
    
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img_arr = np.array(img)
    
    # TorchXRayVision预处理
    img_norm = model.__class__.__module__  # just to ensure model loaded
    import torchxrayvision as xrv
    img_norm = xrv.datasets.normalize(img_arr, 255)
    img_224 = resize(img_norm, (224, 224), anti_aliasing=True)
    img_t = torch.from_numpy(img_224).unsqueeze(0).unsqueeze(0).float()
    
    with torch.no_grad():
        pred = model(img_t)
    
    PATHO_MAP = {
        "Atelectasis": "Atelectasis(肺不张)",
        "Consolidation": "Consolidation(实变)",
        "Edema": "Edema(水肿)",
        "Cardiomegaly": "Cardiomegaly(心脏肥大)",
        "Pneumothorax": "Pneumothorax(气胸)",
        "Effusion": "Pleural Effusion(胸腔积液)",
    }
    
    results = []
    for i, patho in enumerate(model.pathologies):
        if patho in PATHO_MAP:
            raw = float(pred[0][i])
            positive = raw > 0.5
            if positive or raw > 0.3:  # 记录>0.3的
                results.append(f"{PATHO_MAP[patho]}: {raw:.2f} ({'阳性' if positive else '边界'})")
    
    return results if results else ["所有疾病概率<0.3(未检出明显异常)"]

# 报告NER (改进版: 正则+否定+不确定)
DISEASE_PATTERNS = {
    "Atelectasis(肺不张)": [r"\b(atelectasis|atelectatic)\b"],
    "Consolidation(实变)": [r"\b(consolidation|airspace disease)\b"],
    "Edema(水肿)": [r"\b(edema|oedema)\b"],
    "Cardiomegaly(心脏肥大)": [r"\b(cardiomegaly|cardiac enlargement|heart enlarged|heart size enlarged)\b"],
    "Pneumothorax(气胸)": [r"\b(pneumothorax)\b"],
    "Pleural Effusion(胸腔积液)": [r"\b(effusion|pleural fluid)\b"],
}
NEG_WORDS = ["no evidence of", "no ", "without ", "not ", "absence of", "free of", "clear of", "resolved", "no acute", "no significant"]
UNC_WORDS = ["may represent", "may be", "possible", "question of", "suspect", "cannot exclude", "cannot rule out", "could be", "suggest", "likely", "potential"]
NORMAL_RE = r"\b(clear|no acute|no finding|no active|no evidence|no significant|unremarkable|within normal|lungs are clear|heart size normal)\b"

def extract_report_info(text):
    """报告NER: 提取疾病实体 + 否定/不确定检测"""
    tl = text.lower()
    entities = []
    
    for disease, patterns in DISEASE_PATTERNS.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, tl))
            if not matches:
                continue
            best_state = "unmentioned"
            for m in matches:
                before = tl[max(0, m.start()-30):m.start()]
                after = tl[m.end():m.end()+20]
                is_neg = any(n in before for n in NEG_WORDS)
                is_unc = any(u in before for u in UNC_WORDS) or any(u in after for u in UNC_WORDS[:4])
                state = "否定" if is_neg else ("不确定" if is_unc else "阳性")
                pri = {"阳性": 3, "不确定": 2, "否定": 1, "unmentioned": 0}
                if pri.get(state, 0) > pri.get(best_state, 0):
                    best_state = state
            if best_state != "unmentioned":
                entities.append(f"{disease}: {best_state}")
    
    is_normal = bool(re.search(NORMAL_RE, tl))
    normal_str = "报告结论: 正常/无异常" if is_normal else "报告结论: 有异常发现"
    
    return entities, normal_str

# --- MedTVT: 血检值提取 ---
LAB_INFO = {
    "50893": ("乳酸(Lactate)", "mmol/L", 0.5, 2.0, 5.0),
    "51237": ("肌酐(Creatinine)", "mg/dL", 0.6, 1.2, 2.0),
    "50931": ("血糖(Glucose)", "mg/dL", 70, 140, 300),
    "50971": ("钾(Potassium)", "mmol/L", 3.5, 5.0, 6.0),
    "50820": ("pH", "", 7.35, 7.45, 7.20),
}

def extract_lab_info(row):
    """血检值提取 + 异常标注"""
    results = []
    for itemid, (name, unit, lo, hi, severe) in LAB_INFO.items():
        val = row.get(itemid)
        if pd.isna(val) or val == "":
            continue
        try:
            val = float(val)
        except:
            continue
        
        if val < lo:
            status = "严重偏低" if val < severe else "偏低"
        elif val > hi:
            if name.startswith("pH"):
                status = "严重酸中毒" if val < severe else "酸中毒"
            else:
                status = "严重异常" if val > severe else "异常"
        else:
            status = "正常"
        
        unit_str = f" {unit}" if unit else ""
        results.append(f"{name}: {val}{unit_str} (正常{lo}-{hi}{unit_str}, {status})")
    
    return results

def extract_diagnosis(row):
    """诊断标签提取"""
    diags = []
    for col in ["Atelectasis", "Cardiomegaly", "Edema", "Lung Opacity", "No Finding", "Pleural Effusion"]:
        val = row.get(col)
        if val == 1.0:
            diags.append(col)
        elif val == -1.0:
            diags.append(f"{col}(不确定)")
    return diags if diags else ["无诊断标签"]

# --- H4R: 传感器统计 + CLIP ---
def extract_sensor_info(csv_path):
    """焊接传感器时序统计"""
    if not os.path.exists(csv_path):
        return ["传感器文件不存在"]
    
    df = pd.read_csv(csv_path)
    cols = ['Primary Weld Current', 'Secondary Weld Voltage', 'Pressure', 'CO2 Weld Flow']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    weld_mask = df['Primary Weld Current'] > 10
    if weld_mask.sum() < 5:
        return ["无有效焊接段"]
    
    c = df['Primary Weld Current'][weld_mask]
    v = df['Secondary Weld Voltage'][weld_mask]
    p = df['Pressure'][weld_mask]
    co2 = df['CO2 Weld Flow'][weld_mask]
    
    stats = []
    stats.append(f"压力均值: {p.mean():.3f} bar ({'异常偏低' if p.mean() < 0.1 else '正常'})")
    stats.append(f"CO2均值: {co2.mean():.1f} L/min ({'偏低' if co2.mean() < 13 else '正常'})")
    stats.append(f"电流std: {c.std():.1f} ({'偏高' if c.std() > 15 else '正常'})")
    stats.append(f"电压std: {v.std():.2f} ({'偏高' if v.std() > 2 else '正常'})")
    stats.append(f"电流均值: {c.mean():.1f}A")
    
    return stats


# ============================================================
# Phase 2: LLM推理 (核心冲突检测)
# ============================================================

def llm_consistency_check(info_dict, data_type):
    """用Ollama Qwen2判断多模态信息一致性"""
    
    # 构建prompt
    if data_type == "nlmcxr":
        prompt = f"""你是资深放射科医生。请判断以下多模态信息是否一致。

【图片分析】TorchXRayVision模型(DenseNet121, MIMIC-CXR训练)预测:
{chr(10).join(info_dict['image'])}

【报告分析】NER提取的疾病实体:
{chr(10).join(info_dict['report_entities']) if info_dict['report_entities'] else '未提取到疾病实体'}
{info_dict['report_normal']}

请判断:
1. 图片预测的疾病与报告描述的发现是否一致?
2. 报告自身是否自洽? (发现的疾病 vs 结论)
3. 如果不一致，具体哪里矛盾?

请用JSON回答:
{{"consistent": true或false, "conflicts": [{{"type": "冲突类型", "detail": "具体说明", "severity": "HIGH或MEDIUM或LOW"}}], "explanation": "简要总结"}}"""

    elif data_type == "medtvt":
        prompt = f"""你是医学检验专家。请判断以下信息是否一致。

【血检分析】
{chr(10).join(info_dict['labs'])}

【诊断标签】{', '.join(info_dict['diagnosis'])}

请判断血检结果与诊断标签是否一致。如果有异常检验值但诊断为No Finding，则不一致。
注意: 血糖70-140为正常范围(非空腹), 不要将<140判为异常。

请用JSON回答:
{{"consistent": true或false, "conflicts": [{{"type": "冲突类型", "detail": "具体说明", "severity": "HIGH或MEDIUM或LOW"}}], "explanation": "简要总结"}}"""

    elif data_type == "h4r":
        prompt = f"""你是焊接工艺专家。请判断以下多模态信息是否一致。

【时序分析】焊接段传感器统计:
{chr(10).join(info_dict['sensor'])}

【文本描述】{info_dict['text']}

【缺陷标签】{info_dict['label']}

请判断:
1. 时序数据与标签是否一致? (如压力≈0+烧穿标签=一致)
2. 文本描述与时序数据是否一致? (如文本说"电流过大"但时序电流是否真的大?)
3. 如果不一致，哪个模态可能有误?

请用JSON回答:
{{"consistent": true或false, "conflicts": [{{"type": "冲突类型", "detail": "具体说明", "severity": "HIGH或MEDIUM或LOW"}}], "explanation": "简要总结"}}"""

    try:
        resp = requests.post("http://localhost:11434/api/generate", json={
            "model": "qwen2:7b",
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 300}
        }, timeout=60)
        result = json.loads(resp.json()["response"])
        return result
    except Exception as e:
        return {"consistent": None, "conflicts": [], "explanation": f"LLM调用失败: {e}"}


# ============================================================
# Phase 3: 主流程
# ============================================================

def run_nlmcxr(n=20):
    """NLMCXR: X光片 + 放射报告"""
    print(f"\n{'='*60}")
    print(f"NLMCXR (X光片+报告) — {n}条")
    print(f"{'='*60}")
    
    df = pd.read_parquet(os.path.join(SCRIPT_DIR, "nlmcxr/val.parquet"))
    results = []
    
    for idx in range(min(n, len(df))):
        sample = df.iloc[idx]
        report = str(sample["text"])
        img_bytes = sample["image"]["bytes"]
        
        # Phase 1: 信息抽取
        image_info = extract_image_info(img_bytes)
        report_entities, report_normal = extract_report_info(report)
        
        info = {"image": image_info, "report_entities": report_entities, "report_normal": report_normal}
        
        # Phase 2: LLM推理
        llm_result = llm_consistency_check(info, "nlmcxr")
        
        r = {"dataset": "nlmcxr", "idx": idx, "report": report[:100],
             "image_info": image_info, "report_entities": report_entities,
             "report_normal": report_normal, "llm_result": llm_result}
        results.append(r)
        
        tag = f"⚠{len(llm_result.get('conflicts',[]))}冲突" if not llm_result.get("consistent", True) else "✓一致"
        print(f"  样本{idx+1} {tag}: {llm_result.get('explanation','')[:60]}")
        for c in llm_result.get("conflicts", []):
            print(f"    [{c.get('severity','')}] {c.get('type','')}: {c.get('detail','')[:60]}")
    
    return results


def run_medtvt(n=20):
    """MedTVT: 血检 + 诊断标签"""
    print(f"\n{'='*60}")
    print(f"MedTVT (血检+标签) — {n}条")
    print(f"{'='*60}")
    
    df = pd.read_csv(os.path.join(SCRIPT_DIR, "medical_data/medtvt/train.csv"))
    
    # 选10个冲突(异常血检+No Finding) + 10个正常
    conflict_rows, normal_rows = [], []
    for i, row in df.iterrows():
        nf = pd.to_numeric(row.get("No Finding"), errors="coerce")
        if nf != 1.0:
            continue
        labs = extract_lab_info(row)
        has_abnormal = any("异常" in l or "偏低" in l or "酸中毒" in l for l in labs)
        if has_abnormal and len(conflict_rows) < 10:
            conflict_rows.append((i, row))
        elif not has_abnormal and len(normal_rows) < 10:
            normal_rows.append((i, row))
        if len(conflict_rows) >= 10 and len(normal_rows) >= 10:
            break
    
    results = []
    for i, (row_idx, row) in enumerate(conflict_rows + normal_rows):
        expected_conflict = i < 10
        
        # Phase 1
        labs = extract_lab_info(row)
        diagnosis = extract_diagnosis(row)
        info = {"labs": labs, "diagnosis": diagnosis}
        
        # Phase 2
        llm_result = llm_consistency_check(info, "medtvt")
        
        r = {"dataset": "medtvt", "idx": int(row_idx), "subject_id": int(row["subject_id"]),
             "expected_conflict": expected_conflict, "labs": labs, "diagnosis": diagnosis,
             "llm_result": llm_result}
        results.append(r)
        
        actual = not llm_result.get("consistent", True)
        match = "✓" if actual == expected_conflict else "✗"
        tag = "⚠冲突" if actual else "✓正常"
        print(f"  {match} 样本{int(row_idx)} 期望:{'冲突' if expected_conflict else '正常'} → LLM:{tag}")
        if actual:
            print(f"    {llm_result.get('explanation','')[:80]}")
    
    tp = sum(1 for r in results if not r["llm_result"].get("consistent", True) and r["expected_conflict"])
    fp = sum(1 for r in results if not r["llm_result"].get("consistent", True) and not r["expected_conflict"])
    tn = sum(1 for r in results if r["llm_result"].get("consistent", True) and not r["expected_conflict"])
    fn = sum(1 for r in results if r["llm_result"].get("consistent", True) and r["expected_conflict"])
    print(f"\n  TP={tp} FN={fn} TN={tn} FP={fp} 准确率={(tp+tn)/len(results)*100:.0f}%")
    
    return results


def run_h4r():
    """H4R: 时序 + 图片 + 标签 + 文本"""
    print(f"\n{'='*60}")
    print(f"H4R (时序+图片+标签+文本) — 4条")
    print(f"{'='*60}")
    
    jsonl_path = os.path.join(SCRIPT_DIR, "h4r_welding.jsonl")
    results = []
    
    with open(jsonl_path) as f:
        for idx, line in enumerate(f):
            sample = json.loads(line)
            text = sample.get("text", "")
            label = sample.get("meta", {}).get("defect_label", "")
            csv_path = sample.get("meta", {}).get("csv_path", "")
            
            # Phase 1
            sensor_info = extract_sensor_info(csv_path)
            info = {"sensor": sensor_info, "text": text, "label": label}
            
            # Phase 2
            llm_result = llm_consistency_check(info, "h4r")
            
            r = {"dataset": "h4r", "idx": idx, "text": text[:80], "label": label,
                 "sensor": sensor_info, "llm_result": llm_result}
            results.append(r)
            
            tag = f"⚠{len(llm_result.get('conflicts',[]))}冲突" if not llm_result.get("consistent", True) else "✓一致"
            print(f"  样本{idx+1}({label}) {tag}: {llm_result.get('explanation','')[:60]}")
            for c in llm_result.get("conflicts", []):
                print(f"    [{c.get('severity','')}] {c.get('type','')}: {c.get('detail','')[:60]}")
    
    return results


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    all_results = []
    
    # NLMCXR (需要TorchXRayVision, 用data-juicer venv)
    try:
        r1 = run_nlmcxr(20)
        all_results.extend(r1)
    except Exception as e:
        print(f"NLMCXR失败: {e}")
    
    # MedTVT (不需要特殊库)
    try:
        r2 = run_medtvt(20)
        all_results.extend(r2)
    except Exception as e:
        print(f"MedTVT失败: {e}")
    
    # H4R
    try:
        r3 = run_h4r()
        all_results.extend(r3)
    except Exception as e:
        print(f"H4R失败: {e}")
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"汇总: {len(all_results)}条样本")
    n_conflict = sum(1 for r in all_results if not r.get("llm_result", {}).get("consistent", True))
    print(f"有冲突: {n_conflict}/{len(all_results)}")
    
    # 保存
    out_dir = os.path.join(SCRIPT_DIR, "output_unified")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "unified_conflict_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"保存: {out_path}")
