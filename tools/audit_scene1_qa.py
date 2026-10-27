"""场景1高质量QA(对方提供)适配审计: 91条QA ↔ 04数据统一访问SRS证据定位.

输入:
  docs/doc11/场景1-软件需求规格辅助生成场景补发数据/高质量问答对（...04数据统一访问服务...）.json
  data/gjb_438c/mineru_standard/04数据统一访问服务软件需求规格说明-终稿/office/*_content_list.json

产出: data/gjb_438c/scene1_qa_audit.json
  每条: id/question/answer/family/tentative_check_items/anchors/evidence_hits/triage
  仅审计定位, 不标注gold_verdict(留给M3人工双标).

triage规则:
  locatable   - 强锚点(领域实体/数值/E编号/表号)在04号文档命中≥1条解析块
  weak        - 仅弱锚点命中(通用词), 需上游召回+人工复核
  unlocatable - 无命中, 需人工判断是否问题超范围或解析缺失
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

QA_PATH = (BASE / "docs/doc11/场景1-软件需求规格辅助生成场景补发数据"
           / "高质量问答对（配套样例数据中：04数据统一访问服务软件需求规格说明）.json")
CL_GLOB = "data/gjb_438c/mineru_standard/04数据统一访问服务软件需求规格说明-终稿/office/*_content_list.json"
OUT_PATH = BASE / "data/gjb_438c/scene1_qa_audit.json"

# ── 领域锚点(强): 04号SRS的SQL访问/数据类型/功能用例词 ──
STRONG_ANCHORS = [
    "BLOB", "FLOAT", "LOB", "INT", "STRING", "二维数组", "SQL文件",
    "数据查询", "查询数据", "修改数据", "增加数据记录", "删除数据记录",
    "逐行获取", "连接池", "服务端", "用例", "前置条件", "异常流",
    "需求标识", "重用", "性能", "响应时间", "桌面", "平板", "手持",
    # 04号SRS实际功能词(补: 覆盖数据源适配/对象化访问/代码生成等weak条目)
    "数据源适配", "对象化访问", "代码生成", "SQL访问", "JSON输出",
    "错误信息", "数据库连接", "状态图", "内部接口", "接口标识",
    "适应性需求", "应用软件", "CSCI", "数据库初始化", "事务",
]
# ── 弱锚点(通用词): 只能作辅助 ──
WEAK_ANCHORS = ["系统", "功能", "数据", "接口", "操作", "结果", "提示", "步骤"]

FAMILY_PATTERNS: list[tuple[str, str]] = [
    ("异常/错误", r"异常|错误|失败|无法连接|报错"),
    ("主事件流/步骤", r"主事件流|详细步骤|关键步骤|流程"),
    ("前置条件", r"前置条件|前提"),
    ("参与者", r"参与者"),
    ("状态/阶段/设备", r"阶段|运行状态|设备|形态"),
    ("接口/参数", r"接口|参数|字段|类型|大小|数量|值"),
    ("功能/支持", r"功能|支持|包括|哪些"),
    ("规则/一致性", r"一致|冲突|是否|符合|规范|要求"),
]
FAMILY_DEFAULT = "其他"

# family → 40项候选(初稿, 待taxonomy v2人审; 空列表=纯事实核验无直接映射)
FAMILY_CHECK_ITEMS: dict[str, list[str]] = {
    "异常/错误": ["LOGIC-02"],
    "主事件流/步骤": ["LOGIC-03"],
    "前置条件": [],
    "参与者": [],
    "状态/阶段/设备": [],
    "接口/参数": ["PARAM"],
    "功能/支持": ["TERM-03"],
    "规则/一致性": ["PARAM-01", "TERM-03"],
    FAMILY_DEFAULT: [],
}


def family_of(question: str) -> str:
    for name, pat in FAMILY_PATTERNS:
        if re.search(pat, question):
            return name
    return FAMILY_DEFAULT


def anchors_of(text: str) -> tuple[list[str], list[str]]:
    """返回(强锚点, 弱锚点): 领域词 + 数值/E编号/表号."""
    strong = [a for a in STRONG_ANCHORS if a in text]
    # 数值(如65535; 中文语境无\b边界, 用环视)、异常流编号(E1)、表引用(表21)
    for m in re.findall(r"(?<!\d)\d{4,}(?!\d)", text):
        strong.append(m)
    for m in re.findall(r"异常流\s*(E\d+)", text):
        strong.append(m)
    for m in re.findall(r"表\s*(\d+)", text):
        strong.append(f"表{m}")
    weak = [a for a in WEAK_ANCHORS if a in text]
    return strong, weak


def item_text(it: dict) -> str:
    t = str(it.get("text", "") or "")
    tb = str(it.get("table_body", "") or "")
    return re.sub(r"<[^>]+>", "", t + " " + tb)


def item_loc(it: dict, idx: int) -> dict:
    caps = it.get("table_caption") or []
    cap = caps[0] if isinstance(caps, list) and caps else (caps or "")
    txt = str(it.get("text", "") or "")
    sec = ""
    m = re.match(r"^(\d+(?:\.\d+)*)\s", txt.strip())
    if m:
        sec = m.group(1)
    return {"idx": idx, "type": it.get("type", ""), "section": sec, "caption": cap}


def hit_check(anchor: str, corpus: str) -> bool:
    return anchor in corpus


def main() -> None:
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
    cl_path = next((BASE / CL_GLOB).parent.glob(Path(CL_GLOB).name))
    cl = [it for it in json.loads(cl_path.read_text(encoding="utf-8"))
          if isinstance(it, dict)]
    texts = [item_text(it) for it in cl]
    corpus_full = " ".join(texts)

    out_entries: list[dict] = []
    triage_counter: Counter = Counter()
    family_counter: Counter = Counter()
    for i, x in enumerate(qa, 1):
        question = str(x.get("instruction", "")).strip()
        answer = str(x.get("output", "")).strip()
        fam = family_of(question)
        family_counter[fam] += 1
        strong, weak = anchors_of(question + " " + answer)
        hits: list[dict] = []
        hit_anchors: list[str] = []
        for a in strong:
            n_hit = 0
            for idx, (it, txt) in enumerate(zip(cl, texts, strict=True)):
                if a in txt:
                    hits.append(item_loc(it, idx))
                    hit_anchors.append(a)
                    n_hit += 1
                    if n_hit >= 3:  # 每锚点最多记3个命中块
                        break
            # 数值锚点需全corpus命中确认(如65535全文唯一)
            if n_hit == 0 and hit_check(a, corpus_full):
                hit_anchors.append(a)
        # 去重(idx, 保持顺序)
        seen: set[int] = set()
        uniq_hits = [h for h in hits if not (h["idx"] in seen or seen.add(h["idx"]))]
        if strong and hit_anchors:
            triage = "locatable"
        elif weak:
            triage = "weak"
        else:
            triage = "unlocatable"
        triage_counter[triage] += 1
        out_entries.append({
            "id": f"S1QA-{i:03d}",
            "question": question,
            "answer": answer,
            "family": fam,
            "tentative_check_items": FAMILY_CHECK_ITEMS.get(fam, []),
            "strong_anchors": strong,
            "weak_anchors": weak,
            "hit_anchors": sorted(set(hit_anchors)),
            "evidence_hits": uniq_hits[:8],
            "triage": triage,
            "gold_verdict": None,  # M3人工双标, 审计不判
        })

    result = {
        "meta": {
            "version": "scene1_qa_audit_v1",
            "date": "2026-10-20",
            "total": len(out_entries),
            "source_qa": QA_PATH.relative_to(BASE).as_posix(),
            "source_srs": cl_path.relative_to(BASE).as_posix(),
            "families": dict(sorted(family_counter.items())),
            "triage": dict(sorted(triage_counter.items())),
            "notes": [
                "对方提供的场景1示例QA(04数据统一访问SRS配套)",
                "tentative_check_items为40项候选初稿, 待taxonomy v2人审",
                "gold_verdict留空: 审计只做证据定位, 不生成gold",
                "evidence_hits为锚点词命中块, 非上游正式召回结果",
            ],
        },
        "entries": out_entries,
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"scene1_qa_audit: {len(out_entries)}条")
    print(f"families: {dict(sorted(family_counter.items()))}")
    print(f"triage: {dict(sorted(triage_counter.items()))}")
    print(f"saved → {OUT_PATH}")


if __name__ == "__main__":
    main()
