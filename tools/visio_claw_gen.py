"""
visio_claw_gen.py — 爪子图(部件组成图)生成工具 (Visio .vsdx)

参考样式: 系统技术方案-yjw.doc 中"图1 微调数据集构建平台部件组成图"
结构: 中心智能体节点 + 环绕部件节点 + 连线, 全部黑体10px

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

CENTER_W, CENTER_H = 2.0, 0.9     # 中心智能体框
PART_W, PART_H = 1.9, 0.8         # 部件框


def gen_claw(title, parts, out_path):
    """parts: List[str] 部件名称; 中心为 title"""
    # 5 个部件环绕布局 (横向A4 11.69x8.27)
    layout = [
        (0.4, 6.4),   # 左上
        (9.4, 6.4),   # 右上
        (0.4, 3.6),   # 左中
        (9.4, 3.6),   # 右中
        (4.85, 0.4),  # 下中
    ]
    center_xy = (4.85, 3.6)

    with vsdx.VisioFile(TEMPLATE) as vis:
        page = vis.get_page_by_name("Page-1")
        page.name = title
        src = page.find_shape_by_text("RECTANGLE")

        # 中心节点
        center = src
        center.text = title
        center.move(center_xy[0] - center.x, center_xy[1] - center.y)

        # 部件节点
        for i, (name, (px, py)) in enumerate(zip(parts, layout)):
            sh = src.copy(page) if i >= 0 else src
            sh.text = name
            sh.move(px - sh.x, py - sh.y)
            vsdx.Connect.create(page, center, sh)

        # 清理模板残留形状(RECTANGLE源已用作中心,其余旧形状删除)
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


# ---- 图A: 特征提取与上下文关联智能体 ----
def build_feature_context():
    parts = [
        "多模态特征提取",
        "语义角色标注",
        "跨章节实体链接",
        "上下文聚合",
        "条目库管理",
    ]
    out = os.path.join(OUT_DIR, "01_特征提取与上下文关联智能体_部件组成图.vsdx")
    gen_claw("特征提取与上下文关联智能体", parts, out)
    postprocess(out)
    print(f"[A] 已生成: {out}")
    return out


# ---- 图B: 数据一致性校验智能体 ----
def build_consistency_check():
    parts = [
        "语法层校验",
        "语义层校验",
        "逻辑层校验",
        "差异判别",
        "不一致性报告生成",
    ]
    out = os.path.join(OUT_DIR, "02_数据一致性校验智能体_部件组成图.vsdx")
    gen_claw("数据一致性校验智能体", parts, out)
    postprocess(out)
    print(f"[B] 已生成: {out}")
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    if which in ("all", "feature_context"):
        results.append(build_feature_context())
    if which in ("all", "consistency_check"):
        results.append(build_consistency_check())
    return results


if __name__ == "__main__":
    main()
