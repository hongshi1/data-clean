r"""Step1: if-else启发式密度审计 (algorithms/consistency/*.py).

用户核心诉求"代码不要很多的if else 而是应该用模型"的第一步:
用ast静态扫描定位算法层的决策型分支密度, 为模型替换实验
(tools/exp_model_replace.py)选靶. 纯静态分析, 不执行被审计代码,
不修改algorithms/下任何文件.

分类口径:
  决策型分支(decision) = 分支的test/body参与verdict产出或verdict路由:
    - verdict字符串常量: support/refute/not_in_evidence(三态) +
      contradiction/entailment(NLI标签) + 残差通道方法名
      (semantic_unresolved/conservative_unresolved/nli_residual...)
    - ClaimResult(verdict=...)关键字参数, verdict属性/名字引用
    - verify_*/unresolved通道调用(产verdict的入口)
    - test中 .kind/.method 比较(typed分派守卫)
  管道型分支(pipeline) = 其余(数据变换/格式校验/空值卫兵/循环控制)

簇(cluster) = 同一语句序列中连续If语句的最大运行(run), 每条
if-elif-...[-else]链算run中的一个语句(链内elif/else计入分支数).
该口径同时覆盖两种启发式形态:
  - 阶梯(ladder): 连续的早返回if块(如qa_module._aggregate的
    strict/dominant_70/no_minor_block/assertive_*四分支阶梯);
  - 链(chain): 单条if-elif-...(如claim_intervals.verify_numeric的
    subset/disjoint/overlap三分支).
保留条件: run≥2条语句, 或单链分支数≥3.
附加计数: 三元表达式(IfExp), 推导式if子句(不入if分支总数).

输出: data/gjb_438c/distillation/ifelse_audit_v1.json + 控制台表.

用法(PYTHONUTF8=1 PYTHONPATH=. 前缀):
  python tools/audit_ifelse_density.py
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

OUT_PATH = BASE / "data/gjb_438c/distillation/ifelse_audit_v1.json"
SCOPE_DIR = BASE / "algorithms/consistency"
FOCUS_FILES = (
    "claim_channels.py",
    "qa_module.py",
    "qa_router.py",
    "answer_claims.py",
    "coverage_expert.py",
)

#: verdict三态 + NLI标签 + 残差通道方法名(只出现在verdict决策语境)
VERDICT_CONSTANTS = frozenset({
    "support", "refute", "not_in_evidence",
    "contradiction", "entailment",
    "semantic_unresolved", "conservative_unresolved",
    "nli_residual", "nli_residual_unavailable",
    "legacy_binary_nli_unresolved",
})
#: 产出verdict的通道函数名前缀/名单
CHANNEL_CALL_PREFIXES = ("verify_",)
CHANNEL_CALL_NAMES = frozenset({"unresolved"})
#: test中视为typed分派守卫的属性名
DISPATCH_ATTRS = frozenset({"kind", "method"})
#: 簇保留阈值: run语句数下限 / 单链分支数下限
MIN_RUN_STMTS = 2
MIN_CHAIN_BRANCHES = 3
#: 每文件保留的最大簇数
TOP_K_CLUSTERS = 3


def git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=BASE, capture_output=True, text=True, timeout=10, check=False)
        return proc.stdout.strip() or "nogit"
    except (OSError, subprocess.SubprocessError):
        return "nogit"


# ── 分支决策性判定 ───────────────────────────────────────────────────────────


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _markers_in(node: ast.AST, allow_dispatch: bool) -> set[str]:
    """node子树中的决策标记集合(类别见模块docstring)."""
    markers: set[str] = set()
    for sub in ast.walk(node):
        if (isinstance(sub, ast.Constant) and isinstance(sub.value, str)
                and sub.value in VERDICT_CONSTANTS):
            markers.add("verdict_str")
        elif isinstance(sub, ast.keyword) and sub.arg == "verdict":
            markers.add("verdict_kw")
        elif (isinstance(sub, (ast.Name, ast.Attribute))
              and getattr(sub, "id", getattr(sub, "attr", "")) == "verdict"):
            markers.add("verdict_ref")
        elif isinstance(sub, ast.Call):
            name = _call_name(sub.func)
            if (name.startswith(CHANNEL_CALL_PREFIXES)
                    or name in CHANNEL_CALL_NAMES):
                markers.add("channel_call")
        if allow_dispatch and isinstance(sub, ast.Attribute) \
                and sub.attr in DISPATCH_ATTRS:
            markers.add("dispatch")
    return markers


def _markers_in_stmts(stmts: list[ast.stmt],
                      allow_dispatch: bool) -> set[str]:
    markers: set[str] = set()
    for stmt in stmts:
        markers |= _markers_in(stmt, allow_dispatch)
    return markers


def classify_if(node: ast.If) -> tuple[bool, set[str]]:
    """单条if语句(含其if-branch)的决策性判定 → (is_decision, markers)."""
    markers = _markers_in(node.test, allow_dispatch=True)
    markers |= _markers_in_stmts(node.body, allow_dispatch=False)
    return bool(markers), markers


def classify_else(node: ast.If) -> bool:
    """if链末尾else分支(存在时)的决策性判定."""
    orelse = node.orelse
    if not orelse or (len(orelse) == 1 and isinstance(orelse[0], ast.If)):
        return False
    return bool(_markers_in_stmts(orelse, allow_dispatch=False))


# ── 遍历: if记录 + 簇收集 ───────────────────────────────────────────────────


class IfRec:
    """一条if语句的审计记录(elif在AST上=orelse中的嵌套If)."""

    __slots__ = ("node", "func", "depth", "is_elif", "decision", "markers")

    def __init__(self, node: ast.If, func: str, depth: int, is_elif: bool,
                 decision: bool, markers: set[str]) -> None:
        self.node = node
        self.func = func
        self.depth = depth
        self.is_elif = is_elif
        self.decision = decision
        self.markers = markers


def _chain_of(stmt: ast.If) -> list[ast.If]:
    """stmt所在的if-elif链的完整节点序列(AST上orelse=[If]即elif)."""
    chain: list[ast.If] = [stmt]
    current = stmt
    while (len(current.orelse) == 1
           and isinstance(current.orelse[0], ast.If)):
        current = current.orelse[0]
        chain.append(current)
    return chain


def _chain_tail(chain: list[ast.If]) -> list[ast.stmt]:
    """链末尾的真else体(无else或纯elif续链时为空)."""
    last = chain[-1]
    orelse = last.orelse
    if orelse and not (len(orelse) == 1 and isinstance(orelse[0], ast.If)):
        return orelse
    return []


def _emit_cluster(run: list[ast.If], recs: list[IfRec],
                  clusters: list[dict[str, Any]]) -> None:
    """一个run(连续If语句) → 簇摘要(链展开: elif/else计入分支数)."""
    by_node = {r.node: r for r in recs}
    n_stmts = len(run)
    n_branches = 0
    n_decision = 0
    end_lineno = 0
    for root in run:
        chain = _chain_of(root)
        has_else = bool(_chain_tail(chain))
        n_branches += len(chain) + (1 if has_else else 0)
        n_decision += sum(1 for node in chain if by_node[node].decision)
        if has_else and classify_else(chain[-1]):
            n_decision += 1
        chain_ends = [node.end_lineno or node.lineno for node in chain]
        tail = _chain_tail(chain)
        if tail:
            chain_ends.append(tail[-1].end_lineno or tail[-1].lineno)
        end_lineno = max(end_lineno, max(chain_ends))
    if n_stmts < MIN_RUN_STMTS and n_branches < MIN_CHAIN_BRANCHES:
        return
    clusters.append({
        "function": by_node[run[0]].func,
        "lines": [run[0].lineno, end_lineno],
        "n_stmts": n_stmts,
        "n_branches": n_branches,
        "n_decision": n_decision,
        "decision_markers": sorted(
            {m for root in run for node in _chain_of(root)
             for m in by_node[node].markers}),
    })


def _walk_stmts(stmts: list[ast.stmt], func: str, if_depth: int,
                recs: list[IfRec], clusters: list[dict[str, Any]]) -> None:
    """遍历语句序列: 登记IfRec + 收集连续If run簇.

    深度只数if-in-if(循环/try体不加深); 函数/类体内重新起算.
    """
    run: list[ast.If] = []

    def flush() -> None:
        nonlocal run
        if run:
            _emit_cluster(run, recs, clusters)
            run = []

    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            flush()
            name = f"{func}.{stmt.name}" if func else stmt.name
            _walk_stmts(stmt.body, name, 0, recs, clusters)
        elif isinstance(stmt, ast.ClassDef):
            flush()
            name = f"{func}.{stmt.name}" if func else stmt.name
            _walk_stmts(stmt.body, name, if_depth, recs, clusters)
        elif isinstance(stmt, ast.If):
            run.append(stmt)
            chain = _chain_of(stmt)
            for position, node in enumerate(chain):
                decision, markers = classify_if(node)
                recs.append(IfRec(node, func, if_depth + 1,
                                  is_elif=position > 0, decision=decision,
                                  markers=markers))
                _walk_stmts(node.body, func, if_depth + 1, recs, clusters)
            tail = _chain_tail(chain)
            if tail:
                _walk_stmts(tail, func, if_depth + 1, recs, clusters)
        else:
            flush()
            for field in ("body", "orelse", "finalbody"):
                child = getattr(stmt, field, None)
                if isinstance(child, list):
                    _walk_stmts(child, func, if_depth, recs, clusters)
    flush()


# ── 附加计数 ────────────────────────────────────────────────────────────────


def _count_expressions(tree: ast.Module) -> dict[str, int]:
    """三元表达式/推导式if子句计数(附加快照, 不入if分支总数)."""
    n_ifexp = sum(isinstance(n, ast.IfExp) for n in ast.walk(tree))
    n_compif = sum(
        len(n.ifs)
        for n in ast.walk(tree) if isinstance(n, ast.comprehension))
    return {"n_ternary": n_ifexp, "n_comprehension_if": n_compif}


def _router_rules(tree: ast.Module) -> dict[str, int] | None:
    """qa_router专用: 模块级_RULES规则条数与关键词总数(数据表, 非if-else)."""
    for node in tree.body:
        value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "_RULES":
            value = node.value
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_RULES":
                    value = node.value
        if isinstance(value, ast.Tuple):
            n_terms = sum(
                len(elt.elts) if isinstance(elt, ast.Tuple) else 0
                for elt in value.elts)
            return {"keyword_rules": len(value.elts),
                    "keyword_terms": n_terms}
    return None


def audit_file(path: Path) -> dict[str, Any]:
    # utf-8-sig: router.py等文件带BOM, 普通utf-8读入会使ast.parse失败
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    recs: list[IfRec] = []
    clusters: list[dict[str, Any]] = []
    _walk_stmts(tree.body, "", 0, recs, clusters)
    clusters.sort(key=lambda c: (c["n_decision"], c["n_branches"]),
                  reverse=True)
    n_decision = sum(1 for r in recs if r.decision)
    entry: dict[str, Any] = {
        "n_lines": source.count("\n") + 1,
        "n_if": len(recs),
        "n_elif": sum(1 for r in recs if r.is_elif),
        "n_else": sum(
            1 for r in recs
            if r.node.orelse and not (
                len(r.node.orelse) == 1
                and isinstance(r.node.orelse[0], ast.If))),
        "n_decision_if": n_decision,
        "n_pipeline_if": len(recs) - n_decision,
        "decision_ratio": round(n_decision / len(recs), 3) if recs else 0.0,
        "max_if_depth": max((r.depth for r in recs), default=0),
        "n_clusters": len(clusters),
        "top_clusters": clusters[:TOP_K_CLUSTERS],
    }
    entry.update(_count_expressions(tree))
    rules = _router_rules(tree)
    if rules:
        entry.update(rules)
    return entry


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    files = sorted(p for p in SCOPE_DIR.glob("*.py") if p.name != "__init__.py")
    audit: dict[str, dict[str, Any]] = {}
    for path in files:
        audit[path.name] = audit_file(path)

    all_clusters = [
        {"file": name, **cluster}
        for name, entry in audit.items()
        for cluster in entry["top_clusters"]
    ]
    all_clusters.sort(
        key=lambda c: (c["n_decision"], c["n_branches"]), reverse=True)

    result = {
        "tool": "tools/audit_ifelse_density.py",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "scope": f"{SCOPE_DIR.relative_to(BASE).as_posix()}/*.py "
                 f"({len(files)}个顶层文件; logic/semantic/syntax子包不在本次范围)",
        "classification": {
            "decision": "test/body含verdict三态/NLI标签/通道方法名常量, "
                        "verdict关键字或引用, verify_*/unresolved调用, "
                        "或test中.kind/.method分派守卫",
            "pipeline": "其余(数据变换/格式校验/空值卫兵)",
            "cluster": "同一语句序列中连续If语句的run; if-elif链算1个语句, "
                       "链内elif/else计入分支数; 同时覆盖阶梯(早返回if块序列)"
                       "与链(单条if-elif)两种形态; 保留run≥2语句或分支数≥3",
            "note": "三元表达式与推导式if子句单独计数, 不入n_if",
        },
        "totals": {
            "n_files": len(files),
            "n_if": sum(e["n_if"] for e in audit.values()),
            "n_decision_if": sum(e["n_decision_if"] for e in audit.values()),
            "n_pipeline_if": sum(e["n_pipeline_if"] for e in audit.values()),
            "n_ternary": sum(e["n_ternary"] for e in audit.values()),
            "n_comprehension_if": sum(
                e["n_comprehension_if"] for e in audit.values()),
            "max_if_depth": max(
                (e["max_if_depth"] for e in audit.values()), default=0),
        },
        "focus_files": {name: audit.get(name) for name in FOCUS_FILES},
        "files": dict(sorted(audit.items(), key=lambda kv: -kv[1]["n_if"])),
        "top_decision_clusters_global": all_clusters[:10],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    totals = result["totals"]
    print(f"scope: {result['scope']}")
    print(f"总计: if={totals['n_if']} (决策型{totals['n_decision_if']}"
          f"/管道型{totals['n_pipeline_if']}), "
          f"三元={totals['n_ternary']}, "
          f"推导式if={totals['n_comprehension_if']}, "
          f"最大嵌套深度={totals['max_if_depth']}")
    print()
    header = (f"{'file':28s} {'if':>4s} {'elif':>4s} {'else':>4s} "
              f"{'dec':>4s} {'pipe':>4s} {'depth':>5s}  最大决策簇")
    print(header)
    print("-" * len(header))

    def _cluster_desc(entry: dict[str, Any]) -> str:
        top = entry["top_clusters"][0] if entry["top_clusters"] else None
        if not top:
            if entry["n_if"] == 0 and "keyword_rules" in entry:
                return "无if语句——纯关键词规则数据表"
            return ""
        return (f"{top['function']} L{top['lines'][0]}-"
                f"{top['lines'][1]} 分支{top['n_branches']}"
                f"(决策{top['n_decision']})")

    ordered = [n for n in FOCUS_FILES if n in audit] + [
        n for n in sorted(audit, key=lambda n: -audit[n]["n_if"])
        if n not in FOCUS_FILES]
    for name in ordered:
        entry = audit[name]
        rule_note = (f" [rules={entry['keyword_rules']}"
                     f"/terms={entry['keyword_terms']}]"
                     if "keyword_rules" in entry else "")
        print(f"{name:28s} {entry['n_if']:4d} {entry['n_elif']:4d} "
              f"{entry['n_else']:4d} {entry['n_decision_if']:4d} "
              f"{entry['n_pipeline_if']:4d} {entry['max_if_depth']:5d}  "
              f"{_cluster_desc(entry)}{rule_note}")
    print(f"\n输出: {OUT_PATH}")
    print("全局最大决策簇(前10):")
    for cluster in all_clusters[:10]:
        print(f"  {cluster['file']:28s} {cluster['function']}: "
              f"L{cluster['lines'][0]}-{cluster['lines'][1]} "
              f"语句{cluster['n_stmts']} 分支{cluster['n_branches']} "
              f"决策{cluster['n_decision']}")


if __name__ == "__main__":
    main()
