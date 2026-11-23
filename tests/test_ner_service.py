"""ner_service单元测试: /api/ner的词法NER与召回通道分组."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "nkuDataProject" / "backend"))

from services import ner_service  # noqa: E402


def _ents(text: str) -> list[dict]:
    payload, status = ner_service.handle(None, {"text": text})
    assert status == 200, payload
    assert payload["ok"] is True
    return payload["data"]["entities"]


def test_supervision_entities_extracted():
    """监管词典命中: 人员/安全帽 → 监管实体通道, 带位置."""
    ents = _ents("判断图片中是否有人员未佩戴安全帽")
    texts = [e["text"] for e in ents]
    assert "人员" in texts
    assert "安全帽" in texts
    helmet = next(e for e in ents if e["text"] == "安全帽")
    assert helmet["start"] == "判断图片中是否有人员未佩戴安全帽".index("安全帽")
    assert helmet["end"] == helmet["start"] + 3
    assert helmet["recall_channel"] == "监管实体"
    assert helmet["kind"] == "PPE装备"
    assert helmet["color"]


def test_task_words_channel():
    """行为词走任务词通道(借道QA), 不计入种子数."""
    ents = _ents("夜班值守是否存在睡岗行为")
    sleep = next(e for e in ents if e["text"] == "睡岗")
    assert sleep["recall_channel"] == "任务词"
    assert sleep["kind"] == "行为"
    payload, _ = ner_service.handle(None, {"text": "夜班值守是否存在睡岗行为"})
    assert payload["data"]["n_seed"] == 0


def test_longest_first_non_overlapping():
    """最长优先: '作业人员'整体命中, 不拆成'人员'."""
    ents = _ents("作业人员正在作业")
    texts = [e["text"] for e in ents]
    assert "作业人员" in texts
    assert "人员" not in texts


def test_no_match_returns_empty():
    """无命中 → 空实体列表(仍ok)."""
    ents = _ents("随便一句话")
    assert ents == []


def test_bad_request_without_text():
    """text缺失 → 400."""
    payload, status = ner_service.handle(None, {})
    assert status == 400
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BAD_REQUEST"


def test_db_entities_when_available():
    """sqlite DB可用时: SRS实体(别名)进inventory并命中SRS实体通道."""
    try:
        from database import SessionLocal  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — 环境无DB配置时跳过
        import pytest

        pytest.skip("database not importable in this environment")
    db = SessionLocal()
    try:
        ner_service._INV_CACHE.pop(str(ner_service.db_kind), None)  # 清缓存强制重建
        payload, status = ner_service.handle(db, {"text": "数据获取包含哪些功能"})
        assert status == 200
        ents = payload["data"]["entities"]
        texts = [e["text"] for e in ents]
        assert "数据获取" in texts, f"数据获取 not in {texts[:5]}"
        dh = next(e for e in ents if e["text"] == "数据获取")
        assert dh["recall_channel"] == "SRS实体"
        assert dh["kind"] in {"功能", "分系统", "实体"}
        assert dh["doc"], "SRS实体应携带doc编号"
    finally:
        db.close()
        ner_service._INV_CACHE.pop(str(ner_service.db_kind), None)
