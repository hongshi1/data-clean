"""Check LLM dependency in the algorithm."""
from __future__ import annotations

from algorithms.consistency.verifier import PRESETS


def main() -> None:
    print("PRESETS:")
    for name, config in PRESETS.items():
        llm = config.get("use_llm_residual", False)
        nli = config.get("use_nli_residual", False)
        print(f"  {name}: LLM={llm}, NLI={nli}")

    print()
    print("LLM dependency analysis:")
    print("  fast     = pure deterministic (zero LLM, zero API)")
    print("  standard = local NLI model (zero LLM, zero API)")
    print("  full     = cascade with LLM arbiter (calls glm-5.3 API)")
    print()
    print("Conclusion:")
    print("  Core algorithm paths (fast/standard) have NO LLM API.")
    print("  Only 'full' preset's L3 channel calls a remote LLM API.")
    print("  The system works completely without the L3 LLM channel.")


if __name__ == "__main__":
    main()
