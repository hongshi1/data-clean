#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
import great_expectations as gx

DATA_DIR = "/Users/gexuancheng/Desktop/research2/data_clean/h4r_welding"

FILES = [
    "weld_sample.csv",
    "good_sample.csv",
    "crack_sample.csv",
    "fusion_sample.csv",
]

SENSOR_COLUMNS = [
    "Pressure",
    "CO2 Weld Flow",
    "Feed",
    "Primary Weld Current",
    "Wire Consumed",
    "Secondary Weld Voltage",
]

RANGE_RULES = {
    "Pressure": {"min": -1, "max": 10},
    "Primary Weld Current": {"min": 0, "max": 500},
    "Secondary Weld Voltage": {"min": 0, "max": 100},
}


def create_suite_for_file(file_name):
    suite_name = f"h4r_welding_{file_name.replace('.', '_')}_suite"
    suite = gx.ExpectationSuite(name=suite_name)

    for col in SENSOR_COLUMNS:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=col)
        )

    for col, rule in RANGE_RULES.items():
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column=col,
                min_value=rule["min"],
                max_value=rule["max"],
            )
        )

    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="Time")
    )

    return suite


def validate_file(context, file_name, datasource):
    file_path = os.path.join(DATA_DIR, file_name)
    df = pd.read_csv(file_path)
    suite = create_suite_for_file(file_name)

    asset_name = f"asset_{file_name.replace('.', '_')}"
    data_asset = datasource.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe("batch_def")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    validator = context.get_validator(
        batch_request=batch.batch_request,
        expectation_suite=suite,
    )
    results = validator.validate()
    return results


def print_results_in_chinese(file_name, results):
    print(f"\n{'='*60}")
    print(f"📁 文件: {file_name}")
    print(f"{'='*60}")

    overall_success = results.success
    print(f"✅ 总体验证结果: {'通过' if overall_success else '失败'}")

    expectations = results.results
    passed = sum(1 for r in expectations if r.success)
    failed = len(expectations) - passed
    print(f"📊 期望总数: {len(expectations)} | ✅ 通过: {passed} | ❌ 失败: {failed}")

    if failed == 0:
        print("🎉 所有期望均通过，无字段违规！")
    else:
        print(f"⚠️  发现 {failed} 条期望未通过")

    print("\n🔍 详细验证结果（每条期望的通过/失败情况）:")
    print("-" * 60)

    for idx, result in enumerate(expectations, 1):
        exp = result.expectation_config
        exp_type = exp.type
        column = exp.kwargs.get("column", "N/A")
        success = result.success

        status_icon = "✅ 通过" if success else "❌ 失败"

        if "not_be_null" in exp_type:
            desc = f"列 '{column}' 的值不应为 null"
        elif "be_between" in exp_type:
            min_v = exp.kwargs.get("min_value")
            max_v = exp.kwargs.get("max_value")
            desc = f"列 '{column}' 的值应在 [{min_v}, {max_v}] 范围内"
        elif "be_unique" in exp_type:
            desc = f"列 '{column}' 的值应唯一"
        else:
            desc = f"列 '{column}' - {exp_type}"

        print(f"  {idx}. [{status_icon}] {desc}")

        if not success:
            result_info = result.result
            unexpected_count = result_info.get("unexpected_count", "N/A")
            unexpected_percent = result_info.get("unexpected_percent", "N/A")
            element_count = result_info.get("element_count", "N/A")
            pct_str = f"{unexpected_percent:.2f}%" if isinstance(unexpected_percent, (int, float)) else str(unexpected_percent)
            print(f"      ↳ 违规详情: 总记录数={element_count}, 违规数={unexpected_count}, 违规比例={pct_str}")

            partial_unexpected_list = result_info.get("partial_unexpected_list", [])
            if partial_unexpected_list:
                shown = partial_unexpected_list[:5]
                print(f"      ↳ 部分违规值示例: {shown}")
                if len(partial_unexpected_list) > 5:
                    print(f"         ... 共 {len(partial_unexpected_list)} 个不同违规值")

    print("-" * 60)


def main():
    context = gx.get_context(mode="ephemeral")
    datasource = context.data_sources.add_pandas("h4r_welding_datasource")

    print("=" * 60)
    print("🔧 H4R 焊接数据 - Great Expectations 字段校验报告")
    print("=" * 60)

    all_results = {}
    for file_name in FILES:
        try:
            results = validate_file(context, file_name, datasource)
            all_results[file_name] = results
            print_results_in_chinese(file_name, results)
        except Exception as e:
            print(f"\n❌ 处理文件 {file_name} 时出错: {e}")

    print(f"\n{'='*60}")
    print("📋 总体汇总")
    print(f"{'='*60}")
    total_files = len(FILES)
    total_failed = sum(1 for r in all_results.values() if not r.success)
    print(f"校验文件数: {total_files}")
    print(f"通过文件数: {total_files - total_failed}")
    print(f"失败文件数: {total_failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
