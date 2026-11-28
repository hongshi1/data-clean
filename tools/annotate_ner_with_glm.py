"""GLM标注NER训练数据: 五场景文档 → GLM-5.3实体标注 → BIO格式训练集.

设计:
- 从各场景文档采集文本样本
- GLM-5.3教师标注实体span(文本+类型+位置) — 走llm_teacher缓存
- 转换为BIO token分类格式(供chinese-roberta微调)
- 每场景产出一个训练文件 + 合并五场景统一训练集

用法: DEV_DB=sqlite python tools/annotate_ner_with_glm.py [--scene srs]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "deploy/nkuDataProject/backend"))
sys.stdout.reconfigure(encoding="utf-8")

#: 场景实体类型定义(标注prompt用)
SCENE_ENTITY_TYPES: dict[str, list[str]] = {
    "srs": [
        "功能(系统功能名,如'数据获取转换')",
        "接口(系统间接口,如'数据库关闭接口')",
        "参数(技术参数,如'响应时间')",
        "标识符(需求ID,如'PZXQ-GN-SQLFW')",
        "设备(硬件设备名)",
        "章节(章节编号,如'3.2.1')",
        "标准(规范标准名,如'GJB 438C')",
    ],
    "rd_plan": [
        "工序(加工/检验步骤名)",
        "工艺(工艺方法,如'冲压')",
        "材料(原材料/辅助材料名)",
        "设备(生产设备名)",
        "方案(设计方案名)",
        "参数(工艺参数,如'总压力')",
    ],
    "quality_defect": [
        "缺陷(质量缺陷类型,如'密度超差')",
        "检验项(检验项目,如'外观检验')",
        "公差(公差要求,如'±0.15max')",
        "工序(工序名)",
        "参数(质量参数,如'密度')",
        "原因(缺陷成因,如'5M1E')",
    ],
    "engine_maint": [
        "故障(故障现象,如'A通道同步异常')",
        "部件(发动机部件,如'滑油系统')",
        "系统(子系统名)",
        "参数(监控参数,如'滑油压力')",
        "工序(维护工序)",
        "手册(维护手册章节)",
    ],
    "kg_supervision": [
        "人员(人员/角色)",
        "PPE(个人防护装备,如'安全帽')",
        "行为(人员行为,如'吸烟'/'倒地')",
        "位置(位置区域,如'疏散通道')",
        "物品(非PPE物品,如'手机')",
        "状态(人员状态,如'佩戴'/'未佩戴')",
    ],
}

#: 每场景采样数
SAMPLES_PER_SCENE = 30

#: GLM标注prompt模板(简化: 只标注文本+类型, 位置本地计算)
_PROMPT_TEMPLATE = """从以下文本中标注所有实体。

文本: {text}

实体类型:
{entity_types}

返回JSON数组(标注所有出现的实体,不要遗漏):
[{{"text": "实体原文", "type": "类型名"}}]

注意: 只标注文本中实际出现的实体; 类型名不带括号说明; 没有实体返回[]"""


def _find_positions(text: str, entities: list[dict]) -> list[dict]:
    """GLM返回的实体(无位置) → 本地计算字符位置."""
    result = []
    used = []
    for e in entities:
        word = str(e.get("text", "")).strip()
        if not word:
            continue
        # 找第一个未使用的位置
        start = 0
        while True:
            idx = text.find(word, start)
            if idx < 0:
                break
            if not any(s < idx + len(word) and idx < en for s, en in used):
                used.append((idx, idx + len(word)))
                result.append({"text": word,
                               "type": str(e.get("type", "O")),
                               "start": idx, "end": idx + len(word)})
                break
            start = idx + 1
    return result


def collect_texts(scene: str, n: int) -> list[dict]:
    """从场景数据采集文本样本."""
    import sqlite3
    db_path = BASE / "deploy/nkuDataProject/backend/srs_dev.db"
    if scene == "kg_supervision":
        qa_path = (BASE / "deploy/nkuDataProject/data/kg_supervision"
                   "/qa_dataset.jsonl")
        if qa_path.exists():
            recs = [json.loads(line) for line in
                    qa_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            out = []
            for i, r in enumerate(recs[:n]):
                convs = r.get("conversations", [])
                for c in convs:
                    if c.get("from") == "user":
                        out.append({"id": "kg_{}".format(i),
                                    "text": str(c.get("value", ""))})
                        break
            return out

    # engine_maint: em_meta.json
    if scene == "engine_maint":
        em_path = (BASE / "deploy/nkuDataProject/frontend/js/consist"
                   "/em_meta.json")
        if em_path.exists():
            meta = json.loads(em_path.read_text(encoding="utf-8"))
            ds = meta.get("datasets", [])
            return [{"id": "em_{}".format(d.get("num", i)),
                     "text": "{} {}".format(d.get("name", ""),
                                             d.get("question", ""))}
                    for i, d in enumerate(ds[:n])]

    # rd_plan: separate sqlite
    if scene == "rd_plan":
        rd_path = (BASE / "deploy/nkuDataProject/backend/rd_plan.sqlite")
        if rd_path.exists():
            con_rd = sqlite3.connect(str(rd_path))
            rows_rd = con_rd.execute(
                "SELECT question FROM qa_pairs "
                "WHERE LENGTH(question) > 15 LIMIT ?",
                (n,)).fetchall()
            con_rd.close()
            return [{"id": "rd_{}".format(i), "text": r[0][:500]}
                    for i, r in enumerate(rows_rd)]

    # quality_defect: via API (documents endpoint has text metadata)
    if scene == "quality_defect":
        try:
            import urllib.request as _ur
            r = _ur.urlopen(
                "http://127.0.0.1:8300/api/quality-defect/documents",
                timeout=15)
            j = json.loads(r.read())
            docs = j.get("data", j).get("items", [])
            return [{"id": "qd_{}".format(d.get("source_id", i)),
                     "text": "{} {} {}".format(
                         d.get("product_name", ""),
                         d.get("category", ""),
                         d.get("source_path", ""))}
                    for i, d in enumerate(docs[:n])]
        except Exception:
            pass

    # srs + default: elements table
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        "SELECT e.text, e.section, s.source_id FROM elements e "
        "JOIN qa_sources s ON e.source_id = s.id "
        "WHERE s.scene = ? AND LENGTH(e.text) > 20 "
        "ORDER BY RANDOM() LIMIT ?",
        (scene, n)).fetchall()
    con.close()
    return [{"id": "{}_{}".format(scene, i), "text": r[0][:500]}
            for i, r in enumerate(rows)]


def glm_annotate(text: str, scene: str) -> list[dict]:
    """GLM-5.3标注文本中的实体(直接API调用, 避开contract截断)."""
    import sys as _sys
    import urllib.request as _ur
    _sys.path.insert(0, str(BASE / "tools"))
    from ai_config import GLM_KEY, GLM_URL, GLM_MODEL

    entity_types = "\n".join(f"- {t}" for t in
                             SCENE_ENTITY_TYPES.get(scene, []))
    body = json.dumps({
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": "返回JSON数组"},
            {"role": "user", "content":
             f"从以下文本中标注所有实体:\n{text}\n\n"
             f"类型:\n{entity_types}\n"
             f"返回: [{{\"text\":\"实体原文\",\"type\":\"类型名\"}}]"}
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
    }).encode()
    req = _ur.Request(GLM_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + GLM_KEY,
    })
    try:
        resp = _ur.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        content = (result.get("choices", [{}])[0]
                   .get("message", {}).get("content", ""))
        # 解析JSON(处理markdown代码围栏)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content
            content = content.rsplit("```", 1)[0].strip()
        import re as _re
        m = _re.search(r"\[.*\]", content, _re.S)
        if m:
            parsed = json.loads(m.group())
            if isinstance(parsed, list):
                entities = [r for r in parsed if isinstance(r, dict)
                            and "text" in r and "type" in r]
                return _find_positions(text, entities)
        return []
    except Exception as e:
        print(f"  [GLM] 标注失败: {str(e)[:60]}")
        return []


def text_to_bio(text: str, entities: list[dict]) -> list[dict]:
    """文本+实体标注 → BIO token序列(字符级,后续可转token级)."""
    # 按位置排序,去除重叠
    ents = sorted(entities, key=lambda e: int(e.get("start", 0)))
    spans = []
    last_end = 0
    for e in ents:
        start, end = int(e.get("start", 0)), int(e.get("end", 0))
        if start >= last_end and start < len(text) and end <= len(text):
            spans.append((start, end, str(e.get("type", "O"))))
            last_end = end

    # 生成字符级BIO标签
    labels = ["O"] * len(text)
    for start, end, etype in spans:
        labels[start] = f"B-{etype}"
        for i in range(start + 1, end):
            labels[i] = f"I-{etype}"

    # 压缩为非O span列表(高效存储)
    bio_spans = []
    i = 0
    while i < len(labels):
        if labels[i] != "O":
            j = i
            while j < len(labels) and labels[j].startswith(("B-", "I-")):
                j += 1
            bio_spans.append({
                "start": i, "end": j,
                "text": text[i:j],
                "label": labels[i][2:] if labels[i].startswith("B-") else
                         labels[i][2:],
                "bio": labels[i:j],
            })
            i = j
        else:
            i += 1

    return {"text": text, "spans": bio_spans,
            "n_entities": len(bio_spans)}


def annotate_scene(scene: str, n: int, out_dir: Path) -> Path:
    """标注一个场景的文本."""
    print(f"\n{'='*60}")
    print(f"场景: {scene} (采样 {n} 条)")
    print(f"{'='*60}")

    texts = collect_texts(scene, n)
    if not texts:
        print("  无文本数据, 跳过")
        return out_dir / f"ner_{scene}_empty.jsonl"

    out_path = out_dir / f"ner_{scene}.jsonl"
    results = []
    total_ents = 0
    for i, t in enumerate(texts):
        text = t["text"]
        if not text or len(text.strip()) < 10:
            continue
        print(f"  [{i+1}/{len(texts)}] 标注 {text[:40]}...", end="",
              flush=True)
        entities = glm_annotate(text, scene)
        bio = text_to_bio(text, entities)
        bio["scene"] = scene
        bio["id"] = t["id"]
        results.append(bio)
        total_ents += bio["n_entities"]
        print(f" {bio['n_entities']}实体")

    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results)
        + "\n", encoding="utf-8")
    print(f"  → {out_path.name}: {len(results)}条, {total_ents}实体")
    return out_path


def merge_all(out_dir: Path) -> Path:
    """合并五场景为统一训练集."""
    merged_path = out_dir / "ner_all_scenes_train.jsonl"
    all_rows = []
    for scene in SCENE_ENTITY_TYPES:
        p = out_dir / f"ner_{scene}.jsonl"
        if p.exists():
            rows = [json.loads(line) for line in
                    p.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
            all_rows.extend(rows)
    merged_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_rows)
        + "\n", encoding="utf-8")
    from collections import Counter
    scene_counts = Counter(r["scene"] for r in all_rows)
    ent_counts = Counter()
    for r in all_rows:
        for s in r.get("spans", []):
            ent_counts[s.get("label", "?")] += 1
    print(f"\n{'='*60}")
    print(f"合并训练集: {merged_path.name}")
    print(f"  总条目: {len(all_rows)}")
    print(f"  场景分布: {dict(scene_counts)}")
    print(f"  实体类型分布(top15): {dict(ent_counts.most_common(15))}")
    print(f"  总实体数: {sum(ent_counts.values())}")
    return merged_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=str, default="all",
                        help="场景ID或'all'")
    parser.add_argument("--n", type=int, default=SAMPLES_PER_SCENE,
                        help="每场景采样数")
    parser.add_argument("--out-dir", type=Path,
                        default=BASE / "data/gjb_438c/distillation/ner_train")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    scenes = ([args.scene] if args.scene != "all"
              else list(SCENE_ENTITY_TYPES))
    for scene in scenes:
        annotate_scene(scene, args.n, args.out_dir)
    if args.scene == "all":
        merge_all(args.out_dir)


if __name__ == "__main__":
    main()
