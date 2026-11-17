"""Salvage: save the last checkpoint adapter to the target out-dir.

Usage: python tools/salvage_d3_checkpoint.py <run_dir> <out_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

if len(sys.argv) >= 3:
    RUN_DIR = Path(sys.argv[1])
    OUT = Path(sys.argv[2])
else:
    RUN_DIR = (BASE / "data/gjb_438c/runs/train_d3_student_54336ba7_"
               "20261117_003718")
    OUT = BASE / "models/llm/d3_student_v2c"
BASE_MODEL = BASE / "models/llm/qwen3-1.7b"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    trainer_dir = RUN_DIR / "trainer"
    checkpoints = sorted(
        (d for d in trainer_dir.glob("checkpoint-*") if d.is_dir()),
        key=lambda d: int(d.name.split("-")[1]))
    if not checkpoints:
        raise SystemExit(f"无checkpoint: {trainer_dir}")
    ckpt = checkpoints[-1]
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    state = json.loads((ckpt / "trainer_state.json").read_text(
        encoding="utf-8"))
    losses = [h.get("loss") for h in state["log_history"]
              if "loss" in h]
    print(f"checkpoint step {state['global_step']}, "
          f"last loss {losses[-1] if losses else '?'}")
    tokenizer = AutoTokenizer.from_pretrained(str(BASE_MODEL))
    model = AutoModelForCausalLM.from_pretrained(
        str(BASE_MODEL), torch_dtype=torch.float16)
    peft_model = PeftModel.from_pretrained(model, str(ckpt))
    merged = peft_model.merge_and_unload()
    OUT.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    (OUT / "d3_meta.json").write_text(json.dumps({
        "base": str(BASE_MODEL),
        "salvaged_from": str(ckpt),
        "global_step": state["global_step"],
        "note": f"run {RUN_DIR.name} interrupted; adapter from "
                f"{ckpt.name}",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"merged adapter → {OUT}")


if __name__ == "__main__":
    main()
