from tools.mine_function_predicates import (
    mine_function_predicate,
    recompute_slots,
    strip_object_suffix,
    subject_before,
)


def test_whitelist_regex_hits_verb_object_pair() -> None:
    mined = mine_function_predicate("本系统应提供数据获取功能。")
    assert mined is not None
    assert mined["verb"] == "提供"
    assert mined["object_raw"] == "数据获取"
    assert mined["object_stripped"] == "数据获取"
    # 后瞻是零宽断言: 后缀词(功能)不进宾语, 剥离后缀恒为空串
    assert mined["suffix"] == ""


def test_object_suffix_is_stripped() -> None:
    stripped, suffix = strip_object_suffix("数据传输服务")
    assert stripped == "数据传输"
    assert suffix == "服务"
    mined = mine_function_predicate("系统提供数据传输服务。")
    assert mined is not None
    assert mined["object_stripped"] == "数据传输"
    # 后缀词在零宽后瞻处, 不属于宾语原始串
    assert mined["suffix"] == ""


def test_object_stripped_below_two_chars_is_excluded() -> None:
    # 宾语=后缀本身: 剥离后0字 → 跳过; 其后无候选 → None
    assert mine_function_predicate("系统支持服务功能。") is None
    # 同理: 宾语剥后只剩1字也被排除
    assert mine_function_predicate("系统具备告警功能。") is not None


def test_light_verb_object_candidate_is_skipped() -> None:
    # 宾语以"基于"开头(介词短语作伪宾语) → 该候选跳过且无后续候选
    assert mine_function_predicate("系统支持基于证书的鉴权功能。") is None


def test_light_verb_skip_falls_through_to_next_candidate() -> None:
    # 第一个候选(包括,通过网页的告警)宾语以"通过"开头被跳过,
    # 第二个候选(支持,数据加密)干净 → 取之 (一条claim只取第一个合格候选)
    mined = mine_function_predicate("包括通过网页的告警功能，支持数据加密服务。")
    assert mined is not None
    assert mined["verb"] == "支持"
    assert mined["object_stripped"] == "数据加密"


def test_first_qualifying_candidate_wins() -> None:
    mined = mine_function_predicate("系统应具备数据获取功能，并支持格式转换。")
    assert mined is not None
    assert mined["verb"] == "具备"
    assert mined["object_stripped"] == "数据获取"


def test_subject_before_strips_modals_and_particles() -> None:
    # 应/能够/可以属MODAL层, 不计入主语名词
    text = "本系统应提供数据获取功能。"
    start = text.index("提供")
    assert subject_before(text, start) == "本系统"
    text2 = "分系统能够完成数据汇聚。"
    assert subject_before(text2, text2.index("完成")) == "分系统"


def test_recompute_slots_fills_predicate_slot() -> None:
    row = {
        "subject_candidate": "本系统",
        "predicate_candidate": "",
        "operator": "",
        "object_value": None,
        "unit_raw": "",
        "scope_candidate": "3.1",
    }
    slots = recompute_slots(row, "提供数据获取")
    assert slots["slot_fill_fields"] == [
        "subject_candidate", "predicate_candidate", "scope_candidate",
    ]
    assert slots["slot_fill_rate"] == 0.5
    assert slots["parse_status"] == "parsed"


def test_recompute_slots_partial_when_rate_below_half() -> None:
    row = {
        "subject_candidate": "",
        "predicate_candidate": "",
        "operator": "",
        "object_value": None,
        "unit_raw": "",
        "scope_candidate": "3.1",
    }
    slots = recompute_slots(row, "提供数据获取")
    assert slots["slot_fill_fields"] == ["predicate_candidate", "scope_candidate"]
    assert slots["slot_fill_rate"] < 0.5
    assert slots["parse_status"] == "partial"
