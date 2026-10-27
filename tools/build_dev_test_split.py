"""构建91QA的冻结dev/test切分 (P0: 修复dev-on-test效度缺陷).

问题: QAConsistencyModule的全部阈值/规则都是在91条QA+silver标签上看着调的
(dev-on-test), legacy 0.7185/0.800是同分布自评, 无法回答"held-out上还剩多少".

本脚本一次性构建并落盘冻结切分:
  1. 按question的主题聚类(功能/用例关键词, 有序规则first-match): 同一功能/
     用例的QA归同簇 —— 防同主题泄漏(同一BLOB功能簇的QA不允许分居两侧,
     否则"记住该主题"就能在test上兑现).
  2. 簇级原子分配到dev/test(整簇走一侧), 贪心最小化
     (规模不平衡, S/R silver不平衡) 的加权和, 大簇先分.
  3. 尺寸修复: 目标dev=45/test=46; 若贪心结果偏离, 用N-only簇换边修复
     (不动S/R分布).
  4. 落盘 data/gjb_438c/qa_frozen/dev_test_split_v1.json (seed=42冻结;
     重跑同seed逐字节一致; 断言 dev∩test=∅, dev∪test=全集).

硬规则: 切分只用question文本+silver标签, 不接触模块/预测 —— 切分本身
无泄漏; test split此后只用于最终评测(扫参严格只在dev).
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
SPLIT_PATH = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"

SEED = 42
TARGET_DEV = 45
TARGET_TEST = 46
VERDICTS = ("support", "refute", "not_in_evidence")

# 主题聚类规则: 有序, first-match-wins. 每条 = (question正则, 主题名).
# 规则按"最具体的功能/用例名在前"排序; 混合主题问题(如"JSON输出与二维数组
# 输出的区别")归入其命中的第一个主题 —— 两个主题的簇都不收对侧同类QA,
# 泄漏防护不受影响.
TOPIC_RULES: tuple[tuple[str, str], ...] = (
    (r"BLOB", "blob_data"),
    (r"获取LOB", "get_lob"),
    (r"获取FLOAT", "get_float"),
    (r"获取STRING", "get_string"),
    (r"获取INT|逐行获取", "get_int"),
    (r"二维数组", "array_output"),
    (r"JSON输出", "json_output"),
    (r"SQL文件输出", "sql_file_output"),
    (r"数据查询|查询数据|SQL查询|查询结果", "data_query"),
    (r"获取错误信息|错误信息获取", "get_errinfo"),
    (r"修改数据", "modify_record"),
    (r"增加数据记录", "add_record"),
    (r"删除数据记录", "delete_record"),
    (r"数据库关闭", "db_close"),
    (r"数据库连接|无法连接到服务端|无法通过数据库连接", "db_conn"),
    (r"读取配置文件", "cfg_conn"),
    (r"数据库初始化", "db_init"),
    (r"连接池", "conn_pool"),
    (r"缓存", "hot_cache"),
    (r"数据源适配", "datasource"),
    (r"代码生成", "codegen"),
    (r"对象化访问", "obj_access"),
    (r"SQL访问", "sql_access"),
    (r"数据统一访问", "unified_svc"),
    (r"运行状态", "run_state"),
    (r"连接方式", "conn_mode"),
    (r"接口", "interface"),
    (r"重用方式|唯一标识符", "reuse_registry"),
)

RATIONALE = (
    "91QA按question的功能/用例关键词聚类(29个主题簇, first-match有序规则, "
    "规则见TOPIC_RULES); 簇级原子分配(整簇同侧, 防同主题泄漏), 贪心最小化"
    "规模与S/R silver不平衡(权重3:4:4), 大簇先分, random.Random(42)洗牌"
    "同尺寸簇的次序; 目标dev=45/test=46, 偏离时用N-only簇换边修复. "
    "切分只依赖question文本与silver标签, 不依赖任何模块预测. "
    "冻结后test只用于最终评测; 所有扫参只在dev."
)


def question_topic(question: str) -> str:
    """Return the topic cluster of a question (first matching rule wins)."""
    for pattern, topic in TOPIC_RULES:
        if re.search(pattern, question):
            return topic
    return "misc"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def load_corpora() -> tuple[list[dict], dict[str, str]]:
    """Load the frozen QA corpus and its silver labels (id -> verdict)."""
    rows = read_jsonl(QA_FROZEN)
    labels = {row["instance_id"]: row["final_verdict"]
              for row in read_jsonl(SILVER)}
    missing = [row["instance_id"] for row in rows
               if row["instance_id"] not in labels]
    if missing:
        raise ValueError(f"silver标签缺失: {missing}")
    return rows, labels


def _stat(items: list[tuple[str, str]]) -> tuple[int, int, int]:
    return (len(items),
            sum(1 for _, v in items if v == "support"),
            sum(1 for _, v in items if v == "refute"))


def _assign_clusters(
        clusters: dict[str, list[tuple[str, str]]],
        seed: int) -> dict[str, list[tuple[str, str]]]:
    """Greedy cluster-level assignment balancing size and S/R silver.

    Largest clusters first (seed-shuffled within equal sizes); a cluster is
    placed atomically on the side minimizing
    3*|size gap| + 4*|S gap| + 4*|R gap| after placement; ties prefer the
    smaller side, then dev.
    """
    rng = random.Random(seed)
    names = sorted(clusters)
    rng.shuffle(names)
    names.sort(key=lambda name: -len(clusters[name]))
    sides: dict[str, list[tuple[str, str]]] = {"dev": [], "test": []}
    for name in names:
        items = clusters[name]
        best, best_key = None, None
        for side in ("dev", "test"):
            other = "test" if side == "dev" else "dev"
            merged = sides[side] + items
            n, s, r = _stat(merged)
            on, os_, or_ = _stat(sides[other])
            key = (3 * abs(n - on) + 4 * abs(s - os_) + 4 * abs(r - or_),
                   n, side == "test")
            if best_key is None or key < best_key:
                best, best_key = side, key
        sides[best].extend(items)
    return sides


def _repair_size(
        sides: dict[str, list[tuple[str, str]]],
        clusters: dict[str, list[tuple[str, str]]]) -> None:
    """Nudge the split to dev=45/test=46 with neutral (N-only) cluster moves.

    Only clusters without S/R members are movable, so the silver
    stratification is untouched. Each step moves the movable cluster whose
    size best matches the remaining size gap (smallest-first on ties);
    iterations are bounded — a hard assert downstream fails loudly if the
    canonical sizes are unreachable instead of looping forever.
    """
    for _ in range(2 * len(clusters) + 2):
        diff = TARGET_DEV - len(sides["dev"])
        if diff == 0:
            return
        donor = "test" if diff > 0 else "dev"
        needed = abs(diff)
        donor_ids = {iid for iid, _ in sides[donor]}
        movable = sorted(
            (topic for topic, items in clusters.items()
             if all(iid in donor_ids for iid, _ in items)
             and all(v == "not_in_evidence" for _, v in items)),
            key=lambda topic: (abs(len(clusters[topic]) - needed),
                               len(clusters[topic]), topic))
        if not movable:
            break
        topic = movable[0]
        moved = clusters[topic]
        sides[donor] = [item for item in sides[donor] if item not in moved]
        sides["test" if donor == "dev" else "dev"] = (
            sides["test" if donor == "dev" else "dev"] + moved)


def build_split(rows: list[dict], silver: dict[str, str],
                seed: int = SEED) -> dict:
    """Build the frozen dev/test split dict (pure function of inputs+seed)."""
    clusters: dict[str, list[tuple[str, str]]] = {}
    topic_of: dict[str, str] = {}
    for row in rows:
        iid = row["instance_id"]
        topic = question_topic(row["question"])
        topic_of[iid] = topic
        clusters.setdefault(topic, []).append((iid, silver[iid]))
    sides = _assign_clusters(clusters, seed)
    _repair_size(sides, clusters)

    dev_ids = sorted(iid for iid, _ in sides["dev"])
    test_ids = sorted(iid for iid, _ in sides["test"])
    all_ids = sorted(row["instance_id"] for row in rows)
    assert not set(dev_ids) & set(test_ids), "dev与test存在交集"
    assert sorted(dev_ids + test_ids) == all_ids, "dev∪test != 全集"
    assert len(dev_ids) == TARGET_DEV, f"dev={len(dev_ids)} != {TARGET_DEV}"
    assert len(test_ids) == TARGET_TEST, f"test={len(test_ids)} != {TARGET_TEST}"

    dev_set = set(dev_ids)
    cluster_assignment = {
        topic: ("dev" if any(iid in dev_set for iid, _ in items) else "test")
        for topic, items in clusters.items()}
    dist = {"dev": _dist(silver, dev_ids), "test": _dist(silver, test_ids)}
    return {
        "version": "dev_test_split_v1",
        "seed": seed,
        "source": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "silver_labels": ("data/gjb_438c/runs/review_qa_with_glm53_582b51e5"
                          "_20261021_145212/final_labels.jsonl"),
        "silver_type": "glm53_silver_not_gold",
        "n_total": len(all_ids),
        "dev": dev_ids,
        "test": test_ids,
        "cluster_map": {iid: topic_of[iid] for iid in all_ids},
        "cluster_assignment": cluster_assignment,
        "n_clusters": len(clusters),
        "silver_distribution": dist,
        "rationale": RATIONALE,
    }


def _dist(silver: dict[str, str], ids: list[str]) -> dict[str, int]:
    return {v: sum(1 for iid in ids if silver[iid] == v) for v in VERDICTS}


def load_split(path: Path = SPLIT_PATH) -> dict:
    """Load and validate the frozen split file (invariants checked)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    dev, test = data["dev"], data["test"]
    if set(dev) & set(test):
        raise ValueError("dev与test存在交集")
    if sorted(dev + test) != sorted(data["cluster_map"]):
        raise ValueError("dev∪test != cluster_map全集")
    if len(dev) != TARGET_DEV or len(test) != TARGET_TEST:
        raise ValueError(f"切分尺寸异常: dev={len(dev)} test={len(test)}")
    return data


def main() -> None:
    rows, silver = load_corpora()
    split = build_split(rows, silver, seed=SEED)
    SPLIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPLIT_PATH.write_text(
        json.dumps(split, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"written: {SPLIT_PATH}")
    print(f"clusters: {split['n_clusters']}  "
          f"dev: {len(split['dev'])}  test: {len(split['test'])}")
    for side in ("dev", "test"):
        print(f"  {side} silver: {split['silver_distribution'][side]}")
    topics_dev = {split["cluster_map"][iid] for iid in split["dev"]}
    topics_test = {split["cluster_map"][iid] for iid in split["test"]}
    assert not topics_dev & topics_test, "同一主题簇跨侧(泄漏)"
    print(f"topic overlap dev∩test: {sorted(topics_dev & topics_test)} (空=无泄漏)")


if __name__ == "__main__":
    main()
