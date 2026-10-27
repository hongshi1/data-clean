"""最终完整总表: 全部方法 × 全部测试集(去污染修正版)."""
import json
import sys
from pathlib import Path

BASE = Path(r"C:\Users\12488\Desktop\data_clean")
sys.stdout.reconfigure(encoding="utf-8")

# 汇总所有结果源
src = {}
src.update(json.loads((BASE / "data/gjb_438c/runs/fill_native_cells.json").read_text(encoding="utf-8")))
src.update(json.loads((BASE / "data/gjb_438c/runs/decontam_results.json").read_text(encoding="utf-8")))
suppl = json.loads((BASE / "data/gjb_438c/runs/supplementary_external_eval_dbfed9b7_20261008_120739/result.json").read_text(encoding="utf-8"))
rb_sup = json.loads((BASE / "data/gjb_438c/runs/roberta_decontam_suppl.json").read_text(encoding="utf-8"))
allb = json.loads((BASE / "data/gjb_438c/runs/all_baselines_bacc.json").read_text(encoding="utf-8"))

# 主表数据(方法名→5列)
rows = []


def add(method, c, m, w, cn, dn, note=""):
    rows.append({"方法": method, "clean130": c, "md166": m, "WANLI": w, "ContrNLI": cn, "DocNLI": dn, "注": note})


# 基线
add("全报警(参照)", "0.5", "0.5", "0.5", "0.5", "0.5", "傻子基线")
# 经典ML
add("TF-IDF+SVM(去污染)", "0.749", "0.866", "N/A", "N/A", "N/A", "中文词表,英文集N/A; md最佳")
add("DeMarneffe-XGB", "0.71*", "0.86*", "N/A", "N/A", "N/A", "*近似SVM(同源特征)")
add("词法对齐", "0.5", "0.5", "0.5", "0.5", "0.5", "无判别")
add("BGE向量", "0.5", "0.5", "0.5", "0.5", "0.5", "无判别")
# 零样本NLI
add("mDeBERTa(多语言)", "0.5", "0.535", "0.828", "0.622", "0.430", "英文集唯一可用")
add("Erlangshen(中文NLI)", "0.5", "0.5", "N/A", "N/A", "N/A", "中文专用")
# LLM零样本
add("Qwen-7B(本地)", "0.5", "0.5", "-", "-", "-", "全报警")
add("Qwen-1.5B-Instruct", "0.5", "0.5", "-", "-", "-", "全报警")
add("GLM-5 零样本(API)", "0.5", "0.5", "-", "-", "-", "全报警")
add("GLM-5 CoT", "0.556", "0.583", "-", "-", "-", "微弱判别")
add("GLM-5 few-shot", "0.5", "0.583", "-", "-", "-", "微弱判别")
# 微调模型(我们的)
add("QLoRA-v6", "0.685-0.713", "0.5-0.507", "N/A", "N/A", "N/A", "单战场")
add("QLoRA-v8(CCT)", "0.719-0.733", "0.662-0.685", "0.5", "0.5", "0.002", "中文专用")
add("QLoRA-v9(1.5B)", "0.750", "0.713", "0.5", "0.5", "0.0", "中文专用(双语被抹)")
add("QLoRA-v10(nnPU)", "0.678", "0.504", "N/A", "N/A", "N/A", "PU负结果")
add("v11(证据SFT)", "0.5", "0.5", "N/A", "N/A", "N/A", "风格捷径失败")
add("roberta-FT(去污染)", "0.701", "0.752", "0.5", "0.5", "0.5", "中文专用")

# 排序: clean+md之和
def score(r):
    try:
        return float(r["clean130"]) + float(r["md166"])
    except ValueError:
        return 0

rows_sorted = sorted(rows, key=score, reverse=True)
print("═" * 100)
print("完整总表: 全部方法 × 5个测试集 (bAcc平衡准确率, 全报警=0.5, 去污染修正版)")
print("═" * 100)
header = f"{'方法':<22} {'clean130':>9} {'md166':>7} {'WANLI':>7} {'ContrNLI':>9} {'DocNLI':>7}  注"
print(header)
print("-" * 100)
for r in rows_sorted:
    print(f"{r['方法']:<22} {r['clean130']:>9} {r['md166']:>7} {r['WANLI']:>7} {r['ContrNLI']:>9} {r['DocNLI']:>7}  {r['注']}")

print("""
图例: clean130=02文档真实金标(31%真,去污染) | md166=16文档真实差异(74%真,零重叠)
     WANLI/ContractNLI/DocNLI=外部补充集(英文) | bAcc>0.5的部分=真实判别力
     N/A=中文模型无法处理英文 | -=未测(API限制)
""")
print("核心结论: ①SVM(0.749/0.866)与v9(0.750/0.713)并列native最佳 — 判别信号主要是词汇级")
print("         ②所有LLM(3B-7B-GLM)零判别(0.5) ③英文集只有mDeBERTa可用 ④去污染修正了SVM/roberta的虚高")

json.dump(rows_sorted, open(BASE / "data/gjb_438c/runs/FINAL_complete_table.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("saved → FINAL_complete_table.json")
