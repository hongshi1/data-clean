r"""补充12种不足类型: 从全文档chunks提取素材构造变异.

修复mutation_v2.py的12种不足(≤2条)类型:
  PARAM-01/02/05/06/07, TERM-06(数值类, 依赖正文数值)
  GJB-03/05/07/08/10(合规类, 依赖正文关键词)
  UC_NAME_MISMATCH(用例名)

策略: 不依赖pair的text.txt(素材太少), 从5231个chunks中
提取包含目标模式的句子, 构造声明对变异.

用法: python tools/mutation_v2_gapfill.py [--per-type 20]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
OUT = BASE / "data/gjb_438c/benchmark_v2/gapfill_mutations.jsonl"

NUM_PAT = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|毫秒|s|秒|min|分钟|小时|GB|MB|TB|KB|GHz|MHz|Hz|%)")

GAP_PATTERNS: dict[str, dict] = {
    "PARAM-01": {
        "desc": "时间约束",
        "pattern": r"(\d+\.?\d*)\s*(ms|毫秒|s|秒|min|分钟)",
        "conflict": "数值翻倍",
    },
    "PARAM-02": {
        "desc": "周期参数",
        "pattern": r"(?:周期|间隔|频率|定时)\D{0,15}(\d+\.?\d*)\s*(ms|毫秒|s|秒|Hz|kHz)",
        "conflict": "数值减半",
    },
    "PARAM-05": {
        "desc": "资源占用",
        "pattern": r"(?:CPU|内存|存储|磁盘|带宽|资源占用)\D{0,10}(\d+\.?\d*)\s*(GHz|MHz|GB|MB|TB|Mbps|%)",
        "conflict": "数值减半",
    },
    "PARAM-06": {
        "desc": "参数值域",
        "pattern": r"(?:不小于|不大于|至少|至多)\D{0,10}(\d+\.?\d*)\s*(GB|MB|TB|MHz|ms|秒|%|条|路)",
        "conflict": "数值翻倍",
    },
    "PARAM-07": {
        "desc": "存储容量时长",
        "pattern": r"(?:保存|存储|保留|留存)\D{0,10}(\d+\.?\d*)\s*(天|日|月|年|小时|GB|MB)",
        "conflict": "数值减半",
    },
    "TERM-06": {
        "desc": "量纲单位",
        "pattern": r"(\d+\.?\d*)\s*(秒|ms|分钟|小时|GB|MB|KB)",
        "conflict": "单位换算不等效",
    },
    "GJB-03": {
        "desc": "安全访问控制",
        "pattern": r"(访问控制|权限控制|身份认证|安全防护)",
        "conflict": "删除安全条款",
    },
    "GJB-05": {
        "desc": "需求可追溯性",
        "pattern": r"(追溯|追踪关系|映射关系)",
        "conflict": "删除追溯条款",
    },
    "GJB-07": {
        "desc": "软件自检",
        "pattern": r"(自检|开机检测|启动检测)",
        "conflict": "删除自检条款",
    },
    "GJB-08": {
        "desc": "掉电数据保护",
        "pattern": r"(掉电|断电|电源故障|掉电保护)",
        "conflict": "删除掉电保护条款",
    },
    "GJB-10": {
        "desc": "版本升级安全",
        "pattern": r"(版本升级|软件升级|回滚|热更新)",
        "conflict": "删除升级条款",
    },
    "UC_NAME_MISMATCH": {
        "desc": "用例名不一致",
        "pattern": r"用例",
        "conflict": "用例名改写",
    },
}

NAME_MAP = {
    "用户": "使用者", "管理": "管控", "获取": "采集",
    "查询": "检索", "处理": "处置", "监控": "监测",
}


def clean_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def extract_sentences(chunks: list) -> list[dict]:
    """从chunks提取含数值/关键词的句子."""
    sentences = []
    for c in chunks:
        text = clean_html(c.get("text", ""))
        if not text or len(text) < 20:
            continue
        # 按句号切分
        for sent in re.split(r"[。；;]", text):
            sent = sent.strip()
            if len(sent) >= 15:
                sentences.append({
                    "text": sent, "doc": c.get("doc", ""),
                    "section": c.get("section", ""),
                    "type": c.get("type", "text"),
                })
    return sentences


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-type", type=int, default=20)
    args = ap.parse_args()

    print("══ 补充12种不足类型 ══\n")

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    sentences = extract_sentences(chunks)
    print(f"可提取句子: {len(sentences)}句")

    rng = random.Random(42)
    mutations = []

    for ci, spec in GAP_PATTERNS.items():
        pat = re.compile(spec["pattern"])
        matches = []
        for s in sentences:
            for m in pat.finditer(s["text"]):
                matches.append({
                    "sentence": s, "match_start": m.start(),
                    "match_end": m.end(), "matched": m.group(0),
                })
                break  # 每句只取第一个匹配

        print(f"\n{ci}({spec['desc']}): {len(matches)}处素材")

        if not matches:
            print("  ✗ 无素材, 跳过")
            continue

        rng.shuffle(matches)
        n_generated = 0
        for m in matches[:args.per_type * 2]:
            if n_generated >= args.per_type:
                break

            sent_text = m["sentence"]["text"]
            doc = m["sentence"]["doc"]
            section = m["sentence"]["section"]

            if ci.startswith("PARAM") or ci == "TERM-06":
                # 数值类: 变异数值
                val_match = re.match(r"(\d+\.?\d*)(.*)", m["matched"])
                if not val_match:
                    continue
                old_val = float(val_match.group(1))
                unit = val_match.group(2)
                # 矛盾: 值变(翻倍或减半)
                new_val = old_val * 2 if old_val < 100 else old_val / 2
                new_matched = f"{new_val:g}{unit}"
                mutated = (sent_text[:m["match_start"]] + new_matched
                           + sent_text[m["match_end"]:])

                premise = f"文档{section}章节规定：{sent_text[:100]}"
                hypothesis = f"文档{section}章节规定：{mutated[:100]}"
                qa_explain = (f"位置{section}处，原文数值为{m['matched']}，"
                              f"变异为{new_matched}，构成{ci}型不一致。")

            elif ci.startswith("GJB"):
                # 合规类: 删除含关键词的句子
                premise = f"文档{section}章节包含条款：{sent_text[:100]}"
                hypothesis = f"文档{section}章节缺失该条款。"
                mutated = "(条款被删除)"
                new_matched = "(deleted)"
                qa_explain = (f"位置{section}处的{spec['desc']}条款「{sent_text[:50]}」"
                              f"被删除，构成GJB合规缺失。")

            elif ci == "UC_NAME_MISMATCH":
                # 用例名改写
                new_sent = sent_text
                for old_name, new_name in NAME_MAP.items():
                    if old_name in new_sent:
                        new_sent = new_sent.replace(old_name, new_name, 1)
                        break
                if new_sent == sent_text:
                    continue
                premise = f"表格中的用例描述：{sent_text[:100]}"
                hypothesis = f"图中的用例描述：{new_sent[:100]}"
                mutated = new_sent
                new_matched = "(名称改写)"
                qa_explain = (f"表格中的用例名与图中不一致，"
                              f"构成{ci}型不一致。")

            mutations.append({
                "mutation_id": f"GAP-{ci}-{n_generated + 1:04d}",
                "check_item": ci,
                "source_pair": "",
                "scene": "chunk_extract",
                "doc": doc.split("-")[0][:2] if doc else "?",
                "doc_name": doc[:20],
                "section": section,
                "expected_label": "inconsistent",
                "before": m["matched"][:50],
                "after": str(new_matched)[:50],
                "premise": premise,
                "hypothesis": hypothesis,
                "qa": {
                    "judge": {
                        "question": f"以下两处描述是否一致？\n位置A: {premise[:80]}\n位置B: {hypothesis[:80]}",
                        "answer": "不一致",
                        "label": "inconsistent",
                    },
                    "locate": {
                        "question": "不一致发生在哪个位置？",
                        "answer": f"文档{doc[:10]} §{section}",
                        "gold_location": {"doc": doc[:10], "section": section},
                    },
                    "explain": {
                        "question": "为什么这是不一致？",
                        "answer": qa_explain,
                        "conflict_type": ci,
                    },
                },
            })
            n_generated += 1

        print(f"  生成: {n_generated}条")

    # 落盘
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for m in mutations:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print("\n══ 合计 ══")
    print(f"  补充变异: {len(mutations)}条 → {OUT}")

    # 汇总: 合并后48种类型的完整覆盖
    from collections import Counter
    old = Counter(json.loads(line)["check_item"]
                  for line in open(BASE / "data/gjb_438c/benchmark_v2/mutations_v2.jsonl",
                                   encoding="utf-8"))
    new = Counter(m["check_item"] for m in mutations)
    combined = old + new

    ALL_48 = set(['TERM-01','TERM-02','TERM-03','TERM-04','TERM-05','TERM-06','TERM-07','TERM-08',
        'PARAM-01','PARAM-02','PARAM-05','PARAM-06','PARAM-07',
        'LOGIC-01','LOGIC-02','LOGIC-03','LOGIC-04','LOGIC-05',
        'LOGIC-08','LOGIC-09','LOGIC-10','LOGIC-11',
        'GJB-01','GJB-02','GJB-03','GJB-04','GJB-05','GJB-06','GJB-07','GJB-08','GJB-09','GJB-10',
        'TABLE_ITEM_MISSING','ACTOR_MISSING','STEP_MISSING','EXC_MISSING',
        'DIAGRAM_EXTRA','COMPONENT_MISSING','UC_NAME_MISMATCH','ORDER_CONFLICT'])

    print("\n合并后48种覆盖:")
    sufficient = 0
    for ci in sorted(ALL_48):
        n = combined.get(ci, 0)
        status = "✓" if n >= 5 else ("⚠" if n >= 3 else "✗")
        if n >= 5:
            sufficient += 1
        print(f"  {ci:<22} {n:>5}条 {status}")
    print(f"\n充足(≥5条): {sufficient}/40种")


if __name__ == "__main__":
    main()
