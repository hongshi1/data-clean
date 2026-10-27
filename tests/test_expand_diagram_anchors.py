from tools.expand_diagram_anchors import (
    REQ_ID_RE,
    calibrate_theta,
    lexical_match,
    normalize_ws,
    prefix_overlap_len,
)


def test_l1_normalization_equality_ignores_whitespace() -> None:
    assert normalize_ws("数据获取\n转换") == "数据获取 转换".replace(" ", "")
    assert normalize_ws("  用户 登录\t流转 ") == "用户登录流转"
    assert normalize_ws("数据获取") != normalize_ws("数据获取转换")


def test_prefix_overlap_len() -> None:
    assert prefix_overlap_len("数据获取转", "数据获取转换") == 5
    assert prefix_overlap_len("用户登录", "数据处理") == 0


def test_lexical_substring_match_requires_min_length() -> None:
    hit = lexical_match("用户登录", "", "系统应支持用户登录功能。")
    assert hit is not None
    assert hit["kinds"] == ["substring"]
    assert hit["score"] == 1.0
    # <4字不做子串匹配
    assert lexical_match("登录", "", "系统应支持用户登录功能。") is None


def test_lexical_prefix_match_requires_prefix_relation() -> None:
    # node是title前缀(k=5≥4) → 命中
    hit = lexical_match("数据获取转", "数据获取转换", "")
    assert hit is not None
    assert hit["kinds"] == ["prefix"]
    assert hit["score"] == round(5 / 6, 4)
    # 前4字相同但互非前缀 → 不命中(宁缺勿滥)
    assert lexical_match("数据获取界面", "数据获取转换", "") is None
    # title是node前缀(k=4) → 命中
    hit2 = lexical_match("数据获取转换模块", "数据获取", "")
    assert hit2 is not None
    assert hit2["kinds"] == ["prefix"]


def test_lexical_combined_kinds_takes_max_score() -> None:
    hit = lexical_match("数据获取", "数据获取", "…数据获取…")
    assert hit is not None
    assert set(hit["kinds"]) == {"substring", "prefix"}
    assert hit["score"] == 1.0


def test_calibrate_theta_picks_smallest_threshold_meeting_precision() -> None:
    pos = [0.9, 0.85, 0.8, 0.7]
    neg = [0.75, 0.4, 0.3, 0.2]
    cal = calibrate_theta(pos, neg, target=0.95)
    assert cal["target_met"] is True
    assert cal["theta"] == 0.8
    assert cal["tp"] == 3
    assert cal["fp"] == 0
    assert cal["precision"] == 1.0
    assert cal["recall"] == 0.75
    assert abs(cal["auc"] - 0.9375) < 1e-9


def test_calibrate_theta_clean_separation() -> None:
    cal = calibrate_theta([0.9, 0.85, 0.8], [0.5, 0.4, 0.3])
    assert cal["target_met"] is True
    assert cal["theta"] == 0.8
    assert cal["precision"] == 1.0
    assert cal["recall"] == 1.0
    assert cal["auc"] == 1.0


def test_calibrate_theta_falls_back_when_target_unmet() -> None:
    cal = calibrate_theta([0.6, 0.55], [0.9, 0.85])
    assert cal["target_met"] is False
    assert cal["theta"] == 0.55
    assert cal["precision"] == 0.5


def test_requirement_id_regex_requires_word_boundaries() -> None:
    assert REQ_ID_RE.findall("见需求 ZZSJHQZHFW-GN-SJHQ 条目") == ["ZZSJHQZHFW-GN-SJHQ"]
    # CJK紧邻无词边界 → 不命中(与实测L0=0一致)
    assert REQ_ID_RE.search("接口ZZSJHQZHFW-GN-SJHQ负责") is None
    # 段数不足(仅2段)不命中
    assert REQ_ID_RE.search("ZZSJHQZHFW-GN") is None
