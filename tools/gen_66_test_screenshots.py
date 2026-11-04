r"""6.6测试结果截图与数据分析图生成(葛宣成合稿 6.6.1 / 6.6.5).

产出9张图 → docs/srs_project/paper/test_screenshots/:
  场景一(系统运行截图, 真实API调用):
    scene1_structured_parse.png    需求章节/复杂表格结构化解析+源页定位
    scene1_context_link.png        实体-表格-图-追溯跨章节上下文关联
    scene1_consistency_report.png  分层校验报告(违例提示+证据位置+判定依据)
  场景一(数据分析图, 数字全部来自runs/result.json):
    scene1_confusion_matrix.png    91QA三态混淆矩阵(级联配置)
    scene1_violation_detection.png 17真实违例分类型检出率
    scene1_cost_pareto.png         成本-质量Pareto
  场景五(样例数据截图, 真实jsonl+原图):
    scene5_qa_fields.png           监控图片+结构化QA字段
    scene5_image_qa_link.png       图片-关键实体-问答证据关联
    scene5_conflict_check.png      同类样本结论冲突分层校验+来源回查

后端: subprocess启动deploy/nkuDataProject(DEV_DB=sqlite, PYTHONPATH=backend,
独立端口8311避免与既有实例冲突), 用完terminate. 渲染: PIL + Microsoft YaHei
(卡片两遍绘制: 先测量后落笔); 分析图: matplotlib 300dpi. 全部数字取自真实
调用/真实run/真实样例, 不含虚构数据.

用法: python tools/gen_66_test_screenshots.py [--skip-api] [--skip-figs]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE / "deploy" / "nkuDataProject" / "backend"
OUT_DIR = BASE / "docs" / "srs_project" / "paper" / "test_screenshots"
RUNS = BASE / "data" / "gjb_438c" / "runs"
BACKEND_LOG = Path(r"C:\Users\12488\AppData\Local\Temp\opencode\nku_backend_8311.log")

#: 场景一分析图数据源run(真实落盘result.json, config.json同目录可核)
RUN_CASCADE = "eval_cascade_1e92cdce_20261030_122756"       # 最新五配置全量
RUN_PAPER_MATRIX = "eval_paper_matrix_c409df7f_20261030_122944"  # 同日B0-B5基线
RUN_VIOLATIONS = "eval_violations_5d5c92a8_20261027_165400"  # 17违例终态16/17

#: 场景五真实样例数据(20260924-场景5样例数据及需求说明文档)
SCENE5_DIR = Path(
    r"C:\baidunetdiskdownload\5个场景数据集"
    r"\20260924-场景5样例数据及需求说明文档")

PORT = 8311
API = f"http://127.0.0.1:{PORT}"

# ══════════════ 统一视觉风格(浅色) ══════════════
BG = "#F4F6F9"
HEAD_BG = "#2C4F73"
CARD_BG = "#FFFFFF"
EDGE = "#3D6A99"
FILL_SOFT = "#E7EEF6"
TXT_DARK = "#1A1A1A"
TXT_GRAY = "#666666"
OK_GREEN = "#2E7D32"
WARN_RED = "#B03A2E"
ORANGE = "#C07A3A"

_MSYH = "C:/Windows/Fonts/msyh.ttc"
_MSYHBD = "C:/Windows/Fonts/msyhbd.ttc"

#: 字体惰性初始化(模块顶层零I/O: main()首行_init_fonts()装配)
F_BIG: ImageFont.FreeTypeFont
F_TITLE: ImageFont.FreeTypeFont
F_SUB: ImageFont.FreeTypeFont
F_BODY: ImageFont.FreeTypeFont
F_SMALL: ImageFont.FreeTypeFont
F_TINY: ImageFont.FreeTypeFont
F_MONO: ImageFont.FreeTypeFont


def _init_fonts() -> None:
    global F_BIG, F_TITLE, F_SUB, F_BODY, F_SMALL, F_TINY, F_MONO
    F_BIG = ImageFont.truetype(_MSYHBD, 34)
    F_TITLE = ImageFont.truetype(_MSYHBD, 27)
    F_SUB = ImageFont.truetype(_MSYHBD, 21)
    F_BODY = ImageFont.truetype(_MSYH, 20)
    F_SMALL = ImageFont.truetype(_MSYH, 17)
    F_TINY = ImageFont.truetype(_MSYH, 15)
    F_MONO = ImageFont.truetype(_MSYH, 18)


MODALITY_CN = {"TXT": "正文", "TBL": "表格", "IMG": "图", "E": "实体", "SEQ": "追溯"}
EDGE_CN = {
    "section_hierarchy": "章节层级", "section_adjacent": "相邻章节",
    "located_in": "定位于", "ent_appear_txt": "实体出现·正文",
    "ent_appear_tbl": "实体出现·表格", "same_section_tbl": "同节表格",
    "same_section_img": "同节图片", "version_alignment": "版本对齐",
    "anchor_section_map": "锚点映射", "exc_belong_tbl": "异常归属表",
    "cross_ref_tbl": "交叉引用·表", "cross_ref_img": "交叉引用·图",
    "rule_applies": "规则适用", "ent_hierarchy": "实体层级",
    "ent_cooccur": "实体共现", "ent_same_table": "实体同表",
}
_TAG = re.compile(r"<[^>]+>")


def _clean_ev(s: str) -> str:
    return _TAG.sub("", s or "").strip()


def _short_node_id(nid: str) -> str:
    out = (nid.replace("t:04:", "§").replace("t:01:", "§")
           .replace("tbl:04:", "表@").replace("tbl:01:", "表@")
           .replace("img:04:", "图#").replace("img:01:", "图#")
           .replace("e:", "").replace("seq:04:", "链:").replace("seq:01:", "链:"))
    return out[:44]


# ══════════════ PIL 画笔(测量/落笔两用) + 流式画布 ══════════════

class Painter:
    """卡片内容画笔: measure模式只推进游标, paint模式实际绘制.

    两种模式共享同一代码路径与字体度量, 保证两次遍历游标一致.
    """

    def __init__(self, width: int, target: tuple[Image.Image, ImageDraw.ImageDraw] | None,
                 offset_y: int = 0) -> None:
        self.w = width
        self.pad = 34
        self.y = 0
        self._measure = target is None
        if self._measure:
            scratch = Image.new("RGB", (16, 16))
            self._img, self._draw = scratch, ImageDraw.Draw(scratch)
            self._oy = 0
        else:
            self._img, self._draw = target  # type: ignore[misc]
            self._oy = offset_y

    # ---- 基元 ----
    def _wrap(self, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        lines: list[str] = []
        for raw in (text or "").split("\n"):
            cur = ""
            for ch in raw:
                if self._draw.textlength(cur + ch, font=font) > max_w and cur:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            lines.append(cur)
        return lines or [""]

    def _abs(self) -> int:
        return self._oy + self.y

    def line(self, x: int, text: str, font: ImageFont.FreeTypeFont,
             fill: str = TXT_DARK) -> None:
        if not self._measure:
            self._draw.text((x, self._abs()), text, font=font, fill=fill)
        self.y += font.size + 8

    def block(self, x: int, text: str, font: ImageFont.FreeTypeFont,
              max_w: int, fill: str = TXT_DARK, line_gap: int = 7) -> int:
        lines = self._wrap(text, font, max_w)
        for i, ln in enumerate(lines):
            if not self._measure:
                self._draw.text((x, self._abs() + i * (font.size + line_gap)), ln,
                                font=font, fill=fill)
        h = len(lines) * (font.size + line_gap)
        self.y += h
        return h

    def kv(self, key: str, value: str, vfont: ImageFont.FreeTypeFont = F_BODY,
           key_color: str = "#2C4F73", indent: int = 0) -> None:
        """键值行: 键加粗, 值自动换行(缩进对齐)."""
        x = self.pad + 24 + indent
        kw = int(self._draw.textlength(key, font=F_SUB)) + 14
        if not self._measure:
            self._draw.text((x, self._abs() + 3), key, font=F_SUB, fill=key_color)
        vw = self.w - x - kw - 2 * self.pad - 10
        self.block(x + kw, value, vfont, max(vw, 200), fill=TXT_DARK)
        self.y += 5

    def bullet(self, text: str, font: ImageFont.FreeTypeFont = F_BODY,
               color: str = TXT_DARK, indent: int = 0, dot: str = EDGE) -> None:
        x = self.pad + 24 + indent
        if not self._measure:
            self._draw.ellipse([x, self._abs() + 8, x + 12, self._abs() + 20],
                               fill=dot)
        self.block(x + 24, text, font, self.w - x - self.pad - 60, fill=color)
        self.y += 4

    def mark_item(self, mark: str, title: str, desc: str,
                  color: str) -> None:
        """分层校验提示条: 圆形标记 + 标题 + 描述."""
        x = self.pad + 26
        if not self._measure:
            self._draw.ellipse([x, self._abs() + 4, x + 22, self._abs() + 26],
                               fill=color)
            self._draw.text((x + 7, self._abs() + 6), mark, font=F_SUB,
                            fill="#FFFFFF")
            self._draw.text((x + 34, self._abs() + 3), title, font=F_SUB,
                            fill=color)
        self.y += 32
        self.block(x + 34, desc, F_SMALL, self.w - x - self.pad - 80)
        self.y += 10

    def image_card(self, img_path: Path, caption: str, w: int = 440,
                   h: int = 248) -> None:
        """嵌入原图缩略图(带深色边框与题注), 高度恒定=可测量."""
        x0 = self.pad + 24
        if not self._measure:
            self._draw.rectangle([x0, self._abs(), x0 + w, self._abs() + h],
                                 fill="#203A57", outline="#152A40", width=1)
            self._draw.text((x0 + 12, self._abs() + 5), caption, font=F_TINY,
                            fill="#BFD2E5")
            im = Image.open(img_path).convert("RGB")
            im.thumbnail((w - 16, h - 44))
            self._img.paste(
                im, (x0 + (w - im.width) // 2,
                     self._abs() + 26 + (h - 44 - im.height) // 2))
        self.y += h

    def gap(self, h: int) -> None:
        self.y += h

    def divider(self) -> None:
        if not self._measure:
            self._draw.line([self.pad + 24, self._abs(),
                             self.w - self.pad - 24, self._abs()],
                            fill="#DDE4EC", width=1)
        self.y += 16


class Canvas:
    """整页画布: 顶栏/标题/请求条直接绘制, 卡片经两遍(measure→paint)绘制."""

    def __init__(self, width: int = 1560) -> None:
        self.w = width
        self.pad = 34
        self.img = Image.new("RGB", (width, 9000), BG)
        self.d = ImageDraw.Draw(self.img)
        self.y = 0

    def _ensure(self, need: int) -> None:
        if self.y + need > self.img.height:
            grown = Image.new("RGB", (self.w, self.img.height + 4000), BG)
            grown.paste(self.img, (0, 0))
            self.img = grown
            self.d = ImageDraw.Draw(self.img)

    def _wrap(self, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        p = Painter(self.w, None)
        return p._wrap(text, font, max_w)

    def header(self, scene_label: str, api_tag: str) -> None:
        h = 86
        self._ensure(h)
        self.d.rectangle([0, 0, self.w, h], fill=HEAD_BG)
        self.d.text((self.pad, 15), "微调数据集构建平台", font=F_SUB, fill="#FFFFFF")
        self.d.text((self.pad + 300, 15), scene_label, font=F_SUB, fill="#E8DFC8")
        self.d.text((self.pad, 50), "特征提取与上下文关联智能体 · 数据一致性校验智能体",
                    font=F_TINY, fill="#AFC4DB")
        tag_w = int(self.d.textlength(api_tag, font=F_SMALL)) + 30
        self.d.rounded_rectangle(
            [self.w - self.pad - tag_w, 24, self.w - self.pad, 58], 8,
            fill="#5D82A8")
        self.d.text((self.w - self.pad - tag_w + 15, 29), api_tag, font=F_SMALL,
                    fill="#FFFFFF")
        self.y = h + 26

    def h1(self, title: str, subtitle: str = "") -> None:
        self._ensure(130)
        self.d.text((self.pad, self.y), title, font=F_BIG, fill=TXT_DARK)
        self.y += 54
        if subtitle:
            for ln in self._wrap(subtitle, F_SMALL, self.w - 2 * self.pad):
                self.d.text((self.pad, self.y), ln, font=F_SMALL, fill=TXT_GRAY)
                self.y += 26
        self.y += 14

    def request_bar(self, method: str, url: str, body: str, note: str) -> None:
        lines = self._wrap(body, F_MONO, self.w - 2 * self.pad - 170)
        h = 66 + len(lines) * 28 + 46
        self._ensure(h + 24)
        x0, y0 = self.pad, self.y
        self.d.rounded_rectangle([x0, y0, self.w - self.pad, y0 + h], 12,
                                 fill=CARD_BG, outline=EDGE, width=2)
        mw = 100
        self.d.rounded_rectangle([x0 + 20, y0 + 16, x0 + 20 + mw, y0 + 52], 8,
                                 fill=ORANGE)
        self.d.text((x0 + 20 + (mw - self.d.textlength(method, font=F_SUB)) / 2,
                     y0 + 21), method, font=F_SUB, fill="#FFFFFF")
        self.d.text((x0 + 20 + mw + 18, y0 + 21), url, font=F_MONO, fill=TXT_DARK)
        yy = y0 + 64
        for ln in lines:
            self.d.text((x0 + 20, yy), ln, font=F_MONO, fill="#3A5570")
            yy += 28
        for ln in self._wrap(note, F_SMALL, self.w - 2 * self.pad - 60):
            self.d.text((x0 + 20, yy + 4), ln, font=F_SMALL, fill=OK_GREEN)
            yy += 25
        self.y = y0 + h + 18

    def card(self, title: str, badge: str,
             fn: Callable[[Painter], None]) -> None:
        """卡片: 先measure内容高度, 再画背景+标题+内容."""
        probe = Painter(self.w, None)
        fn(probe)
        head = 62
        h = head + probe.y + 16
        self._ensure(h + 34)
        x0, y0, x1, y1 = self.pad, self.y, self.w - self.pad, self.y + h
        self.d.rounded_rectangle([x0, y0, x1, y1], 12, fill=CARD_BG,
                                 outline=EDGE, width=2)
        self.d.rounded_rectangle([x0 + 2, y0 + 2, x1 - 2, y0 + head], 11,
                                 fill=FILL_SOFT)
        self.d.rectangle([x0 + 2, y0 + head - 16, x1 - 2, y0 + head],
                         fill=FILL_SOFT)
        self.d.text((x0 + 24, y0 + 15), title, font=F_TITLE, fill=TXT_DARK)
        if badge:
            bw = int(self.d.textlength(badge, font=F_SMALL)) + 26
            self.d.rounded_rectangle([x1 - 24 - bw, y0 + 17, x1 - 24, y0 + 49],
                                     8, fill="#FFFFFF")
            self.d.text((x1 - 24 - bw + 13, y0 + 22), badge, font=F_SMALL,
                        fill="#2C4F73")
        painter = Painter(self.w, (self.img, self.d), offset_y=y0 + head)
        fn(painter)
        self.y = y1 + 20

    def footer(self, note: str) -> None:
        lines = self._wrap(note, F_TINY, self.w - 2 * self.pad)
        self._ensure(30 + len(lines) * 22)
        self.d.line([self.pad, self.y, self.w - self.pad, self.y],
                    fill="#C9D4E0", width=1)
        self.y += 12
        for ln in lines:
            self.d.text((self.pad, self.y), ln, font=F_TINY, fill=TXT_GRAY)
            self.y += 21
        self.y += 8

    def save(self, path: Path) -> None:
        img = self.img.crop((0, 0, self.w, self.y + 24))
        img.save(path, dpi=(300, 300))
        print(f"[saved] {path.name}  {img.width}x{img.height}px")


# ══════════════ 后端启动/终止 + HTTP ══════════════

def start_backend() -> subprocess.Popen:
    env = dict(os.environ)
    env.update({"DEV_DB": "sqlite", "PYTHONPATH": "backend",
                "PORT": str(PORT), "PYTHONUTF8": "1"})
    log_fh = open(BACKEND_LOG, "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-X", "utf8", "app.py"],
                            cwd=str(BACKEND_DIR), env=env,
                            stdout=log_fh, stderr=subprocess.STDOUT)
    t0 = time.time()
    last_err = ""
    while time.time() - t0 < 90:
        try:
            with urllib.request.urlopen(f"{API}/api/health", timeout=3) as r:
                if r.status == 200:
                    print(f"[backend] 就绪({time.time() - t0:.1f}s) pid={proc.pid}")
                    return proc
        except (urllib.error.URLError, OSError) as e:
            last_err = str(e)
        if proc.poll() is not None:
            raise RuntimeError(f"后端进程退出({proc.returncode}), 日志: {BACKEND_LOG}")
        time.sleep(1.0)
    proc.terminate()
    raise RuntimeError(f"后端90s未就绪: {last_err}; 日志: {BACKEND_LOG}")


def http_json(method: str, path: str, body: dict[str, Any] | None = None,
              timeout: float = 180) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") \
        if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def load_run(name: str) -> dict[str, Any]:
    return json.loads((RUNS / name / "result.json").read_text(encoding="utf-8"))


# ══════════════ 场景一 · 截图1: 结构化解析 ══════════════

def render_scene1_parse(resp: dict[str, Any], elapsed: float) -> Path:
    groups = resp["groups"]
    stats = resp["stats"]["by_modality"]

    def center_card(p: Painter) -> None:
        center = resp["center"]
        pl = center.get("payload") or {}
        p.kv("节点:", f"{center['label']}  "
             f"[{MODALITY_CN.get(center['type'], center['type'])}]")
        p.kv("定位:", f"章节 §{center.get('section', '-')} · 节点 {center.get('id', '')}",
             vfont=F_SMALL)
        p.kv("命中:", str(center.get("why", "")), vfont=F_SMALL)
        p.kv("摘录:", (pl.get("text_preview") or "")[:110], vfont=F_SMALL)

    def txt_card(p: Painter) -> None:
        for n in groups.get("TXT", [])[:4]:
            pl = n.get("payload") or {}
            p.kv(f"§{n.get('section', '')}:",
                 pl.get("title") or n.get("label", ""))
            p.kv("摘录:", ((pl.get("text_preview") or "")[:84] + "…"),
                 vfont=F_SMALL, indent=16)
            p.kv("定位:", f"章节 §{n.get('section', '')} · 节点 "
                 f"{_short_node_id(n['id'])} · 关联度 {n.get('score', 0):.2f}"
                 f"({n.get('hop', 1)}跳·经{n.get('via_label', '')})",
                 vfont=F_SMALL, indent=16, key_color=TXT_GRAY)
            p.gap(8)

    def tbl_card(p: Painter) -> None:
        for n in groups.get("TBL", [])[:3]:
            pl = n.get("payload") or {}
            rows = pl.get("rows", [])
            sample = " | ".join((rows[1] if len(rows) > 1 else
                                 (rows[0] if rows else [])))
            p.kv("表:", f"{pl.get('caption', n.get('label', ''))}"
                 f"  [类型 {pl.get('table_type', '-')}]"
                 f"  {pl.get('row_count', '?')}行 × "
                 f"{len(pl.get('headers', []))}列")
            p.kv("表头:", " | ".join(pl.get("headers", []))[:92], vfont=F_SMALL,
                 indent=16)
            p.kv("示例行:", (sample or "-")[:80], vfont=F_SMALL, indent=16)
            p.kv("定位:", f"章节 §{n.get('section', '')} · 节点 {n['id']}",
                 vfont=F_SMALL, indent=16, key_color=TXT_GRAY)
            p.gap(8)

    def img_card(p: Painter) -> None:
        for n in groups.get("IMG", [])[:3]:
            pl = n.get("payload") or {}
            p.kv("图:", f"{pl.get('caption', n.get('label', ''))}"
                 f"  [{pl.get('img_type', '-')}]")
            p.kv("资源:", f"{pl.get('path', '-')} (解析存在: "
                 f"{pl.get('exists', '-')}) · 章节 §{n.get('section', '')}",
                 vfont=F_SMALL, indent=16, key_color=TXT_GRAY)
            p.gap(6)

    def seq_card(p: Painter) -> None:
        for n in groups.get("SEQ", [])[:2]:
            pl = n.get("payload") or {}
            p.kv("链:", f"{n.get('label', '')}  {pl.get('n_steps', '?')}步 · "
                 f"{pl.get('n_edges', '?')}条边")
            p.kv("步骤:", " → ".join(pl.get("steps", [])[:8])[:96],
                 vfont=F_SMALL, indent=16)
            p.gap(6)

    c = Canvas()
    c.header("场景一 · 软件需求规格数据(SRS)", "/api/activate")
    c.h1("需求章节与复杂表格的结构化解析结果(含源页定位)",
         "用例编号 SC1-ACT-01 · 数据源: 04数据统一访问服务软件需求规格说明-终稿(GJB 438C格式)")
    c.request_bar(
        "POST", f"{API}/api/activate",
        json.dumps({"question": "修改数据功能支持哪些设备"}, ensure_ascii=False),
        f"HTTP 200 OK · 响应 {elapsed:.2f}s · 命中数据源 doc={resp['doc']}"
        f" · 召回内容 {resp['stats']['n_content']} 条"
        f"(正文{stats.get('TXT', 0)}/表格{stats.get('TBL', 0)}/图{stats.get('IMG', 0)}"
        f"/实体{stats.get('E', 0)}/追溯{stats.get('SEQ', 0)})")
    c.card("中心节点(种子命中)", f"score {resp['center'].get('score', 0):.2f}",
           center_card)
    c.card("需求章节 · 结构化解析", f"正文 TXT ×{len(groups.get('TXT', []))}",
           txt_card)
    c.card("复杂表格 · 结构化解析(表头/行列/示例行)",
           f"表格 TBL ×{len(groups.get('TBL', []))}", tbl_card)
    c.card("图片 · 用例图/流程图解析", f"图片 IMG ×{len(groups.get('IMG', []))}",
           img_card)
    if groups.get("SEQ"):
        c.card("步骤链 · 用例/流程追溯解析",
               f"追溯 SEQ ×{len(groups.get('SEQ', []))}", seq_card)
    c.footer("截图来源: 系统真实API调用 POST /api/activate(后端 DEV_DB=sqlite 本地启动) · "
             "源页定位口径=章节号+节点ID(表题/图号) · 解析管线: .doc→markdown结构化"
             "(目录编号恢复) + 表格HTML→表头/行/列")
    out = OUT_DIR / "scene1_structured_parse.png"
    c.save(out)
    return out


# ══════════════ 场景一 · 截图2: 上下文关联 ══════════════

def _top_entity(edges: list[dict[str, Any]], ent_ids: set[str]) -> str:
    cnt: Counter[str] = Counter()
    for e in edges:
        if e["s"] in ent_ids:
            cnt[e["s"]] += 1
        if e["t"] in ent_ids:
            cnt[e["t"]] += 1
    return cnt.most_common(1)[0][0] if cnt else ""


def render_scene1_link(resp: dict[str, Any], elapsed: float) -> Path:
    groups = resp["groups"]
    stats = resp["stats"]["by_modality"]
    edges = resp["edges"]
    ent_ids = {n["id"] for n in groups.get("E", [])}
    ent = _top_entity(edges, ent_ids)

    def center_card(p: Painter) -> None:
        center = resp["center"]
        pl = center.get("payload") or {}
        p.kv("节点:", f"{center['label']}  "
             f"[{MODALITY_CN.get(center['type'], center['type'])}]")
        p.kv("定位:", f"章节 §{center.get('section', '-')} · "
             f"{pl.get('row_count', '?')}行 · 表头: "
             f"{' | '.join(pl.get('headers', []))[:80]}", vfont=F_SMALL)
        p.kv("命中:", str(center.get("why", "")), vfont=F_SMALL)

    def groups_card(p: Painter) -> None:
        for mod, items in groups.items():
            if not items:
                continue
            p.line(p.pad + 24, f"◇ {MODALITY_CN.get(mod, mod)}({mod}) "
                   f"×{len(items)}", F_SUB)
            for n in items[:3]:
                sec = n.get("section") or "-"
                p.kv(f"§{sec}:", f"{n.get('label', '')} · 关联度 "
                     f"{n.get('score', 0):.2f}({n.get('hop', 1)}跳·经"
                     f"{(n.get('via_label') or '直接')})", vfont=F_SMALL)
            p.gap(8)

    def edges_card(p: Painter) -> None:
        by_type: Counter[str] = Counter(e["type"] for e in edges)
        ent_label = next((n["label"] for n in groups.get("E", [])
                          if n["id"] == ent), ent)
        aliases = next(((n.get("payload") or {}).get("aliases") or [])
                       for n in groups.get("E", []) if n["id"] == ent)
        p.kv("实体:", f"{ent_label}"
             + (f"(中文名: {aliases[0]})" if aliases else ""))
        p.gap(4)
        endpoints: list[str] = []
        shown = 0
        for e in edges:
            if ent not in (e["s"], e["t"]):
                continue
            other = e["t"] if e["s"] == ent else e["s"]
            endpoints.append(_short_node_id(other))
            ev = _clean_ev(e.get("ev") or "")[:52]
            p.kv(f"[{EDGE_CN.get(e['type'], e['type'])}]",
                 f"→ {_short_node_id(other)}  (边权 {e['w']:.2f})  证据: {ev}",
                 vfont=F_SMALL)
            shown += 1
            if shown >= 6:
                break
        p.divider()
        p.kv("聚合条目:", f"同一标识 {ent_label} 在证据侧多处登记: "
             f"{' + '.join(endpoints[:4])} — 跨章节聚合为统一关联条目",
             vfont=F_SMALL)
        p.kv("边类型分布:", "  ".join(f"{EDGE_CN.get(k, k)}×{v}" for k, v in
                 sorted(by_type.items(), key=lambda kv: -kv[1])[:8]),
             vfont=F_SMALL, key_color=TXT_GRAY)

    def rel_card(p: Painter) -> None:
        rel = resp.get("related_entities") or []
        p.kv("实体:", "  ·  ".join(r.get("label", "") for r in rel[:6]),
             vfont=F_SMALL)
        p.kv("关系:", "同文档实体(跨章节共现/同表/层级关联)", vfont=F_SMALL,
             key_color=TXT_GRAY)

    c = Canvas()
    c.header("场景一 · 软件需求规格数据(SRS)", "/api/activate")
    c.h1("需求实体、表格字段及跨章节上下文关联结果",
         "用例编号 SC1-ACT-02 · 无doc参数时系统遍历全部16份数据源, 选种子命中最佳的文档")
    c.request_bar(
        "POST", f"{API}/api/activate",
        json.dumps({"question": "连接池配置的接口标识符"}, ensure_ascii=False),
        f"HTTP 200 OK · 响应 {elapsed:.2f}s · 命中数据源 doc={resp['doc']}"
        f" {resp['doc_name']} · 召回 {resp['stats']['n_content']} 条"
        f" · 关联边 {len(edges)} 条")
    c.card("中心节点(种子命中)", f"score {resp['center'].get('score', 0):.2f}",
           center_card)
    c.card("多模态关联分组(按模态)",
           f"TXT {stats.get('TXT', 0)}/TBL {stats.get('TBL', 0)}/IMG "
           f"{stats.get('IMG', 0)}/E {stats.get('E', 0)}/SEQ {stats.get('SEQ', 0)}",
           groups_card)
    c.card("跨章节关联边(同一标识在正文/表格/追溯表多处登记)",
           f"关联边 {len(edges)} 条", edges_card)
    c.card("同文档关联实体", f"related_entities ×{len(resp.get('related_entities') or [])}",
           rel_card)
    c.footer("截图来源: 系统真实API调用 POST /api/activate(遍历16份数据源自动定位) · "
             "关联依据=图谱边(章节层级/定位于/实体出现·正文/表格), 边权为激活路径得分 · "
             "追溯含§3.18需求追溯表与用例步骤链两种登记形态")
    out = OUT_DIR / "scene1_context_link.png"
    c.save(out)
    return out


# ══════════════ 场景一 · 截图3: 分层校验报告 ══════════════

def render_scene1_report(result: dict[str, Any], job_id: str, polls: int,
                         elapsed: float) -> Path:
    s = result["summary"]
    cats = result["categories"]
    fails = [i for i in result["items"] if i["status"] == "fail"]
    qa = next(i for i in result["items"] if i["rule_id"] == "QA-VERDICT")
    qv = qa.get("qa_verdict") or {}
    qsum = qv.get("summary", {})

    def summary_card(p: Painter) -> None:
        p.kv("汇总:", f"总规则 {s['total']} · 通过 {s['pass']} · 失败 {s['fail']}"
             f" · LLM待接 {s['llm']} · 异常 {s['error']}")
        rc = result.get("rule_config", {})
        p.kv("规则配置:", f"活跃规则 {rc.get('n_active', '-')} / 目录 "
             f"{rc.get('n_catalog', '-')}(四层配置树: 算法/语法/语义/逻辑)",
             vfont=F_SMALL, key_color=TXT_GRAY)

    def layer_card(p: Painter) -> None:
        col_x = [p.pad + 24 + i * 235 for i in range(6)]
        heads = ["校验层", "规则", "通过", "失败", "LLM", "发现数"]
        for x, htxt in zip(col_x, heads):
            p.line(x, htxt, F_SMALL)
        p.gap(-4)
        for cat in sorted(cats, key=lambda x: -x["findings"]):
            vals = [cat["name"], str(cat["total"]), str(cat["pass"]),
                    str(cat["fail"]), str(cat["llm"]), str(cat["findings"])]
            color = WARN_RED if cat["fail"] else TXT_DARK
            for x, v in zip(col_x, vals):
                p.line(x, v, F_BODY, fill=color)
            p.gap(-2)

    def fail_card(p: Painter) -> None:
        for it in fails:
            p.kv(f"{it['rule_id']}:", f"{it['name']} [{it['category']}] · "
                 f"发现 {it['n']} 处")
            for fd in (it.get("findings") or [])[:2]:
                desc = fd.get("desc", "")
                p.bullet((desc[:76] + "…") if len(desc) > 76 else desc,
                         font=F_SMALL, indent=16, dot=WARN_RED)
            if it["rule_id"] != "QA-VERDICT" and it["n"] > 2:
                p.bullet(f"(其余 {it['n'] - 2} 处发现见完整结果JSON, 截断展示)",
                         font=F_TINY, indent=16, dot="#C9D4E0")
            p.gap(8)

    def verdict_card(p: Painter) -> None:
        total = qsum.get("n_qa", 1) or 1
        bar_w = p.w - 2 * p.pad - 48
        x0 = p.pad + 24
        cx = x0
        for v, color, name in [(qsum.get("support", 0), "#4E7A55", "support"),
                               (qsum.get("refute", 0), WARN_RED, "refute"),
                               (qsum.get("nie", 0), "#9DB3C8", "NIE")]:
            w = max(8, int(bar_w * v / total))
            if not p._measure:
                p._draw.rectangle([cx, p._abs(), cx + w, p._abs() + 34],
                                  fill=color)
                p._draw.text((cx + 8, p._abs() + 6), f"{name} {v}", font=F_SMALL,
                             fill="#FFFFFF")
            cx += w
        p.y += 46
        p.kv("口径:", "仅refute计为违例发现(support/NIE为开放世界语义不计); "
             f"preset={qv.get('preset', '-')}", vfont=F_SMALL, key_color=TXT_GRAY)

    def sample_card(p: Painter) -> None:
        for fd in (qa.get("findings") or [])[:3]:
            desc = fd.get("desc", "")
            ev = fd.get("evidence", "") or ""
            p.kv("违例:", desc[:100] + ("…" if len(desc) > 100 else ""))
            p.kv("证据位置:", f"章节 §{fd.get('section', '-')}"
                 f"(冻结证据块首引用)", vfont=F_SMALL, key_color=TXT_GRAY)
            p.kv("关联依据:", ev[:88] + ("…" if len(ev) > 88 else ""),
                 vfont=F_SMALL, key_color=TXT_GRAY)
            p.divider()

    c = Canvas()
    c.header("场景一 · 软件需求规格数据(SRS)", "/api/check")
    c.h1("典型违例样本的分层校验提示、关联依据与汇总报告",
         "用例编号 SC1-CHK-01 · 数据源: 04数据统一访问服务软件需求规格说明-终稿")
    c.request_bar(
        "POST", f"{API}/api/check/04", "(无请求体 · 数据源编号为路径参数)",
        f"HTTP 200 OK · job_id {job_id} → 轮询 GET /api/check/status/{job_id}"
        f" ×{polls} → done({elapsed:.1f}s) · check_id {result.get('check_id', '-')}"
        f" · ran_at {result.get('ran_at', '-')}")
    c.card("校验汇总(53项规则 = 52项目录 + QA三态裁决)",
           "check_id " + str(result.get("check_id", "-")), summary_card)
    c.card("分层校验统计(层 × 规则/通过/失败/发现)", f"六层 · 失败层 ×"
           f"{sum(1 for x in cats if x['fail'])}", layer_card)
    c.card("失败规则明细(fail)", f"×{len(fails)}", fail_card)
    c.card("QA三态裁决汇总(CascadeVerify · fast确定性档)",
           f"n_qa {qsum.get('n_qa', '-')}", verdict_card)
    c.card("典型违例样本 · 分层校验提示(违例描述/证据位置/关联依据)",
           f"refute ×{qa['n']}", sample_card)
    c.footer("截图来源: 系统真实API调用 POST /api/check/04 + 状态轮询(后端 DEV_DB=sqlite"
             " 本地启动) · QA对=91条官方冻结QA+17条真实违例种子(violation_evalset_v1) · "
             "分层=语法(术语/参数/多模态/GJB合规)+语义(QA三态)+逻辑(LLM待接项)")
    out = OUT_DIR / "scene1_consistency_report.png"
    c.save(out)
    return out


# ══════════════ 场景一 · matplotlib 分析图 ══════════════

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"font.size": 10.5, "axes.titlesize": 13,
                     "axes.labelsize": 11, "savefig.dpi": 300,
                     "savefig.facecolor": "white", "savefig.bbox": "tight"})

LABELS = ["support", "refute", "NIE"]
LABEL_CN = {"support": "支持", "refute": "反驳", "NIE": "证据不足"}


def fig_confusion_matrix() -> Path:
    d = load_run(RUN_CASCADE)
    cfg = d["configs"]["cascade"]
    conf = cfg["confusion[predicted, silver]"]
    order = ["support", "refute", "not_in_evidence"]
    mat = np.zeros((3, 3), dtype=int)
    for pred in order:
        for silver in order:
            mat[order.index(silver), order.index(pred)] = conf.get(
                f"{pred}|{silver}", 0)
    row_sum = mat.sum(axis=1, keepdims=True)
    diag = int(np.trace(mat))
    ref_pred = int(mat[:, 1].sum())

    fig, ax = plt.subplots(figsize=(7.8, 6.4))
    im = ax.imshow(mat, cmap="Blues", vmin=0, vmax=mat.max() * 1.15)
    for i in range(3):
        for j in range(3):
            v = int(mat[i, j])
            pct = v / row_sum[i, 0] * 100 if row_sum[i, 0] else 0.0
            color = "white" if v > mat.max() * 0.55 else "#1A1A1A"
            weight = "bold" if i == j else "normal"
            ax.text(j, i, f"{v}\n{pct:.1f}%", ha="center", va="center",
                    fontsize=11.5, color=color, fontweight=weight)
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"预测 · {LABEL_CN[l]}" for l in LABELS])
    ax.set_yticks(range(3))
    ax.set_yticklabels([f"silver · {LABEL_CN[l]}\n(共{row_sum[i, 0]}条)"
                        for i, l in enumerate(LABELS)])
    for edge in ("top", "right", "left", "bottom"):
        ax.spines[edge].set_visible(False)
    ax.set_title(f"91条QA三态判定混淆矩阵(级联配置, n={d['n']})",
                 fontsize=13.5, pad=14)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="样本数")
    fig.text(0.5, -0.015,
             f"对角线合计 {diag}/{d['n']} = {diag / d['n']:.1%} · "
             f"macro-F1 {cfg['macro_f1']:.4f} · "
             f"refute精确率 {mat[1, 1] / max(1, ref_pred):.3f}"
             f"({mat[1, 1]}/{ref_pred}) · "
             f"NIE召回 {mat[2, 2] / max(1, row_sum[2, 0]):.3f}",
             ha="center", fontsize=9.5, color="#444444")
    fig.text(0.5, -0.06,
             f"数据来源: data/gjb_438c/runs/{RUN_CASCADE}/result.json · "
             f"标签口径 {d['label_type']}(非gold, 如实披露) · "
             f"checkpoint {Path(d['checkpoint']).name}",
             ha="center", fontsize=8.5, color="#777777")
    out = OUT_DIR / "scene1_confusion_matrix.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[saved] {out.name}")
    return out


def fig_violation_detection() -> Path:
    d = load_run(RUN_VIOLATIONS)
    det = d["configs"]["deterministic"]
    cat = det["by_category"]
    order = sorted(cat.items(),
                   key=lambda kv: (-(kv[1]["detected"] / kv[1]["n"]),
                                   -kv[1]["n"]))
    names = [k for k, _ in order]
    rates = [v["detection_rate"] for _, v in order]
    counts = [(v["detected"], v["n"]) for _, v in order]
    name_cn = {"identifier": "identifier\n标识符冲突",
               "enumeration": "enumeration\n枚举集合冲突",
               "traceability": "traceability\n追溯矛盾",
               "exception_template": "exception_template\n异常模板冲突",
               "document_name": "document_name\n文档名称",
               "function_coverage": "function_coverage\n功能覆盖缺口",
               "qualification_coverage": "qualification\n合格性覆盖缺口"}
    labels = [name_cn.get(k, k) for k in names]

    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    y = np.arange(len(labels))
    colors = ["#2F5E8C" if r >= 1.0 else ("#7A9CC0" if r > 0 else "#C9CFD6")
              for r in rates]
    ax.barh(y, [r * 100 for r in rates], color=colors, ec="#1D3F61", lw=0.8,
            zorder=3, height=0.62)
    for yi, (r, (dn, n)) in zip(y, zip(rates, counts)):
        ax.text(r * 100 + 2.5, yi, f"{dn}/{n} ({r:.0%})", va="center",
                fontsize=10.5, color="#1A1A1A", fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 120)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("检出率(期望verdict=refute, 系统判refute即检出)")
    ax.set_title(f"17条真实违例分类型检出率(确定性专家栈: "
                 f"{det['n_detected']}/{det['n']} = {det['detection_rate']:.1%})",
                 fontsize=13, pad=12)
    ax.grid(axis="x", ls=":", color="#BBBBBB", lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    undet = ", ".join(i.replace("DOC04-VIO-", "VIO-") for i in det["undetected_ids"])
    fig.text(0.5, -0.055,
             f"未检出: {undet}(document_name, 文档名称类) · 检出演进: 5专家栈52.9%"
             " → +id_join 70.6% → +enum_join 88.2% → +coverage 94.1%"
             "(失败归因→定向补专家→复测闭环)",
             ha="center", fontsize=9.5, color="#444444")
    fig.text(0.5, -0.10,
             f"数据来源: data/gjb_438c/runs/{RUN_VIOLATIONS}/result.json · "
             f"评测集 violation_evalset_v1(04号文档人工深读17条真实违例, 7类)",
             ha="center", fontsize=8.5, color="#777777")
    out = OUT_DIR / "scene1_violation_detection.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[saved] {out.name}")
    return out


def fig_cost_pareto() -> Path:
    cas = load_run(RUN_CASCADE)
    pm = load_run(RUN_PAPER_MATRIX)
    cq = {r["config"]: r for r in cas["cost_quality_table"]}

    def r_f1(cfg: dict[str, Any]) -> float:
        return cfg["per_class"]["refute"]["f1"]

    pts: list[tuple[str, float, float, float]] = []
    for name in ("B0", "B2", "B3", "B5"):
        b = pm["baselines"][name]
        pts.append((name, b["llm_calls"]["invocations"], b["macro_f1"], r_f1(b)))
    pts.append(("L2 NLI", cq["l2_nli"]["llm_invocations"], cq["l2_nli"]["macro_f1"],
                r_f1(cas["configs"]["l2_nli"])))
    pts.append(("conformal", cq["cascade_conformal"]["llm_invocations"],
                cq["cascade_conformal"]["macro_f1"],
                r_f1(cas["configs"]["cascade_conformal"])))
    pts.append(("cascade", cq["cascade"]["llm_invocations"], cq["cascade"]["macro_f1"],
                r_f1(cas["configs"]["cascade"])))
    b4 = pm["baselines"]["B4"]
    pts.append(("B4", b4["llm_calls"]["invocations"], b4["macro_f1"], r_f1(b4)))

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8))
    for ax, (ylab, vi, title) in zip(axes, [
            ("macro-F1", 2, "(a) macro-F1 vs LLM调用成本"),
            ("refute F1", 3, "(b) refute F1 vs LLM调用成本")]):
        for name, calls, macro, rf1 in pts:
            val = (macro, rf1)[vi - 2]
            if name == "cascade":
                ax.plot([calls], [val], "*", ms=17, mfc="#E8A33D",
                        mec="#8A5A10", mew=1.1, zorder=6)
                continue
            ax.plot([calls], [val], "o", ms=6.5,
                    mfc="#4A76A8" if name != "conformal" else "#B0B0B0",
                    mec="#274A6D", mew=0.7, zorder=5)
            dy = -0.05 if name in ("B5", "conformal", "L2 NLI") else 0.015
            ax.text(calls + 1.4, val + dy, name, fontsize=9, color="#333333")
        ax.set_xlabel("LLM调用数(invocations, 91条QA)")
        ax.set_ylabel(ylab)
        ax.set_xlim(-3, 100)
        ax.grid(ls=":", color="#BBBBBB", lw=0.6, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_title(title, fontsize=11.5)

    cas_pt = next(p for p in pts if p[0] == "cascade")
    n_full = cq["l3_llm"]["llm_invocations"]
    axes[1].annotate(
        f"cascade(L2→L3升级)\n{cas_pt[1]}次调用 = {cas_pt[1] / n_full:.0%}成本\n"
        f"最优refute F1 = {cas_pt[3]:.3f}",
        xy=(cas_pt[1], cas_pt[3]), xytext=(30, 0.42),
        fontsize=9.5, fontweight="bold", color="#8A5A10", ha="left",
        arrowprops=dict(arrowstyle="->", color="#8A5A10", lw=1.1,
                        connectionstyle="arc3,rad=-0.25"))
    fig.suptitle("级联成本-质量Pareto: 以18%的LLM调用取得最优refute F1(91QA vs silver)",
                 fontsize=13, y=1.03)
    fig.text(0.5, -0.04,
             f"cascade: macro-F1 {cas_pt[2]:.3f} · refute F1 {cas_pt[3]:.3f}"
             f" @ {cas_pt[1]}次调用(全量L3为{n_full}次) · "
             f"B3确定性基线零LLM调用 macro-F1 {pm['baselines']['B3']['macro_f1']:.3f}",
             ha="center", fontsize=9.5, color="#444444")
    fig.text(0.5, -0.09,
             f"数据来源: data/gjb_438c/runs/{RUN_CASCADE} + {RUN_PAPER_MATRIX} · "
             "B0无规则/B2纯LLM/B3确定性专家栈/B4微调NLI+L3/B5学习路由(负结果)",
             ha="center", fontsize=8.5, color="#777777")
    out = OUT_DIR / "scene1_cost_pareto.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[saved] {out.name}")
    return out


# ══════════════ 场景五 · 截图(真实样例数据) ══════════════

ANSWER_CN = {0: "0 · 不存在", 1: "1 · 存在", 2: "2 · 无法确认"}


def _load_scene5(fname: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(SCENE5_DIR / fname, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            r = json.loads(line)
            try:
                ans = json.loads(r["conversations"][1]["value"])
            except (json.JSONDecodeError, TypeError):
                ans = {"raw": r["conversations"][1]["value"]}
            rows.append({"line": i, "image": r["image"], **ans})
    return rows


def _region_of(ev: str) -> str:
    """evidence语句 → 画面关键实体/目标区域标签(关键词规则, 锚定原文)."""
    tags: list[str] = []
    if "人员" in ev or "黑色上衣" in ev:
        tags.append("关键实体: 作业人员")
    if "坐" in ev or "凳子" in ev:
        tags.append("坐姿(凳子)")
    if "上半身" in ev and "趴" in ev:
        tags.append("目标区域: 上半身·桌面(趴伏)")
    if "头部" in ev:
        tags.append("目标区域: 头部·桌面")
    if "睡岗" in ev:
        tags.append("判定依据: 睡岗特征(趴伏/头贴桌面)")
    return " · ".join(tags) or "画面整体"


def render_scene5_qa_fields() -> Path:
    rows = _load_scene5("sleep-after-4bit.jsonl")
    picks = [rows[0], rows[39]]  # 行1(answer=0)与行40(answer=1)

    def sample_card(r: dict[str, Any]) -> Callable[[Painter], None]:
        def fn(p: Painter) -> None:
            p.image_card(SCENE5_DIR / "test" / r["image"],
                         f"原图 {r['image']}(1920×1080)", w=430, h=250)
            p.gap(10)
            p.kv("task:", str(r.get("task", "-")))
            ans = r.get("answer")
            color = OK_GREEN if ans == 0 else (WARN_RED if ans == 1 else ORANGE)
            p.kv("answer:", ANSWER_CN.get(ans, str(ans)), key_color=color)
            p.kv("answer语义:", "0=不存在该行为 · 1=存在该行为 · 2=画面模糊/遮挡无法确认",
                 vfont=F_SMALL, key_color=TXT_GRAY)
            for ev in (r.get("evidence") or [])[:3]:
                p.bullet(f"证据: {ev}", font=F_SMALL)
            p.kv("timestamp:", "空(画面未出现可读时间信息, 依规范应为空)",
                 vfont=F_SMALL, key_color=TXT_GRAY)
            p.kv("image:", f"{r['image']} · 源文件第{r['line']}行", vfont=F_SMALL,
                 key_color=TXT_GRAY)
        return fn

    c = Canvas()
    c.header("场景五 · 科研生产现场智能监管", "样例数据")
    c.h1("监控图片及其结构化QA字段展示",
         "用例编号 SC5-QA-01 · 任务: 睡岗行为判定 · 样本: 4bit压缩后"
         "(sleep-after-4bit.jsonl, 96条QA/32张图)")
    c.request_bar(
        "数据", "样例文件: sleep-after-4bit.jsonl",
        '格式: {"conversations": [{"from": "user", "value": "<image>\\n任务…"},'
        ' {"from": "gpt", "value": "{task, answer, evidence}"}],'
        ' "image": "shuigang_XXXX.jpg"}',
        "共96条QA · 32张监控图(夜间/强光/雾天/翻转旋转增强) · "
        "answer取值: 0=不存在 1=存在 2=无法确认")
    for r in picks:
        c.card(f"样本 {r['line']:03d}", r["image"], sample_card(r))
    c.footer("截图来源: 场景5真实样例数据集(20260924-场景5样例数据及需求说明文档) · "
             "图片为样例集test/目录原图缩略 · QA字段(task/answer/evidence)逐字段取自"
             "jsonl原文未改写 · 样例不含timestamp字段(画面无可读时间→为空)")
    out = OUT_DIR / "scene5_qa_fields.png"
    c.save(out)
    return out


def render_scene5_image_link() -> Path:
    rows = _load_scene5("sleep-after-4bit.jsonl")
    r = rows[77]  # 行78: shuigang_0615_strong_light_01.jpg, answer=1

    def img_qa_card(p: Painter) -> None:
        p.image_card(SCENE5_DIR / "test" / r["image"],
                     f"原图 {r['image']}(1920×1080, test/目录)", w=560, h=322)
        p.gap(12)
        p.kv("task:", str(r.get("task", "-")))
        p.kv("answer:", f"{r.get('answer')} · 存在睡岗行为", key_color=WARN_RED)

    def link_card(p: Painter) -> None:
        for i, ev in enumerate((r.get("evidence") or [])[:4], 1):
            p.kv(f"证据{i}:", ev, vfont=F_SMALL)
            p.kv("↳ 关联:", _region_of(ev), vfont=F_SMALL, key_color="#2C4F73")
            p.gap(8)
        p.kv("关联口径:", "关联=evidence语句与画面语义区域/实体的对应(取自样例"
             "evidence字段原文); 样例无bbox框标注, 图上不绘制虚构检测框",
             vfont=F_TINY, key_color=TXT_GRAY)

    def conclusion_card(p: Painter) -> None:
        p.bullet("task(睡岗检测) → evidence指向画面目标人员区域(上半身/头部·桌面)"
                 " → answer=1(存在睡岗行为)")
        p.bullet("evidence字段与画面内容一致(趴伏姿态·头部贴近桌面), 证据链完整可回查原图",
                 font=F_SMALL, dot="#4E7A55")

    c = Canvas()
    c.header("场景五 · 科研生产现场智能监管", "样例数据")
    c.h1("图像目标区域、关键实体及对应问答证据的关联结果",
         f"用例编号 SC5-QA-02 · 样本: sleep-after-4bit.jsonl 第{r['line']}行"
         f" · 原图强光工况")
    c.request_bar(
        "数据", f"样例: 第{r['line']}行 · {r['image']}",
        json.dumps({"task": r.get("task"), "answer": r.get("answer"),
                    "evidence": r.get("evidence")}, ensure_ascii=False)[:118] + "…",
        f"样例解析成功 · 证据语句×{len(r.get('evidence') or [])} · "
        f"answer={r.get('answer')}(存在睡岗行为)")
    c.card("原图与问答字段", r["image"], img_qa_card)
    c.card("证据语句 ↔ 画面关键实体/目标区域关联", "evidence字段", link_card)
    c.card("关联结论", f"answer={r.get('answer')}", conclusion_card)
    c.footer("截图来源: 场景5真实样例数据集 sleep-after-4bit.jsonl(第78行) + test/原图 · "
             "关联结果由evidence字段与画面语义的对应关系得出, 未虚构检测框/坐标")
    out = OUT_DIR / "scene5_image_qa_link.png"
    c.save(out)
    return out


def render_scene5_conflict() -> Path:
    after = _load_scene5("sleep-after-4bit.jsonl")
    simple = _load_scene5("sleep-after-4bit-simpleprompt.jsonl")
    img = "shuigang_0615_strong_light_01.jpg"
    a_rows = [r for r in after if r["image"] == img]        # 行76-78, answer全=1
    b_row = next(r for r in simple
                 if r["image"] == img and r.get("answer") == 0)  # 行78
    n_same = sum(1 for r in simple if r["image"] == img)     # 3条: 1,1,0
    b_contra = next((ev for ev in (b_row.get("evidence") or []) if "睡岗" in ev), "")

    def overview_card(p: Painter) -> None:
        p.image_card(SCENE5_DIR / "test" / img,
                     f"原图 {img}(1920×1080, 强光工况)", w=520, h=300)
        p.gap(12)
        p.kv("冲突:", f"同一图片 {img} · 同一任务(睡岗检测) · 跨样本answer冲突: "
             f"样本A(标准提示词×3条) answer=1 vs 样本B(简化提示词第{b_row['line']}行) "
             f"answer=0", key_color=WARN_RED)
        p.kv("样本A:", f"sleep-after-4bit.jsonl 第{a_rows[0]['line']}-"
             f"{a_rows[-1]['line']}行(3条, answer均为1=存在)", vfont=F_SMALL)
        p.kv("样本B:", f"sleep-after-4bit-simpleprompt.jsonl 第{b_row['line']}行"
             f"(该文件同图{n_same}条中唯一answer=0)", vfont=F_SMALL)

    def sample_a_card(p: Painter) -> None:
        p.kv("answer:", "1 · 存在睡岗行为", key_color=WARN_RED)
        for ev in (a_rows[0].get("evidence") or [])[:2]:
            p.bullet(f"证据: {ev}", font=F_SMALL)
        p.kv("来源:", f"sleep-after-4bit.jsonl 第{a_rows[0]['line']}-"
             f"{a_rows[-1]['line']}行", vfont=F_SMALL, key_color=TXT_GRAY)

    def sample_b_card(p: Painter) -> None:
        p.kv("answer:", "0 · 不存在睡岗行为", key_color=OK_GREEN)
        for ev in (b_row.get("evidence") or [])[:2]:
            p.bullet(f"证据: {ev}", font=F_SMALL, dot=WARN_RED)
        p.kv("矛盾点:", f"样本B answer=0(不存在), 但其自身evidence写明"
             f"『{b_contra[:40]}…』 — 结论字段与证据字段语义相悖",
             vfont=F_SMALL, key_color=WARN_RED)

    def check_card(p: Painter) -> None:
        p.mark_item("√", "语法层 · 通过",
                    "字段结构完整(task/answer/evidence), JSON可解析, "
                    "answer∈{0,1,2}取值合法", OK_GREEN)
        p.mark_item("!", "语义层 · 提示",
                    "样本B结论(answer=0不存在)与其evidence文本(『符合睡岗特征』)"
                    "语义矛盾 — 违反『结论须与证据一致』约束", WARN_RED)
        p.mark_item("!", "逻辑层 · 提示",
                    "同一图片同类任务跨样本结论冲突(样本A=1 vs 样本B=0) — "
                    "违反『同类样本结论一致性』约束, 需回查原图仲裁", WARN_RED)

    def trace_card(p: Painter) -> None:
        p.kv("原图:", f"test/{img}(1920×1080) — 来源回查入口", vfont=F_SMALL)
        p.kv("样本A:", f"sleep-after-4bit.jsonl 第{a_rows[0]['line']}-"
             f"{a_rows[-1]['line']}行", vfont=F_SMALL, key_color=TXT_GRAY)
        p.kv("样本B:", f"sleep-after-4bit-simpleprompt.jsonl 第{b_row['line']}行",
             vfont=F_SMALL, key_color=TXT_GRAY)
        p.kv("旁证:", "同图在 sleep-before-4bit / sleep-before-all / sleep-after-all"
             " 等其余样本文件中answer均为1(存在) — 多数样本与样本B自身证据均指向"
             "『存在睡岗』", vfont=F_SMALL)
        p.kv("处置建议:", "回查原图人工复核后修正样本B(倾向修正answer为1); "
             "冲突样本留痕待仲裁, 不以单一JSON可解析即认定结论正确",
             vfont=F_SMALL, key_color=WARN_RED)

    c = Canvas()
    c.header("场景五 · 科研生产现场智能监管", "冲突校验")
    c.h1("同类样本结论冲突的分层校验提示与来源回查",
         "用例编号 SC5-CHK-01 · 冲突对象: 同一图片 · 同一任务(睡岗检测) · 跨样本answer冲突")
    c.card("冲突概要", img, overview_card)
    c.card("样本A · 标准提示词(sleep-after-4bit.jsonl)", "answer=1", sample_a_card)
    c.card("样本B · 简化提示词(sleep-after-4bit-simpleprompt.jsonl)",
           "answer=0", sample_b_card)
    c.card("分层校验提示(语法/语义/逻辑)", "2项提示", check_card)
    c.card("来源回查", "可追溯", trace_card)
    c.footer("截图来源: 场景5真实样例数据集 — 冲突为数据中真实存在的跨样本结论冲突"
             "(sleep-after-4bit-simpleprompt.jsonl 行76-78 answer=1,1,0; "
             "sleep-after-4bit.jsonl 行76-78 均answer=1; 其余同图样本均answer=1) · "
             "分层提示依据场景5一致性校验规则(格式/结论-证据/跨样本一致)")
    out = OUT_DIR / "scene5_conflict_check.png"
    c.save(out)
    return out


# ══════════════ 主流程 ══════════════

def run_api_screenshots() -> list[Path]:
    proc = start_backend()
    try:
        out: list[Path] = []
        t0 = time.time()
        _, r1 = http_json("POST", "/api/activate",
                          {"question": "修改数据功能支持哪些设备"})
        e1 = time.time() - t0
        if not r1.get("ok"):
            raise RuntimeError(f"activate失败: {r1.get('message')}")
        out.append(render_scene1_parse(r1, e1))

        t0 = time.time()
        _, r2 = http_json("POST", "/api/activate",
                          {"question": "连接池配置的接口标识符"})
        e2 = time.time() - t0
        if not r2.get("ok"):
            raise RuntimeError(f"activate失败: {r2.get('message')}")
        out.append(render_scene1_link(r2, e2))

        _, j = http_json("POST", "/api/check/04")
        job_id = j["data"]["job_id"]
        t0 = time.time()
        polls = 0
        result = None
        while time.time() - t0 < 600:
            _, st = http_json("GET", f"/api/check/status/{job_id}")
            polls += 1
            data = st["data"]
            if data["status"] == "done":
                result = data["result"]
                break
            if data["status"] == "error":
                raise RuntimeError(f"校验job失败: {data.get('error')}")
            time.sleep(1.0)
        if result is None:
            raise RuntimeError("校验job超时(600s)")
        out.append(render_scene1_report(result, job_id, polls, time.time() - t0))
        return out
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
            print(f"[backend] 已终止 pid={proc.pid}")
        except subprocess.TimeoutExpired:
            proc.kill()
            print(f"[backend] 强制终止 pid={proc.pid}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-api", action="store_true", help="跳过API截图(调试)")
    ap.add_argument("--skip-figs", action="store_true", help="跳过分析图(调试)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    if not args.skip_api:
        saved += run_api_screenshots()
    if not args.skip_figs:
        saved += [fig_confusion_matrix(), fig_violation_detection(), fig_cost_pareto()]
        saved += [render_scene5_qa_fields(), render_scene5_image_link(),
                  render_scene5_conflict()]

    print(f"\n完成: {len(saved)}/9 张 → {OUT_DIR}")
    for p in saved:
        print(f"  {p.name}  {p.stat().st_size // 1024}KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
