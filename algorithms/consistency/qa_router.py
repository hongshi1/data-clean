"""Question-aware, conservative candidate routing over legacy check-item IDs.

The router proposes detector families; it does not decide verdicts or expose gold labels.
"""
from __future__ import annotations

import re


_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("LOGIC-02", ("异常", "故障处理", "错误处理", "失败时")),
    ("LOGIC-03", ("顺序", "先", "后", "主事件流", "步骤")),
    ("LOGIC-04", ("流向", "发送方", "接收方", "回传", "数据流")),
    ("LOGIC-05", ("分支", "工况", "场景", "模式", "哪些状态")),
    ("LOGIC-09", ("权限", "角色", "允许", "禁止", "访问控制")),
    ("LOGIC-10", ("恢复", "重启", "故障后")),
    ("LOGIC-11", ("重搜", "重新搜索", "增量搜索", "全量搜索")),
    ("PARAM-01", ("响应时间", "处理时间", "时延", "延迟")),
    ("PARAM-02", ("周期", "频率", "间隔")),
    ("PARAM-03", ("阈值", "门限")),
    ("PARAM-04", ("对齐误差", "时间对齐", "融合误差")),
    ("PARAM-05", ("内存", "CPU", "带宽", "资源占用", "磁盘")),
    ("PARAM-06", ("取值范围", "值域", "上下界")),
    ("PARAM-07", ("存储容量", "保存时长", "保留期限")),
    ("PARAM-08", ("守时精度", "同步精度", "同步误差")),
    ("PARAM-09", ("降级阈值", "降级触发")),
    ("PARAM-10", ("故障持续", "故障判定时长", "恢复超时")),
    ("TERM-06", ("毫秒", "秒", "单位", "精度")),
    ("TERM-08", ("缩写", "简称", "全称")),
    ("TERM-07", ("接口名", "接口类型", "接口标识")),
    ("TERM-05", ("指令", "命令")),
    ("TERM-04", ("告警", "状态")),
    ("TERM-03", ("包括哪些", "包含哪些", "几种", "数量", "所有")),
    ("GJB-05", ("追溯", "映射到", "对应测试")),
    ("GJB-01", ("可测试", "可验证", "量化指标")),
    ("TERM-01", ("术语", "同义", "别名", "名称是否一致", "是否同一")),
    ("TERM-02", ("定义", "含义", "同名")),
    ("LOGIC-01", ("优先", "优先级", "抢占")),
    ("LOGIC-06", ("互斥", "不能同时", "独占")),
    ("LOGIC-07", ("原子", "不可中断", "可中断", "打断")),
    ("LOGIC-08", ("主备", "冗余", "仲裁", "备用", "切换到")),
    ("GJB-02", ("容错", "故障容错")),
    ("GJB-03", ("访问控制", "权限控制", "安全控制")),
    ("GJB-04", ("审计", "日志记录", "记录哪些")),
    ("GJB-06", ("报警要素", "报警级别", "报警内容", "报警原因")),
    ("GJB-07", ("自检", "自测试", "开机检测")),
    ("GJB-08", ("掉电", "断电保护", "掉电保护")),
    ("GJB-09", ("输入校验", "输入防护", "非法输入", "输入过滤")),
    ("GJB-10", ("升级", "回滚", "版本更新")),
    ("GJB-11", ("降级模式", "降级运行")),
)


def route_question(question: str) -> tuple[str, ...]:
    """Return ordered candidate types; no match is explicit, not a verdict."""
    q = re.sub(r"\s+", "", question)
    hits = [check_item for check_item, terms in _RULES
            if any(term in q for term in terms)]
    return tuple(dict.fromkeys(hits))
