from scenario5.tools.run_cv_benchmark import (
    box_iou_xyxy,
    iou_distance_matrix,
    parse_meva_activities,
    read_mot_gt,
    xyxy_to_xywh,
)


def test_read_mot_gt_filters_invalid_classes_and_frame_range() -> None:
    text = """1,7,10,20,30,40,1,1,1
2,8,11,21,31,41,0,1,1
3,9,12,22,32,42,1,3,1
4,10,13,23,33,43,1,1,1
"""
    assert read_mot_gt(text, 1, 3) == {
        1: [(7, 10.0, 20.0, 30.0, 40.0)],
    }


def test_box_conversions_and_iou() -> None:
    assert xyxy_to_xywh((10, 20, 40, 60)) == (10.0, 20.0, 30.0, 40.0)
    assert box_iou_xyxy((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert box_iou_xyxy((0, 0, 10, 10), (10, 10, 20, 20)) == 0.0


def test_iou_distance_matrix_gates_below_threshold_pairs() -> None:
    result = iou_distance_matrix(
        [(0.0, 0.0, 10.0, 10.0), (30.0, 30.0, 10.0, 10.0)],
        [(0.0, 0.0, 10.0, 10.0), (12.0, 0.0, 10.0, 10.0)],
        0.5,
    )
    assert result[0, 0] == 0.0
    assert result[0, 1] != result[0, 1]
    assert result[1, 0] != result[1, 0]


def test_parse_meva_activity_span_and_actor() -> None:
    import tempfile
    from pathlib import Path

    text = "- { act: { act3: { Enter_Facility: 1.0 } , id2: 1, timespan: [{tsr0: [2679, 2734]}], actors: [{ id1: 0, timespan: [{tsr0: [2679, 2734]}]}  ]} }\n"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "activities.yml"
        path.write_text(text, encoding="utf-8")
        rows = parse_meva_activities(path)
    assert rows == [{"activity": "Enter_Facility", "start_frame": 2679, "end_frame": 2734, "actor_ids": [0]}]
