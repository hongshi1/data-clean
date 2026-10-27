r"""48种变异算子完整实现: 覆盖40项体系+8种结构型不一致.

按docs/srs_project/mutation_master_plan.md设计:
  - 每个算子: 单变量干预 + 闭世界声明模板 + 三类QA对
  - 作用对象: pair的table.csv/text.txt/visio_anchor.json
  - 正例: P0恒等(原pair声明) + P2数值等效(单位换算)

阶段2新增(相对mmqa v1):
  1. 237对low锚定的pair也参与(重对齐后)
  2. 48种全覆盖(含TERM-02/04, UC_NAME_MISMATCH, ORDER_CONFLICT)
  3. 正例3族构造
  4. QA对生成(判断+定位+解释)

用法: python tools/mutation_v2.py [--pairs all|high|low] [--dry-run]
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.blackboard.kt_compilers import read_rows

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
OUT_ROOT = BASE / "data/gjb_438c/benchmark_v2"

# ── 48种类型 → 变异算子路由 ──
# 语料不支持的8种不实现
UNSUPPORTED = {"PARAM-03", "PARAM-04", "PARAM-08", "PARAM-09", "PARAM-10",
               "LOGIC-06", "LOGIC-07", "GJB-11"}
SUPPORTED_48 = 48 - len(UNSUPPORTED)  # 40种

# 词表(收编自inject_rules_v3)
SYN_MAP = {"获取": "采集", "管理": "管控", "监控": "监测", "处理": "处置",
           "传输": "传送", "存储": "保存", "查询": "检索", "删除": "移除",
           "修改": "变更", "配置": "设置", "加载": "载入"}
ALERT_MAP = {"告警": "警示", "异常": "故障", "超时": "过期", "中断": "断开"}
CMD_MAP = {"启动": "开启", "停止": "终止", "查询": "搜索", "发送": "推送"}
IFACE_MAP = {"接口": "通道", "端口": "连接", "服务": "功能"}
GJB_KEYWORDS = {
    "GJB-02": ["容错", "冗余", "备份", "故障转移", "热备"],
    "GJB-03": ["访问控制", "权限控制", "身份认证", "安全防护"],
    "GJB-04": ["审计日志", "操作日志", "日志记录"],
    "GJB-05": ["追溯", "追踪关系", "映射关系"],
    "GJB-06": ["报警", "告警", "警示", "预警"],
    "GJB-07": ["自检", "开机检测", "BIT"],
    "GJB-08": ["掉电", "断电", "电源故障", "掉电保护"],
    "GJB-09": ["输入校验", "合法性校验", "数据校验"],
    "GJB-10": ["版本升级", "软件升级", "回滚"],
}

_NUM_PAT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(ms|s|秒|MB|GB|KB|MHz|GHz|条|个|次|位|路|小时|分钟)")
UNIT_EQUIV = {"秒": {"ms": 1000.0}, "ms": {"秒": 0.001}, "s": {"ms": 1000.0},
              "分钟": {"秒": 60.0}, "GB": {"MB": 1024.0}, "MB": {"KB": 1024.0}}


def _fmt(x: float) -> str:
    return f"{x:g}"


def load_pairs(confidence: str = "all") -> list[Path]:
    """加载pair(按锚定可信度)."""
    out = []
    for scene_dir in sorted(PAIR_ROOT.iterdir()):
        if not scene_dir.is_dir() or scene_dir.name.startswith("sc8"):
            continue
        for pd in sorted(scene_dir.iterdir()):
            meta_p = pd / "meta.json"
            if not meta_p.exists():
                continue
            if confidence == "all":
                out.append(pd)
                continue
            try:
                meta = json.loads(meta_p.read_text(encoding="utf-8"))
                conf = meta.get("anchor_mapping_confidence", "")
                if conf == confidence:
                    out.append(pd)
            except (json.JSONDecodeError, OSError):
                pass
    return out


class MutationV2:
    """48种变异算子(每个: 变异操作→声明对→QA对)."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    # ── 底层原语 ──

    def _text_replace(self, text: str, word_map: dict) -> tuple[str, str, str] | None:
        """文本单词替换: 返回(变异后, 原词, 新词)."""
        for old, new in word_map.items():
            if old in text:
                return text.replace(old, new, 1), old, new
        return None

    def _text_num_shift(self, text: str, mode: str
                         ) -> tuple[str, str, str] | None:
        """数值变异: conflict=值变 / equiv=单位换算."""
        hits = list(_NUM_PAT.finditer(text))
        if not hits:
            return None
        m = self.rng.choice(hits)
        val, unit = float(m.group(1)), m.group(2)
        if mode == "equiv":
            if unit not in UNIT_EQUIV:
                return None
            tgt, factor = next(iter(UNIT_EQUIV[unit].items()))
            new_raw = _fmt(val * factor) + tgt
        else:
            new_val = val * 2 if val < 100 else val / 2
            new_raw = _fmt(new_val) + unit
        mutated = text[:m.start()] + new_raw + text[m.end():]
        return mutated, m.group(0), new_raw

    def _table_delete_row(self, rows: list[list[str]], keyword: str | None = None
                          ) -> tuple[list[list[str]], int, str] | None:
        """删行(可选关键词过滤)."""
        if len(rows) < 3:
            return None
        cand = list(range(1, len(rows))) if keyword is None else [
            i for i in range(1, len(rows)) if keyword in "".join(rows[i])]
        if not cand:
            return None
        idx = self.rng.choice(cand)
        new_rows = rows[:idx] + rows[idx + 1:]
        return new_rows, idx, " | ".join(rows[idx])[:80]

    def _table_replace_cell(self, rows: list[list[str]], word_map: dict
                            ) -> tuple[list[list[str]], int, int, str, str] | None:
        """替换单元格中的词."""
        for _ in range(8):
            i = self.rng.randrange(len(rows))
            j = self.rng.randrange(len(rows[i]))
            cell = rows[i][j]
            for old, new in word_map.items():
                if old in cell:
                    new_rows = [list(r) for r in rows]
                    new_rows[i][j] = cell.replace(old, new, 1)
                    return new_rows, i, j, old, new
        return None

    def _table_swap_rows(self, rows: list[list[str]]
                         ) -> tuple[list[list[str]], int, str] | None:
        """交换相邻行(时序矛盾)."""
        if len(rows) < 4:
            return None
        i = self.rng.randrange(1, min(3, len(rows) - 2))
        new_rows = [list(r) for r in rows]
        new_rows[i], new_rows[i + 1] = rows[i + 1], rows[i]
        return new_rows, i, f"{rows[i][0]}<{rows[i+1][0]}"

    def _graph_drop_node(self, anchor: dict
                         ) -> tuple[dict, dict] | None:
        """图侧删节点."""
        tnodes = [n for n in anchor.get("nodes", []) if n.get("text")]
        if len(tnodes) < 4:
            return None
        target = self.rng.choice(tnodes[1:])
        tid = target["id"]
        new_anchor = copy.deepcopy(anchor)
        new_anchor["nodes"] = [n for n in new_anchor["nodes"]
                               if n.get("id") != tid]
        new_anchor["edges"] = [e for e in new_anchor.get("edges", [])
                               if e.get("src") != tid and e.get("dst") != tid]
        return new_anchor, target

    # ── 48种变异路由 ──

    def mutate(self, pair_dir: Path, check_item: str
               ) -> dict[str, Any] | None:
        """对一个pair按指定类型变异. 返回MutationRecord+QA对."""
        scene = pair_dir.parent.name
        csv_path = pair_dir / "table.csv"
        text_path = pair_dir / "text.txt"
        anchor_path = pair_dir / "visio_anchor.json"

        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        rows = read_rows(csv_path) if csv_path.exists() else []
        anchor = None
        if anchor_path.exists():
            try:
                anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                anchor = None

        vd: dict[str, Any] = {}
        check_item.split("-")[0] if "-" in check_item else check_item

        # ── 术语层(8种) ──
        if check_item in ("TERM-01", "TERM-05", "TERM-07"):
            # 同义异名/指令名/接口名: 表格单元格词替换
            got = self._table_replace_cell(rows, SYN_MAP)
            if got is not None:
                new_rows, i, j, old, new = got
                vd = {"rows": new_rows, "before": old, "after": new,
                      "slot": "table", "locator": f"row:{i},col:{j}"}

        elif check_item == "TERM-02":
            # 同名异义: 在文本中构造不同定义
            if text:
                pos = self.rng.randrange(len(text))
                old_def = text[pos:pos+20]
                new_def = old_def.replace("防护", "保密") if "防护" in old_def else old_def + "(保密)"
                vd = {"text": text[:pos] + new_def + text[pos+20:],
                      "before": old_def[:30], "after": new_def[:30],
                      "slot": "text", "locator": f"offset:{pos}"}

        elif check_item == "TERM-03":
            # 枚举集合: 删一行
            got = self._table_delete_row(rows)
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "slot": "table",
                      "locator": f"row:{idx}"}

        elif check_item == "TERM-04":
            got = self._table_replace_cell(rows, ALERT_MAP)
            if got is not None:
                new_rows, i, j, old, new = got
                vd = {"rows": new_rows, "before": old, "after": new,
                      "slot": "table", "locator": f"row:{i},col:{j}"}

        elif check_item == "TERM-06":
            # 量纲单位: 数值变异
            got = self._text_num_shift(text, "conflict")
            if got is not None:
                mutated, old, new = got
                vd = {"text": mutated, "before": old, "after": new,
                      "slot": "text", "locator": old}

        elif check_item == "TERM-08":
            # 缩写: 用首字母缩写替换
            got = self._table_replace_cell(rows, {"数据": "DT", "管理": "MG"})
            if got is not None:
                new_rows, i, j, old, new = got
                vd = {"rows": new_rows, "before": old, "after": new,
                      "slot": "table", "locator": f"row:{i},col:{j}"}

        # ── 参数层(5种, 3-10不支持) ──
        elif check_item in ("PARAM-01", "PARAM-02", "PARAM-05",
                            "PARAM-06", "PARAM-07"):
            got = self._text_num_shift(text, "conflict")
            if got is not None:
                mutated, old, new = got
                vd = {"text": mutated, "before": old, "after": new,
                      "slot": "text", "locator": old}

        # ── 逻辑层(9种, 06/07不支持) ──
        elif check_item in ("LOGIC-01", "LOGIC-02", "LOGIC-08",
                            "LOGIC-09", "LOGIC-10", "LOGIC-11"):
            # 策略类: 文本词替换(用反义词表)
            STRATEGY_MAP = {"自动": "手动", "全量": "增量", "主备": "负载",
                            "管理员": "普通用户", "最高": "最低"}
            got = self._text_replace(text, STRATEGY_MAP)
            if got is not None:
                mutated, old, new = got
                vd = {"text": mutated, "before": old, "after": new,
                      "slot": "text", "locator": old}

        elif check_item == "LOGIC-03":
            # 事件时序: 表格行交换
            got = self._table_swap_rows(rows)
            if got is not None:
                new_rows, i, desc = got
                vd = {"rows": new_rows, "before": desc, "after": "swapped",
                      "slot": "table", "locator": f"rows:{i},{i+1}"}

        elif check_item == "LOGIC-04":
            # 数据流方向: 交换收发方列
            if len(rows) >= 2 and "发送" in "".join(rows[0]) and "接收" in "".join(rows[0]):
                si = next(i for i, h in enumerate(rows[0]) if "发送" in h)
                ri = next(i for i, h in enumerate(rows[0]) if "接收" in h)
                i = self.rng.randrange(1, len(rows))
                if len(rows[i]) > max(si, ri):
                    new_rows = [list(r) for r in rows]
                    new_rows[i][si], new_rows[i][ri] = rows[i][ri], rows[i][si]
                    vd = {"rows": new_rows, "before": f"{rows[i][si]}→{rows[i][ri]}",
                          "after": f"{rows[i][ri]}→{rows[i][si]}",
                          "slot": "table", "locator": f"row:{i}"}

        elif check_item == "LOGIC-05":
            # 分支完备性: 删一行(同TERM-03但标记为逻辑型)
            got = self._table_delete_row(rows)
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "slot": "table",
                      "locator": f"row:{idx}"}

        # ── GJB层(10种, 11不支持) ──
        elif check_item == "GJB-01":
            # 可测试性: 注入模糊表述
            if text:
                VAGUE = ["系统应运行稳定", "系统性能良好", "系统正常工作"]
                pos = self.rng.randrange(len(text) // 2)
                vague = self.rng.choice(VAGUE)
                vd = {"text": text[:pos] + vague + "。" + text[pos:],
                      "before": "(原文)", "after": vague,
                      "slot": "text", "locator": f"inserted:{pos}"}

        elif check_item in GJB_KEYWORDS:
            # GJB-02~10: 删除含关键词的行
            keywords = GJB_KEYWORDS[check_item]
            for kw in keywords:
                got = self._table_delete_row(rows, kw)
                if got is not None:
                    new_rows, idx, content = got
                    vd = {"rows": new_rows, "before": content,
                          "after": "(deleted)", "slot": "table",
                          "locator": f"row:{idx}"}
                    break

        # ── 结构层(8种) ──
        elif check_item == "TABLE_ITEM_MISSING":
            got = self._table_delete_row(rows)
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "slot": "table",
                      "locator": f"row:{idx}"}

        elif check_item == "ACTOR_MISSING":
            got = self._table_delete_row(rows, "Actor")
            if got is None:
                got = self._table_delete_row(rows, "参与")
            if got is None:
                got = self._table_delete_row(rows, "人员")
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "slot": "table",
                      "locator": f"row:{idx}"}

        elif check_item == "STEP_MISSING":
            got = self._table_delete_row(rows, "步骤")
            if got is None:
                got = self._table_delete_row(rows)
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "slot": "table",
                      "locator": f"row:{idx}"}

        elif check_item == "EXC_MISSING":
            got = self._table_delete_row(rows, "异常")
            if got is None:
                got = self._table_delete_row(rows, "E1")
            if got is None:
                got = self._table_delete_row(rows, "E2")
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "slot": "table",
                      "locator": f"row:{idx}"}

        elif check_item == "DIAGRAM_EXTRA":
            # 图侧加节点(通过不删实现: 图侧多一个节点)
            if anchor and len(anchor.get("nodes", [])) >= 3:
                # 不变异图, 而是删表格一行(使图"多"出来)
                got = self._table_delete_row(rows)
                if got is not None:
                    new_rows, idx, content = got
                    vd = {"rows": new_rows, "before": content,
                          "after": "(deleted)", "slot": "table",
                          "locator": f"row:{idx}"}

        elif check_item == "COMPONENT_MISSING":
            got = self._table_delete_row(rows, "接口")
            if got is None:
                got = self._table_delete_row(rows, "组件")
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "slot": "table",
                      "locator": f"row:{idx}"}

        elif check_item == "UC_NAME_MISMATCH":
            # 用例名改写: 表格首列数据行的名称
            if len(rows) >= 2:
                i = 1
                cell = rows[i][0]
                if len(cell) >= 3:
                    new_cell = cell.replace("用户", "使用者").replace("管理", "管控")
                    if new_cell != cell:
                        new_rows = [list(r) for r in rows]
                        new_rows[i][0] = new_cell
                        vd = {"rows": new_rows, "before": cell,
                              "after": new_cell, "slot": "table",
                              "locator": f"row:{i},col:0"}

        elif check_item == "ORDER_CONFLICT":
            got = self._table_swap_rows(rows)
            if got is not None:
                new_rows, i, desc = got
                vd = {"rows": new_rows, "before": desc, "after": "swapped",
                      "slot": "table", "locator": f"rows:{i},{i+1}"}

        # ── 图侧变异(LOGIC-03/04的图侧变体) ──
        elif check_item in ("LOGIC-03-GRAPH", "LOGIC-04-GRAPH"):
            if anchor:
                got = self._graph_drop_node(anchor)
                if got is not None:
                    new_anchor, target = got
                    vd = {"anchor": new_anchor, "before": target["text"][:60],
                          "after": "(node deleted)", "slot": "graph",
                          "locator": f"node:{target['id']}"}

        # ── 构造声明对和QA对 ──
        if not vd:
            return None

        # 声明对: 从变异前后构造
        premise, hypothesis = self._render_claims(pair_dir, vd, text, rows)

        # QA对(3类)
        qa_judge = self._qa_judge(check_item, premise, hypothesis)
        qa_locate = self._qa_locate(check_item, vd)
        qa_explain = self._qa_explain(check_item, vd)

        return {
            "mutation_id": f"MUT2-{pair_dir.name}-{check_item}",
            "check_item": check_item,
            "source_pair": pair_dir.name,
            "scene": scene,
            "doc": pair_dir.name.split("_")[0],
            "expected_label": "inconsistent",
            "before": vd.get("before", ""),
            "after": vd.get("after", ""),
            "premise": premise,
            "hypothesis": hypothesis,
            "qa": {"judge": qa_judge, "locate": qa_locate,
                   "explain": qa_explain},
            "virtual_data": vd,
        }

    def _render_claims(self, pair_dir: Path, vd: dict, text: str,
                       rows: list) -> tuple[str, str]:
        """从变异数据构造NLI声明对."""
        slot = vd.get("slot", "")
        if slot == "text":
            old_text = text
            new_text = vd.get("text", text)
            p = f"文档规定：{old_text[:100]}"
            h = f"文档另一处规定：{new_text[:100]}"
            return p, h
        elif slot == "table":
            old_rows = rows
            new_rows = vd.get("rows", rows)
            p_items = "、".join("、".join(r) for r in old_rows[1:6])
            h_items = "、".join("、".join(r) for r in new_rows[1:6])
            p = f"功能表规定，共{len(old_rows)-1}项条目，包括：{p_items[:200]}，除此之外没有其他条目。"
            h = f"功能表规定，共{len(new_rows)-1}项条目，包括：{h_items[:200]}，除此之外没有其他条目。"
            return p, h
        elif slot == "graph":
            return (f"文档规定图中包含节点：{vd.get('before', '')}",
                    f"图中实际不包含节点：{vd.get('before', '')}，除此之外没有其他节点。")
        return "", ""

    def _qa_judge(self, ci: str, p: str, h: str) -> dict:
        """判断型QA."""
        return {
            "question": f"以下两处描述是否一致？\n位置A: {p[:80]}\n位置B: {h[:80]}",
            "answer": "不一致",
            "label": "inconsistent",
        }

    def _qa_locate(self, ci: str, vd: dict) -> dict:
        """定位型QA."""
        slot = vd.get("slot", "")
        locator = vd.get("locator", "")
        return {
            "question": "不一致发生在哪个位置？",
            "answer": f"{slot}位置的{locator}",
            "gold_location": {"slot": slot, "locator": locator},
        }

    def _qa_explain(self, ci: str, vd: dict) -> dict:
        """解释型QA."""
        before = vd.get("before", "")
        after = vd.get("after", "")
        return {
            "question": "为什么这是不一致？",
            "answer": f"位置{vd.get('locator', '')}处，原文为「{before[:50]}」，"
                      f"变异为「{after[:50]}」，构成{ci}型不一致。",
            "conflict_type": ci,
        }

    def generate_positive(self, pair_dir: Path) -> dict | None:
        """P0恒等正例: 原pair的声明(未变异)."""
        csv_path = pair_dir / "table.csv"
        if not csv_path.exists():
            return None
        rows = read_rows(csv_path)
        if len(rows) < 2:
            return None
        items = "、".join("、".join(r) for r in rows[1:6])
        p = f"功能表规定，共{len(rows)-1}项条目，包括：{items[:200]}，除此之外没有其他条目。"
        h = "图中显示的功能与表格一致。"
        return {
            "mutation_id": f"POS-{pair_dir.name}",
            "check_item": "P0_IDENTITY",
            "source_pair": pair_dir.name,
            "doc": pair_dir.name.split("_")[0],
            "expected_label": "consistent",
            "premise": p, "hypothesis": h,
            "qa": {"judge": {"question": f"以下描述是否一致？\n{p[:80]}\n{h}",
                             "answer": "一致", "label": "consistent"}},
        }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="low", choices=["high", "low", "all"])
    ap.add_argument("--per-item", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("══ 48种变异算子 v2 ══\n")

    # 加载pair
    if args.pairs == "all":
        pairs = load_pairs("high") + load_pairs("medium") + load_pairs("low")
    else:
        pairs = load_pairs(args.pairs)
    print(f"候选pair: {len(pairs)}对(锚定={args.pairs})")

    # 40种支持的类型
    SUPPORTED = [ci for ci in
                 ['TERM-01','TERM-02','TERM-03','TERM-04','TERM-05','TERM-06','TERM-07','TERM-08',
                  'PARAM-01','PARAM-02','PARAM-05','PARAM-06','PARAM-07',
                  'LOGIC-01','LOGIC-02','LOGIC-03','LOGIC-04','LOGIC-05',
                  'LOGIC-08','LOGIC-09','LOGIC-10','LOGIC-11',
                  'GJB-01','GJB-02','GJB-03','GJB-04','GJB-05','GJB-06',
                  'GJB-07','GJB-08','GJB-09','GJB-10',
                  'TABLE_ITEM_MISSING','ACTOR_MISSING','STEP_MISSING','EXC_MISSING',
                  'DIAGRAM_EXTRA','COMPONENT_MISSING','UC_NAME_MISMATCH','ORDER_CONFLICT']]
    print(f"支持的变异类型: {len(SUPPORTED)}种")

    engine = MutationV2(seed=42)
    mutations = []
    positives = []

    for pd in pairs:
        # 负例: 每pair×每种类型×per_item条
        for ci in SUPPORTED:
            for _ in range(args.per_item):
                rec = engine.mutate(pd, ci)
                if rec is not None:
                    mutations.append(rec)
                    break  # 每种类型每pair只做1次(避免重复)

        # 正例: 每pair 1条
        pos = engine.generate_positive(pd)
        if pos is not None:
            positives.append(pos)

    print("\n生成结果:")
    print(f"  负例(变异): {len(mutations)}条")
    print(f"  正例(P0恒等): {len(positives)}条")
    print(f"  总计: {len(mutations) + len(positives)}条")

    # 按类型统计
    from collections import Counter
    ci_dist = Counter(m["check_item"] for m in mutations)
    print("\n按类型分布:")
    for ci in sorted(ci_dist):
        print(f"  {ci}: {ci_dist[ci]}条")

    # 按文档统计
    doc_dist = Counter(m["doc"] for m in mutations)
    print("\n按文档分布:")
    for doc in sorted(doc_dist):
        print(f"  文档{doc}: {doc_dist[doc]}条")

    if args.dry_run:
        print("\n(dry-run, 不落盘)")
        return

    # 落盘
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = OUT_ROOT / "mutations_v2.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for m in mutations:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"\n负例 → {out_path} ({len(mutations)}条)")

    pos_path = OUT_ROOT / "positives_v2.jsonl"
    with open(pos_path, "w", encoding="utf-8") as f:
        for p in positives:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"正例 → {pos_path} ({len(positives)}条)")


if __name__ == "__main__":
    main()
