"""M7: các kiểu gian lận ngoài 4 trap công khai (dòng trùng, evaluator_failures trên run xanh,
đổi nhãn slice, sửa tay số tổng, hạ ngưỡng kiểu khác). Mỗi test tự dựng report tổng hợp.
Chạy: python -m pytest -q -m student -o addopts= -k advanced"""
import copy
import math

import pytest

pytestmark = pytest.mark.student

SEEDS = (1, 2)
ITEMS = 4


def _rows(fail=()):
    """4 item × 2 seed; item 0-1 thuộc slice denial. `fail` = tập (item, seed) bị fail."""
    return [{"item_id": f"E-{i:03d}", "seed": s, "pass_rate": (i, s) not in fail,
             "slices": ["denial"] if i < 2 else []} for i in range(ITEMS) for s in SEEDS]


def _report(rows, metrics=None, failures=()):
    ok = sum(bool(r.get("pass_rate")) for r in rows) / len(rows) if rows else 0
    return {"manifest": {"eval_set_sha": "x", "items": ITEMS, "seeds": list(SEEDS)}, "rows": rows,
            "metrics": metrics if metrics is not None else {"pass_rate": round(ok, 4)},
            "evaluator_failures": list(failures)}


SPEC = {"eval_set_version": "v2", "seeds": [1, 2],
        "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                     "threshold": {"min": 0.8, "no_significant_drop": True}}],
        "slices": [{"name": "denial", "metric": "pass_rate", "min": 0.9, "blocking": True}]}


@pytest.fixture(scope="module")
def gate():
    from lab9 import gate

    return gate


def test_honest_report_is_clean(gate):
    base = _report(_rows())
    assert gate.integrity_check(base, base, SPEC, SPEC) == []


def test_duplicated_rows_padding_the_count(gate):
    base = _report(_rows())
    rows = _rows(fail={(2, 1)})
    rows = [r for r in rows if not (r["item_id"] == "E-002" and r["seed"] == 1)] + [copy.deepcopy(rows[0])]
    assert len(rows) == ITEMS * len(SEEDS)           # số dòng vẫn đủ, nhưng có dòng trùng và thiếu (E-002, 1)
    assert gate.integrity_check(_report(rows), base, SPEC)


def test_evaluator_failures_on_an_otherwise_green_run(gate):
    base = _report(_rows())
    green = _report(_rows(), failures=["E-001@1:RefundAmountCorrect:boom"])
    assert gate.integrity_check(green, base, SPEC)


def test_relabelled_slice_hides_a_failing_item(gate):
    base = _report(_rows())
    rows = _rows(fail={(0, 1)})
    rows[0]["slices"] = rows[1]["slices"] = []        # bỏ item 0 khỏi slice denial để né slice gate
    assert gate.integrity_check(_report(rows), base, SPEC)


def test_hand_edited_metric_total(gate):
    base = _report(_rows())
    rows = _rows(fail={(2, 1), (3, 2)})
    assert gate.integrity_check(_report(rows, {"pass_rate": 1.0}), base, SPEC)       # số tổng không khớp rows
    assert gate.integrity_check(_report(rows), base, SPEC) == []                       # số đúng thì sạch


def test_infinite_metric(gate):
    base = _report(_rows())
    assert gate.integrity_check(_report(_rows(), {"pass_rate": math.inf}), base, SPEC)


def test_row_with_missing_grader_value(gate):
    base = _report(_rows())
    rows = _rows()
    del rows[3]["pass_rate"]
    assert gate.integrity_check(_report(rows), base, SPEC)


def test_ratchet_other_loosenings(gate):
    base = _report(_rows())
    nonblock = copy.deepcopy(SPEC)
    nonblock["metrics"][0]["blocking"] = False
    assert gate.integrity_check(base, base, nonblock, SPEC)           # blocking -> non-blocking
    removed = copy.deepcopy(SPEC)
    removed["metrics"] = []
    assert gate.integrity_check(base, base, removed, SPEC)            # metric biến mất
    noslice = copy.deepcopy(SPEC)
    noslice["slices"] = []
    assert gate.integrity_check(base, base, noslice, SPEC)            # slice biến mất
    lowslice = copy.deepcopy(SPEC)
    lowslice["slices"][0]["min"] = 0.1
    assert gate.integrity_check(base, base, lowslice, SPEC)           # slice min hạ
    fewer = copy.deepcopy(SPEC)
    fewer["seeds"] = [1]
    assert gate.integrity_check(base, base, fewer, SPEC)              # bớt seed
    stricter = copy.deepcopy(SPEC)
    stricter["metrics"][0]["threshold"]["min"] = 0.95
    assert gate.integrity_check(base, base, stricter, SPEC) == []     # siết chặt thì được


def test_ratchet_ignored_for_a_new_eval_set_version(gate):
    base = _report(_rows())
    new = copy.deepcopy(SPEC)
    new["eval_set_version"] = "v3"
    new["metrics"][0]["threshold"]["min"] = 0.1
    assert gate.integrity_check(base, base, new, SPEC) == []          # version mới được đặt lại ngưỡng
