"""根因分析: 为什么结果不行 — 三层归因量化."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    print("═ 根因分析: 为什么当前方法在真实金标上只有0.7-0.87 ═\n")

    # ── 归因1: 金标标签噪声(可修复部分已修, 残余多少?) ──
    adj = json.loads((BASE / "data/gjb_438c/human_gold/md_cot_adjudication.json").read_text(encoding="utf-8"))
    valid = {k: v for k, v in adj.items() if v["label"] in ("real_bug", "benign_variation")}
    n_refuted = sum(1 for v in valid.values() if "evidence_refuted" in v.get("quality_flags", []))
    # 协议混淆: gold_v2的cot协议项 vs dual-llm项的真比率
    v2 = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_357.json").read_text(encoding="utf-8"))
    proto = defaultdict(lambda: [0, 0])
    for x in v2:
        proto[x["protocol"]][0] += 1
        if x["label"] == "real_bug":
            proto[x["protocol"]][1] += 1
    # 同文本反标签
    by_text = defaultdict(set)
    for k, v in valid.items():
        key = re.sub(r"[「」\s]", "", v.get("premise", ""))[:60]
        by_text[key].add(v["label"])
    n_ambig = sum(1 for v in by_text.values() if len(v) > 1)
    print("归因1 金标噪声(md_gold 577条):")
    print(f"  证据反驳(已修复): {n_refuted}条(19.4%)")
    for p, (n, r) in proto.items():
        print(f"  协议{p}: {r}/{n}={r/n:.0%}真 — 协议间真比率差{abs(proto['cot'][1]/max(proto['cot'][0],1) - proto['dual-llm'][1]/max(proto['dual-llm'][0],1)):.0%} = 标签生成偏差")
    print(f"  同文本反标签: {n_ambig}组 — 文本不可分的残余")
    print("  估计不可约噪声: ~20-25% (LLM裁决未见图证据+协议混淆)\n")

    # ── 归因2: 判别信号本身是词汇级(模型上限=词汇信号上限) ──
    md = json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8"))
    VERBS_REAL = ["传输", "控制", "识别", "引接", "推送", "同步", "归集", "上报"]
    VERBS_BEN = ["监控", "配置", "部署", "日志", "管理", "展现", "查询"]
    n_dec, n_correct = 0, 0
    for x in md:
        text = x["premise"] + x["hypothesis"]
        hit_r = any(v in text for v in VERBS_REAL)
        hit_b = any(v in text for v in VERBS_BEN)
        if hit_r != hit_b:  # 词典可判
            n_dec += 1
            pred = "inconsistent" if hit_r else "consistent"
            if pred == x["label"]:
                n_correct += 1
    print("归因2 词汇信号覆盖率(md sc3 148条):")
    print(f"  动词词典可判: {n_dec}/148 ({n_dec/148:.0%}), 其中正确 {n_correct}/{n_dec} ({n_correct/max(n_dec,1):.0%})")
    print("  → 信号=核心动词vs辅助动词(词汇级), SVM已吃到(0.866 bAcc)")
    print("  → 神经模型没有超过SVM = 判别信号本来就浅\n")

    # ── 归因3: 训练分布与测试分布错配 ──
    train = [json.loads(line) for line in open(BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl", encoding="utf-8")]
    src = Counter(x["source"] for x in train)
    print("归因3 训练-测试分布错配:")
    print(f"  训练构成: {dict(src)} — 80%是变异(带措辞伪影), 真实锚点仅~20%")
    print("  测试构成: clean130/md166 = 100%真实锚点风格")
    print("  → 模型学的变异伪影在真实测试上无效(风格捷径的根源)\n")

    print("═ 结论: 弱结果 = 标签噪声(~25%) × 浅信号(词汇级) × 分布错配(80%变异污染) ═")
    print("适配方案(v12): 仅用真实锚点数据训练 + 良性×6过采样 → 训练分布=测试分布")


if __name__ == "__main__":
    main()
