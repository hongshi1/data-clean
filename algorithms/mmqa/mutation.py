"""LEGACY: MMQA pair-directory context mutation layer.

It is not an answer-side operator for the post-retrieval QA module. The active
answer contract is implemented in ``algorithms.consistency.answer_mutations``;
this module remains only for historical migration experiments.

Historical MMQA受控变异层: 40项校验体系对齐版(不自创算子).

算子ID = 14_strict_40_design.md的40项check_item(外部实施方案定义):
  术语8项(TERM-01~08) + 参数10项(PARAM-01~10) +
  逻辑11项(LOGIC-01~11) + GJB合规11项(GJB-01~11)

注入操作实现收编自 tools/inject_rules_v3.py(766行成熟实现:
词表/正则/Z3 gate/occurrences回写), 本模块补三件事:
  1. MutationRecord v2 schema(before/after/expected_label/single_factor/
     source_evidence/verify_gate) — 文本级注入升级为可审计记录
  2. 虚拟pair物化 — 注入结果写入pair目录布局, 现有声明编译/
     词法/NLI管线零改动复用
  3. 最小对: TERM-06等注入自带"等效不冲突"正例(0.2秒vs200ms);
     删除型注入的对照=原pair(恒等正例)

NLI通道分流(按实测能力边界, 非算子发明):
  nli-strong: 参数值冲突(0.98)/计数缺失闭世界(1.00)/枚举集合
  nli-weak:   方向/时序(0.67)
  lexical:    同义异名/缩写/指令名(NLI判neutral — 术语通道职责)
  syntax:     GJB删除型(语法/结构规则职责)
"""
from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path
from typing import Any

from algorithms.mmqa.atoms import table_rows_from_csv

# ── 40项 → 通道映射(NLI能力边界, 实测依据见docs/srs_project/nli报告) ──

CHANNEL_MAP: dict[str, str] = {
    # 术语层: 语义相似≠矛盾 → 术语/词法通道(NLI对surface variant判neutral)
    "TERM-01": "lexical", "TERM-02": "lexical", "TERM-04": "lexical",
    "TERM-05": "lexical", "TERM-07": "lexical", "TERM-08": "lexical",
    # TERM-03枚举集合(闭世界计数) / TERM-06量纲冲突 → NLI可判
    "TERM-03": "nli-strong", "TERM-06": "nli-strong",
    # 参数层: 全部NLI可判(值冲突0.98), 值域类加Z3 gate
    **{f"PARAM-{i:02d}": "nli-strong" for i in range(1, 11)},
    # 逻辑层: 时序/方向类NLI弱(0.67)单列; 策略/互斥类需业务判断归LLM
    "LOGIC-03": "nli-weak", "LOGIC-04": "nli-weak", "LOGIC-05": "nli-strong",
    "LOGIC-01": "llm", "LOGIC-02": "llm", "LOGIC-06": "llm",
    "LOGIC-07": "llm", "LOGIC-08": "llm", "LOGIC-09": "llm",
    "LOGIC-10": "llm", "LOGIC-11": "llm",
    # GJB层: 删除型 → 语法/结构规则通道
    **{f"GJB-{i:02d}": "syntax" for i in range(1, 12)},
}

# 40项的issue_type语义(对齐14_strict_40_design的校验项名)
ITEM_NAME = {
    "TERM-01": "同义异名", "TERM-02": "同名异义", "TERM-03": "枚举集合",
    "TERM-04": "状态告警术语", "TERM-05": "指令名称", "TERM-06": "量纲单位",
    "TERM-07": "信号接口命名", "TERM-08": "缩写代号",
    "PARAM-01": "时间约束", "PARAM-02": "周期参数", "PARAM-03": "阈值边界",
    "PARAM-04": "多源时间对齐", "PARAM-05": "资源占用", "PARAM-06": "参数值域",
    "PARAM-07": "存储容量时长", "PARAM-08": "守时精度", "PARAM-09": "降级阈值",
    "PARAM-10": "故障持续时长",
    "LOGIC-01": "模式切换优先级", "LOGIC-02": "异常处置策略",
    "LOGIC-03": "事件时序", "LOGIC-04": "数据流流向", "LOGIC-05": "工况分支完备",
    "LOGIC-06": "互斥控制", "LOGIC-07": "任务切换原子性", "LOGIC-08": "冗余仲裁",
    "LOGIC-09": "权限访问控制", "LOGIC-10": "故障恢复", "LOGIC-11": "追踪重搜",
    "GJB-01": "可测试性合规", "GJB-02": "故障容错完备", "GJB-03": "安全访问控制",
    "GJB-04": "审计日志合规", "GJB-05": "需求可追溯性", "GJB-06": "异常报警要素",
    "GJB-07": "软件自检", "GJB-08": "掉电数据保护", "GJB-09": "输入数据防护",
    "GJB-10": "版本升级安全", "GJB-11": "降级运行",
}

# 词表(收编自inject_rules_v3)
SYN_MAP = {
    "获取": "采集", "管理": "管控", "监控": "监测", "处理": "处置",
    "传输": "传送", "存储": "保存", "查询": "检索", "注册": "登记",
    "部署": "安装", "启动": "开启", "关闭": "停止", "删除": "移除",
    "修改": "变更", "添加": "新增", "配置": "设置", "加载": "载入",
    "捕捉": "捕获", "归集": "汇集", "转换": "变换", "发布": "分发",
}

_NUM_PAT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(ms|s|秒|MB|GB|KB|MHz|GHz|条|个|次|位|路|小时|分钟|%)")
UNIT_EQUIV = {"秒": {"ms": 1000.0}, "ms": {"秒": 0.001},
              "s": {"ms": 1000.0}, "分钟": {"秒": 60.0}}


def _fmt(x: float) -> str:
    return f"{x:g}"


class MutationEngine40:
    """40项对齐的pair级变异: 文本级注入+虚拟pair物化.

    与inject_rules_v3的关系: 注入操作逻辑同源(词表/正则), 但作用
    单位从"实体occurrence对"升级为"pair的证据文件"(table.csv/
    text.txt/visio_anchor.json), 使现有NLI声明编译管线可直接消费.
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    # ── 底层单点编辑原语(40项注入的组合积木, 非独立算子) ──

    def _edit_text_num(self, text: str, mode: str
                       ) -> tuple[str, dict[str, str]] | None:
        """数值单点编辑: conflict=值平移 / equiv=单位换算.

        服务PARAM-01~10(按数值上下文归类)与TERM-06.
        """
        hits = [m for m in _NUM_PAT.finditer(text)]
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
        return mutated, {"before": m.group(0), "after": new_raw}

    def _edit_table_delete_row(self, rows: list[list[str]]
                               ) -> tuple[list[list[str]], int, str] | None:
        if len(rows) < 3:
            return None
        idx = 2 + self.rng.randrange(len(rows) - 2)
        new_rows = rows[:idx] + rows[idx + 1:]
        return new_rows, idx, " | ".join(rows[idx])[:80]

    def _edit_table_synonym(self, rows: list[list[str]]
                            ) -> tuple[list[list[str]], int, int, str, str] | None:
        """同义异名: 表格单元格里的词换成同义词(TERM-01)."""
        for _ in range(8):
            i = self.rng.randrange(len(rows))
            j = self.rng.randrange(len(rows[i]))
            cell = rows[i][j]
            for old, new in SYN_MAP.items():
                if old in cell:
                    return ([r if k != i else
                             r[:j] + [cell.replace(old, new, 1)] + r[j + 1:]
                             for k, r in enumerate(rows)],
                            i, j, old, new)
        return None

    def _edit_table_enum_drop(self, rows: list[list[str]]
                              ) -> tuple[list[list[str]], int, str] | None:
        """枚举删项(TERM-03/LOGIC-05): 闭世界清单删1成员."""
        if len(rows) < 3:
            return None
        idx = 1 + self.rng.randrange(len(rows) - 1)
        new_rows = rows[:idx] + rows[idx + 1:]
        return new_rows, idx, " | ".join(rows[idx])[:80]

    def _edit_table_dir_flip(self, rows: list[list[str]]
                             ) -> tuple[list[list[str]], int, str, str] | None:
        """收发方交换(LOGIC-04数据流流向)."""
        if len(rows) < 2:
            return None
        hdr = "".join(rows[0])
        if "发送" not in hdr or "接收" not in hdr:
            return None
        si = next(i for i, h in enumerate(rows[0]) if "发送" in h)
        ri = next(i for i, h in enumerate(rows[0]) if "接收" in h)
        i = 1 + self.rng.randrange(len(rows) - 1)
        if len(rows[i]) <= max(si, ri):
            return None
        new_rows = [list(r) for r in rows]
        new_rows[i][si], new_rows[i][ri] = rows[i][ri], rows[i][si]
        return new_rows, i, rows[i][si], rows[i][ri]

    def _edit_table_order_swap(self, rows: list[list[str]]
                               ) -> tuple[list[list[str]], int, str] | None:
        """相邻步骤交换(LOGIC-03事件时序)."""
        if len(rows) < 4:
            return None
        i = 1 + self.rng.randrange(min(3, len(rows) - 2))
        new_rows = [list(r) for r in rows]
        new_rows[i], new_rows[i + 1] = rows[i + 1], rows[i]
        return new_rows, i, f"{rows[i][0]}<{rows[i+1][0]}"

    def _edit_graph_drop_node(self, anchor: dict
                              ) -> tuple[dict, dict] | None:
        """图侧删节点(TERM-03/LOGIC-05图侧变体)."""
        tnodes = [n for n in anchor.get("nodes", []) if n.get("text")]
        if len(tnodes) < 4:
            return None
        import copy
        target = self.rng.choice(tnodes[1:])
        tid = target["id"]
        new_anchor = copy.deepcopy(anchor)
        new_anchor["nodes"] = [n for n in new_anchor["nodes"]
                               if n.get("id") != tid]
        new_anchor["edges"] = [e for e in new_anchor.get("edges", [])
                               if e.get("src") != tid and e.get("dst") != tid]
        return new_anchor, target

    # ── 40项路由: 每项check_item映射到编辑原语组合 ──

    def mutate(self, pair_dir: Path, check_item: str
               ) -> dict[str, Any] | None:
        """对一个pair按40项之一注入. 不适用返回None(诚实排除)."""
        text_path = pair_dir / "text.txt"
        csv_path = pair_dir / "table.csv"
        anchor_path = pair_dir / "visio_anchor.json"
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        rows = table_rows_from_csv(csv_path) if csv_path.exists() else []
        anchor = None
        if anchor_path.exists():
            try:
                anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                anchor = None

        vd: dict[str, Any] = {}
        layer = check_item.split("-")[0]
        ok = False

        if layer == "PARAM" or check_item == "TERM-06":
            got = self._edit_text_num(text, "conflict")
            if got is not None:
                mutated, fields = got
                vd = {"text": mutated, **fields}
                ok = True
        elif check_item in ("TERM-01", "TERM-05", "TERM-07", "TERM-08"):
            got = self._edit_table_synonym(rows)
            if got is not None:
                new_rows, i, j, old, new = got
                vd = {"rows": new_rows, "before": old, "after": new,
                      "locator": f"row:{i},col:{j}"}
                ok = True
        elif check_item in ("TERM-03", "LOGIC-05"):
            # 文侧/表侧闭世界删项(图侧变体走anchor)
            if self.rng.random() < 0.5 and rows:
                got = self._edit_table_enum_drop(rows)
                if got is not None:
                    new_rows, idx, content = got
                    vd = {"rows": new_rows, "before": content,
                          "after": "(deleted)", "locator": f"row:{idx}"}
                    ok = True
            elif anchor is not None:
                got = self._edit_graph_drop_node(anchor)
                if got is not None:
                    new_anchor, target = got
                    vd = {"anchor": new_anchor, "before": target["text"][:60],
                          "after": "(node deleted)",
                          "locator": f"node:{target['id']}"}
                    ok = True
        elif layer == "GJB":
            # GJB删除型: 表格条件/异常行删除(对应容错/审计等条款缺失)
            got = self._edit_table_delete_row(rows)
            if got is not None:
                new_rows, idx, content = got
                vd = {"rows": new_rows, "before": content,
                      "after": "(deleted)", "locator": f"row:{idx}"}
                ok = True
        elif check_item == "LOGIC-04":
            got = self._edit_table_dir_flip(rows)
            if got is not None:
                new_rows, i, s, r = got
                vd = {"rows": new_rows, "before": f"{s}→{r}",
                      "after": f"{r}→{s}", "locator": f"row:{i}"}
                ok = True
        elif check_item == "LOGIC-03":
            got = self._edit_table_order_swap(rows)
            if got is not None:
                new_rows, i, desc = got
                vd = {"rows": new_rows, "before": desc,
                      "after": "swapped", "locator": f"rows:{i},{i+1}"}
                ok = True

        if not ok:
            return None
        return self._record(pair_dir, check_item, vd)

    def _record(self, pair_dir: Path, check_item: str,
                vd: dict[str, Any]) -> dict[str, Any]:
        mid = f"MUT-{pair_dir.name}-{check_item}"
        return {
            "mutation_id": mid,
            "check_item": check_item,
            "issue_name": ITEM_NAME.get(check_item, ""),
            "source_evidence": {
                "pair_id": pair_dir.name, "scene": pair_dir.parent.name,
                "slot": "text" if vd.get("text") is not None else
                        ("graph" if vd.get("anchor") is not None else "table"),
                "locator": vd.get("locator", "")},
            "before": vd.get("before", ""), "after": vd.get("after", ""),
            "expected_label": "inconsistent",
            "channel": CHANNEL_MAP.get(check_item, "llm"),
            "single_factor": True,
            "verify_gate": {"diff_ok": True, "claim_compilable": None},
            "virtual_data": vd,
        }


def materialize(record: dict[str, Any], out_root: Path,
                base_dir: Path) -> Path:
    """虚拟pair物化: 变异文件写入out_root/{mid}/, 布局同pair目录."""
    vd = record["virtual_data"]
    vdir = out_root / record["mutation_id"]
    vdir.mkdir(parents=True, exist_ok=True)

    def _write_csv(path: Path, rows: list[list[str]]) -> None:
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)

    if vd.get("rows") is not None:
        _write_csv(vdir / "table.csv", vd["rows"])
    elif (base_dir / "table.csv").exists():
        (vdir / "table.csv").write_bytes((base_dir / "table.csv").read_bytes())
    if vd.get("text") is not None:
        (vdir / "text.txt").write_text(vd["text"], encoding="utf-8")
    elif (base_dir / "text.txt").exists():
        (vdir / "text.txt").write_bytes((base_dir / "text.txt").read_bytes())
    if vd.get("anchor") is not None:
        (vdir / "visio_anchor.json").write_text(
            json.dumps(vd["anchor"], ensure_ascii=False), encoding="utf-8")
    elif (base_dir / "visio_anchor.json").exists():
        (vdir / "visio_anchor.json").write_bytes(
            (base_dir / "visio_anchor.json").read_bytes())
    for fname in ("meta.json", "1_" + base_dir.name + ".md"):
        src = base_dir / fname
        if src.exists():
            (vdir / fname).write_bytes(src.read_bytes())
    return vdir
