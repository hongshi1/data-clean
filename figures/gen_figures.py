#!/usr/bin/env python3
"""生成3个架构图：SRS技术路线 / 通用五场景 / 数据集合成流程"""
import os, sys, time
from google import genai

API_KEY = "AIzaSyD-YR4qIe5d_g2Ddpu0sKDeLqPdpK2m1SY"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
client = genai.Client(api_key=API_KEY)
MODEL = "gemini-3-pro-image-preview"

STYLE_BLOCK = """
VISUAL STYLE — MODERN MINIMAL:
- Ultra-clean geometric shapes with crisp edges
- Bold color blocks as backgrounds for sections using desaturated tones: slate blue (#E8EDF2), warm sand (#F5F0E8), cool mint (#E8F2EE)
- Component boxes have ROUNDED CORNERS (12px radius), NO visible border, subtle shadow (1px, 4px blur, rgba(0,0,0,0.06))
- ONE accent color per section: Deep blue (#2563EB), Emerald (#059669), Amber (#D97706), Rose (#E11D48), Purple (#7C3AED)
- Arrows are thin (1.5px), dark gray (#6B7280), with small filled circle at source and clean arrowhead at target
- Typography: Inter or system sans-serif, title 600 weight, body 400 weight
- Labels INSIDE boxes, not beside them
- Generous whitespace — at least 24px between elements
- NO decorative elements, NO icons — let the structure speak
- White background (#FFFFFF)
- The entire diagram should fit in a 16:9 aspect ratio landscape orientation
"""

COLOR_PALETTE = """
COLOR PALETTE — "Ocean Dusk":
- Deep teal #264653 (titles, headers)
- Teal #2A9D8F (layer 1 - data input)
- Gold #E9C46A (layer 2 - data assets)
- Sandy orange #F4A261 (layer 3 - context association)
- Burnt coral #E76F51 (layer 4 - inconsistency detection)
- Purple #7C3AED (layer 5 - evaluation)
- Gray #6B7280 (arrows, secondary text)
- Light backgrounds: #E8EDF2, #F5F0E8, #E8F2EE, #FDF2F0, #F3F0FD
"""

# ===== Figure 1: SRS技术路线架构图 =====
PROMPT_1 = f"""
Create a MODERN MINIMAL-style technical architecture diagram for a research paper.
The diagram shows a 5-layer technical architecture for SRS (Software Requirement Specification) inconsistency detection.

{STYLE_BLOCK}

{COLOR_PALETTE}

LAYOUT — 5 horizontal layers stacked vertically (bottom to top), with a base/foundation layer at the very bottom:

LAYER 5 (TOP, purple background #F3F0FD, accent #7C3AED):
- Title: "L5 评测与应用层"
- 4 boxes side by side: "P/R/F1报告", "多LLM标注", "人类基线", "论文产出"
- Small label on right: "→ 论文/审稿/工具"

LAYER 4 (coral background #FDF2F0, accent #E76F51):
- Title: "L4 三层不一致检测"
- 3 boxes: "语法层 S1-S7 (GJB规则驱动)", "语义层 7种图方法 (BGE/GCN/注意力)", "逻辑层 Z3+LLM (Solver验证unsat)"

LAYER 3 (orange background #FFF8F0, accent #F4A261):
- Title: "L3 上下文关联层"
- 4 boxes: "双图融合4通道 (recall=0.809)", "ID-Graph (2181节点)", "语义图 (508实体)", "VLM图片分析 (163张流程图)"

LAYER 2 (gold background #FFFBF0, accent #E9C46A):
- Title: "L2 数据资产工厂"
- 4 boxes: "Pair Dataset (366个配对)", "切片 5231条 (16份文档)", "GJB规则 120条", "词典 11参数"

LAYER 1 (teal background #E8F5F3, accent #2A9D8F):
- Title: "L1 数据入口层"
- 4 boxes: "16份GJB SRS", "MinerU解析", "textutil双源", "VLM分类 379张"

BASE/FOUNDATION (dark teal background #E8EDF2, accent #264653):
- Title: "底座基础设施"
- 6 boxes in a row: "LightRAG (11872实体)", "BGE-zh (512维)", "Z3 Solver", "kimi-k2.6 (moonshot)", "claude (wanqing)", "CoVe验证"

CONNECTIONS:
- Upward arrows from L1→L2→L3→L4→L5 (thin gray arrows, 1.5px)
- Upward arrow from BASE to all layers
- All arrows point upward

CONSTRAINTS:
- All text must be in Chinese (Simplified)
- Spell every label exactly as written above
- Do NOT add any English text except metric numbers
- Keep the diagram clean and professional
- 16:9 landscape orientation
"""

# ===== Figure 2: 通用五场景应用架构图 =====
PROMPT_2 = f"""
Create a MODERN MINIMAL-style technical architecture diagram for a research paper.
The diagram shows a unified technology platform serving 5 application scenarios.

{STYLE_BLOCK}

{COLOR_PALETTE}

LAYOUT — Top row has 5 scenario boxes, middle section is the unified platform with 4 technology modules, bottom is the infrastructure base:

TOP ROW (5 scenario boxes, each with different accent color):
- Box 1 (teal #2A9D8F): "技术文档一致性校验" with subtitle "SRS/标准/规范"
- Box 2 (gold #E9C46A): "多模态文档理解" with subtitle "图+表+文QA"
- Box 3 (orange #F4A261): "需求工程辅助" with subtitle "生成/检测/追溯"
- Box 4 (coral #E76F51): "知识图谱构建" with subtitle "实体/关系/推理"
- Box 5 (purple #7C3AED): "合规性检测" with subtitle "GJB/IEEE/国标"

MIDDLE SECTION (large rounded rectangle, light gray background #F8FAFC):
- Title at top: "统一技术中台 (Unified Platform)"
- 4 technology modules in a row:
  - Module 1 (blue accent): "上下文关联" / "双图融合4通道" / "跨位置聚合"
  - Module 2 (emerald accent): "三层检测" / "语法/语义/逻辑" / "Z3 Solver验证"
  - Module 3 (amber accent): "评测集合成" / "四段式流水线" / "40种注入方法"
  - Module 4 (rose accent): "检测器评测" / "P/R/F1分层报告" / "多LLM标注"

BOTTOM SECTION (infrastructure base, dark teal #264653 background, white text):
- Title: "底座: RAG | VLM | Z3 | LLM(kimi+claude) | BGE向量 | LightRAG"

CONNECTIONS:
- Downward arrows from each of the 5 scenario boxes to the middle platform section
- Downward arrow from middle section to bottom base
- All arrows are thin (1.5px) gray (#6B7280)

CONSTRAINTS:
- All text in Chinese (Simplified) except "Unified Platform"
- Spell every label exactly as written
- 16:9 landscape orientation
- Professional, clean, academic style
"""

# ===== Figure 3: 数据集合成流程图 =====
PROMPT_3 = f"""
Create a MODERN MINIMAL-style pipeline/workflow diagram for a research paper.
The diagram shows a 4-stage synthesis pipeline for constructing an evaluation dataset.

{STYLE_BLOCK}

{COLOR_PALETTE}

LAYOUT — 4 stages flowing left to right, each stage is a large rounded rectangle with internal components:

STAGE 1 (leftmost, teal background #E8F5F3, accent #2A9D8F):
- Title: "阶段1: 检测对象提取"
- Subtitle: "确定性, 可复现"
- Internal boxes (stacked vertically):
  - "Pair Dataset 366个"
  - "VLM用例图 136条"
  - "VLM流程图 163张"
  - "chunks 5231条"
  - Arrow down to: "5类检测对象 1128个"
- Output label below: "→ 功能名913 + 接口159 + 参数870 + 流程13 + 表头40"

STAGE 2 (gold background #FFFBF0, accent #E9C46A):
- Title: "阶段2: 40种规则注入"
- Subtitle: "seed=42, Z3 gate验证"
- Internal structure: 4 small groups stacked:
  - "术语 8种" (with subtitle "同义异名/同名异义/枚举/告警/指令/量纲/接口/缩写")
  - "参数 10种" (with subtitle "时间/周期/阈值/对齐/资源/值域/存储/精度/降级/故障")
  - "逻辑 11种" (with subtitle "模式切换/异常处置/时序/数据流/分支/互斥/原子/仲裁/权限/恢复/重搜")
  - "GJB 11种" (with subtitle "可测试/容错/安全/审计/追溯/报警/自检/掉电/防护/升级/降级")
- Small badge: "Z3 Solver验证unsat" with checkmark
- Output: "→ 注入结果 200条"

STAGE 3 (orange background #FFF8F0, accent #F4A261):
- Title: "阶段3: LLM改写"
- Subtitle: "kimi-k2.6 via moonshot"
- Internal boxes:
  - "thinking=disabled"
  - "temperature=0.6"
  - "response_format=json"
  - "只改语言不改结论"
- Output: "→ 自然语言QA 200条"

STAGE 4 (coral background #FDF2F0, accent #E76F51):
- Title: "阶段4: 分层验证"
- Two sub-boxes stacked:
  - Sub-box 1 (gold border): "Gold层" / "Z3 Solver验证unsat" / "规则确定性验证" / "零人工" / "≈150条"
  - Sub-box 2 (purple border): "Silver层" / "kimi+claude双LLM" / "不同endpoint交叉验证" / "延期人工audit" / "≈200条"
- Output: "→ 评测集 400条"

FLOW ARROWS:
- Large rightward arrows between each stage (thick, 3px, colored by source stage)
- Below the entire pipeline, a separate result box:
  "多LLM独立标注验证: kimi 79.9% | claude 65.8% | glm 78.9% | Cohen κ=0.57-0.78"

CONSTRAINTS:
- All text in Chinese (Simplified)
- Spell every label exactly as written above
- Left to right flow
- 16:9 landscape orientation
- Professional academic style
"""

def generate_image(prompt_text, name, attempt_num):
    print(f"\n{'='*60}\n{name} - Attempt {attempt_num}\n{'='*60}")
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt_text,
            config=genai.types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        output_path = os.path.join(OUTPUT_DIR, f"{name}_attempt{attempt_num}.png")
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                with open(output_path, "wb") as f:
                    f.write(part.inline_data.data)
                print(f"Saved: {output_path} ({os.path.getsize(output_path):,} bytes)")
                return output_path
            elif part.text:
                print(f"Text: {part.text[:300]}")
        print("WARNING: No image in response")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def main():
    figures = [
        (PROMPT_1, "fig_srs_architecture"),
        (PROMPT_2, "fig_unified_platform"),
        (PROMPT_3, "fig_synthesis_pipeline"),
    ]
    
    for prompt, name in figures:
        for i in range(1, 4):  # 3 attempts each
            if i > 1:
                time.sleep(3)
            generate_image(prompt, name, i)
    
    print("\n=== All figures generated ===")
    print("Review the attempt images and pick the best one for each figure.")

if __name__ == "__main__":
    main()
