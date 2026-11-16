"""Salvage: save the last checkpoint adapter to the target out-dir."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CKPT = (BASE / "data/gjb_438c/runs/train_d3_student_54336ba7_"
        "20261117_003718/trainer/checkpoint-120")
OUT = BASE / "models/llm/d3_student_v2c"
BASE_MODEL = BASE / "models/llm/qwen3-1.7b"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    state = json.loads((CKPT / "trainer_state.json").read_text(
        encoding="utf-8"))
    losses = [h.get("loss") for h in state["log_history"]
              if "loss" in h]
    print(f"checkpoint step {state['global_step']}, "
          f"last loss {losses[-1] if losses else '?'}")
    tokenizer = AutoTokenizer.from_pretrained(str(BASE_MODEL))
    model = AutoModelForCausalLM.from_pretrained(
        str(BASE_MODEL), torch_dtype=torch.float16)
    peft_model = PeftModel.from_pretrained(model, str(CKPT))
    merged = peft_model.merge_and_unload()
    OUT.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    (OUT / "d3_meta.json").write_text(json.dumps({
        "base": str(BASE_MODEL),
        "salvaged_from": str(CKPT),
        "global_step": state["global_step"],
        "note": "2-epoch run OOM at step 139; adapter from checkpoint-120"
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"merged adapter → {OUT}")


if __name__ == "__main__":
    main()
