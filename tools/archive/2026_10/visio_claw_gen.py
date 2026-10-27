"""
visio_claw_gen.py — 爪子图(部件组成图)生成工具 (Visio .vsdx) v2 通用版

设计原则:
  - 部件数量精简为 3 个(布局清晰), 命名具备跨场景通用性
  - 五个典型场景均适用: 数智研发软件需求规格设计 / 引信方案设计 /
    引信质量缺陷溯源 / 航空发动机维护保障 / 航天科工现场智能监管
  - 全部黑体10px, 命名空间已修复

用法:
  python visio_claw_gen.py                     # 生成全部两张图
  python visio_claw_gen.py feature_context     # 只生成特征提取与上下文关联智能体
  python visio_claw_gen.py consistency_check   # 只生成数据一致性校验智能体

输出:
  output/01_特征提取与上下文关联智能体_部件组成图.vsdx
  output/02_数据一致性校验智能体_部件组成图.vsdx
"""

from __future__ import annotations
import os
import re
import sys
import zipfile

import vsdx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "output")
TEMPLATE = os.path.join(os.path.dirname(vsdx.__file__), "media", "media.vsdx")

VISIO_NS = "http://schemas.microsoft.com/office/visio/2012/main"
FONT_ID_HEITI = "10"
FONT_SIZE_PT = 10

CENTER_W, CENTER_H = 2.6, 1.0     # 中心智能体框
PART_W, PART_H = 2.4, 0.9         # 部件框


def gen_claw(title, parts, out_path):
    """parts: List[str] 部件名称; 中心为 title。三角环绕布局"""
    layout = [
        (0.6, 6.2),   # 左上
        (8.8, 6.2),   # 右上
        (4.7, 0.8),   # 下中
    ]
    center_xy = (4.7, 3.7)

    with vsdx.VisioFile(TEMPLATE) as vis:
        page = vis.get_page_by_name("Page-1")
        page.name = title
        src = page.find_shape_by_text("RECTANGLE")

        # 中心节点
        center = src
        center.text = title
        center.move(center_xy[0] - center.x, center_xy[1] - center.y)

        # 部件节点
        for name, (px, py) in zip(parts, layout):
            sh = src.copy(page)
            sh.text = name
            sh.move(px - sh.x, py - sh.y)
            vsdx.Connect.create(page, center, sh)

        # 清理模板残留形状
        for s in list(page.child_shapes or []):
            if s.text and s.text.strip() in ("CONNECTED_SHAPE", "STRAIGHT_CONNECTOR", "CURVED_CONNECTOR", "CIRCLE", "LINE"):
                s.remove()

        vis.save_vsdx(out_path)


def postprocess(path):
    """命名空间修复 + 黑体10px注入 + 页面横向"""
    src = zipfile.ZipFile(path)
    parts = {}
    for name in src.namelist():
        parts[name] = src.read(name)
    src.close()

    new_parts = {}
    for name, data in parts.items():
        if not (name.endswith(".xml") or name.endswith(".rels")):
            new_parts[name] = data
            continue
        text = data.decode("utf-8")
        text = text.replace(f'xmlns:ns0="{VISIO_NS}"', f'xmlns="{VISIO_NS}"')
        text = text.replace("ns0:", "")
        new_parts[name] = text.encode("utf-8")

    doc_name = "visio/document.xml"
    if doc_name in new_parts:
        doc = new_parts[doc_name].decode("utf-8")
        if "SimHei" not in doc:
            face = (f'<FaceName NameU="SimHei" ID="{FONT_ID_HEITI}" '
                    f'UnicodeRanges="-2147483648 0 0 0" CharSets="0 0" Panose="2 2 0 0 0 0 0 0 0 0" Flags="325"/>')
            doc = doc.replace("</FaceNames>", face + "</FaceNames>")
        new_parts[doc_name] = doc.encode("utf-8")

    page_name = "visio/pages/page1.xml"
    if page_name in new_parts:
        page = new_parts[page_name].decode("utf-8")
        char_section = (
            f'<Section N="Character"><Row IX="0">'
            f'<Cell N="Font" V="{FONT_ID_HEITI}"/>'
            f'<Cell N="Size" V="{FONT_SIZE_PT}"/>'
            f'<Cell N="Color" V="0"/>'
            f'<Cell N="Style" V="0"/>'
            f'</Row></Section>'
        )
        page = re.sub(
            r'(<Section N="Geometry"|</Section><Text|<Text)',
            lambda m: char_section + m.group(1),
            page,
        )
        new_parts[page_name] = page.encode("utf-8")

    pages_name = "visio/pages/pages.xml"
    if pages_name in new_parts:
        pages = new_parts[pages_name].decode("utf-8")
        pages = re.sub(r'<Cell N="PageWidth"[^>]*/>', '<Cell N="PageWidth" V="11.69291338582677"/>', pages)
        pages = re.sub(r'<Cell N="PageHeight"[^>]*/>', '<Cell N="PageHeight" V="8.26771653543307"/>', pages)
        new_parts[pages_name] = pages.encode("utf-8")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in new_parts.items():
            zout.writestr(name, data)


# ---- 图A: 特征提取与上下文关联智能体 (3 个通用部件) ----
def build_feature_context():
    parts = [
        "多模态特征提取",
        "跨源实体关联",
        "条目汇聚管理",
    ]
    out = os.path.join(OUT_DIR, "01_特征提取与上下文关联智能体_部件组成图.vsdx")
    gen_claw("特征提取与上下文关联智能体", parts, out)
    postprocess(out)
    print(f"[A] 已生成: {out}")
    return out


# ---- 图B: 数据一致性校验智能体 (3 个通用部件) ----
def build_consistency_check():
    parts = [
        "语法层校验",
        "语义层校验",
        "逻辑层校验",
    ]
    out = os.path.join(OUT_DIR, "02_数据一致性校验智能体_部件组成图.vsdx")
    gen_claw("数据一致性校验智能体", parts, out)
    postprocess(out)
    print(f"[B] 已生成: {out}")
    return out


# ---- 图C: 设计经验结构化建模智能体 (3 个通用部件) ----
def build_exp_modeling():
    parts = [
        "经验知识抽取",
        "知识形式化",
        "知识图谱构建",
    ]
    out = os.path.join(OUT_DIR, "03_设计经验结构化建模智能体_部件组成图.vsdx")
    gen_claw("设计经验结构化建模智能体", parts, out)
    postprocess(out)
    print(f"[C] 已生成: {out}")
    return out


# ---- 图D: 数据合成与增强智能体 (3 个通用部件) ----
def build_synth_enhance():
    parts = [
        "数据合成",
        "样本增强",
        "类别均衡",
    ]
    out = os.path.join(OUT_DIR, "04_数据合成与增强智能体_部件组成图.vsdx")
    gen_claw("数据合成与增强智能体", parts, out)
    postprocess(out)
    print(f"[D] 已生成: {out}")
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    if which in ("all", "feature_context"):
        results.append(build_feature_context())
    if which in ("all", "consistency_check"):
        results.append(build_consistency_check())
    if which in ("all", "exp_modeling"):
        results.append(build_exp_modeling())
    if which in ("all", "synth_enhance"):
        results.append(build_synth_enhance())
    return results


if __name__ == "__main__":
    main()
