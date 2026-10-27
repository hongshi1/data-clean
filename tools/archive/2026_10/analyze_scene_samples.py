# -*- coding: utf-8 -*-
"""场景解析器设计前的样例分析: 用例图/流程图/other类结构详情"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
av = json.load(open("data/gjb_438c/anchor_v2/anchors_v2.json", encoding="utf-8"))


def show(doc, idx, title, max_nodes=20, max_edges=25):
    s = av[doc]["structures"][idx]
    print(f"=== {title} ({doc[:8]} s{idx}) ===")
    print(f"page: {s['page']}, meta: {json.dumps(s['meta'], ensure_ascii=False)[:200]}")
    for n in s["nodes"][:max_nodes]:
        bbox = [round(v, 2) for v in n["bbox"]]
        print("  node {:5s} {:9s} bbox={} text={!r}".format(
            n["id"], n["type"], bbox, n["text"][:24]))
    for e in s["edges"][:max_edges]:
        print("  edge {}({!r}) -> {}({!r}) label={!r} via={}".format(
            e["src"], e["src_text"][:10], e["dst"], e["dst_text"][:10],
            e["label"][:12], e["via"]))
    print()


# 1. 用例图
show("01数据获取转换分系统需求规格说明-终稿", 2, "用例图样例")
# 2. 复杂用例图(doc02 s2: boundary1 usecase5 actor7)
show("02界面集成框架软件需求规格说明-终稿", 2, "复杂用例图样例")
# 3. 流程图
show("02界面集成框架软件需求规格说明-终稿", 0, "流程图样例")
# 4. other类(全process)
show("02界面集成框架软件需求规格说明-终稿", 1, "other类样例(功能图?)")
# 5. sc3接口图: 找doc04(数据统一访问,接口多)的一个结构看看
show("04数据统一访问服务软件需求规格说明-终稿", 3, "doc04样例(可能接口图)")
