r"""NLI零样本评测: Erlangshen(中文) + mDeBERTa(多语言) × 真实SRS矛盾对
测试对来自doc11 gold标记与04文档原文(非自制语料)
用法: .venv-nli\Scripts\python.exe tools\nli_realdata_test.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from torch_dll_fix import preload_torch_dlls  # noqa: E402

preload_torch_dlls()
import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE, "models", "nli")
torch.set_grad_enabled(False)

# ════════════════════════════════════════════════════════════════
# 真实测试对: (premise文档事实, hypothesis QA声明/变体, 期望标签, 类别)
# P全部来自04号文档原文; H来自doc11真实QA答案或其变体
# ════════════════════════════════════════════════════════════════
BLOB_ENUM = "BLOB数据操作功能包括：BLOB数据插入、BLOB删除数据记录、BLOB数据查询功能"
BLOB_USECASE = "BLOB数据操作包括三个子用例：BLOB数据插入、BLOB数据修改、BLOB数据查询"
PAIRS = [
    # —— 枚举冲突(gold#1/#2/#3) ——
    (BLOB_ENUM, "BLOB数据操作包括修改、查询和插入", "contradiction", "枚举冲突"),
    (BLOB_ENUM, "BLOB数据操作包括插入、删除、查询功能", "entailment", "枚举一致"),
    (BLOB_ENUM, "对大字段数据进行删除、更新和查询", "contradiction", "枚举冲突-更新"),
    (BLOB_USECASE, "BLOB数据操作包括插入、删除、查询", "contradiction", "文档自矛盾"),
    # —— 术语变体 ——
    ("此功能在桌面版、平板版、手持版提供并使用", "此功能在桌面、平版、手持设备上提供并使用",
     "entailment", "术语变体-平版"),
    # —— 参数(数值) ——
    ("系统在1秒内查询最多1000条数据", "系统在1秒内查询最多500条数据", "contradiction", "参数冲突"),
    ("系统在1秒内查询最多1000条数据", "系统能在1秒内查询最多1000条数据", "entailment", "参数一致"),
    ("每个BLOB数据的大小不超过65535字节", "BLOB数据的大小不超过10000字节", "contradiction", "参数冲突-BLOB"),
    ("每个BLOB数据的大小不超过65535字节", "BLOB数据大小上限为65535字节", "entailment", "参数一致-BLOB"),
    # —— 无关/外推(gold#6) ——
    ("系统从连接池中获取数据库的连接句柄执行SQL语句", "逐行获取INT值的功能常用于库存管理和成绩评分系统",
     "neutral", "外推-无关"),
    # —— ID变体(gold#4) ——
    ("修改数据-删除数据记录的项目唯一标识符为PZXQ-GN-SQLFW-XGSJ-SJXG",
     "删除数据记录的编号为PZXQ-GN-SQLFW-SJXG", "neutral", "ID截断"),
    # —— 蕴含(子句) ——
    ("应用软件通过调用数据库的数据查询接口，提供所需的信息", "应用软件调用数据查询接口",
     "entailment", "子句蕴含"),
    # —— 前置条件 ——
    ("在进行BLOB数据插入操作前需要满足数据库连接正常的前置条件", "BLOB数据插入的前置条件是数据库连接正常",
     "entailment", "前置一致"),
    # —— 方向反转 ——
    ("应用软件调用数据库的接口，数据库执行插入操作", "数据库调用应用软件的接口执行插入操作",
     "contradiction", "方向反转"),
]


def load_model(name):
    d = os.path.join(MODELS_DIR, name)
    # Erlangshen兜底: 根目录散落的config/vocab归位
    for f in ("config.json", "vocab.txt"):
        if not os.path.exists(os.path.join(d, f)) and os.path.exists(os.path.join(MODELS_DIR, f)):
            os.replace(os.path.join(MODELS_DIR, f), os.path.join(d, f))
    tok = AutoTokenizer.from_pretrained(d, local_files_only=True)
    mdl = AutoModelForSequenceClassification.from_pretrained(d, local_files_only=True)
    mdl.eval()
    id2label = {int(k): v for k, v in mdl.config.id2label.items()}
    return tok, mdl, id2label


def normalize(label):
    lab = label.lower()
    if "entail" in lab:
        return "entailment"
    if "contradict" in lab or lab in ("contradiction", "错误", "冲突"):
        return "contradiction"
    return "neutral"


def run_model(tok, mdl, id2label, pairs):
    results = []
    for prem, hyp, exp, cat in pairs:
        # 两种输入序都试一遍取置信高者? 先用标准(prem, hyp)
        enc = tok(prem, hyp, return_tensors="pt", truncation=True, max_length=256)
        logits = mdl(**enc).logits
        probs = torch.softmax(logits, -1)[0]
        idx = int(torch.argmax(probs))
        pred = normalize(id2label.get(idx, str(idx)))
        conf = float(probs[idx])
        # 逆序核对(hyp, prem): NLI方向性检查
        enc2 = tok(hyp, prem, return_tensors="pt", truncation=True, max_length=256)
        probs2 = torch.softmax(mdl(**enc2).logits, -1)[0]
        idx2 = int(torch.argmax(probs2))
        pred2 = normalize(id2label.get(idx2, str(idx2)))
        results.append({"cat": cat, "exp": exp, "pred": pred, "conf": conf,
                        "pred_rev": pred2, "ok": pred == exp})
    return results


def main():
    print(f"测试对: {len(PAIRS)}条(来自doc11真实gold+04文档原文)\n")
    for name in ("Erlangshen-Roberta-110M-NLI",
                 "mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"):
        d = os.path.join(MODELS_DIR, name)
        if not os.path.isdir(d):
            print(f"[跳过] {name} 未下载")
            continue
        print(f"════ {name} ════")
        tok, mdl, id2label = load_model(name)
        print("  标签映射:", id2label)
        res = run_model(tok, mdl, id2label, PAIRS)
        acc = sum(r["ok"] for r in res) / len(res)
        print(f"  准确率: {acc:.1%} ({sum(r['ok'] for r in res)}/{len(res)})")
        bycat = {}
        for r in res:
            bycat.setdefault(r["cat"], []).append(r["ok"])
        print("  分类别:", {k: f"{sum(v)}/{len(v)}" for k, v in bycat.items()})
        print("  明细:")
        for (prem, hyp, exp, cat), r in zip(PAIRS, res):
            mark = "✓" if r["ok"] else "✗"
            print(f"    {mark} [{cat}] 期望{exp} 预测{r['pred']}(conf={r['conf']:.2f}) "
                  f"逆序={r['pred_rev']} | H:{hyp[:24]}")
        print()


if __name__ == "__main__":
    main()
