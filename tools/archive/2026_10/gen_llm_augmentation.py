r"""LLM批量数据增强: 不一致对premise多样化改写 + 15种不足类型定向生成.

任务1: pair_dataset_canonical/train.jsonl中source=srs_mutation的前50条不一致对,
       对每条生成语义等价但措辞不同的premise改写(数值/术语/结构不变, label保持inconsistent).
任务2: 15种类型(TERM/PARAM/LOGIC/GJB)×10条(5 inconsistent + 5 consistent)定向合成,
       GJB风格"文档X章节规定..."文本对; 一致对须有真实表面差异.

LLM: algorithms/llm_client.llm_json(cache=True, prefer=glm) — 磁盘缓存, 幂等可断点续跑
输出: data/gjb_438c/llm_generated_augmentation.json

并行安全: 并行分片各用独立缓存目录(llm_cache_shards/shardK), 全部完成后由主进程
     单线程合并分片结果与分片缓存到主缓存(llm_cache/llm_cache.jsonl), 避免并发写污染.

用法:
  python tools/gen_llm_augmentation.py                          # 顺序全量(200次调用, ~3h)
  python tools/gen_llm_augmentation.py --parallel 5             # 5进程并行(~40min)
  python tools/gen_llm_augmentation.py --merge-shards 5         # 只合并已有分片(断点收尾)
  python tools/gen_llm_augmentation.py --task1-limit 2 --types TERM-06  # 冒烟测试
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

TRAIN = BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl"
OUT = BASE / "data/gjb_438c/llm_generated_augmentation.json"
SHARD_DIR = BASE / "data/gjb_438c/llm_cache_shards"
MAIN_CACHE = BASE / "data/gjb_438c/llm_cache/llm_cache.jsonl"
SYSTEM = "你是GJB 438C军用软件需求规格说明(SRS)一致性数据集构造专家,只输出JSON。"

TYPE_DEFS: dict[str, dict[str, str]] = {
    "TERM-06": {
        "name": "量纲单位一致性",
        "def": "同一物理量在文档不同位置用不同单位/数值表述, 需换算后比较是否等效",
        "inconsistent": "两处约束换算成相同单位后数值不相等(如A处\"响应时间不超过0.2秒\"与B处\"响应时间不超过20毫秒\", 0.2秒=200毫秒≠20毫秒, 构成冲突)",
        "consistent": "两处单位不同但换算后数值完全相等(如A处\"0.2秒\"与B处\"200ms\", 0.2秒=200毫秒, 语义等价)",
    },
    "PARAM-01": {
        "name": "时间约束",
        "def": "响应时间/延迟/超时等时间指标在正文与表格/图等不同位置的数值约束",
        "inconsistent": "两处对同一时间指标给出不同的数值约束(如正文\"≤200ms\"与表格\"300ms\")",
        "consistent": "两处对同一时间指标的数值约束相同(单位可等价换算), 仅表述位置与措辞不同",
    },
    "PARAM-05": {
        "name": "资源占用指标",
        "def": "内存/CPU/会话数等资源占用上限在文档不同位置的数值约束",
        "inconsistent": "两处对同一资源占用指标给出不同上限(如A处\"内存占用≤512MB\"与B处\"内存占用≤256MB\")",
        "consistent": "两处对同一资源占用指标的数值约束相同, 仅表述位置与措辞不同",
    },
    "PARAM-06": {
        "name": "参数值域范围",
        "def": "同一参数的取值范围/值域在文档不同位置的表述",
        "inconsistent": "两处对同一参数给出不同值域(如A处\"取值范围0~100\"与B处\"取值范围0~1000\")",
        "consistent": "两处对同一参数的值域相同(端点与闭开区间一致), 仅表述方式不同",
    },
    "PARAM-07": {
        "name": "存储容量与保存时长",
        "def": "存储容量下限、数据保存时长等指标在文档不同位置的数值约束",
        "inconsistent": "两处对存储容量或保存时长给出不同数值(如A处\"存储容量≥256GB\"与B处\"存储容量≥56GB\")",
        "consistent": "两处对存储容量或保存时长的数值约束相同(单位可等价换算), 仅表述方式不同",
    },
    "LOGIC-01": {
        "name": "模式切换优先级",
        "def": "多种运行模式(手动/自动/应急/降级等)之间的优先级与抢占关系在文档不同位置的规定",
        "inconsistent": "两处对模式优先级的规定矛盾(如A处\"应急模式优先级最高\"与B处\"自动模式可抢占应急模式\")",
        "consistent": "两处对模式优先级的规定语义相同(同一优先级顺序/同一抢占方向), 但叙述角度和措辞不同",
    },
    "LOGIC-08": {
        "name": "数据冗余仲裁逻辑",
        "def": "主用/备用冗余数据源的仲裁选取策略在文档不同位置的规定",
        "inconsistent": "两处对主备仲裁策略的规定矛盾(如A处\"主用数据源优先\"与B处\"备用数据源优先\")",
        "consistent": "两处对主备仲裁策略的规定语义相同(同优先/同切换条件), 但叙述角度和措辞不同",
    },
    "LOGIC-09": {
        "name": "权限访问控制逻辑",
        "def": "用户角色对功能/配置/数据的访问与操作权限在文档不同位置的规定",
        "inconsistent": "两处对权限的规定矛盾(如A处\"仅系统管理员可修改配置\"与B处\"普通用户也可修改配置\")",
        "consistent": "两处对权限的规定语义相同(同一角色集合拥有同一权限), 但叙述角度和措辞不同",
    },
    "LOGIC-10": {
        "name": "故障恢复逻辑",
        "def": "故障发生后系统的恢复方式(自动恢复/人工干预)在文档不同位置的规定",
        "inconsistent": "两处对故障恢复方式的规定矛盾(如A处\"故障后自动恢复\"与B处\"需人工手动重启恢复\")",
        "consistent": "两处对故障恢复方式的规定语义相同(同恢复方式/同恢复条件), 但叙述角度和措辞不同",
    },
    "LOGIC-11": {
        "name": "追踪重搜逻辑",
        "def": "目标追踪失败后的重新搜索范围/策略在文档不同位置的规定",
        "inconsistent": "两处对追踪失败后重搜范围的规定矛盾(如A处\"重新搜索全库数据\"与B处\"只搜索增量数据\")",
        "consistent": "两处对重搜范围/策略的规定语义相同, 但叙述角度和措辞不同",
    },
    "GJB-03": {
        "name": "安全访问控制合规",
        "def": "GJB 438C要求SRS安全设计必须包含访问权限控制条款(角色分级/权限定义/访问控制措施)",
        "inconsistent": "hypothesis描述的安全设计内容缺失访问权限控制条款(如安全章节仅规定身份标识与日志审计, 未规定任何访问控制措施), 与premise引用的合规要求不满足",
        "consistent": "两处都规定完备的访问权限控制且相互呼应(同一角色分级/同一控制措施), 措辞明显不同",
    },
    "GJB-05": {
        "name": "需求可追溯性合规",
        "def": "GJB 438C要求每个需求项在追溯表中都有对应的测试项/验证方法, 追溯链不得断裂",
        "inconsistent": "hypothesis给出的追溯表中至少一个需求项的测试项为空或缺失, 追溯链断裂",
        "consistent": "hypothesis给出的追溯表完整覆盖premise提及的需求项(每项都有测试项), 两处对同一需求的描述措辞明显不同",
    },
    "GJB-06": {
        "name": "异常报警要素合规",
        "def": "GJB 438C要求报警设计包含报警级别等必备要素(级别/触发条件/处置方式)",
        "inconsistent": "hypothesis给出的报警设计缺失报警级别(或触发条件)等必备要素",
        "consistent": "hypothesis给出的报警设计要素完备(级别/触发条件/处置齐全)且与premise语义呼应, 措辞明显不同",
    },
    "GJB-07": {
        "name": "软件自检条款合规",
        "def": "GJB 438C要求系统初始化设计包含开机自检条款(自检项目/自检范围/故障处理)",
        "inconsistent": "hypothesis描述的初始化流程缺失开机自检条款(如仅规定加载配置与启动服务, 未规定自检)",
        "consistent": "两处都规定完备的开机自检(同一自检范围/同一故障处理方式), 措辞明显不同",
    },
    "GJB-08": {
        "name": "掉电数据保护合规",
        "def": "GJB 438C要求数据管理设计包含掉电数据保护条款(掉电检测/数据保障/恢复措施)",
        "inconsistent": "hypothesis描述的数据管理设计缺失掉电数据保护条款(如仅规定定期备份, 未规定掉电保护)",
        "consistent": "两处都规定完备的掉电数据保护(同一检测机制/同一保障手段), 措辞明显不同",
    },
}

SCENARIOS = [
    "数据引接汇聚服务", "实时数据处理服务", "流媒体传输服务", "数据存储管理服务",
    "用户权限管理功能", "外部接口适配服务", "告警监控功能", "任务调度功能",
    "网络传输链路管理", "系统配置管理", "日志审计功能", "数据分发服务",
    "态势目标追踪处理", "数据质量核查功能", "服务集成框架", "运行支撑服务",
    "安全防护功能", "软件升级与维护", "系统部署与运行监测", "综合态势显示",
]

POS_HINTS = [
    ("3.4节接口设计正文", "外部接口数据格式表"),
    ("3.9节性能要求正文", "参数配置表"),
    ("3.2节功能需求描述", "功能条目设计说明"),
    ("3.11节运行设计正文", "状态转换说明"),
    ("3.5节适应性要求正文", "部署约束说明"),
]

N_PER_TYPE = 10
N_RETRY = 2
N_API_RETRY = 3
API_BACKOFF_S = 15


def _norm(s: str) -> str:
    return re.sub(r"[\s，。；：、,.;:“”\"'()（）\-—_*《》]", "", s)


def _num_tokens(s: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", s)


def _alnum_tokens(s: str) -> set[str]:
    return set(re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", s))


def _llm_json_cached(prompt: str) -> tuple[dict, str | None]:
    from algorithms.common.llm_client import llm_json

    last_err = ""
    for api_try in range(N_API_RETRY):
        try:
            raw, _model = llm_json(prompt, system=SYSTEM, prefer="glm", cache=True)
            return (raw if isinstance(raw, dict) else {}), None
        except (RuntimeError, OSError) as e:
            last_err = str(e)
            if api_try < N_API_RETRY - 1:
                time.sleep(API_BACKOFF_S * (api_try + 1))
    return {}, f"API连续{N_API_RETRY}次失败: {last_err}"


def _gen_with_retry(build_prompt, validate):
    feedback = None
    j: dict = {}
    for _ in range(N_RETRY + 1):
        prompt = build_prompt()
        if feedback:
            prompt += ("\n\n注意: 上一次输出未通过自动校验(" + feedback +
                       "), 请修正后重新输出, 仍只输出JSON。")
        j, api_err = _llm_json_cached(prompt)
        if api_err is not None:
            return {}, api_err
        feedback = validate(j)
        if feedback is None:
            return j, None
    return j, feedback


def _task1_prompt(premise: str) -> str:
    return (
        "对下面SRS文档中的premise文本, 生成一个语义等价但措辞不同的改写版本。\n\n"
        "硬性要求:\n"
        "1. 语义完全等价: 所有数值、单位、编号、专有名词、代号、条目数量、逻辑关系"
        "必须逐一保留(原文中的插入语和特殊标记也原样保留)\n"
        "2. 只改变句式结构、语序、连接词、开头引入方式等表达方式\n"
        "3. 保持GJB军品需求文档的正式书面风格\n"
        "4. 改写后长度与原文相近(0.8~1.25倍)\n\n"
        "原文premise:\n" + premise + "\n\n"
        '输出JSON: {"rewrite": "..."}'
    )


def _validate_task1(j: dict, orig: str):
    rw = str(j.get("rewrite", "")).strip()
    if not rw:
        return "rewrite为空"
    if _norm(rw) == _norm(orig):
        return "改写与原文相同"
    missing_nums = [n for n in _num_tokens(orig) if n not in _num_tokens(rw)]
    if missing_nums:
        return f"改写缺少数值{missing_nums[:5]}"
    missing_terms = sorted(_alnum_tokens(orig) - _alnum_tokens(rw))
    if missing_terms:
        return f"改写缺少术语/代号{missing_terms[:3]}"
    ratio = len(rw) / max(len(orig), 1)
    if not 0.5 <= ratio <= 2.0:
        return f"长度偏差过大({ratio:.2f}倍)"
    return None


def _task2_prompt(tid: str, t: dict[str, str], label: str,
                  scenario: str, pos: tuple[str, str]) -> str:
    lab_desc = ("不一致对(两处规定构成矛盾或缺失, label=inconsistent)" if label == "inconsistent"
                else "一致对(两处规定语义等价, label=consistent)")
    req = t["inconsistent"] if label == "inconsistent" else t["consistent"]
    return (
        "为GJB 438C军用软件SRS一致性校验数据集生成一条文本对。\n\n"
        f"校验类型: {tid} {t['name']}\n"
        f"类型定义: {t['def']}\n"
        f"本条标注: {lab_desc}\n"
        f"类型要求: {req}\n"
        f"业务场景(必须围绕该子系统, 涉及的接口/数据/角色要具体): {scenario}\n"
        f"两处位置(参考, 章节号可微调): premise出自{pos[0]}, hypothesis出自{pos[1]}\n\n"
        "硬性要求:\n"
        "1. premise以\"文档\"+具体章节号+\"规定\"开头(如\"文档3.4.2规定\"), "
        "hypothesis以\"文档\"+另一位置(章节/表格/设计说明)开头\n"
        "2. GJB军品需求文档正式书面风格, 数值/单位/术语/编号具体明确, 不用占位符\n"
        "3. 两句的措辞、句式、详略必须有差异; 一致对的表面差异要真实明显"
        "(不是同句重复, 不是只改一两个词)\n"
        "4. 文本中不得出现label字样、校验类型ID或\"不一致/一致\"等判定词\n\n"
        '输出JSON: {"premise": "...", "hypothesis": "..."}'
    )


def _validate_task2(j: dict, label: str):
    p = str(j.get("premise", "")).strip()
    h = str(j.get("hypothesis", "")).strip()
    if not p or not h:
        return "premise或hypothesis为空"
    if len(p) < 15 or len(h) < 15:
        return "文本过短(<15字)"
    np_, nh = _norm(p), _norm(h)
    if np_ == nh:
        return "premise与hypothesis归一化后相同"
    low = (p + h).lower()
    for leak in ("inconsistent", "consistent", "label", "premise", "hypothesis"):
        if leak in low:
            return f"文本泄漏了保留词{leak}"
    if re.search(r"\b(TERM|PARAM|LOGIC|GJB)-\d{2}\b", p + h):
        return "文本泄漏了校验类型ID"
    if label == "consistent":
        r = difflib.SequenceMatcher(None, np_, nh).ratio()
        if r > 0.92:
            return f"表面差异不足(相似度{r:.2f}), 需更明显的措辞与详略差异"
    return None


def _build_items(task1_limit: int, type_ids: list[str]) -> list[dict]:
    recs = [json.loads(line) for line in
            TRAIN.read_text(encoding="utf-8").splitlines() if line.strip()]
    mut = [r for r in recs
           if r.get("source") == "srs_mutation"
           and r.get("label") == "inconsistent"][:task1_limit]
    items: list[dict] = [{"task": 1, "idx": i, "rec": r} for i, r in enumerate(mut)]
    for ti, tid in enumerate(type_ids):
        for k in range(N_PER_TYPE):
            label = "inconsistent" if k < N_PER_TYPE // 2 else "consistent"
            items.append({
                "task": 2,
                "idx": task1_limit + ti * N_PER_TYPE + k,
                "tid": tid,
                "k": k,
                "label": label,
                "scenario": SCENARIOS[(ti + k) % len(SCENARIOS)],
                "pos": POS_HINTS[k % len(POS_HINTS)],
            })
    return items


def _run_items(items: list[dict]) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []
    t0 = time.time()
    for n, it in enumerate(items):
        if it["task"] == 1:
            r = it["rec"]
            premise = r["pair"]["premise"]
            j, err = _gen_with_retry(
                lambda p=premise: _task1_prompt(p),
                lambda j_, p=premise: _validate_task1(j_, p))
            if err is not None:
                errors.append(f"task1[{r['id']}]: {err}")
                continue
            records.append({
                "premise": str(j["rewrite"]).strip(),
                "hypothesis": r["pair"]["hypothesis"],
                "label": r["label"],
                "type": r["angle"].get("type", ""),
                "origin_id": r["id"],
                "_idx": it["idx"],
            })
        else:
            j, err = _gen_with_retry(
                lambda t_=TYPE_DEFS[it["tid"]], l_=it["label"], s_=it["scenario"],
                       p_=it["pos"], tid_=it["tid"]:
                _task2_prompt(tid_, t_, l_, s_, p_),
                lambda j_, l_=it["label"]: _validate_task2(j_, l_))
            if err is not None:
                errors.append(f"task2[{it['tid']}-{it['k']}-{it['label']}]: {err}")
                continue
            records.append({
                "premise": str(j["premise"]).strip(),
                "hypothesis": str(j["hypothesis"]).strip(),
                "label": it["label"],
                "type": it["tid"],
                "_idx": it["idx"],
            })
        if (n + 1) % 10 == 0 or n + 1 == len(items):
            print(f"  进度 {n + 1}/{len(items)} (err={len(errors)}, "
                  f"{time.time() - t0:.0f}s)", flush=True)
    return records, errors


def _write_output(t1: list[dict], t2: list[dict], errors: list[str],
                  task1_limit: int, type_ids: list[str]) -> None:
    for rec in t1 + t2:
        rec.pop("_idx", None)
    out = {
        "meta": {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "llm": "algorithms/llm_client.llm_json(cache=True, prefer=glm)",
            "task1": {
                "input": "pair_dataset_canonical/train.jsonl: source=srs_mutation "
                         "且 label=inconsistent, 文件顺序前50条",
                "n_ok": len(t1),
                "n_input": task1_limit,
                "method": "premise语义等价改写(数值/术语/结构不变, label保持inconsistent)",
            },
            "task2": {
                "types": type_ids,
                "per_type": f"{N_PER_TYPE}条(5 inconsistent + 5 consistent)",
                "n_ok": len(t2),
                "n_expected": len(type_ids) * N_PER_TYPE,
                "method": "15种不足类型定向生成, GJB风格'文档X章节规定...'格式",
            },
            "errors": errors,
        },
        "task1_rewrites": t1,
        "task2_targeted": t2,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def _shard_cache_dir(k: int) -> Path:
    return SHARD_DIR / f"shard{k}"


def _run_shard(k: int, nshards: int, task1_limit: int, type_ids: list[str]) -> int:
    import algorithms.common.llm_client as lc

    lc.CACHE_DIR = _shard_cache_dir(k)
    items = [it for i, it in enumerate(_build_items(task1_limit, type_ids))
             if i % nshards == k]
    print(f"[shard {k}/{nshards}] {len(items)}条开始", flush=True)
    records, errors = _run_items(items)
    t1 = sorted([r for r in records if "_idx" in r and r["_idx"] < task1_limit],
                key=lambda r: r["_idx"])
    t2 = sorted([r for r in records if "_idx" in r and r["_idx"] >= task1_limit],
                key=lambda r: r["_idx"])
    result = {"shard": k, "task1_rewrites": t1, "task2_targeted": t2,
              "errors": errors}
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    (SHARD_DIR / f"shard{k}.result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[shard {k}/{nshards}] 完成: {len(records)}条, err={len(errors)}",
          flush=True)
    return 0 if not errors else 1


def _merge_shard_caches(nshards: int) -> int:
    keys: set[str] = set()
    if MAIN_CACHE.exists():
        for line in MAIN_CACHE.read_text(encoding="utf-8").splitlines():
            try:
                keys.add(json.loads(line)["k"])
            except (json.JSONDecodeError, KeyError):
                continue
    added = 0
    MAIN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(MAIN_CACHE, "a", encoding="utf-8") as f:
        for k in range(nshards):
            p = _shard_cache_dir(k) / "llm_cache.jsonl"
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("k") in keys:
                    continue
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                keys.add(rec["k"])
                added += 1
    return added


def _run_parallel(nshards: int, task1_limit: int, type_ids: list[str]) -> int:
    shard_files = [SHARD_DIR / f"shard{k}.result.json" for k in range(nshards)]
    missing = [k for k, p in enumerate(shard_files) if not p.exists()]
    if not missing:
        print(f"全部{nshards}个分片结果已存在, 直接合并")
        return _merge_shards(nshards, task1_limit, type_ids)
    procs = []
    for k in missing:
        cmd = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()),
               "--shard", str(k), "--nshards", str(nshards),
               "--task1-limit", str(task1_limit)]
        if type_ids != list(TYPE_DEFS):
            cmd += ["--types", ",".join(type_ids)]
        procs.append((k, subprocess.Popen(cmd)))
    for k, p in procs:
        rc = p.wait()
        if rc != 0:
            print(f"[shard {k}] 退出码{rc}(有错误项, 仍合并已完成部分)")
    return _merge_shards(nshards, task1_limit, type_ids)


def _merge_shards(nshards: int, task1_limit: int, type_ids: list[str]) -> int:
    all_items = _build_items(task1_limit, type_ids)
    expected = {it["idx"] for it in all_items}
    t1: list[dict] = []
    t2: list[dict] = []
    errors: list[str] = []
    seen: set[int] = set()
    for k in range(nshards):
        p = SHARD_DIR / f"shard{k}.result.json"
        if not p.exists():
            errors.append(f"分片{k}结果文件缺失")
            continue
        res = json.loads(p.read_text(encoding="utf-8"))
        for rec in res["task1_rewrites"] + res["task2_targeted"]:
            if rec["_idx"] in seen:
                continue
            seen.add(rec["_idx"])
            (t1 if rec["_idx"] < task1_limit else t2).append(rec)
        errors.extend(f"[shard{k}] {e}" for e in res["errors"])
    t1.sort(key=lambda r: r["_idx"])
    t2.sort(key=lambda r: r["_idx"])
    added = _merge_shard_caches(nshards)
    _write_output(t1, t2, errors, task1_limit, type_ids)
    n_expected = len(all_items)
    print(f"合并: {len(seen)}/{n_expected}条, 主缓存新增{added}条, "
          f"err={len(errors)} → {OUT}")
    if seen == expected and not errors:
        for k in range(nshards):
            d = _shard_cache_dir(k)
            if d.exists():
                for f in d.iterdir():
                    f.unlink()
                d.rmdir()
            rp = SHARD_DIR / f"shard{k}.result.json"
            if rp.exists():
                rp.unlink()
        if SHARD_DIR.exists() and not any(SHARD_DIR.iterdir()):
            SHARD_DIR.rmdir()
        return 0
    return 1


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--task1-limit", type=int, default=50)
    ap.add_argument("--types", type=str, default="",
                    help="逗号分隔的类型ID(默认全部15种)")
    ap.add_argument("--parallel", type=int, default=1,
                    help="并行分片进程数(1=顺序)")
    ap.add_argument("--shard", type=int, default=-1, help="内部: 分片模式")
    ap.add_argument("--nshards", type=int, default=0, help="内部: 分片总数")
    ap.add_argument("--merge-shards", type=int, default=0,
                    help="只合并已有分片结果")
    args = ap.parse_args()

    type_ids = ([t.strip() for t in args.types.split(",") if t.strip()]
                if args.types else list(TYPE_DEFS))
    for tid in type_ids:
        if tid not in TYPE_DEFS:
            raise SystemExit(f"未知类型: {tid}")

    if args.merge_shards > 0:
        sys.exit(_merge_shards(args.merge_shards, args.task1_limit, type_ids))
    if args.shard >= 0 and args.nshards > 0:
        sys.exit(_run_shard(args.shard, args.nshards, args.task1_limit, type_ids))
    if args.parallel > 1:
        sys.exit(_run_parallel(args.parallel, args.task1_limit, type_ids))

    items = _build_items(args.task1_limit, type_ids)
    print(f"顺序模式: 共{len(items)}条(任务1={args.task1_limit}, "
          f"任务2={len(type_ids)}×{N_PER_TYPE})")
    records, errors = _run_items(items)
    t1 = sorted([r for r in records if r["_idx"] < args.task1_limit],
                key=lambda r: r["_idx"])
    t2 = sorted([r for r in records if r["_idx"] >= args.task1_limit],
                key=lambda r: r["_idx"])
    _write_output(t1, t2, errors, args.task1_limit, type_ids)
    print(f"\n完成: 任务1={len(t1)}/{args.task1_limit}, "
          f"任务2={len(t2)}/{len(type_ids) * N_PER_TYPE}, err={len(errors)} → {OUT}")
    for e in errors[:10]:
        print(f"  ERR {e}")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
