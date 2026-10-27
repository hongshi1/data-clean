#!/usr/bin/env python3
"""
P0-1: 确定性Mutation注入引擎
==============================
基于真实pair(Visio结构+表格CSV+文本)注入已知的不一致性。

7类Mutation算子(对应75条真实调研的7类不一致性):
  1. ID不一致(32%): 需求ID数字替换/章节号偏移
  2. 名称不一致(16%): 同义词替换/前后缀删除
  3. 值矛盾(7%): 数值偏移/单位族内错误换算
  4. 章节错位(24%): 表格行与错误章节配对
  5. 异常流缺失(8%): 删除异常流行/Visio边
  6. Caption错误(5%): 图号/表号偏移
  7. 逻辑矛盾(3%): 允许vs禁止对立

关键设计(对抗Korn et al.失败模式):
  - 确定性规则mutation(非LLM自由生成)
  - 程序验证(diff符合预期)
  - 对照组(语义保持改写=合理差异)

用法: python3 tools/srs_mutation_engine.py
"""
import re
import json
import random
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE = Path(__file__).resolve().parent.parent
PAIR_DIR = BASE / "data/gjb_438c/pair_dataset"
MAPPING_PATH = BASE / "data/gjb_438c/visio_extracted/sc2_visio_mapping_v2.json"
OUTPUT_DIR = BASE / "data/gjb_438c/mutated_dataset"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)


# ═══════════════════════════════════════════════════════════════
# Mutation算子
# ═══════════════════════════════════════════════════════════════

def mutate_id(text: str) -> tuple[str, str]:
    """算子1: ID不一致 — 需求ID数字替换/章节号偏移"""
    # 模式: ZZSJHQZHFW-GN-SJHQ-JGHSJGJ → 改最后一个段
    pattern = r'([A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+)-([A-Z0-9]+)'
    m = re.search(pattern, text)
    if m:
        old_id = m.group(0)
        # 替换最后一段为不同值
        last_seg = m.group(2)
        if last_seg[-1].isdigit():
            new_digit = str((int(last_seg[-1]) + 3) % 10)
            new_id = old_id[:-1] + new_digit
        else:
            new_id = old_id + "XX"
        return text.replace(old_id, new_id), f"ID替换: {old_id} → {new_id}"
    
    # 模式: 章节号 3.2.1.2 → 3.2.1.5 (偏移)
    sec_pattern = r'\b(\d+\.\d+\.\d+)\.(\d+)\b'
    m = re.search(sec_pattern, text)
    if m:
        old_sec = m.group(0)
        new_num = int(m.group(2)) + 2
        new_sec = f"{m.group(1)}.{new_num}"
        return text.replace(old_sec, new_sec), f"章节号偏移: {old_sec} → {new_sec}"
    
    return text, ""


def mutate_name(text: str) -> tuple[str, str]:
    """算子2: 名称不一致 — 关键词替换"""
    # 常见军事/技术术语替换对(基于数据观察)
    replacements = [
        ("发送", "接收"), ("接收", "发送"),
        ("上传", "下载"), ("下载", "上传"),
        ("初始化", "销毁"), ("启动", "停止"),
        ("登录", "注销"), ("注册", "注销"),
        ("数据库", "数据仓库"), ("内存", "存储"),
        ("实时", "批量"), ("增量", "全量"),
        ("同步", "异步"), ("异步", "同步"),
        ("加密", "解密"), ("解密", "加密"),
        ("导入", "导出"), ("导出", "导入"),
    ]
    for old, new in replacements:
        if old in text:
            # 只替换第一次出现
            new_text = text.replace(old, new, 1)
            return new_text, f"术语替换: '{old}' → '{new}'"
    return text, ""


def mutate_value(text: str) -> tuple[str, str]:
    """算子3: 值矛盾 — 数值偏移/单位错误"""
    # 数值偏移
    num_pattern = r'(\d+\.?\d*)\s*(ms|s|KB|MB|GB|MHz|GHz|%|V|A|W)'
    m = re.search(num_pattern, text)
    if m:
        old_val = float(m.group(1))
        unit = m.group(2)
        # 偏移策略
        if old_val < 10:
            new_val = old_val * 3  # 小值乘3
        elif old_val < 100:
            new_val = old_val * 2  # 中值乘2
        else:
            new_val = old_val / 2  # 大值减半
        
        # 保持格式
        if '.' in m.group(1):
            new_str = f"{new_val:.1f}"
        else:
            new_str = str(int(new_val))
        
        old_str = f"{m.group(1)}{unit}"
        new_str_full = f"{new_str}{unit}"
        return text.replace(old_str, new_str_full, 1), f"数值偏移: {m.group(1)}{unit} → {new_str}{unit}"
    
    # 单位错误换算
    unit_replacements = [
        ("MB", "KB"), ("GB", "MB"), ("GHz", "MHz"),
        ("ms", "s"), ("s", "ms"),
    ]
    for old_unit, new_unit in unit_replacements:
        pattern = rf'(\d+\.?\d*)\s*{old_unit}\b'
        m = re.search(pattern, text)
        if m:
            old_str = m.group(0)
            new_str = f"{m.group(1)}{new_unit}"
            return text.replace(old_str, new_str, 1), f"单位错误: {old_str} → {new_str}"
    
    return text, ""


def mutate_section_shift(table_content: str, all_sections: list[str]) -> tuple[str, str]:
    """算子4: 章节错位 — 将表格行关联到错误章节"""
    if not all_sections:
        return table_content, ""
    wrong_section = random.choice([s for s in all_sections if s not in table_content[:10]])
    # 在表格开头注入错误章节引用
    mutated = f"【本表适用于章节 {wrong_section}】\n" + table_content
    return mutated, f"章节错位注入: 关联到错误章节 {wrong_section}"


def mutate_exception_removal(table_content: str) -> tuple[str, str]:
    """算子5: 异常流缺失 — 删除异常流行"""
    lines = table_content.split('\n')
    new_lines = []
    removed = []
    for line in lines:
        if '异常流' in line and ('E' in line or '异常' in line):
            removed.append(line.strip()[:50])
            continue  # 跳过(删除)
        new_lines.append(line)
    
    if removed:
        return '\n'.join(new_lines), f"异常流删除: {len(removed)}行 ({removed[0][:30]}...)"
    return table_content, ""


def mutate_caption(text: str) -> tuple[str, str]:
    """算子6: Caption错误 — 图号/表号偏移"""
    # 图号偏移: "图 7" → "图 9"
    fig_pattern = r'图\s*(\d+)'
    m = re.search(fig_pattern, text)
    if m:
        old_num = int(m.group(1))
        new_num = old_num + 2
        old_str = m.group(0)
        new_str = f"图 {new_num}"
        return text.replace(old_str, new_str, 1), f"图号偏移: {old_str} → {new_str}"
    
    # 表号偏移: "表 3" → "表 5"
    tbl_pattern = r'表\s*(\d+)'
    m = re.search(tbl_pattern, text)
    if m:
        old_num = int(m.group(1))
        new_num = old_num + 2
        old_str = m.group(0)
        new_str = f"表 {new_num}"
        return text.replace(old_str, new_str, 1), f"表号偏移: {old_str} → {new_str}"
    
    return text, ""


def mutate_logic_contradiction(text: str) -> tuple[str, str]:
    """算子7: 逻辑矛盾 — 允许vs禁止对立"""
    # 允许→禁止 / 不允许→必须
    logic_replacements = [
        ("允许", "禁止"), ("可以", "不得"), ("支持", "不支持"),
        ("不低于", "不超过"), ("不超过", "不低于"),
        ("至少", "至多"), ("最多", "最少"),
        ("必须", "禁止"), ("应", "不应"),
    ]
    for old, new in logic_replacements:
        if old in text:
            new_text = text.replace(old, new, 1)
            return new_text, f"逻辑反转: '{old}' → '{new}'"
    return text, ""


def mutate_semantic_preserve(text: str) -> tuple[str, str]:
    """对照组: 语义保持改写(合理差异, 非矛盾)"""
    # 同义改写(不改变语义)
    synonyms = [
        ("提供", "给予"), ("支持", "辅助"), ("实现", "完成"),
        ("使用", "利用"), ("通过", "借助"), ("包括", "包含"),
        ("进行", "执行"), ("需要", "要求"), ("具有", "拥有"),
    ]
    for old, new in synonyms:
        if old in text:
            new_text = text.replace(old, new, 1)
            return new_text, f"语义保持改写: '{old}' → '{new}' (合理差异)"
    return text, ""


# 算子注册表
MUTATION_OPERATORS = {
    'id_inconsistency': mutate_id,
    'name_inconsistency': mutate_name,
    'value_contradiction': mutate_value,
    'section_shift': mutate_section_shift,
    'exception_removal': mutate_exception_removal,
    'caption_error': mutate_caption,
    'logic_contradiction': mutate_logic_contradiction,
    'semantic_preserve': mutate_semantic_preserve,  # 对照组
}


# ═══════════════════════════════════════════════════════════════
# 注入引擎
# ═══════════════════════════════════════════════════════════════

def load_pairs() -> list[dict]:
    """加载所有pair_dataset样本"""
    pairs = []
    for sc_dir in sorted(PAIR_DIR.iterdir()):
        if not sc_dir.is_dir(): continue
        for sample_dir in sorted(sc_dir.iterdir()):
            if not sample_dir.is_dir(): continue
            meta_p = sample_dir / "meta.json"
            if not meta_p.exists(): continue
            
            meta = json.loads(meta_p.read_text())
            pair = {
                'scenario': sc_dir.name,
                'sample_id': sample_dir.name,
                'dir': sample_dir,
                'meta': meta,
            }
            
            # 加载text
            text_p = sample_dir / "text.txt"
            if text_p.exists():
                pair['text'] = text_p.read_text(encoding='utf-8')
            
            # 加载table
            table_p = sample_dir / "table.csv"
            if table_p.exists():
                pair['table'] = table_p.read_text(encoding='utf-8')
            
            pairs.append(pair)
    return pairs


def inject_mutation(pair: dict, operator_name: str) -> dict:
    """对单个pair注入指定的mutation"""
    op_func = MUTATION_OPERATORS[operator_name]
    
    # 深拷贝
    mutated = {
        'source_pair': pair['sample_id'],
        'scenario': pair['scenario'],
        'operator': operator_name,
        'mutation_type': 'semantic_preserve' if operator_name == 'semantic_preserve' else 'inconsistency',
        'is_injected': operator_name != 'semantic_preserve',
    }
    
    # 对text注入
    if pair.get('text'):
        if operator_name == 'section_shift':
            # 章节错位需要额外参数
            all_sections = ["1.1", "1.2", "2.1", "3.1", "3.2", "3.3", "3.10", "3.11", "4.1", "5.1"]
            new_text, desc = op_func(pair['text'], all_sections)
        else:
            new_text, desc = op_func(pair['text'])
        
        if desc:
            mutated['text_original'] = pair['text'][:100]
            mutated['text_mutated'] = new_text[:100]
            mutated['text_mutation'] = desc
            mutated['mutated_text_full'] = new_text
    
    # 对table注入
    if pair.get('table'):
        if operator_name == 'section_shift':
            all_sections = ["1.1", "3.2", "3.3", "4.1"]
            new_table, tbl_desc = op_func(pair['table'], all_sections)
        else:
            new_table, tbl_desc = op_func(pair['table'])
        
        if tbl_desc:
            mutated['table_mutation'] = tbl_desc
            mutated['mutated_table_full'] = new_table
    
    # 验证: mutation是否实际生效
    has_text_mutation = 'text_mutation' in mutated
    has_table_mutation = 'table_mutation' in mutated
    mutated['mutation_applied'] = has_text_mutation or has_table_mutation
    
    return mutated


def main():
    print("=" * 60)
    print("P0-1: 确定性Mutation注入引擎")
    print("=" * 60)
    
    # 加载pair
    pairs = load_pairs()
    print(f"原始pair数: {len(pairs)}")
    
    # 7类不一致性 + 1类对照 = 8个算子
    operators = list(MUTATION_OPERATORS.keys())
    print(f"Mutation算子: {len(operators)}个")
    for op in operators:
        print(f"  - {op}")
    
    # 注入: 每个pair对每个算子尝试一次
    all_mutations = []
    stats = Counter()
    failed = Counter()
    
    for pair in pairs:
        for op_name in operators:
            result = inject_mutation(pair, op_name)
            if result.get('mutation_applied'):
                all_mutations.append(result)
                stats[op_name] += 1
            else:
                failed[op_name] += 1
    
    # 统计
    print(f"\n{'=' * 60}")
    print("注入结果")
    print(f"{'=' * 60}")
    print(f"成功注入: {len(all_mutations)}对")
    print(f"注入失败: {sum(failed.values())}次(无匹配模式)")
    
    print("\n按算子统计:")
    for op in operators:
        success = stats.get(op, 0)
        fail = failed.get(op, 0)
        total = success + fail
        rate = success / max(1, total)
        print(f"  {op:25s}: {success:4d}成功 / {fail:4d}失败 ({rate:.0%})")
    
    # 按mutation_type分
    inconsistency_count = sum(1 for m in all_mutations if m['mutation_type'] == 'inconsistency')
    preserve_count = sum(1 for m in all_mutations if m['mutation_type'] == 'semantic_preserve')
    print(f"\n不一致性注入: {inconsistency_count}对")
    print(f"语义保持对照: {preserve_count}对")
    
    # 按场景分
    by_scenario = Counter(m['scenario'] for m in all_mutations)
    print("\n按场景:")
    for sc, cnt in by_scenario.most_common():
        print(f"  {sc:30s}: {cnt}")
    
    # 展示样例
    print(f"\n{'=' * 60}")
    print("注入样例")
    print(f"{'=' * 60}")
    
    for op in operators[:3]:
        samples = [m for m in all_mutations if m['operator'] == op][:2]
        for s in samples:
            print(f"\n  [{op}] {s['source_pair']} ({s['scenario'][:20]}):")
            if 'text_mutation' in s:
                print(f"    原文: \"{s['text_original'][:50]}\"")
                print(f"    变异: \"{s['text_mutated'][:50]}\"")
                print(f"    操作: {s['text_mutation']}")
            if 'table_mutation' in s:
                print(f"    表格: {s['table_mutation']}")
    
    # 保存
    output = {
        'engine_version': '1.0',
        'generate_date': datetime.now().isoformat(),
        'source': '确定性Mutation引擎(规则引导,非LLM自由生成)',
        'total_mutations': len(all_mutations),
        'inconsistency_mutations': inconsistency_count,
        'preserve_mutations': preserve_count,
        'by_operator': dict(stats),
        'by_scenario': dict(by_scenario),
        'mutation_type': 'inconsistency' if 'inconsistency' else 'semantic_preserve',
        'mutations': all_mutations,
    }
    output_path = OUTPUT_DIR / "mutated_dataset.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n已保存: {output_path}")
    
    # 保存摘要
    summary = {
        'engine_version': '1.0',
        'generate_date': datetime.now().isoformat(),
        'total': len(all_mutations),
        'by_operator': dict(stats),
        'by_scenario': dict(by_scenario),
    }
    summary_path = OUTPUT_DIR / "_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"摘要: {summary_path}")


if __name__ == "__main__":
    main()
