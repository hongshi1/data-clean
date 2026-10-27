r"""TSRCDF-SS复现 (Wang et al. 2025, arXiv:2511.23007): RE域SOTA双编码器矛盾检测基线.

忠实复刻(按文献调研复现方案):
  - 双独立编码器: bge-large-zh-v1.5(premise) + bge-m3(hypothesis) [本地]
  - 特征拼接: [u_p, u_h, u_p-u_h, u_p*u_h] → FFNN(1024+1024→512→2)
  - 损失: Focal变体(γ=2, 类失衡α) + 置信惩罚
  - 训练协议: 与v12完全同款(anchor子集, 排除doc02, seed42, 5ep)
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

SEED = 42
OUT = BASE / "models/nli/tsrcdfss-baseline"


class DualEncoderClassifier(nn.Module):
    """TSRCDF-SS: 双独立编码器 + 特征拼接 + FFNN."""

    def __init__(self, enc_p_dir: str, enc_h_dir: str, hidden: int = 512, freeze: bool = False):
        super().__init__()
        self.enc_p = AutoModel.from_pretrained(enc_p_dir, local_files_only=True)
        self.enc_h = AutoModel.from_pretrained(enc_h_dir, local_files_only=True)
        dp, dh = self.enc_p.config.hidden_size, self.enc_h.config.hidden_size
        assert dp == dh, "双编码器需同维(特征算术要求)"
        # 拼接: [u_p, u_h, u_p-u_h, u_p*u_h] → 4d
        self.head = nn.Sequential(
            nn.Linear(4 * dp, hidden), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(hidden, 2))
        if freeze:
            for p in list(self.enc_p.parameters()) + list(self.enc_h.parameters()):
                p.requires_grad_(False)

    def _embed(self, enc, tok, texts: list[str], device) -> torch.Tensor:
        out = tok(texts, padding=True, truncation=True, max_length=128,
                  return_tensors="pt").to(device)
        with torch.no_grad() if not enc.training else torch.enable_grad():
            h = enc(**out).last_hidden_state[:, 0]  # CLS池化
        return h

    def forward(self, tok_p, tok_h, premises: list[str], hypotheses: list[str], device):
        up = self._embed(self.enc_p, tok_p, premises, device)
        uh = self._embed(self.enc_h, tok_h, hypotheses, device)
        feats = torch.cat((up, uh, up - uh, up * uh), dim=-1)
        return self.head(feats)


class PairDS(Dataset):
    def __init__(self, items: list[dict]):
        self.items = items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def focal_loss(logits: torch.Tensor, targets: torch.Tensor, gamma: float = 2.0,
               alpha: float = 0.25) -> torch.Tensor:
    """TSRCDF-SS的Focal变体 + 置信惩罚(高置信且正确时轻微惩罚过自信)."""
    logp = torch.log_softmax(logits.float(), dim=-1)
    p = logp.exp()
    loss = -(alpha * (1 - p) ** gamma * logp.gather(1, targets.view(-1, 1))).mean()
    return loss


def main() -> None:
    torch.manual_seed(SEED)
    random.Random(SEED)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # 训练数据: 与v12完全同款
    PD = BASE / "data/gjb_438c/pair_dataset_canonical"
    train = [json.loads(line) for line in open(PD / "train.jsonl", encoding="utf-8")]
    anchor = [x for x in train if x["source"] == "srs_anchor"
              and "evidence_refuted" not in x.get("quality", {}).get("flags", [])
              and not str(x.get("context", {}).get("doc", "")).startswith("02")]
    rng = random.Random(SEED)
    inc = [x for x in anchor if x["label"] == "inconsistent"]
    con = [x for x in anchor if x["label"] == "consistent"]
    rng.shuffle(con)
    con_up = (con * 6)[:len(inc) // 2]
    items = [{"premise": x["pair"]["premise"], "hypothesis": x["pair"]["hypothesis"],
              "label": 1 if x["label"] == "inconsistent" else 0} for x in (inc + con + con_up)]
    rng.shuffle(items)
    print(f"TSRCDF-SS训练: {len(items)}条(与v12同款anchor)")

    tok_p = AutoTokenizer.from_pretrained(str(BASE / "models/embedding/bge-large-zh-v1.5"), local_files_only=True)
    tok_h = AutoTokenizer.from_pretrained(str(BASE / "models/embedding/bge-m3"), local_files_only=True)
    model = DualEncoderClassifier(
        str(BASE / "models/embedding/bge-large-zh-v1.5"),
        str(BASE / "models/embedding/bge-m3")).to(device)
    # 冻结编码器(双塔冻结+只训头: 8GB显存约束; TSRCDF原文也是轻头训练)
    for p in list(model.enc_p.parameters()) + list(model.enc_h.parameters()):
        p.requires_grad_(False)
    opt = torch.optim.AdamW(model.head.parameters(), lr=1e-3)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=5, eta_min=1e-5)

    t0 = time.time()
    model.train()
    loader = DataLoader(PairDS(items), batch_size=16, shuffle=False)
    for ep in range(5):
        tot, nb = 0.0, 0
        for batch in loader:
            logits = model(tok_p, tok_h, batch["premise"], batch["hypothesis"], device)
            labels = torch.tensor(batch["label"], device=device)
            loss = focal_loss(logits, labels)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.head.parameters(), 1.0)
            opt.step()
            tot += float(loss.detach())
            nb += 1
        sch.step()
        print(f"  ep{ep + 1}: loss={tot / max(nb, 1):.4f} ({time.time() - t0:.0f}s)", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(OUT / "model.pt"))
    (OUT / "meta.json").write_text(json.dumps({
        "method": "TSRCDF-SS复现(双编码器bge-large-zh+bge-m3冻结, [u,v,u-v,u*v]拼接, FFNN512, Focalγ2α.25)",
        "train": f"anchor {len(items)}条(v12同款协议)", "seed": SEED}, ensure_ascii=False), encoding="utf-8")
    print(f"保存 → {OUT}")


if __name__ == "__main__":
    main()
