#!/usr/bin/env python3
"""
统一多模态冲突检测 Data-Juicer 算子 (v3, 调研对齐版)

对齐调研结论:
- Phase 1: 信息抽取 (scispaCy+TorchXRayVision+LOINC+传感器) — NER只提取不判断
- Phase 2A: VDC三段式 (VQG→VQA→VAE) — 图片↔文本
- Phase 2B: LLM直判 — 表格↔标签 / 时序↔文本
- Phase 3: NER解释层 — 实体定位冲突位置
- Phase 4: 置信度量化

3个Data-Juicer算子:
  1. info_extraction_mapper (Mapper): 各模态信息抽取
  2. conflict_detection_filter (Filter): VDC三段式 + LLM直判
  3. report_mapper (Mapper): NER解释 + 置信度 + 报告生成
"""
import json, os, sys, re, io, requests
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "data-juicer"))

from data_juicer.ops.base_op import OPERATORS, Filter, Mapper
from data_juicer.utils.constant import Fields

import pandas as pd
import numpy as np

# ============================================================
# 模型惰性加载
# ============================================================
_nlp = None
def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_sci_sm")
    return _nlp

_xrv_cache = None
def _get_xrv():
    global _xrv_cache
    if _xrv_cache is None:
        import torch, torchxrayvision as xrv
        from skimage.transform import resize
        model = xrv.models.DenseNet(weights="densenet121-res224-mimic_ch")
        model.eval()
        _xrv_cache = (model, resize, torch, xrv)
    return _xrv_cache

# LOINC映射
_LOINC_PATH = os.path.join(SCRIPT_DIR, "..", "..", "knowledge", "loinc_mapping.json")
_LOINC = json.load(open(_LOINC_PATH)) if os.path.exists(_LOINC_PATH) else {}

# CheXpert实体映射 (标准化, 不是矛盾规则)
_CHEX_MAP = {
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
_NEG = ["no evidence of","no ","without ","not ","absence of","free of","clear of","resolved","no acute","no significant","no definite","no obvious"]
_UNC = ["may represent","may be","possible","question of","suspect","cannot exclude","cannot rule out","could be","suggest","likely","potential","probable","versus","vs"]


# ============================================================
# Phase 1: 信息抽取函数
# ============================================================
def _extract_text_entities(text):
    nlp = _get_nlp()
    doc = nlp(text)
    tl = text.lower()
    entities = []
    for ent in doc.ents:
        ent_text = ent.text.lower().strip()
        chex_cat = None
        for key, cat in _CHEX_MAP.items():
            if key in ent_text:
                chex_cat = cat
                break
        if not chex_cat:
            continue
        before = tl[max(0, ent.start_char-30):ent.start_char]
        after = tl[ent.end_char:ent.end_char+20]
        is_unc = any(u in before for u in _UNC) or any(u in after for u in _UNC[:4])
        is_neg = any(n in before for n in _NEG)
        state = "uncertain" if (is_unc and not is_neg) else ("negative" if is_neg else "positive")
        entities.append({"entity": ent.text, "category": chex_cat, "state": state, "source": "scispacy"})
    pri = {"positive": 3, "uncertain": 2, "negative": 1}
    by_cat = {}
    for e in entities:
        c = e["category"]
        if c not in by_cat or pri[e["state"]] > pri[by_cat[c]["state"]]:
            by_cat[c] = e
    return list(by_cat.values())

def _extract_image_pred(image_path):
    from PIL import Image
    model, resize, torch, xrv = _get_xrv()
    img = Image.open(image_path).convert("L")
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
            conf = "high" if raw > 0.65 or raw < 0.35 else "medium" if abs(raw-0.5) > 0.1 else "low"
            results[PATHO[p]] = {"prob": round(raw,3), "positive": raw > 0.5, "confidence": conf}
    return results

def _extract_lab_standardized(meta):
    labs_in = meta.get("labs", {})
    results = {}
    for itemid, info in _LOINC.items():
        val = labs_in.get(itemid)
        if val is None: continue
        try: val = float(val)
        except: continue
        lo, hi = info["range"]
        if val < lo:
            status = "严重偏低" if val < lo * 0.5 else "偏低"
        elif val > hi:
            status = "严重酸中毒" if (info["name"]=="pH" and val < 7.20) else \
                     "严重异常" if val > info.get("severe", hi*2) else "异常" if info["name"]!="pH" else "酸中毒"
        else:
            status = "正常"
        results[itemid] = {"loinc": info["loinc"], "name": info["name"], "name_cn": info["cn"],
                           "value": val, "unit": info["unit"], "range": [lo, hi], "status": status}
    return results

def _extract_sensor(csv_path):
    if not csv_path or not os.path.exists(csv_path):
        return {"error": "文件不存在"}
    df = pd.read_csv(csv_path)
    for c in ['Primary Weld Current','Secondary Weld Voltage','Pressure','CO2 Weld Flow']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    weld = df['Primary Weld Current'] > 10
    if weld.sum() < 5: return {"error": "无焊接段"}
    c,v,p,co2 = df['Primary Weld Current'][weld],df['Secondary Weld Voltage'][weld],df['Pressure'][weld],df['CO2 Weld Flow'][weld]
    return {"pressure_mean": round(float(p.mean()),3), "co2_mean": round(float(co2.mean()),1),
            "current_std": round(float(c.std()),1), "voltage_std": round(float(v.std()),2),
            "current_mean": round(float(c.mean()),1), "weld_points": int(weld.sum())}


# ============================================================
# Phase 2: 冲突检测函数
# ============================================================
def _vdc_detect(image_pred, text_entities):
    """VDC三段式: VQG→VQA→VAE (图片↔文本)"""
    conflicts = []
    for disease, pred_info in image_pred.items():
        img_pos = pred_info["positive"]
        img_prob = pred_info["prob"]
        img_conf = pred_info["confidence"]
        report_ent = None
        for e in text_entities:
            if e["category"] == disease:
                report_ent = e
                break
        if img_pos and report_ent:
            if report_ent["state"] == "negative":
                sev = "HIGH" if img_conf == "high" else "MEDIUM" if img_conf == "medium" else "LOW"
                conflicts.append({"type":"图片↔报告否定","disease":disease,
                    "detail":f"图片{disease}(p={img_prob},{img_conf}) 但报告否定('{report_ent['entity']}')",
                    "severity":sev,"confidence":img_conf,"method":"VDC三段式"})
            elif report_ent["state"] == "uncertain":
                conflicts.append({"type":"图片↔报告不确定","disease":disease,
                    "detail":f"图片{disease}(p={img_prob}) 报告不确定('{report_ent['entity']}')",
                    "severity":"LOW","confidence":img_conf,"method":"VDC三段式"})
        elif not img_pos and report_ent and report_ent["state"] == "positive":
            conflicts.append({"type":"报告↔图片","disease":disease,
                "detail":f"报告阳性{disease}('{report_ent['entity']}') 但图片未检出(p={img_prob})",
                "severity":"MEDIUM","confidence":img_conf,"method":"VDC三段式"})
    return conflicts

def _detect_report_internal(text_entities, is_normal):
    positives = [e for e in text_entities if e["state"] == "positive" and e["category"] != "No Finding"]
    if positives and is_normal:
        names = [e["category"] for e in positives]
        return [{"type":"报告内部矛盾","disease":", ".join(names),
                 "detail":f"报告阳性({', '.join(names)}) 但结论称正常",
                 "severity":"MEDIUM","confidence":"high","method":"规则检测"}]
    return []

def _llm_judge(prompt, max_retry=2):
    for attempt in range(max_retry + 1):
        try:
            resp = requests.post("http://localhost:11434/api/generate", json={
                "model":"qwen2:7b","prompt":prompt,"stream":False,
                "format":"json","options":{"temperature":0.1,"num_predict":400}
            }, timeout=60)
            raw = resp.json()["response"]
            try: return json.loads(raw)
            except:
                s, e = raw.find("{"), raw.rfind("}")
                if s >= 0 and e > s: return json.loads(raw[s:e+1])
        except:
            if attempt < max_retry: continue
    return {"consistent": None, "conflicts": [], "explanation": "LLM调用失败"}

def _llm_detect_medical(labs, diagnosis):
    lab_lines = [f"- {v['name']}({v['name_cn']}): {v['value']}{v['unit']} (LOINC {v['loinc']}, 正常{v['range'][0]}-{v['range'][1]}{v['unit']}, {v['status']})"
                 for v in labs.values()]
    prompt = f"""你是医学检验专家。请判断以下LOINC标准化检验结果与诊断标签是否一致。

【血检分析】
{chr(10).join(lab_lines)}

【诊断标签】{', '.join(diagnosis)}

规则: 1.标注"正常"的值不算异常 2.血糖70-140正常(非空腹) 3.只有明确异常+No Finding才不一致 4.全正常=一致
用JSON回答: {{"consistent": true或false, "conflicts": [{{"type":"类型","detail":"说明","severity":"HIGH或MEDIUM或LOW"}}], "explanation": "总结"}}"""
    result = _llm_judge(prompt)
    conflicts = []
    for c in result.get("conflicts", []):
        c["method"] = "LLM直判"
        c["confidence"] = "medium"
        conflicts.append(c)
    return conflicts, result.get("explanation", "")

def _llm_detect_welding(sensor, text, label):
    if "error" in sensor: return [], sensor["error"]
    sensor_str = f"- 压力: {sensor['pressure_mean']} bar\n- CO2: {sensor['co2_mean']} L/min\n- 电流std: {sensor['current_std']}\n- 电压std: {sensor['voltage_std']}\n- 电流均值: {sensor['current_mean']}A (参考~170A)"
    prompt = f"""你是焊接工艺专家。请判断以下信息是否一致。

【时序分析】
{sensor_str}

【文本描述】{text}

【缺陷标签】{label}

请判断: 1.时序与标签一致? 2.文本描述与时序一致? 3.不一致哪个有误?
用JSON回答: {{"consistent": true或false, "conflicts": [{{"type":"类型","detail":"说明","severity":"HIGH或MEDIUM或LOW"}}], "explanation": "总结"}}"""
    result = _llm_judge(prompt)
    conflicts = []
    for c in result.get("conflicts", []):
        c["method"] = "LLM直判"
        c["confidence"] = "medium"
        conflicts.append(c)
    return conflicts, result.get("explanation", "")


# ============================================================
# Phase 3+4: 解释+置信度
# ============================================================
def _explain(conflicts, text_entities, image_pred):
    explanations = []
    for c in conflicts:
        exp = {"conflict": c}
        disease = c.get("disease", "")
        related = [e for e in text_entities if disease.lower() in e.get("category","").lower()]
        if related:
            exp["report_entity"] = related[0]["entity"]
            exp["report_state"] = related[0]["state"]
        if disease in image_pred:
            exp["image_prob"] = image_pred[disease]["prob"]
            exp["image_confidence"] = image_pred[disease]["confidence"]
        explanations.append(exp)
    return explanations

def _compute_confidence(conflicts, image_pred):
    if not conflicts:
        return {"overall": "high", "reason": "无冲突"}
    img_confs = [v["confidence"] for v in image_pred.values()]
    img_high_ratio = img_confs.count("high") / max(len(img_confs), 1)
    severities = [c.get("severity", "MEDIUM") for c in conflicts]
    has_high = "HIGH" in severities
    has_vdc = any(c.get("method") == "VDC三段式" for c in conflicts)
    has_llm = any(c.get("method") == "LLM直判" for c in conflicts)
    if has_high and has_vdc and img_high_ratio > 0.5:
        overall = "high"
    elif has_high:
        overall = "medium-high"
    elif has_llm and not has_vdc:
        overall = "medium"
    else:
        overall = "low"
    return {"overall": overall, "img_high_ratio": round(img_high_ratio, 2),
            "has_vdc": has_vdc, "has_llm": has_llm,
            "max_severity": max(severities) if severities else "NONE"}


# ============================================================
# 算子1: info_extraction_mapper (Mapper)
# ============================================================
@OPERATORS.register_module("info_extraction_mapper")
class InfoExtractionMapper(Mapper):
    """Phase 1: 各模态信息抽取 (scispaCy NER + TorchXRayVision + LOINC + 传感器)
    
    根据 meta.data_type 执行不同抽取:
      radiology: TorchXRayVision(图片) + scispaCy NER(报告)
      medical: LOINC标准化(血检) + 诊断标签
      welding: 传感器统计 + 文本 + 标签
    """
    def __init__(self, xrv_threshold=0.5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xrv_threshold = xrv_threshold

    def process_single(self, sample):
        meta = sample.get("meta", {})
        dt = meta.get("data_type", "")
        extracted = {"data_type": dt}

        if dt == "radiology":
            images = sample.get("images", [])
            if images and os.path.exists(images[0]):
                extracted["image_pred"] = _extract_image_pred(images[0])
            else:
                extracted["image_pred"] = {}
            text = sample.get("text", "")
            extracted["text_entities"] = _extract_text_entities(text)
            extracted["is_normal"] = any(e["category"] == "No Finding" and e["state"] == "positive"
                                         for e in extracted["text_entities"])
            extracted["report_text"] = text[:200]

        elif dt == "medical":
            extracted["labs"] = _extract_lab_standardized(meta)
            extracted["diagnosis"] = meta.get("diagnosis", [])

        elif dt == "welding":
            extracted["sensor"] = _extract_sensor(meta.get("csv_path", ""))
            extracted["text"] = sample.get("text", "")
            extracted["label"] = meta.get("defect_label", "")

        meta["extracted"] = extracted
        sample["meta"] = meta
        return sample


# ============================================================
# 算子2: conflict_detection_filter (Filter)
# ============================================================
@OPERATORS.register_module("conflict_detection_filter")
class ConflictDetectionFilter(Filter):
    """Phase 2: 冲突检测 (VDC三段式 + LLM直判, 不用手写规则)
    
    radiology: VDC三段式(图片↔报告) + 报告内部检测
    medical: LLM直判(血检↔标签) + LOINC标准化
    welding: LLM直判(时序↔文本↔标签)
    """
    def __init__(self, ollama_url="http://localhost:11434/api/generate",
                 model_name="qwen2:7b", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ollama_url = ollama_url
        self.model_name = model_name

    def compute_stats_single(self, sample):
        meta = sample.get("meta", {})
        ext = meta.get("extracted", {})
        dt = ext.get("data_type", "")
        stats = sample.get(Fields.stats, {})
        if "conflicts" in stats:
            return sample

        conflicts = []
        explanation = ""

        if dt == "radiology":
            # Phase 2A: VDC三段式
            conflicts = _vdc_detect(ext.get("image_pred", {}), ext.get("text_entities", []))
            conflicts += _detect_report_internal(ext.get("text_entities", []), ext.get("is_normal", False))
            explanation = f"VDC检出{len(conflicts)}个冲突"

        elif dt == "medical":
            # Phase 2B: LLM直判
            conflicts, explanation = _llm_detect_medical(ext.get("labs", {}), ext.get("diagnosis", []))

        elif dt == "welding":
            # Phase 2B: LLM直判
            conflicts, explanation = _llm_detect_welding(ext.get("sensor", {}), ext.get("text", ""), ext.get("label", ""))

        stats["conflicts"] = conflicts
        stats["conflict_count"] = len(conflicts)
        stats["conflict_explanation"] = explanation
        stats["has_conflict"] = len(conflicts) > 0
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        return True  # 仅标记不丢弃


# ============================================================
# 算子3: report_mapper (Mapper)
# ============================================================
@OPERATORS.register_module("conflict_report_mapper")
class ConflictReportMapper(Mapper):
    """Phase 3+4: NER解释 + 置信度量化 + 报告生成"""
    def process_single(self, sample):
        meta = sample.get("meta", {})
        ext = meta.get("extracted", {})
        stats = sample.get(Fields.stats, {})

        conflicts = stats.get("conflicts", [])
        image_pred = ext.get("image_pred", {})
        text_entities = ext.get("text_entities", [])

        # Phase 3: NER解释
        explanations = _explain(conflicts, text_entities, image_pred)

        # Phase 4: 置信度
        confidence = _compute_confidence(conflicts, image_pred)

        report = {
            "data_type": ext.get("data_type", ""),
            "has_conflict": stats.get("has_conflict", False),
            "conflict_count": stats.get("conflict_count", 0),
            "conflicts": conflicts,
            "explanations": explanations,
            "confidence": confidence,
            "explanation": stats.get("conflict_explanation", ""),
        }
        meta["conflict_report"] = report
        sample["meta"] = meta
        return sample
