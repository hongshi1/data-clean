"""ai_config: 全仓库唯一密钥/端点配置源 (Secrets Single Source of Truth).

规则(AGENTS.md硬规则):
  - 只有本模块允许读 .env; 其他任何代码出现密钥字面量 = 违规
  - 用法: from ai_config import KIMI_KEY / WQ_API_KEY / GLM_KEY ...
  - .env 不入库(.gitignore), 参考 .env.example; 缺失时本模块报错并给出修复指引

密钥泄漏过的旧值已进git历史 → 必须在API平台轮换, 删代码不算修复.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _load_env_file() -> dict[str, str]:
    env: dict[str, str] = {}
    p = BASE / ".env"
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_FILE_ENV = _load_env_file()


def _get(name: str, default: str = "") -> str:
    v = os.environ.get(name) or _FILE_ENV.get(name) or ""
    if v:
        return v
    if default:
        return default
    raise RuntimeError(
        f"缺少配置 {name}: 在仓库根目录创建 .env(参考 .env.example) "
        f"或设置环境变量 {name}. 已泄漏的旧密钥请在API平台轮换.")


# ── wanqing(内部网关: GLM/kimi/claude端点 + embedding) ──
WQ_API_KEY = _get("WQ_API_KEY")
WQ_BASE_URL = _get("WQ_BASE_URL", default="https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints")
WQ_CHAT_URL = WQ_BASE_URL + "/chat/completions"
EMB_URL = _get("EMB_URL", default=WQ_BASE_URL + "/embeddings")
EMB_MODEL = _get("EMB_MODEL", default="ep-qrkeon-1785654358657880827")

# ── moonshot kimi(外网) ──
KIMI_KEY = _get("KIMI_KEY")
KIMI_URL = _get("KIMI_URL", default="https://api.moonshot.cn/v1/chat/completions")
KIMI_MODEL = _get("KIMI_MODEL", default="kimi-k2.6")

# ── 智谱GLM(外网) ──
GLM_KEY = _get("GLM_KEY")
GLM_URL = _get("GLM_URL", default="https://open.bigmodel.cn/api/paas/v4/chat/completions")
GLM_MODEL = _get("GLM_MODEL", default="glm-5")
