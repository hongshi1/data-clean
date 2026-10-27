"""确定性词法匹配工具 (vendored from tools/m1_compare_engine.py 纯stdlib子集).

为什么vendor而不是import: m1顶层import requests并在import期加载emb_cache,
而本模块只依赖其中的纯re/csv部分. 同步性由tests/test_kt_sync.py保证
(vendored版与live版在真实表格上输出逐字节一致).

保持与tools/m1_compare_engine.py同步 — 修改任一侧必须跑同步测试.
"""
from __future__ import annotations

import re

# ── 文本规范化 ──────────────────────────────────────────

def normalize_text(s: str) -> str:
    """文本规范化: 编号剥离+空白压缩+全角半角统一"""
    if not s:
        return ''
    s = re.sub(r'^\s*\d+\s*[\.．、]\s*', '', s)          # 前导编号
    s = s.replace('（', '(').replace('）', ')')
    s = s.replace('，', ',').replace('。', '.').replace('；', ';')
    s = re.sub(r'\s+', '', s)                              # 全部空白
    return s.strip()


def char_keywords(s: str, k: int = 4) -> set[str]:
    """关键词: 中文滑动k字窗口 + 英文/数字token"""
    cjk = re.findall(r'[\u4e00-\u9fff]', s)
    ascii_tokens = re.findall(r'[A-Za-z0-9]+', s)
    kws = set()
    if len(cjk) >= k:
        kws |= {''.join(cjk[i:i + k]) for i in range(len(cjk) - k + 1)}
    elif cjk:
        kws.add(''.join(cjk))
    kws |= {t.lower() for t in ascii_tokens if len(t) >= 2}
    return kws


SYN_CHARS = {'坐': '席'}  # 单向归一到规范形
IFACE_PAT = re.compile(r'^与(.+?)(?:交互)?接口$')


def _lev(a: str, b: str) -> int:
    """编辑距离"""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            cur.append(min(prev[j + 1] + 1, cur[j] + 1, prev[j] + (ca != cb)))
        prev = cur
    return prev[-1]


def _unwrap_interface(s: str) -> str:
    """'与X交互接口' → X"""
    m = IFACE_PAT.match(s)
    return m.group(1) if m else ''


def text_match_score(a: str, b: str) -> float:
    """确定性文本匹配分(0-1): 精确>包含>接口名解包>错字容差>字符重叠"""
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    # 包含关系
    if na in nb or nb in na:
        return 0.9
    # 功能词剥离后包含(修饰词差异: 数据抽取转换↔异构数据抽取与转换)
    FUNC_CHARS = set('与的及和或者对于在中上将下其各该')
    na_f = ''.join(c for c in na if c not in FUNC_CHARS)
    nb_f = ''.join(c for c in nb if c not in FUNC_CHARS)
    if len(na_f) >= 3 and len(nb_f) >= 3 and (na_f in nb_f or nb_f in na_f):
        return 0.87
    # 同义字归一后再试(坐位↔席位)
    na_s = ''.join(SYN_CHARS.get(c, c) for c in na)
    nb_s = ''.join(SYN_CHARS.get(c, c) for c in nb)
    if na_s == nb_s or na_s in nb_s or nb_s in na_s:
        return 0.88
    # 接口名解包: "与X交互接口" vs "X"(或反向)
    for u, other in ((na, nb), (nb, na)):
        core = _unwrap_interface(u)
        if core and (core in other or other in core) and len(core) >= 3:
            return 0.86
    # 错字容差: 编辑距离≤1且长度≥5
    if min(len(na), len(nb)) >= 5 and _lev(na, nb) <= 1:
        return 0.85
    # 字符重叠 (4字窗口Jaccard)
    ka, kb = char_keywords(a), char_keywords(b)
    if ka and kb:
        j = len(ka & kb) / len(ka | kb)
        return round(j, 3)
    return 0.0


MATCH_TH = 0.5  # 匹配阈值(与m1一致)
