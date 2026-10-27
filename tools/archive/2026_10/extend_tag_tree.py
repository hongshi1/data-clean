#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扩展标签树: 把36个实际questionLabel挂到四层树的对应分支
使 领域树视图 的 questionCount 全部点亮（getTags按Question.label匹配计数）"""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ED = "http://localhost:1717"
PID = "xZb5IZMWfTmO"


def http(method, url, payload=None, timeout=30):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def flat_tags(resp):
    out = {}
    def walk(nodes):
        for n in nodes or []:
            out[n["label"]] = n
            walk(n.get("child"))
    walk(resp.get("tags", []))
    return out


def main():
    tags = flat_tags(http("GET", f"{ED}/api/projects/{PID}/tags"))
    print(f"现有树节点: {len(tags)}")

    def add(label, parent_label):
        if label in tags:
            return
        p = tags.get(parent_label)
        assert p, f"父节点不存在: {parent_label}"
        resp = http("PUT", f"{ED}/api/projects/{PID}/tags",
                    {"tags": {"label": label, "parentId": p["id"]}})
        tags[label] = resp.get("tags", {})
        print(f"  + {label} → {parent_label}")

    # 域内注入族(新父节点)
    if "域内注入族" not in tags:
        resp = http("PUT", f"{ED}/api/projects/{PID}/tags",
                    {"tags": {"label": "域内注入族", "parentId": tags["PoolA-域内真实SRS"]["id"]}})
        tags["域内注入族"] = resp.get("tags", {})
        print("  + 域内注入族 → PoolA")

    uml = ["UML-ASSOCIATION", "UML-usecase", "UML-actor", "UML-REALIZATION", "UML-state",
           "UML-DIRECTED", "UML-boundary", "UML-component", "UML-interface", "UML-COMPOSITION"]
    for tag in uml:
        add(tag, "UML族")
    t_series = ["T1_visual_consistency", "T2_table_factual", "T3_counting", "T4_tracing",
                "T5_text_understanding", "T7_consistency", "T8_cross_reference"]
    for tag in t_series:
        add(tag, "章节QA族")
    for tag in ["terminology", "gjb_compliance", "business_logic", "parameter"]:
        add(tag, "域内注入族")
    for tag in ["P1_需求识别", "P2_术语问答", "P3_章节结构", "P4_修饰符"]:
        add(tag, "外部-PURE")
    for tag in ["N1_冲突判别", "N2_缺陷分类", "N3_FRNFR分类"]:
        add(tag, "外部-NLIRE")
    for tag in ["A1_指代歧义", "A2_并列歧义"]:
        add(tag, "外部-歧义类")
    for tag in ["F1_topological", "F1_applied_scenario", "F1_fact_retrieval", "F1_flow_referential"]:
        add(tag, "外部-FlowVQA")
    add("L1_质量评估", "外部-LLMGen")

    # 验证(正确键名: child; questionCount按Question.label)
    tree = http("GET", f"{ED}/api/projects/{PID}/tags").get("tags", [])
    def show(nodes, depth=0):
        for n in nodes:
            qc = n.get("questionCount", 0)
            print("  " * depth + f"- {n['label']}" + (f"  [{qc}题]" if qc else ""))
            show(n.get("child"), depth + 1)
    print("\n最终标签树:")
    show(tree)
    print(f"根节点: {len(tree)}, 总节点: {len(flat_tags({'tags': tree}))}")


if __name__ == "__main__":
    main()
