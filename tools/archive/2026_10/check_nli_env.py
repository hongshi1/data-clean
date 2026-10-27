import sys

sys.stdout.reconfigure(encoding="utf-8")
print("python:", sys.version.split()[0])
import numpy  # noqa: F401  (Anaconda torch DLL常需要numpy先载入MKL)
try:
    import torch
    print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available())
except OSError as e:
    print("torch DLL ERROR:", str(e)[:120])
for m in ["transformers", "huggingface_hub"]:
    try:
        mod = __import__(m)
        print(m, ":", getattr(mod, "__version__", "?"))
    except ImportError:
        print(m, ": NOT INSTALLED")
