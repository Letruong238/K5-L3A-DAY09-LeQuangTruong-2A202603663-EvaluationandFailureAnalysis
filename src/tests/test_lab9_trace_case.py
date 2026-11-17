"""Regression test cho trace case C-002@11 (docs/trace_case.md): FM-03 ticket_trust.

Ticket nói trễ 5 ngày, DB nói 2 ngày. Bản lỗi phải bị grader bắt, bản `fixed` phải qua.
Chạy: python -m pytest -q -m student -o addopts= -k "lab9 and not advanced"
"""
import pytest

pytestmark = pytest.mark.student


def _ctx(trial, label):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=label, output=trial,
                            duration=0.0, _span_tree=None, attributes={}, metrics={})


@pytest.fixture(scope="module")
def cases():
    from lab9.trace_case import investigate

    return {shape: investigate(shape, "C-002", 11) for shape in ("seeded_regression", "fixed")}


def test_first_wrong_step_is_model_override(cases):
    events = cases["seeded_regression"]["trial"]["events"]
    kinds = [e["kind"] for e in events]
    assert "model_override" in kinds
    # bước sai đầu tiên: agent ghi đè delay_days bằng số trong ticket (5), trong khi DB ghi 2
    first = next(e for e in events if e["kind"] == "model_override")
    assert first["payload"] == {"delay_days": 5}
    assert kinds.index("model_override") < kinds.index("quote")   # sai trước khi báo giá


def test_graders_catch_the_regression(cases):
    from lab9 import graders

    t, label = cases["seeded_regression"]["trial"], cases["seeded_regression"]["label"]
    assert graders.RefundAmountCorrect().evaluate(_ctx(t, label)).value is False   # ledger 20.000 thay vì 0
    assert graders.DbFactKept().evaluate(_ctx(t, label)).value is False            # có event model_override
    assert t["lab8_pass"] is False


def test_fixed_passes_everything(cases):
    from lab9 import graders

    t, label = cases["fixed"]["trial"], cases["fixed"]["label"]
    assert graders.RefundAmountCorrect().evaluate(_ctx(t, label)).value is True
    assert graders.DbFactKept().evaluate(_ctx(t, label)).value is True
    assert graders.ReplyMatchesLedger().evaluate(_ctx(t, label)).value is True
    assert graders.ApprovalBypass().evaluate(_ctx(t, label)).value is False
    assert t["lab8_pass"] is True
