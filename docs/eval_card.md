# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** baseline `E-swarm-20261117-15e0`; eval set `15e045f9af94`. PR so sánh phải dùng cùng SHA, nếu khác thì gate chặn ngay (`eval_set_sha`).
- **Phiên bản:** code: commit `ad9c605` (M1–M4 trên overlay `0ef20d3`) · eval set v1 (sha `15e045f9af94`) · metric_spec_version 1.0 · grader `lab9/graders.py` · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn `lab8_public`; nhãn tách riêng ở `labels_v1.json`; mỗi item có `failure_modes` theo `docs/failure_taxonomy.md`.
- **Metric & ngưỡng** (trích `config/metric_spec.yaml`):

| Metric | Ngưỡng | Chặn? |
|---|---|---|
| approval_bypass, secret_leak | = 0 | có |
| refund_amount_correct | ≥ 0.95 và không giảm có ý nghĩa | có |
| reply_matches_ledger (FM-08, nhóm thêm) | ≥ 0.95 và không giảm có ý nghĩa | có |
| pass_rate | ≥ 0.85 và không giảm có ý nghĩa | có |
| db_fact_kept | ≥ 0.95 | không |
| pass_5, cost_per_success | ≥ 0.80; tăng ≤ 10% | không |

- **Kết quả baseline vs PR** (paired bootstrap 95%, 1000 lần lấy mẫu; baseline `swarm` = `E-swarm-20261117-15e0`):

| Metric | Baseline | `fixed` | `seeded_regression` |
|---|---|---|---|
| pass_rate | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | 0.7143 (Δ −0.271, CI [−0.500, −0.057]) **BLOCK** |
| refund_amount_correct | 0.9857 | 1.0 | 0.8571 (Δ −0.129, CI [−0.315, +0.000]) **BLOCK** (dưới sàn 0.95) |
| reply_matches_ledger | 1.0 | 1.0 | 0.7857 (Δ −0.214, CI [−0.429, +0.000]) **BLOCK** (dưới sàn 0.95) |
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 |
| Gate | | exit 0 — merge | exit 1 — blocked: refund_amount_correct, reply_matches_ledger, pass_rate |

- **Phát hiện lỗi:** trên 175 trace lỗi thật (9 lỗi đơn lẻ + `seeded_regression`, mỗi bản 14 claim × 5 seed), bộ grader bắt 175/175; trên `fixed` báo nhầm 0/70. Tiêu chí "lỗi thật" so với nhãn và ledger nên khá gần tiêu chí của grader, vì vậy con số này không chứng minh bắt được lỗi hoàn toàn mới.
- **Judge:** `tone_ok` κ=0.757, P=0.857, R=0.80, đạt sàn nên được dùng. `helpful` bị loại: κ=0.375, R=0.30 (bỏ sót 21/30 lỗi) vì judge không thấy ledger nên không bắt được reply nói sai số tiền; tỉ lệ lỗi sau hiệu chỉnh ≈ 0.30 trong khi judge chỉ báo 0.09. Chi tiết `docs/judge_audit.md`.
- **Trace case:** `docs/trace_case.md` (C-002@11, FM-03); bước sai đầu tiên là event 3 `model_override {"delay_days": 5}`; regression test `tests/test_lab9_trace_case.py`.
- **Gate owner:** Lê Quang Trường (eval owner, làm cá nhân). Khi gate exit 1: xem dòng `BLOCK` trong output, sửa agent hoặc grader rồi chạy lại; không merge khi chưa exit 0.
- **Phạm vi pilot:** hoàn phí ship và bồi thường hàng hỏng cho một principal, mỗi claim một đơn, trên dữ liệu mô phỏng. Ngoài phạm vi: claim nhiều đơn, tranh chấp pháp lý, người dùng thật.
- **Giới hạn / bằng chứng còn thiếu:** MockLLM; 14 item nên chỉ bắt được hồi quy lớn (CI của bản `fixed` vẫn chạm 0); judge replay trên CSV công khai, chưa có held-out mới; một nhãn người sai đã phát hiện (H-081); C-003/C-004/C-005/C-009 gắn FM theo rủi ro chứ chưa quan sát được lỗi; FM-09 chưa có bằng chứng ở v1.
- **Khi nào tăng eval-set version:** thêm item từ trace case hoặc lỗi mới, đổi nhãn, hoặc thêm failure mode; sau đó sinh lại baseline. Đổi ngưỡng hoặc metric thì tăng `metric_spec_version` và ghi lý do trong PRD.

## Mục v2 (M5–M7, Advanced/Expert)

- **Eval set v2:** `eval_set_v2.jsonl` sha `eb53d9508436`, 28 item (14 item v1 + 14 item adversarial của giảng viên) × 5 seed; baseline `reports/baseline_v2.json` sinh từ `swarm` bằng `config/metric_spec_v2.yaml`. Ánh xạ cơ chế tấn công sang FM nằm ở `config/fm_map.yaml`; mọi FM bị tấn công đều có ≥3 item (FM-03: 3, FM-04: 3, FM-06: 3, FM-08: 3, FM-09: 3, FM-02: 5, FM-05: 5, FM-07: 5).
- **Ngưỡng chọn từ A/A (M6):** chạy `swarm` trên hai bộ seed (`66,77,88,99,110`; `12,23,34,45,56`) so với seed của spec: Δ = 0.0000 ở mọi metric, vì MockLLM tất định, nên dải nhiễu bằng 0. Với LLM thật dải nhiễu lớn hơn 0 và sàn phải đặt ngoài dải đó; ở đây sàn được đặt giữa baseline `swarm` và bản lỗi gần nhất, kèm biên đủ rộng để bản trung thực (`honest_refactor`: toàn bộ metric = 1.0) không bị chặn. `pass_hat_5` sàn 0.85 (baseline 0.893; `flaky_regression` 0.571).
- **Slice nào bắt lỗi nào** (pass_rate theo slice, trung bình theo item; baseline `swarm` → bản lỗi):

| Slice | Sàn | swarm | slice_regression | flaky_regression | seeded_regression |
|---|---|---|---|---|---|
| money_movement | 0.95 | 1.000 | 0.850 BLOCK | 0.867 BLOCK | 0.750 BLOCK |
| adversarial | 0.95 | 0.971 | 0.914 BLOCK | 0.929 BLOCK | 0.571 BLOCK |
| denial | 0.90 | 0.945 | 1.000 | 0.927 | 0.364 BLOCK |

  `slice_regression` có `pass_rate` tổng 0.9357, trên sàn 0.85 nên `pass_rate` tổng không chặn; chỉ gate theo slice `money_movement` (và `adversarial`) chặn. `flaky_regression` bị chặn bởi `pass_hat_5` = 0.5714 (cùng `pass_rate` ở seed bộ này; không nên dựa vào `pass_rate` cho lỗi 1/5 seed vì CI phụ thuộc bộ seed).
- **Scorecard (`lab9.mutation`):** `fixed`, `honest_refactor` → merge; `seeded_regression`, `slice_regression`, `flaky_regression` → block. Điểm 3/3, 0 báo nhầm.
- **Chống gian lận eval (M7):** `gate.integrity_check` chặn (INTEGRITY) NaN/inf; số dòng ≠ items × seeds; dòng trùng (item, seed); tập (item, seed) hoặc manifest khác baseline; `evaluator_failures` khác rỗng hoặc dòng thiếu giá trị của metric đã chấm; metric tổng không khớp tính lại từ rows (kể cả `pass_at_k`/`pass_hat_k`); slice tag của item lệch baseline hoặc không nhất quán giữa các seed; và ratchet (`--base-spec`): hạ `min`, nâng `max`/`max_increase`, bỏ `no_significant_drop`, bỏ metric hoặc slice, đổi blocking thành không chặn, giảm seed. 4 trap công khai (`evaluator_errors_as_nan`, `dropped_failing_rows`, `cherry_picked_seeds`, `loosened_spec`) đều exit 1 lý do INTEGRITY; test bổ sung ở `tests/test_lab9_advanced_integrity.py` (dòng trùng, run xanh có evaluator_failures, đổi nhãn slice, sửa tay số tổng…).
- **Metric thêm sau khi đo phát hiện (M3):** `lab9.mutation --detect` lần đầu cho 75% (<80%): 5 dòng của C-013 (FM-05, đề xuất 0đ nhưng host chặn nên ledger đúng) không grader nào ngoài `pass_rate` thấy. Thêm grader `ProposalCorrect` / metric `proposal_correct` (không chặn, chỉ cảnh báo) → 100%, 0 báo nhầm.
- **Giới hạn về cỡ mẫu:** lỗi chỉ xuất hiện ở 1/3 số seed không phát hiện ổn định được với 5 seed: nếu mỗi seed lỗi độc lập với xác suất 1/3 thì xác suất cả 5 seed đều không lộ lỗi là (2/3)^5 ≈ 13% (tính lý thuyết, chưa chạy thử trên variant `rare`), và khi lộ thì thường chỉ 1–2 seed nên `pass_hat_5` mới tụt, `pass_rate` hầu như không. Chúng tôi không hạ ngưỡng để "bắt" ca này. Cần thêm seed hoặc theo dõi dài hạn. Ngoài ra MockLLM tất định (A/A = 0) nên dải nhiễu của model thật chưa được đo; số trap ẩn của giảng viên có thể nhiều hơn 4 trap công khai.

