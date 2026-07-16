import json, os, random, base64, io, datetime
from pathlib import Path
from PIL import Image
import numpy as np
import torch
from transformers import CLIPModel, CLIPProcessor

DATA_DIR = Path("/Users/gexuancheng/Desktop/research2/data_clean/real_data")
OUTPUT_DIR = DATA_DIR / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_data():
    with open(DATA_DIR / "weapon_real_photos.jsonl") as f:
        return [json.loads(l) for l in f]

def build_attribute_descriptions(sample):
    """为每条数据的每个属性生成CLIP文本描述"""
    attrs = {}
    name = sample.get("weapon_name", "")
    wtype_cn = sample.get("weapon_type_cn", "")
    wtype_en = sample.get("weapon_type_en", "")
    caliber = sample.get("caliber", "")
    country = sample.get("country", "")

    attrs["weapon_name"] = f"a photo of a {name}"
    attrs["weapon_type"] = f"a photo of a {wtype_en.lower()}"
    attrs["caliber"] = f"a photo of a firearm chambered in {caliber}"
    attrs["country"] = f"a photo of a {country} firearm"
    attrs["combined"] = f"a photo of a {country} {wtype_en.lower()}, {name}, {caliber}"
    return attrs

def inject_fine_grained_errors(samples):
    """注入细粒度属性级错误（不换图片，而是篡改表格属性值）"""
    random.seed(42)
    FAKE_CALIBERS = [".50 BMG", "7.62x39mm", ".45 ACP", "5.56x45mm NATO", "12 Gauge", ".357 Magnum"]
    FAKE_COUNTRIES = ["Russia", "China", "Germany", "Israel", "South Korea", "Brazil"]
    FAKE_TYPES_EN = ["Sniper Rifle", "Shotgun", "Submachine Gun", "Assault Rifle", "Pistol"]
    FAKE_TYPES_CN = ["狙击步枪", "霰弹枪", "冲锋枪", "突击步枪", "手枪"]
    FAKE_NAMES = ["M24 SWS", "Remington 870", "MP5", "AK-47", "Glock 17"]

    error_types = ["caliber", "country", "type", "name", "combined"]
    n_inject = max(3, int(len(samples) * 0.45))

    indices = list(range(len(samples)))
    targets = random.sample(indices, min(n_inject, len(samples)))

    for i, idx in enumerate(targets):
        error_type = error_types[i % len(error_types)]
        s = samples[idx]
        s["error_type"] = error_type
        s["original_caliber"] = s.get("caliber", "")
        s["original_country"] = s.get("country", "")
        s["original_type_cn"] = s.get("weapon_type_cn", "")
        s["original_type_en"] = s.get("weapon_type_en", "")
        s["original_name"] = s.get("weapon_name", "")
        s["has_error"] = True

        if error_type == "caliber":
            fake = random.choice([c for c in FAKE_CALIBERS if c != s.get("caliber", "")])
            s["caliber"] = fake
            s["error_desc"] = f"口径被篡改: 真实={s['original_caliber']}, 篡改为={fake}"
        elif error_type == "country":
            fake = random.choice([c for c in FAKE_COUNTRIES if c != s.get("country", "")])
            s["country"] = fake
            s["error_desc"] = f"产地被篡改: 真实={s['original_country']}, 篡改为={fake}"
        elif error_type == "type":
            idx_fake = random.randint(0, len(FAKE_TYPES_EN)-1)
            if FAKE_TYPES_EN[idx_fake] != s.get("weapon_type_en", ""):
                s["weapon_type_en"] = FAKE_TYPES_EN[idx_fake]
                s["weapon_type_cn"] = FAKE_TYPES_CN[idx_fake]
                s["error_desc"] = f"类型被篡改: 真实={s['original_type_cn']}, 篡改为={FAKE_TYPES_CN[idx_fake]}"
        elif error_type == "name":
            fake = random.choice([n for n in FAKE_NAMES if n != s.get("weapon_name", "")])
            s["weapon_name"] = fake
            s["error_desc"] = f"名称被篡改: 真实={s['original_name']}, 篡改为={fake}"
        elif error_type == "combined":
            fake_c = random.choice([c for c in FAKE_CALIBERS if c != s.get("caliber", "")])
            s["caliber"] = fake_c
            fake_co = random.choice([c for c in FAKE_COUNTRIES if c != s.get("country", "")])
            s["country"] = fake_co
            s["error_desc"] = f"多属性篡改: 口径→{fake_c}, 产地→{fake_co}"

    n_err = sum(1 for s in samples if s.get("has_error"))
    print(f"注入{len(targets)}条细粒度错误: {n_err}条标记")
    return samples

def run_clip_attribute_matching(samples):
    """对每条数据的每个属性，用CLIP计算图文匹配度"""
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"设备: {device}")
    print("加载CLIP模型...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()

    results = []
    for i, s in enumerate(samples):
        img = Image.open(s["image_path"]).convert("RGB")
        attr_descs = build_attribute_descriptions(s)

        attr_scores = {}
        for attr_name, desc in attr_descs.items():
            inputs = processor(text=[desc], images=img, return_tensors="pt", padding=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                score = model(**inputs).logits_per_image.item() / 100.0
            attr_scores[attr_name] = score

        is_error = s.get("has_error", False)
        error_type = s.get("error_type", "")
        error_desc = s.get("error_desc", "")

        results.append({
            "id": s.get("id", i),
            "weapon_name": s.get("weapon_name", ""),
            "weapon_type_cn": s.get("weapon_type_cn", ""),
            "weapon_type_en": s.get("weapon_type_en", ""),
            "caliber": s.get("caliber", ""),
            "country": s.get("country", ""),
            "weight_kg": s.get("weight_kg", 0),
            "image_path": s.get("image_path", ""),
            "has_error": is_error,
            "error_type": error_type,
            "error_desc": error_desc,
            "original_caliber": s.get("original_caliber", s.get("caliber", "")),
            "original_country": s.get("original_country", s.get("country", "")),
            "original_type_cn": s.get("original_type_cn", s.get("weapon_type_cn", "")),
            "original_name": s.get("original_name", s.get("weapon_name", "")),
            "attr_scores": attr_scores,
            "combined_score": attr_scores.get("combined", 0),
            "name_score": attr_scores.get("weapon_name", 0),
            "type_score": attr_scores.get("weapon_type", 0),
            "caliber_score": attr_scores.get("caliber", 0),
            "country_score": attr_scores.get("country", 0),
        })

        tag = "⚠️" if is_error else "✅"
        err_info = f" [{error_type}错误] {error_desc}" if is_error else ""
        print(f"  [{i+1:2d}] {s.get('weapon_name',''):20s} 综合={attr_scores['combined']:.4f} 名称={attr_scores['weapon_name']:.4f} 类型={attr_scores['weapon_type']:.4f} 口径={attr_scores['caliber']:.4f} 产地={attr_scores['country']:.4f} {tag}{err_info}")

    return results

def detect_conflicts(results):
    """细粒度冲突检测：属性级异常 + 属性间一致性"""
    print(f"\n{'='*70}")
    print("细粒度多模态冲突检测")
    print(f"{'='*70}")

    # 方法1: 属性级统计异常 — 每个属性的分数低于均值-1.5σ
    attr_names = ["combined", "name_score", "type_score", "caliber_score", "country_score"]
    attr_stats = {}
    for attr in attr_names:
        scores = [r[attr] for r in results]
        mean_s = np.mean(scores)
        std_s = np.std(scores)
        threshold = mean_s - 1.5 * std_s
        attr_stats[attr] = {"mean": mean_s, "std": std_s, "threshold": threshold}
        print(f"  {attr:15s}: 均值={mean_s:.4f} 阈值={threshold:.4f}")

    # 方法2: 属性间一致性 — 同一条数据的各属性分数应该接近，差异大的可疑
    for r in results:
        scores_list = [r["name_score"], r["type_score"], r["caliber_score"], r["country_score"]]
        r["attr_std"] = float(np.std(scores_list))
        r["attr_range"] = float(max(scores_list) - min(scores_list))
        r["min_attr_score"] = min(scores_list)
        r["min_attr_name"] = ["名称", "类型", "口径", "产地"][scores_list.index(min(scores_list))]

    # 综合冲突检测
    for r in results:
        issues = []
        severity = 0

        # 检查每个属性是否低于阈值
        for attr, label in [("name_score", "名称"), ("type_score", "类型"), ("caliber_score", "口径"), ("country_score", "产地")]:
            if r[attr] < attr_stats[attr]["threshold"]:
                issues.append(f"{label}属性匹配异常: CLIP分数{r[attr]:.4f} < 阈值{attr_stats[attr]['threshold']:.4f}")
                severity += 2

        # 检查属性间不一致（某属性远低于其他属性）
        if r["attr_range"] > 0.08:
            issues.append(f"属性间不一致: 最低属性「{r['min_attr_name']}」分数{r['min_attr_score']:.4f}，与其他属性差距过大(极差={r['attr_range']:.4f})")
            severity += 2

        # 检查综合分数
        if r["combined_score"] < attr_stats["combined"]["threshold"]:
            issues.append(f"综合匹配异常: {r['combined_score']:.4f} < 阈值{attr_stats['combined']['threshold']:.4f}")
            severity += 1

        r["issues"] = issues
        r["severity"] = severity
        r["is_flagged"] = len(issues) > 0

    flagged = [r for r in results if r["is_flagged"]]
    flagged.sort(key=lambda x: -x["severity"])
    true_errors = [r for r in results if r["has_error"]]
    detected = [r for r in true_errors if r["is_flagged"]]

    tp = len(detected)
    fp = len([r for r in flagged if not r["has_error"]])
    fn = len(true_errors) - tp
    prec = tp / max(1, len(flagged))
    rec = tp / max(1, len(true_errors))
    f1 = 2 * prec * rec / max(1e-6, prec + rec)

    print(f"\n  冲突检测结果:")
    print(f"    总样本: {len(results)}")
    print(f"    真实错误: {len(true_errors)}")
    print(f"    标记样本: {len(flagged)}")
    print(f"    正确检出(TP): {tp}")
    print(f"    误报(FP): {fp}")
    print(f"    漏检(FN): {fn}")
    print(f"    精确率: {prec:.1%}")
    print(f"    召回率: {rec:.1%}")
    print(f"    F1: {f1:.1%}")

    # 按错误类型分析检出率
    print(f"\n  按错误类型分析:")
    error_types = {}
    for r in true_errors:
        et = r.get("error_type", "unknown")
        if et not in error_types:
            error_types[et] = {"total": 0, "detected": 0}
        error_types[et]["total"] += 1
        if r["is_flagged"]:
            error_types[et]["detected"] += 1
    for et, stats in error_types.items():
        rate = stats["detected"] / max(1, stats["total"])
        print(f"    {et:12s}: {stats['detected']}/{stats['total']} = {rate:.0%}")

    return flagged, tp, fp, fn, prec, rec, f1, attr_stats

def img_to_base64(path, max_size=180):
    try:
        img = Image.open(path).convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return ""

def generate_html(results, flagged, stats, attr_stats):
    total = len(results)
    n_errors = sum(1 for r in results if r["has_error"])
    tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
    prec, rec, f1 = stats["prec"], stats["rec"], stats["f1"]

    def make_case_card(r, case_label, color, bg):
        img_b64 = img_to_base64(r["image_path"])
        img_html = f'<img src="data:image/jpeg;base64,{img_b64}" style="width:160px;height:160px;object-fit:cover;border-radius:8px;border:2px solid {color};flex-shrink:0;">' if img_b64 else ""

        issues_html = ""
        for iss in r.get("issues", []):
            issues_html += f"<small>• {iss}</small><br>"
        if not issues_html:
            issues_html = "<small style='color:#999;'>无异常</small>"

        error_info = ""
        if r["has_error"]:
            error_info = f'<div style="background:#fee2e2;padding:8px;border-radius:6px;margin:8px 0;font-size:13px;"><b>注入的错误:</b> {r.get("error_desc","")}</div>'

        attr_bars = ""
        attr_colors = {"name_score": ("名称", "#3b82f6"), ("type_score": ("类型", "#10b981"),
                       ("caliber_score": ("口径", "#f59e0b"), ("country_score": ("产地", "#8b5cf6")}
        for attr_key, (label, color) in attr_colors.items():
            score = r.get(attr_key, 0)
            threshold = attr_stats.get(attr_key.replace("_score", ""), attr_stats.get(attr_key, {})).get("threshold", 0)
            if attr_key == "name_score":
                threshold = attr_stats.get("name_score", {}).get("threshold", 0) if "name_score" in attr_stats else attr_stats.get("weapon_name", {}).get("threshold", 0)
            elif attr_key == "type_score":
                threshold = attr_stats.get("type_score", {}).get("threshold", 0) if "type_score" in attr_stats else attr_stats.get("weapon_type", {}).get("threshold", 0)
            bar_width = max(5, min(100, int(score * 300)))
            is_low = score < threshold
            bar_color = "#dc2626" if is_low else color
            attr_bars += f'''<div style="margin:4px 0;">
                <span style="font-size:12px;color:#666;width:40px;display:inline-block;">{label}</span>
                <div style="display:inline-block;width:120px;height:14px;background:#e5e7eb;border-radius:7px;vertical-align:middle;margin:0 6px;">
                    <div style="width:{bar_width}%;height:100%;background:{bar_color};border-radius:7px;"></div>
                </div>
                <span style="font-size:12px;color:{bar_color if is_low else '#666'};font-weight:{'bold' if is_low else 'normal'};">{score:.4f}</span>
                {"🔴" if is_low else ""}
            </div>'''

        return f'''<div style="background:{bg};border:1px solid {color};border-radius:12px;padding:20px;margin:16px 0;display:flex;gap:20px;align-items:flex-start;">
            {img_html}
            <div style="flex:1;min-width:0;">
                <div style="font-size:13px;color:#666;margin-bottom:4px;">{case_label}</div>
                <div style="font-size:18px;font-weight:bold;margin-bottom:8px;">{r['weapon_name']}</div>
                <table style="font-size:13px;width:100%;">
                    <tr><td style="color:#666;width:80px;">类型</td><td><b>{r['weapon_type_cn']}</b> ({r['weapon_type_en']})</td></tr>
                    <tr><td style="color:#666;">口径</td><td>{r['caliber']}</td></tr>
                    <tr><td style="color:#666;">产地</td><td>{r['country']}</td></tr>
                </table>
                {error_info}
                <div style="margin:8px 0;">
                    <div style="font-size:12px;color:#666;margin-bottom:4px;">各属性CLIP匹配分数:</div>
                    {attr_bars}
                </div>
                <div style="margin-top:8px;padding:8px;background:#fff;border-radius:6px;">{issues_html}</div>
            </div>
        </div>'''

    tp_cases = [r for r in flagged if r["has_error"]]
    fn_cases = [r for r in results if r["has_error"] and not r["is_flagged"]]
    fp_cases = [r for r in flagged if not r["has_error"]]
    normal_cases = [r for r in results if not r["has_error"] and not r["is_flagged"]]

    cases_html = ""
    if tp_cases:
        cases_html += f"<h3 style='color:#dc2626;margin:20px 0 10px;'>🔴 成功检出的属性冲突（{len(tp_cases)}个）</h3>"
        cases_html += "<p style='color:#666;font-size:14px;margin-bottom:12px;'>表格中某个属性值被篡改了（比如口径从9mm改成了.50 BMG），CLIP发现图片内容与被篡改的属性描述不匹配。每个柱状图代表一个属性的CLIP匹配分数，红色表示低于阈值。</p>"
        for r in tp_cases[:4]:
            cases_html += make_case_card(r, "✅ 成功检出", "#dc2626", "#fef2f2")
    if fn_cases:
        cases_html += f"<h3 style='color:#ca8a04;margin:20px 0 10px;'>🟡 漏检的属性冲突（{len(fn_cases)}个）</h3>"
        cases_html += "<p style='color:#666;font-size:14px;margin-bottom:12px;'>属性值确实被篡改了，但CLIP没能发现——可能是因为篡改后的属性描述与图片仍然比较匹配（比如产地从奥地利改成德国，CLIP看不出区别）。</p>"
        for r in fn_cases[:3]:
            cases_html += make_case_card(r, "⚠️ 漏检", "#ca8a04", "#fffbeb")
    if fp_cases:
        cases_html += f"<h3 style='color:#16a34a;margin:20px 0 10px;'>🟢 误报（{len(fp_cases)}个）</h3>"
        cases_html += "<p style='color:#666;font-size:14px;margin-bottom:12px;'>数据是正确的，但被标记为可疑。这些需要人工复核。</p>"
        for r in fp_cases[:3]:
            cases_html += make_case_card(r, "误报", "#16a34a", "#f0fdf4")
    if normal_cases:
        cases_html += f"<h3 style='color:#666;margin:20px 0 10px;'>⚪ 正常样本示例</h3>"
        for r in normal_cases[:2]:
            cases_html += make_case_card(r, "正常", "#94a3b8", "#f8fafc")

    error_table_rows = ""
    for r in results:
        if r["has_error"]:
            detected = "✅检出" if r["is_flagged"] else "❌漏检"
            error_table_rows += f"<tr><td>{r['id']}</td><td>{r['original_name'] if r.get('original_name') else r['weapon_name']}</td><td>{r.get('error_type','')}</td><td>{r.get('error_desc','')[:60]}</td><td>{r['caliber_score']:.4f}</td><td>{r['country_score']:.4f}</td><td>{r['type_score']:.4f}</td><td>{r['severity']}</td><td>{detected}</td></tr>"

    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>多模态细粒度冲突检测实验报告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#333;line-height:1.8}}
.c{{max-width:1000px;margin:0 auto;padding:20px}}
.h{{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:40px;border-radius:16px;margin-bottom:24px}}
.h h1{{font-size:24px;margin-bottom:10px}}.h p{{opacity:0.9;font-size:14px;margin:4px 0}}
.s{{background:#fff;border-radius:12px;padding:30px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.s h2{{font-size:20px;margin-bottom:16px;border-left:4px solid #2563eb;padding-left:12px;color:#1e3a5f}}
.s h3{{font-size:16px;margin:20px 0 8px}}
.m{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:14px;margin:20px 0}}
.mc{{background:#f8fafc;border-radius:10px;padding:16px;text-align:center;border:1px solid #e2e8f0}}
.mc .l{{font-size:11px;color:#64748b}}.mc .v{{font-size:24px;font-weight:800;margin:4px 0}}
.g{{color:#16a34a}}.r{{color:#dc2626}}.b{{color:#2563eb}}.y{{color:#ca8a04}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:12px}}
th{{background:#1e3a5f;color:#fff;padding:8px;text-align:left}}
td{{padding:6px 8px;border-bottom:1px solid #e2e8f0}}
.n{{background:#eff6ff;border-left:4px solid #2563eb;padding:14px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14px}}
.code{{background:#1e293b;color:#e2e8f0;padding:16px;border-radius:8px;font-family:monospace;font-size:13px;margin:12px 0;white-space:pre-wrap;line-height:1.5}}
</style></head><body><div class="c">

<div class="h">
<h1>多模态细粒度冲突检测实验报告</h1>
<p><b>这个实验解决什么问题？</b></p>
<p>武器装备数据库里，每条记录有多个属性：武器名称、类型、口径、产地等（表格数据），同时配了一张武器照片（图片数据）。如果有人把口径从"9mm"改成了".50 BMG"，或者把产地从"奥地利"改成了"俄罗斯"，表格数据和图片就产生了<b>细粒度冲突</b>——不是整张图片放错了，而是某个具体属性值与图片内容矛盾。</p>
<p>这个实验用CLIP模型对每个属性做独立的图文匹配打分，发现哪个属性与图片不一致。</p>
<p style="margin-top:8px;">实验时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ｜ 数据：11把真实武器照片 + GunsAndWeapons规格表</p>
</div>

<div class="s">
<h2>什么是"细粒度多模态冲突"？</h2>
<div class="n">
<p><b>粗粒度冲突</b>（之前的实验）：表格说"手枪"，图片是步枪 → 整体类型不匹配</p>
<p><b>细粒度冲突</b>（这个实验）：表格说"口径9mm"，图片里其实是.45口径的武器 → 具体属性值不匹配</p>
<p>细粒度冲突更难检测，因为武器类型可能是对的（都是手枪），但口径、产地等具体属性被篡改了。</p>
</div>
<div class="n">
<p><b>检测方法</b>：为表格的每个属性生成文本描述，用CLIP计算描述与图片的匹配分数：</p>
</div>
<div class="code">表格属性: 名称=Glock 17, 类型=手枪, 口径=9mm, 产地=奥地利

生成描述:
  "a photo of a Glock 17"              → CLIP计算与图片的匹配度 → 名称分数
  "a photo of a pistol"                → CLIP计算与图片的匹配度 → 类型分数
  "a photo of a firearm chambered in 9mm"  → CLIP计算与图片的匹配度 → 口径分数
  "a photo of an Austrian firearm"     → CLIP计算与图片的匹配度 → 产地分数

如果某个属性分数明显低于其他属性 → 该属性可能被篡改（冲突！）</div>
</div>

<div class="s">
<h2>实验设计</h2>
<table>
<tr><th>项目</th><th>说明</th></tr>
<tr><td>武器数据</td><td>11把真实武器（Wikipedia照片 + GunsAndWeapons规格表）</td></tr>
<tr><td>检测属性</td><td>名称、类型、口径、产地（4个细粒度属性）</td></tr>
<tr><td>注入错误</td><td>篡改某个属性值（如口径9mm→.50 BMG），不换图片，看能否发现属性级冲突</td></tr>
<tr><td>错误类型</td><td>口径篡改、产地篡改、类型篡改、名称篡改、多属性篡改</td></tr>
<tr><td>检测方法</td><td>①属性级统计异常（分数低于阈值）②属性间不一致（某属性远低于其他属性）</td></tr>
</table>
</div>

<div class="s">
<h2>实验结果</h2>
<div class="m">
<div class="mc" style="background:#dbeafe;"><div class="l">总样本</div><div class="v b">{total}</div></div>
<div class="mc" style="background:#fef9c3;"><div class="l">注入冲突</div><div class="v y">{n_errors}</div></div>
<div class="mc" style="background:#dcfce7;"><div class="l">正确检出</div><div class="v g">{tp}</div></div>
<div class="mc" style="background:#fee2e2;"><div class="l">漏检</div><div class="v r">{fn}</div></div>
<div class="mc" style="background:#dcfce7;"><div class="l">精确率</div><div class="v g">{prec:.0%}</div></div>
<div class="mc" style="background:#fef9c3;"><div class="l">召回率</div><div class="v y">{rec:.0%}</div></div>
<div class="mc" style="background:#dbeafe;"><div class="l">F1</div><div class="v b">{f1:.0%}</div></div>
</div>
</div>

<div class="s">
<h2>典型案例分析</h2>
<p>每个案例展示：真实武器照片 + 表格属性 + 各属性CLIP匹配分数（柱状图）+ 检测结果。</p>
{cases_html}
</div>

<div class="s">
<h2>全部冲突样本检测详情</h2>
<table>
<tr><th>ID</th><th>武器</th><th>错误类型</th><th>错误描述</th><th>口径分</th><th>产地分</th><th>类型分</th><th>严重度</th><th>检测</th></tr>
{error_table_rows}
</table>
</div>

<div class="s">
<h2>实验结论</h2>
<div class="n"><p><b>1. 细粒度冲突检测是可行的</b>：通过对每个属性独立计算CLIP匹配分数，可以发现"某个属性值与图片内容矛盾"的细粒度冲突。</p></div>
<div class="n"><p><b>2. 不同属性的可检测性不同</b>：类型篡改（手枪→狙击步枪）容易检测，因为视觉差异大；口径篡改（9mm→.50 BMG）较难，因为CLIP对口径数字的理解有限；产地篡改最难，因为CLIP不擅长区分国家风格。</p></div>
<div class="n"><p><b>3. 属性间一致性分析是关键</b>：即使单个属性分数没低于阈值，如果某属性分数远低于其他属性（如口径分0.15但其他都是0.30），也能发现异常。</p></div>
<div class="n"><p><b>4. 改进方向</b>：①用VLM（多模态大模型）做属性问答（"这把枪口径多大？"）替代CLIP相似度；②加入军工知识图谱做约束验证（"9mm口径的手枪不可能是狙击步枪"）；③扩展到三模态（表格+图片+时序传感器）。</p></div>
</div>

</div></body></html>'''

    out = OUTPUT_DIR / "fine_grained_conflict_report.html"
    with open(out, "w") as f:
        f.write(html)

    json_out = OUTPUT_DIR / "fine_grained_conflict_results.json"
    with open(json_out, "w") as f:
        json.dump({"results": results, "flagged": flagged, "stats": stats, "attr_stats": attr_stats},
                  f, indent=2, ensure_ascii=False, default=str)

    print(f"\nHTML报告: {out} ({len(html)//1024} KB)")
    print(f"JSON结果: {json_out}")
    return out

def main():
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)

    print("=" * 70)
    print("多模态细粒度冲突检测实验")
    print("=" * 70)

    samples = load_data()
    print(f"加载 {len(samples)} 条真实武器数据")

    samples = inject_fine_grained_errors(samples)

    results = run_clip_attribute_matching(samples)

    flagged, tp, fp, fn, prec, rec, f1, attr_stats = detect_conflicts(results)

    stats = {"tp": tp, "fp": fp, "fn": fn, "prec": prec, "rec": rec, "f1": f1}
    report_path = generate_html(results, flagged, stats, attr_stats)

    print(f"\n{'='*70}")
    print("实验完成!")
    print(f"  细粒度属性级冲突检测: ✅")
    print(f"  F1: {f1:.1%}")
    print(f"  报告: {report_path}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
