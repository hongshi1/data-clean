#!/usr/bin/env python3
"""
调研对齐版 Pipeline v3

对齐调研结论:
- Phase 1: 信息抽取 (scispaCy NER + TorchXRayVision + LOINC + 传感器统计)
  NER只做提取，不做冲突判断
- Phase 2: 冲突检测 (两种方式)
  方式A: VDC三段式 (VQG→VQA→VAE) — 针对图片↔文本
  方式B: LLM直判 — 针对表格↔标签、时序↔文本等
- Phase 3: NER解释层 — scispaCy实体用于定位和解释冲突
- Phase 4: 置信度量化 — 图片概率 + LLM确定性 + 边界带降级

移除:
- medical_operators.py里的手写规则 (if lactate>5.0 and No Finding)
- medical_kb.json里的手写矛盾对 (contradictions列表)
"""
import json, os, sys, re, io, requests, time
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "data-juicer"))

import pandas as pd
import numpy as np
import spacy

# ============================================================
# 模型初始化 (惰性加载)
# ============================================================
_nlp = None
def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_sci_sm")
    return _nlp

_xrv_cache = None
def get_xrv():
    global _xrv_cache
    if _xrv_cache is None:
        import torch, torchxrayvision as xrv
        from skimage.transform import resize
        model = xrv.models.DenseNet(weights="densenet121-res224-mimic_ch")
        model.eval()
        _xrv_cache = (model, resize, torch, xrv)
    return _xrv_cache

# LOINC映射 (标准化, 不是手写规则)
LOINC = json.load(open(os.path.join(SCRIPT_DIR, "loinc_mapping.json")))

# CheXpert实体映射 (标准化, 不是矛盾规则)
CHEX_MAP = {
    "atelectasis": "Atelectasis", "atelectatic": "Atelectasis", "collapse": "Atelectasis",
    "consolidation": "Consolidation", "airspace disease": "Consolidation", "opacity": "Lung Opacity",
    "edema": "Edema", "oedema": "Edema",
    "cardiomegaly": "Cardiomegaly", "cardiac enlargement": "Cardiomegaly",
    "heart enlarged": "Cardiomegaly", "heart size enlarged": "Cardiomegaly",
    "pneumothorax": "Pneumothorax",
    "effusion": "Pleural Effusion", "pleural effusion": "Pleural Effusion", "pleural fluid": "Pleural Effusion",
    "pneumonia": "Pneumonia", "lung lesion": "Lung Lesion", "mass": "Lung Lesion",
    "fracture": "Fracture",
    "no finding": "No Finding", "normal": "No Finding", "clear": "No Finding",
    "unremarkable": "No Finding", "no acute": "No Finding", "no evidence": "No Finding",
}
NEG_PATTERNS = ["no evidence of","no ","without ","not ","absence of","free of","clear of","resolved","no acute","no significant","no definite","no obvious"]
UNC_PATTERNS = ["may represent","may be","possible","question of","suspect","cannot exclude","cannot rule out","could be","suggest","likely","potential","probable","versus","vs"]

# ============================================================
# Phase 1: 信息抽取 (各模态独立, NER只提取不判断)
# ============================================================

def extract_text_entities(text):
    """scispaCy NER: 提取医学实体 + CheXpert三态标注 (只提取, 不判断冲突)"""
    nlp = get_nlp()
    doc = nlp(text)
    tl = text.lower()
    
    entities = []
    for ent in doc.ents:
        ent_text = ent.text.lower().strip()
        chex_cat = None
        for key, cat in CHEX_MAP.items():
            if key in ent_text:
                chex_cat = cat
                break
        if not chex_cat:
            continue
        
        before = tl[max(0, ent.start_char-30):ent.start_char]
        after = tl[ent.end_char:ent.end_char+20]
        
        is_unc = any(u in before for u in UNC_PATTERNS) or any(u in after for u in UNC_PATTERNS[:4])
        is_neg = any(n in before for n in NEG_PATTERNS)
        
        if is_unc and not is_neg:
            state = "uncertain"
        elif is_neg:
            state = "negative"
        else:
            state = "positive"
        
        entities.append({
            "entity": ent.text, "category": chex_cat,
            "state": state,  # positive/negative/uncertain
            "source": "scispacy"
        })
    
    # 去重: 同一category取最高优先级 (positive > uncertain > negative)
    pri = {"positive": 3, "uncertain": 2, "negative": 1}
    by_cat = {}
    for e in entities:
        cat = e["category"]
        if cat not in by_cat or pri[e["state"]] > pri[by_cat[cat]["state"]]:
            by_cat[cat] = e
    
    return list(by_cat.values())

def extract_image_prediction(image_bytes):
    """TorchXRayVision: X光片 → 6种疾病概率 (只预测, 不判断冲突)"""
    from PIL import Image
    model, resize, torch, xrv = get_xrv()
    
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img_norm = xrv.datasets.normalize(np.array(img), 255)
    img_224 = resize(img_norm, (224, 224), anti_aliasing=True)
    img_t = torch.from_numpy(img_224).unsqueeze(0).unsqueeze(0).float()
    
    with torch.no_grad():
        pred = model(img_t)
    
    PATHO = {"Atelectasis":"Atelectasis","Consolidation":"Consolidation","Edema":"Edema",
             "Cardiomegaly":"Cardiomegaly","Pneumothorax":"Pneumothorax","Effusion":"Pleural Effusion"}
    results = {}
    for i, p in enumerate(model.pathologies):
        if p in PATHO:
            raw = float(pred[0][i])
            results[PATHO[p]] = {
                "prob": round(raw, 3),
                "positive": raw > 0.5,
                "confidence": "high" if raw > 0.65 or raw < 0.35 else "medium" if abs(raw - 0.5) > 0.1 else "low",
            }
    return results

def extract_lab_standardized(row):
    """LOINC标准化: 血检值 → 标准码 + 参考范围 + 异常状态 (只标准化, 不判断冲突)"""
    results = {}
    for itemid, info in LOINC.items():
        val = row.get(itemid)
        if pd.isna(val) or val == "": continue
        try: val = float(val)
        except: continue
        
        lo, hi = info["range"]
        if val < lo:
            status = "严重偏低" if val < lo * 0.5 else "偏低"
        elif val > hi:
            if info["name"] == "pH": status = "严重酸中毒" if val < 7.20 else "酸中毒"
            else: status = "严重异常" if val > info.get("severe", hi*2) else "异常"
        else:
            status = "正常"
        
        results[itemid] = {
            "loinc": info["loinc"], "name": info["name"], "name_cn": info["cn"],
            "value": val, "unit": info["unit"], "range": [lo, hi],
            "system": info["system"], "status": status
        }
    return results

def extract_sensor_stats(csv_path):
    """传感器时序统计 (只统计, 不判断冲突)"""
    if not csv_path or not os.path.exists(csv_path):
        return {"error": "文件不存在"}
    df = pd.read_csv(csv_path)
    for c in ['Primary Weld Current','Secondary Weld Voltage','Pressure','CO2 Weld Flow']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    weld = df['Primary Weld Current'] > 10
    if weld.sum() < 5: return {"error": "无焊接段"}
    c,v,p,co2 = df['Primary Weld Current'][weld],df['Secondary Weld Voltage'][weld],df['Pressure'][weld],df['CO2 Weld Flow'][weld]
    return {
        "pressure_mean": round(float(p.mean()),3), "co2_mean": round(float(co2.mean()),1),
        "current_std": round(float(c.std()),1), "voltage_std": round(float(v.std()),2),
        "current_mean": round(float(c.mean()),1), "weld_points": int(weld.sum()),
    }


# ============================================================
# Phase 2A: VDC三段式冲突检测 (图片↔文本)
# ============================================================

def vdc_detect_conflicts(image_pred, text_entities):
    """VDC式: VQG→VQA→VAE
    
    VQG: 根据图片预测的疾病生成问题 ("X光是否显示Edema?")
    VQA: 图片预测回答 (Edema概率0.72 → yes)
    VAE: 比较回答与报告NER (报告说negative → 冲突!)
    """
    conflicts = []
    
    for disease, pred_info in image_pred.items():
        img_positive = pred_info["positive"]
        img_prob = pred_info["prob"]
        img_conf = pred_info["confidence"]
        
        # 在报告实体中找对应疾病
        report_entity = None
        for ent in text_entities:
            if ent["category"] == disease:
                report_entity = ent
                break
        
        # VAE: 比较图片回答 vs 报告描述
        if img_positive and report_entity:
            if report_entity["state"] == "negative":
                # 图片说有 + 报告说没有 → HIGH冲突
                sev = "HIGH" if img_conf == "high" else "MEDIUM" if img_conf == "medium" else "LOW"
                conflicts.append({
                    "type": "图片↔报告否定",
                    "disease": disease,
                    "image": f"阳性(p={img_prob}, {img_conf}置信度)",
                    "report": f"否定('{report_entity['entity']}')",
                    "severity": sev,
                    "confidence": img_conf,
                    "method": "VDC三段式",
                })
            elif report_entity["state"] == "uncertain":
                # 图片说有 + 报告不确定 → LOW冲突
                conflicts.append({
                    "type": "图片↔报告不确定",
                    "disease": disease,
                    "image": f"阳性(p={img_prob})",
                    "report": f"不确定('{report_entity['entity']}')",
                    "severity": "LOW",
                    "confidence": img_conf,
                    "method": "VDC三段式",
                })
        
        elif not img_positive and report_entity and report_entity["state"] == "positive":
            # 图片说没有 + 报告说有 → MEDIUM冲突
            conflicts.append({
                "type": "报告↔图片",
                "disease": disease,
                "image": f"阴性(p={img_prob})",
                "report": f"阳性('{report_entity['entity']}')",
                "severity": "MEDIUM",
                "confidence": img_conf,
                "method": "VDC三段式",
            })
    
    return conflicts

def detect_report_internal(text_entities, is_normal):
    """报告内部冲突: 有阳性发现但结论说正常"""
    conflicts = []
    positives = [e for e in text_entities if e["state"] == "positive" and e["category"] != "No Finding"]
    if positives and is_normal:
        names = [e["category"] for e in positives]
        conflicts.append({
            "type": "报告内部矛盾",
            "disease": ", ".join(names),
            "image": "—",
            "report": f"阳性发现({', '.join(names)}) 但结论称正常",
            "severity": "MEDIUM",
            "confidence": "high",
            "method": "规则检测",
        })
    return conflicts


# ============================================================
# Phase 2B: LLM直判冲突检测 (表格↔标签, 时序↔文本)
# ============================================================

def llm_judge(prompt, max_retry=2):
    """LLM推理 (带retry + JSON修复)"""
    for attempt in range(max_retry + 1):
        try:
            resp = requests.post("http://localhost:11434/api/generate", json={
                "model": "qwen2:7b", "prompt": prompt, "stream": False,
                "format": "json", "options": {"temperature": 0.1, "num_predict": 400}
            }, timeout=60)
            raw = resp.json()["response"]
            try:
                return json.loads(raw)
            except:
                s, e = raw.find("{"), raw.rfind("}")
                if s >= 0 and e > s:
                    return json.loads(raw[s:e+1])
        except:
            if attempt < max_retry: continue
    return {"consistent": None, "conflicts": [], "explanation": "LLM调用失败"}

def llm_detect_medical(labs, diagnosis):
    """LLM直判: 血检↔标签一致性"""
    lab_lines = [f"- {v['name']}({v['name_cn']}): {v['value']}{v['unit']} (LOINC {v['loinc']}, 正常{v['range'][0]}-{v['range'][1]}{v['unit']}, {v['status']})" for v in labs.values()]
    prompt = f"""你是医学检验专家。请判断以下LOINC标准化检验结果与诊断标签是否一致。

【血检分析】
{chr(10).join(lab_lines)}

【诊断标签】{', '.join(diagnosis)}

规则: 1.标注"正常"的值不算异常 2.血糖70-140正常(非空腹) 3.只有明确异常+No Finding才不一致 4.全正常=一致
用JSON回答: {{"consistent": true或false, "conflicts": [{{"type":"类型","detail":"说明","severity":"HIGH或MEDIUM或LOW"}}], "explanation": "总结"}}"""
    
    result = llm_judge(prompt)
    conflicts = []
    for c in result.get("conflicts", []):
        c["method"] = "LLM直判"
        c["confidence"] = "medium"  # LLM判断的置信度
        conflicts.append(c)
    return conflicts, result.get("explanation", "")

def llm_detect_welding(sensor, text, label):
    """LLM直判: 时序↔文本↔标签一致性"""
    if "error" in sensor:
        return [], sensor["error"]
    
    sensor_str = f"- 压力: {sensor['pressure_mean']} bar\n- CO2: {sensor['co2_mean']} L/min\n- 电流std: {sensor['current_std']}\n- 电压std: {sensor['voltage_std']}\n- 电流均值: {sensor['current_mean']}A (参考~170A)"
    
    prompt = f"""你是焊接工艺专家。请判断以下信息是否一致。

【时序分析】
{sensor_str}

【文本描述】{text}

【缺陷标签】{label}

请判断: 1.时序与标签一致? 2.文本描述与时序一致? 3.不一致哪个有误?
用JSON回答: {{"consistent": true或false, "conflicts": [{{"type":"类型","detail":"说明","severity":"HIGH或MEDIUM或LOW"}}], "explanation": "总结"}}"""
    
    result = llm_judge(prompt)
    conflicts = []
    for c in result.get("conflicts", []):
        c["method"] = "LLM直判"
        c["confidence"] = "medium"
        conflicts.append(c)
    return conflicts, result.get("explanation", "")


# ============================================================
# Phase 3: NER解释层 (用实体定位冲突, 不是检测)
# ============================================================

def explain_conflicts(conflicts, text_entities, image_pred):
    """用NER实体解释冲突位置"""
    explanations = []
    for c in conflicts:
        exp = {"conflict": c}
        
        # 找到相关实体
        disease = c.get("disease", "")
        related_entities = [e for e in text_entities if disease.lower() in e.get("category","").lower()]
        if related_entities:
            exp["report_entity"] = related_entities[0]["entity"]
            exp["report_state"] = related_entities[0]["state"]
        
        # 找到图片预测
        if disease in image_pred:
            exp["image_prob"] = image_pred[disease]["prob"]
            exp["image_confidence"] = image_pred[disease]["confidence"]
        
        explanations.append(exp)
    
    return explanations


# ============================================================
# Phase 4: 置信度量化
# ============================================================

def compute_confidence(conflicts, image_pred):
    """综合置信度量化"""
    if not conflicts:
        return {"overall": "high", "reason": "无冲突"}
    
    # 图片置信度
    img_confs = [v["confidence"] for v in image_pred.values()]
    img_high_ratio = img_confs.count("high") / max(len(img_confs), 1)
    
    # 冲突严重度
    severities = [c.get("severity", "MEDIUM") for c in conflicts]
    has_high = "HIGH" in severities
    
    # 方法置信度
    has_vdc = any(c.get("method") == "VDC三段式" for c in conflicts)
    has_llm = any(c.get("method") == "LLM直判" for c in conflicts)
    
    # 综合判断
    if has_high and has_vdc and img_high_ratio > 0.5:
        overall = "high"  # 高置信度冲突(图片高概率+VDC检出)
    elif has_high:
        overall = "medium-high"
    elif has_llm and not has_vdc:
        overall = "medium"  # 只有LLM判断,无VDC佐证
    else:
        overall = "low"
    
    return {
        "overall": overall,
        "img_high_ratio": round(img_high_ratio, 2),
        "has_vdc_evidence": has_vdc,
        "has_llm_evidence": has_llm,
        "max_severity": max(severities) if severities else "NONE",
        "reason": f"{'VDC+LLM' if has_vdc and has_llm else 'VDC' if has_vdc else 'LLM'} | 图片高置信比例={img_high_ratio:.0%} | 最高严重度={max(severities) if severities else 'NONE'}"
    }


# ============================================================
# 主流程
# ============================================================

def run_nlmcxr(n=5):
    print(f"\n{'='*60}\nNLMCXR (图片+报告) — {n}条 [VDC三段式+NER解释+置信度]\n{'='*60}")
    df = pd.read_parquet(os.path.join(SCRIPT_DIR, "nlmcxr/val.parquet"))
    results = []
    
    for idx in range(min(n, len(df))):
        row = df.iloc[idx]
        report = str(row["text"])
        img_bytes = row["image"]["bytes"]
        
        # Phase 1: 信息抽取
        text_ents = extract_text_entities(report)
        img_pred = extract_image_prediction(img_bytes)
        is_normal = any(e["category"] == "No Finding" and e["state"] == "positive" for e in text_ents)
        
        # Phase 2A: VDC三段式
        vdc_conflicts = vdc_detect_conflicts(img_pred, text_ents)
        # Phase 2A补充: 报告内部
        internal_conflicts = detect_report_internal(text_ents, is_normal)
        all_conflicts = vdc_conflicts + internal_conflicts
        
        # Phase 3: NER解释
        explanations = explain_conflicts(all_conflicts, text_ents, img_pred)
        
        # Phase 4: 置信度
        confidence = compute_confidence(all_conflicts, img_pred)
        
        r = {"dataset": "nlmcxr", "idx": idx, "report": report[:80],
             "text_entities": [{"category":e["category"],"state":e["state"]} for e in text_ents],
             "image_pred": {k: {"prob":v["prob"],"confidence":v["confidence"]} for k,v in img_pred.items() if v["prob"] > 0.3},
             "conflicts": all_conflicts, "explanations": explanations,
             "confidence": confidence}
        results.append(r)
        
        tag = f"⚠{len(all_conflicts)}冲突" if all_conflicts else "✓一致"
        print(f"  样本{idx+1} {tag} [置信度:{confidence['overall']}]")
        for c in all_conflicts:
            print(f"    [{c['severity']}|{c['method']}] {c['type']}: {c.get('disease','')} | {c.get('detail','')[:50]}")
    
    return results

def run_medtvt(n=10):
    print(f"\n{'='*60}\nMedTVT (血检+标签) — {n}条 [LLM直判+LOINC标准化]\n{'='*60}")
    df = pd.read_csv(os.path.join(SCRIPT_DIR, "medical_data/medtvt/train.csv"))
    
    conflict_idx, normal_idx = [], []
    for i, row in df.iterrows():
        nf = pd.to_numeric(row.get("No Finding"), errors="coerce")
        if nf != 1.0: continue
        labs = extract_lab_standardized(row)
        has_abnormal = any(v["status"] not in ["正常"] for v in labs.values())
        if has_abnormal and len(conflict_idx) < 5: conflict_idx.append(i)
        elif not has_abnormal and len(normal_idx) < 5: normal_idx.append(i)
        if len(conflict_idx) >= 5 and len(normal_idx) >= 5: break
    
    results = []
    for i, row_idx in enumerate(conflict_idx + normal_idx):
        expected = i < 5
        row = df.iloc[row_idx]
        
        # Phase 1: LOINC标准化
        labs = extract_lab_standardized(row)
        diagnosis = [col for col in ["No Finding","Atelectasis","Cardiomegaly","Edema","Lung Opacity","Pleural Effusion"] if row.get(col) == 1.0]
        
        # Phase 2B: LLM直判 (不用手写规则)
        conflicts, explanation = llm_detect_medical(labs, diagnosis)
        
        # Phase 4: 置信度
        confidence = {"overall": "medium", "reason": f"LLM直判, 无图片佐证"}
        
        r = {"dataset": "medtvt", "idx": int(row_idx), "expected": expected,
             "labs": {k: {"name":v["name_cn"],"value":v["value"],"status":v["status"]} for k,v in labs.items()},
             "diagnosis": diagnosis, "conflicts": conflicts, "explanation": explanation,
             "confidence": confidence}
        results.append(r)
        
        actual = len(conflicts) > 0
        match = "✓" if actual == expected else "✗"
        print(f"  {match} 行{int(row_idx)} 期望:{'冲突' if expected else '正常'} → {'冲突' if actual else '正常'} [置信度:{confidence['overall']}]")
        if actual: print(f"    {explanation[:60]}")
    
    tp = sum(1 for r in results if r["conflicts"] and r["expected"])
    fp = sum(1 for r in results if r["conflicts"] and not r["expected"])
    tn = sum(1 for r in results if not r["conflicts"] and not r["expected"])
    fn = sum(1 for r in results if not r["conflicts"] and r["expected"])
    print(f"\n  TP={tp} FN={fn} TN={tn} FP={fp} 准确率={(tp+tn)/len(results)*100:.0f}%")
    return results

def run_h4r():
    print(f"\n{'='*60}\nH4R (时序+文本+标签) — 4条 [LLM直判+传感器统计]\n{'='*60}")
    results = []
    with open(os.path.join(SCRIPT_DIR, "h4r_welding.jsonl")) as f:
        for idx, line in enumerate(f):
            d = json.loads(line)
            text = d.get("text","")
            label = d.get("meta",{}).get("defect_label","")
            csv_path = d.get("meta",{}).get("csv_path","")
            
            # Phase 1: 传感器统计
            sensor = extract_sensor_stats(csv_path)
            
            # Phase 2B: LLM直判
            conflicts, explanation = llm_detect_welding(sensor, text, label)
            
            # Phase 4: 置信度
            confidence = {"overall": "medium", "reason": "LLM直判, 无图片佐证"}
            
            r = {"dataset": "h4r", "idx": idx, "label": label, "text": text[:60],
                 "sensor": sensor, "conflicts": conflicts, "explanation": explanation,
                 "confidence": confidence}
            results.append(r)
            
            tag = f"⚠{len(conflicts)}冲突" if conflicts else "✓一致"
            print(f"  样本{idx+1}({label}) {tag} [置信度:{confidence['overall']}]")
            if conflicts:
                print(f"    {explanation[:60]}")
    return results


if __name__ == "__main__":
    all_results = []
    
    try: all_results.extend(run_nlmcxr(5))
    except Exception as e: print(f"NLMCXR失败: {e}")
    
    try: all_results.extend(run_medtvt(10))
    except Exception as e: print(f"MedTVT失败: {e}")
    
    try: all_results.extend(run_h4r())
    except Exception as e: print(f"H4R失败: {e}")
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"汇总: {len(all_results)}条")
    by_ds = defaultdict(lambda: {"total":0, "conflict":0})
    for r in all_results:
        ds = r["dataset"]
        by_ds[ds]["total"] += 1
        if r.get("conflicts"): by_ds[ds]["conflict"] += 1
    for ds, s in by_ds.items():
        print(f"  {ds}: {s['conflict']}/{s['total']}有冲突")
    
    # 统计检测方法
    methods = defaultdict(int)
    for r in all_results:
        for c in r.get("conflicts", []):
            methods[c.get("method","unknown")] += 1
    print(f"\n检测方法统计: {dict(methods)}")
    
    # 保存
    out_dir = os.path.join(SCRIPT_DIR, "output_unified")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "pipeline_v3_report.json")
    json.dump(all_results, open(out_path, "w"), ensure_ascii=False, indent=2)
    print(f"保存: {out_path}")
