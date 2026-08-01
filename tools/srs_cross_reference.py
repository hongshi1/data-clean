#!/usr/bin/env python3
"""
Image-Table-Text Cross-Reference Builder
将图片、表格、文本三类数据交叉配对，生成统一的可视化报告。

配对策略:
  1. 图片分类: 用VLM/heuristic判断每张图片是"表格截图"还是"技术图表"
  2. 表格截图 → 与HTML表格配对(按页面顺序+内容匹配)
  3. 技术图表 → 与文本描述配对(caption+context+section)
  4. 生成统计报告
"""

import json
import os
import re
import base64
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET = REPO_ROOT / "data" / "gjb_438c" / "dataset_v2"
OUTPUT = DATASET / "cross_reference_report.html"

KIMI_API = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
KIMI_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
KIMI_MODEL = "ep-0dkcs8-1777515852343838800"


def classify_image_with_vlm(img_path: str, timeout: int = 60) -> dict:
    """用VLM判断图片类型。"""
    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        resp = requests.post(
            KIMI_API,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {KIMI_KEY}"},
            json={
                "model": KIMI_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "text", "text": "分析这张图片。输出JSON: {\"content_type\": \"table_screenshot|technical_diagram|cover_page|text_page|other\", \"description\": \"30字描述\", \"has_table\": true/false}"}
                    ]
                }],
                "temperature": 0.1,
                "max_tokens": 256
            },
            timeout=timeout
        )
        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip()
        for prefix in ["```json", "```"]:
            if content.startswith(prefix):
                content = content[len(prefix):]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except:
        return {"content_type": "unknown", "description": "VLM分析失败", "has_table": False}


def classify_image_heuristic(img_data: dict, doc_tables: list) -> str:
    """启发式判断图片类型(不用VLM)。"""
    ftype = img_data.get("image_type", "")
    size = img_data.get("image_size_kb", 0)
    has_caption = bool(img_data.get("caption"))
    
    # orphaned + doc has tables → likely table screenshot
    if ftype == "orphaned_figure" and len(doc_tables) > 0:
        return "table_screenshot"
    
    # Has caption with "Figure" or "图" → technical diagram
    caption = (img_data.get("caption") or "").lower()
    if "figure" in caption or "图" in caption:
        return "technical_diagram"
    
    # Has specific diagram types → technical
    if ftype in ["architecture_diagram", "flowchart", "state_diagram", "interface_diagram", "data_diagram", "context_diagram"]:
        return "technical_diagram"
    
    # 0KB → file doesn't exist, can't determine
    if size == 0:
        return "missing_file"
    
    # Has caption but generic → figure
    if has_caption:
        return "technical_diagram"
    
    return "unknown"


def pair_image_with_table(img_data: dict, tables: list, img_index: int) -> dict:
    """将表格截图与HTML表格配对。"""
    # Strategy: match by order (image N → table N)
    # Also try content matching if VLM description available
    
    best_match = None
    if img_index < len(tables):
        best_match = tables[img_index]
    
    return {
        "image_file": img_data.get("image_file", ""),
        "image_size_kb": img_data.get("image_size_kb", 0),
        "matched_table": {
            "type": best_match.get("type", "") if best_match else None,
            "section": best_match.get("section", "") if best_match else None,
            "headers": best_match.get("headers", [])[:5] if best_match else [],
            "row_count": best_match.get("row_count", 0) if best_match else 0,
            "is_empty": best_match.get("is_empty", False) if best_match else None,
        } if best_match else None,
        "pairing_method": "order_based",
        "pairing_confidence": 0.6,  # Low confidence for order-based
    }


def pair_image_with_text(img_data: dict) -> dict:
    """将技术图表与文本描述配对。"""
    return {
        "image_file": img_data.get("image_file", ""),
        "image_size_kb": img_data.get("image_size_kb", 0),
        "caption": img_data.get("caption"),
        "figure_number": img_data.get("figure_number"),
        "image_type": img_data.get("image_type", ""),
        "section": img_data.get("section"),
        "context_before": img_data.get("context_before"),
        "context_after": img_data.get("context_after"),
        "has_caption": img_data.get("has_caption", False),
        "has_context": img_data.get("has_context", False),
        "pairing_method": "md_reference",
        "pairing_confidence": 0.9 if img_data.get("has_caption") else 0.5,
    }


def process_all_documents():
    """处理所有文档，生成交叉配对报告。"""
    print("=" * 60)
    print("Image-Table-Text Cross-Reference Builder")
    print("=" * 60)
    
    catalog = json.load(open(DATASET / "catalog.json"))
    
    all_results = []
    stats = {
        "total_docs": 0,
        "total_images": 0,
        "total_tables": 0,
        "images_by_type": defaultdict(int),
        "tables_by_type": defaultdict(int),
        "pairings": {
            "image_table_pairs": 0,
            "image_text_pairs": 0,
            "unpaired_images": 0,
            "missing_files": 0,
        },
        "by_category": {
            "gjb_srs": {"docs": 0, "images": 0, "tables": 0, "table_screenshots": 0, "technical_diagrams": 0},
            "general_srs": {"docs": 0, "images": 0, "tables": 0, "table_screenshots": 0, "technical_diagrams": 0},
        }
    }
    
    for entry in catalog:
        doc_dir = DATASET / entry["path"]
        struct_path = doc_dir / "structured.json"
        if not struct_path.exists():
            continue
        
        struct = json.load(open(struct_path))
        images = struct.get("images", [])
        tables = struct.get("tables", [])
        
        if not images and not tables:
            continue
        
        cat = "gjb_srs" if entry["is_gjb"] else "general_srs"
        stats["total_docs"] += 1
        stats["total_images"] += len(images)
        stats["total_tables"] += len(tables)
        stats["by_category"][cat]["docs"] += 1
        stats["by_category"][cat]["images"] += len(images)
        stats["by_category"][cat]["tables"] += len(tables)
        
        doc_result = {
            "doc_id": entry["doc_id"],
            "doc_name": entry["doc_name"],
            "category": cat,
            "is_gjb": entry["is_gjb"],
            "language": entry.get("language", "zh"),
            "system_type": entry.get("system_type", "unknown"),
            "total_images": len(images),
            "total_tables": len(tables),
            "image_table_pairs": [],
            "image_text_pairs": [],
            "unpaired_images": [],
            "tables_without_image": [],
        }
        
        # Classify each image and pair accordingly
        table_img_idx = 0  # Counter for table screenshots
        
        for i, img in enumerate(images):
            img_type = classify_image_heuristic(img, tables)
            stats["images_by_type"][img_type] += 1
            
            if img_type == "table_screenshot":
                # Pair with table
                pair = pair_image_with_table(img, tables, table_img_idx)
                doc_result["image_table_pairs"].append(pair)
                stats["pairings"]["image_table_pairs"] += 1
                stats["by_category"][cat]["table_screenshots"] += 1
                table_img_idx += 1
            elif img_type == "technical_diagram":
                # Pair with text
                pair = pair_image_with_text(img)
                doc_result["image_text_pairs"].append(pair)
                stats["pairings"]["image_text_pairs"] += 1
                stats["by_category"][cat]["technical_diagrams"] += 1
            elif img_type == "missing_file":
                doc_result["unpaired_images"].append({
                    "image_file": img.get("image_file", ""),
                    "reason": "文件不存在(0KB)",
                    "image_type": img.get("image_type", ""),
                    "section": img.get("section"),
                })
                stats["pairings"]["missing_files"] += 1
            else:
                doc_result["unpaired_images"].append({
                    "image_file": img.get("image_file", ""),
                    "reason": f"类型未知({img_type})",
                    "image_type": img.get("image_type", ""),
                    "section": img.get("section"),
                    "caption": img.get("caption"),
                })
                stats["pairings"]["unpaired_images"] += 1
        
        # Tables without matching image
        paired_table_count = len(doc_result["image_table_pairs"])
        for j, t in enumerate(tables):
            if j >= paired_table_count:
                doc_result["tables_without_image"].append({
                    "type": t.get("type", ""),
                    "section": t.get("section", ""),
                    "headers": t.get("headers", [])[:3],
                    "row_count": t.get("row_count", 0),
                    "is_empty": t.get("is_empty", False),
                })
        
        # Table type stats
        for t in tables:
            stats["tables_by_type"][t.get("type", "unknown")] += 1
        
        all_results.append(doc_result)
    
    # Convert defaultdicts
    stats["images_by_type"] = dict(stats["images_by_type"])
    stats["tables_by_type"] = dict(stats["tables_by_type"])
    
    # Generate HTML report
    generate_html_report(all_results, stats)
    
    # Save JSON
    (DATASET / "cross_reference.json").write_text(
        json.dumps({"stats": stats, "documents": all_results}, indent=2, ensure_ascii=False), "utf-8"
    )
    
    print(f"\n{'=' * 60}")
    print("交叉配对完成")
    print(f"  文档数: {stats['total_docs']}")
    print(f"  总图片: {stats['total_images']}")
    print(f"  总表格: {stats['total_tables']}")
    print(f"  图片-表格配对: {stats['pairings']['image_table_pairs']}")
    print(f"  图片-文本配对: {stats['pairings']['image_text_pairs']}")
    print(f"  未配对图片: {stats['pairings']['unpaired_images']}")
    print(f"  缺失文件: {stats['pairings']['missing_files']}")
    print(f"  图片类型: {stats['images_by_type']}")
    print(f"  表格类型: {stats['tables_by_type']}")
    print(f"  输出: {OUTPUT}")


def generate_html_report(documents: list, stats: dict):
    """生成HTML交叉配对报告。"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>SRS数据集 — 图片-表格-文本交叉配对报告</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
h2 {{ color: #4CAF50; margin-top: 40px; }}
h3 {{ color: #555; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th {{ background: #4CAF50; color: white; padding: 10px; text-align: left; font-size: 13px; }}
td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; font-size: 13px; }}
tr:hover {{ background: #f0f0f0; }}
.gjb {{ background: #e8f5e9; }}
.general {{ background: #e3f2fd; }}
.stat-card {{ display: inline-block; background: white; padding: 15px 25px; margin: 8px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; min-width: 120px; }}
.stat-num {{ font-size: 24px; font-weight: bold; }}
.stat-label {{ font-size: 12px; color: #666; }}
.pair-card {{ background: white; margin: 10px 0; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.pair-table {{ border-left: 4px solid #ff9800; }}
.pair-text {{ border-left: 4px solid #4CAF50; }}
.pair-unpaired {{ border-left: 4px solid #f44336; }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin: 2px; }}
.tag-table {{ background: #fff3e0; color: #e65100; }}
.tag-tech {{ background: #e8f5e9; color: #2e7d32; }}
.tag-miss {{ background: #ffebee; color: #c62828; }}
.tag-gjb {{ background: #c8e6c9; color: #2e7d32; }}
.tag-gen {{ background: #bbdefb; color: #1565c0; }}
.bar-container {{ display: inline-block; width: 200px; height: 20px; background: #eee; border-radius: 3px; vertical-align: middle; }}
.bar-fill {{ height: 20px; border-radius: 3px; }}
</style>
</head>
<body>

<h1>SRS数据集 — 图片-表格-文本交叉配对报告</h1>
<p>生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 文档数: {stats['total_docs']}</p>

<h2>📊 配对总览</h2>
<div>
"""
    
    # Stat cards
    for label, value, color in [
        ("总文档", stats['total_docs'], "#333"),
        ("总图片", stats['total_images'], "#e91e63"),
        ("总表格", stats['total_tables'], "#9c27b0"),
        ("图片→表格配对", stats['pairings']['image_table_pairs'], "#ff9800"),
        ("图片→文本配对", stats['pairings']['image_text_pairs'], "#4CAF50"),
        ("未配对", stats['pairings']['unpaired_images'] + stats['pairings']['missing_files'], "#f44336"),
    ]:
        html += f'<div class="stat-card"><div class="stat-num" style="color:{color}">{value}</div><div class="stat-label">{label}</div></div>\n'
    
    html += "</div>\n"
    
    # Category comparison
    html += """
<h2>📈 GJB vs 一般SRS 对比</h2>
<table>
<tr><th>指标</th><th>GJB SRS</th><th>一般SRS</th><th>总计</th></tr>
"""
    for label, key in [("文档数", "docs"), ("图片数", "images"), ("表格数", "tables"), ("表格截图", "table_screenshots"), ("技术图表", "technical_diagrams")]:
        g = stats['by_category']['gjb_srs'][key]
        n = stats['by_category']['general_srs'][key]
        html += f'<tr><td>{label}</td><td>{g}</td><td>{n}</td><td>{g+n}</td></tr>\n'
    html += "</table>\n"
    
    # Image type distribution
    html += """
<h2>🖼️ 图片类型分布</h2>
<table>
<tr><th>图片类型</th><th>数量</th><th>占比</th><th>分布</th></tr>
"""
    total_imgs = stats['total_images']
    for t, count in sorted(stats['images_by_type'].items(), key=lambda x: -x[1]):
        pct = count / max(total_imgs, 1) * 100
        bar_w = int(pct * 3)
        color = {"table_screenshot": "#ff9800", "technical_diagram": "#4CAF50", "missing_file": "#f44336", "unknown": "#999"}.get(t, "#2196F3")
        html += f'<tr><td>{t}</td><td>{count}</td><td>{pct:.1f}%</td><td><div class="bar-container"><div class="bar-fill" style="width:{bar_w}px;background:{color}"></div></div></td></tr>\n'
    html += "</table>\n"
    
    # Table type distribution
    html += """
<h2>📊 表格类型分布</h2>
<table>
<tr><th>表格类型</th><th>数量</th><th>占比</th></tr>
"""
    total_tbls = stats['total_tables']
    for t, count in sorted(stats['tables_by_type'].items(), key=lambda x: -x[1]):
        pct = count / max(total_tbls, 1) * 100
        html += f'<tr><td>{t}</td><td>{count}</td><td>{pct:.1f}%</td></tr>\n'
    html += "</table>\n"
    
    # Per-document details
    html += """
<h2>📋 每份文档配对详情</h2>
"""
    
    for doc in sorted(documents, key=lambda x: (not x['is_gjb'], -(x['total_images'] + x['total_tables']))):
        cat_class = "gjb" if doc['is_gjb'] else "general"
        cat_tag = f'<span class="tag tag-gjb">GJB</span>' if doc['is_gjb'] else f'<span class="tag tag-gen">一般</span>'
        
        html += f'<h3>{doc["doc_id"]} {doc["doc_name"][:40]} {cat_tag}</h3>\n'
        html += f'<p>图片: {doc["total_images"]}张 | 表格: {doc["total_tables"]}个 | 图片→表格: {len(doc["image_table_pairs"])} | 图片→文本: {len(doc["image_text_pairs"])} | 未配对: {len(doc["unpaired_images"])}</p>\n'
        
        # Image-Table pairs
        if doc['image_table_pairs']:
            html += '<table>\n<tr><th>配对类型</th><th>图片</th><th>大小</th><th>→配对表格</th><th>表格类型</th><th>表格章节</th><th>表头</th><th>行数</th><th>空表</th></tr>\n'
            for p in doc['image_table_pairs']:
                mt = p.get('matched_table', {})
                headers_str = ", ".join(mt.get('headers', []))[:40] if mt else ""
                html += f'<tr class="{cat_class}"><td><span class="tag tag-table">图片→表格</span></td><td>{p["image_file"][:20]}...</td><td>{p["image_size_kb"]}KB</td><td>→</td><td>{mt.get("type","") if mt else ""}</td><td>{mt.get("section","")[:30] if mt else ""}</td><td>{headers_str}</td><td>{mt.get("row_count","") if mt else ""}</td><td>{"是" if mt and mt.get("is_empty") else "否"}</td></tr>\n'
            html += '</table>\n'
        
        # Image-Text pairs
        if doc['image_text_pairs']:
            html += '<table>\n<tr><th>配对类型</th><th>图片</th><th>大小</th><th>标题</th><th>图号</th><th>类型</th><th>章节</th><th>有上下文</th><th>置信度</th></tr>\n'
            for p in doc['image_text_pairs']:
                cap = (p.get('caption') or '(无)')[:30]
                fig = f'Fig {p["figure_number"]}' if p.get('figure_number') else '无'
                section = (p.get('section') or '(无)')[:25]
                ctx = '是' if p.get('has_context') else '否'
                conf = p.get('pairing_confidence', 0)
                html += f'<tr class="{cat_class}"><td><span class="tag tag-tech">图片→文本</span></td><td>{p["image_file"][:20]}...</td><td>{p["image_size_kb"]}KB</td><td>{cap}</td><td>{fig}</td><td>{p["image_type"]}</td><td>{section}</td><td>{ctx}</td><td>{conf:.0%}</td></tr>\n'
            html += '</table>\n'
        
        # Unpaired images
        if doc['unpaired_images']:
            html += '<table>\n<tr><th>状态</th><th>图片</th><th>类型</th><th>章节</th><th>原因</th></tr>\n'
            for u in doc['unpaired_images']:
                html += f'<tr class="{cat_class}"><td><span class="tag tag-miss">未配对</span></td><td>{u["image_file"][:20]}...</td><td>{u.get("image_type","")}</td><td>{(u.get("section") or "")[:25]}</td><td>{u["reason"]}</td></tr>\n'
            html += '</table>\n'
        
        # Tables without image
        if doc['tables_without_image']:
            html += f'<p style="color:#999;font-size:12px;">无对应图片的表格: {len(doc["tables_without_image"])}个</p>\n'
    
    # Method explanation
    html += f"""
<h2>🔧 配对方法说明</h2>

<h3>图片分类方法</h3>
<table>
<tr><th>判断条件</th><th>分类结果</th><th>配对方式</th></tr>
<tr><td>image_type=orphaned_figure 且文档有表格</td><td>table_screenshot (表格截图)</td><td>→ 与HTML表格按顺序配对</td></tr>
<tr><td>caption含"Figure"/"图"</td><td>technical_diagram (技术图表)</td><td>→ 与文本描述配对(caption+context)</td></tr>
<tr><td>image_type为architecture/flowchart/state等</td><td>technical_diagram</td><td>→ 与文本描述配对</td></tr>
<tr><td>image_size_kb=0</td><td>missing_file (文件缺失)</td><td>→ 无法配对</td></tr>
<tr><td>其他</td><td>unknown</td><td>→ 无法配对</td></tr>
</table>

<h3>图片→表格配对方法</h3>
<p>当图片被判定为表格截图时(MinerU将PDF表格渲染为图片):</p>
<ul>
<li><strong>顺序匹配</strong>: 图片按MinerU提取顺序(=页面顺序)排序，与HTML表格按出现顺序一一配对</li>
<li><strong>置信度</strong>: 0.6(低，因为仅基于顺序，无内容验证)</li>
<li><strong>验证方法</strong>: 可用VLM描述图片内容，与HTML表格表头做语义匹配</li>
</ul>

<h3>图片→文本配对方法</h3>
<p>当图片被判定为技术图表时(MinerU在MD中保留了![]引用):</p>
<ul>
<li><strong>caption</strong>: 图片引用(![])的下一行非空文本</li>
<li><strong>context_before</strong>: 图片引用的前3行非空文本(跳过![]和#行)</li>
<li><strong>section</strong>: 向上搜索最近的#标题</li>
<li><strong>figure_number</strong>: 从caption中正则提取"Figure N"/"图N"</li>
<li><strong>image_type</strong>: caption关键词匹配(architecture/flowchart/state等)</li>
<li><strong>置信度</strong>: 0.9(有caption) / 0.5(无caption)</li>
</ul>

<h3>已知限制</h3>
<ul>
<li>GJB SRS(调度器/电池/编译器)的"图片"全是表格截图，无技术图表</li>
<li>部分图片文件缺失(0KB)，为原始MD引用了外部路径但文件未下载</li>
<li>顺序匹配的置信度低，需要VLM验证图片内容与表格内容的对应关系</li>
<li>跨文档图片关联(同系统SRS/SDD的相同图片)未实现</li>
</ul>

<hr>
<p style="color:#999;font-size:12px;">生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据集版本 v2</p>
</body>
</html>
"""
    
    OUTPUT.write_text(html, "utf-8")
    print(f"HTML报告: {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    process_all_documents()
