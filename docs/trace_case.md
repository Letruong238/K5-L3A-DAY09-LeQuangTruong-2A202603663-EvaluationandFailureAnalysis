# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case của nhóm: C-002@11, FM-03 ticket_trust

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `R-seeded_regression-C-002-s11`, trong report `E-seeded_regression-20261117-15e0` |
| Triệu chứng | Lab 8 grader FAIL: `status resolved != denied`. Ledger ghi hoàn 20.000đ (1 lần) trong khi nhãn là 0đ (từ chối). Reply nói "đã hoàn 20.000đ cho đơn O-202", khớp ledger nên một reply trôi chảy che mất việc hoàn sai. |
| Bước sai đầu tiên | **Event 3, `model_override {"delay_days": 5}`**: agent ghi đè số ngày trễ bằng số trong ticket (5 ngày), trong khi DB ghi `delay_days = 2` cho đơn O-202. |
| Vì sao là bước *đầu tiên* | Event 1 (`handoff`) và event 2 (`investigator`) đúng: agent tra được đơn O-202 và lấy đúng `delay_days: 2` từ DB. Sai lệch bắt đầu ở event 3. Event 4 (`quote` 20.000đ, clause `SHIP-LATE-03`), event 5 (`refund_history`) và event 6 (`reply`) chỉ là hệ quả của số ngày bị ghi đè. |
| Failure mode | **FM-03 ticket_trust** (`docs/failure_taxonomy.md`) |
| Đối chứng | `fixed C-002@11`: không có event `model_override`; event 3 là `quote {"amount_vnd": 0, "reason": "no_entitlement"}` nên không hoàn tiền; reply "đơn O-202 chưa đủ điều kiện hoàn". Ledger 0đ, status `denied`, khớp nhãn. |
| Regression test | `tests/test_lab9_trace_case.py` (3 test). `test_first_wrong_step_is_model_override` và `test_graders_catch_the_regression` kiểm tra bản lỗi: có `model_override {"delay_days": 5}` đứng trước `quote`, `RefundAmountCorrect` = False, `DbFactKept` = False. `test_fixed_passes_everything` kiểm tra `fixed` qua mọi grader. Đã chạy: 14 passed cùng các test lab9 khác. |
| Chưa chắc chắn | Trace không cho biết **vì sao** agent tin ticket: ở bản mô phỏng đây là công tắc lỗi `ticket_trust`, không phải lý do của model thật. Mới kiểm tra 1 claim và 1 seed. Test này không chứng minh các FM khác. |

Lệnh tái hiện (ở thư mục `src`):
```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= tests/test_lab9_trace_case.py
```

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
