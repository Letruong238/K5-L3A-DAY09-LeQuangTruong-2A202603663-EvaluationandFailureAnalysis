# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5` (ở thư mục `src`). Dương tính (positive) = FAIL, vì việc của judge là tìm lỗi.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có (cả 3) | **Dùng** (kèm sửa rubric bên dưới) |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và recall đều dưới sàn | **Loại**, không dùng làm gate |

Ma trận nhầm lẫn (tp / fp / fn / tn):
- tone_ok: 24 / 4 / 6 / 66. Tỉ lệ lỗi quan sát 0.28, sau hiệu chỉnh Rogan-Gladen 0.30.
- helpful: 9 / 0 / 21 / 70. Tỉ lệ lỗi quan sát 0.09, sau hiệu chỉnh 0.30.

## ≥5 case audit thủ công (tone_ok, 10 bất đồng)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú / sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha…" | PASS | FAIL | Người | Xưng "em" + "nha" quá suồng sã. Rubric: cấm "nha/nhé/nè" và xưng hô ngoài "LogiX – anh/chị". |
| 2 | H-029 "…không cần nhắn thêm." | PASS | FAIL | Người | Giọng ra lệnh. Judge chỉ thấy "Dạ, vui lòng". Rubric: câu cấm/ra lệnh khách là FAIL dù có "Dạ". |
| 3 | H-063 "…sẽ hoàn thêm cho anh/chị ạ." | PASS | FAIL | Người | Hứa ngoài kết quả hệ thống. Lỗi này thuộc FM-08 nên cần grader code, không để judge đoán. |
| 4 | H-070 "…ạ 😂😂" | PASS | FAIL | Người | Emoji không hợp ngữ cảnh khiếu nại. Rubric: cấm emoji trong phản hồi khiếu nại. |
| 5 | H-081 "…chưa đủ điều kiện hoàn…" | FAIL | PASS | **Judge** | Ghi chú dữ liệu: nhãn người sai (đọc nhầm ticket). Sửa nhãn người thành FAIL, không sửa judge. |
| 6 | H-051 "…đã refund 90.000đ…" | FAIL | PASS | Người | CS LogiX cho phép từ "refund". Rubric: nêu rõ từ vay mượn được phép, đừng phạt tiếng Anh. |
| 7 | H-042 "…đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | Người | Ngắn nhưng đủ ý. Judge phạt vì "thiếu xin lỗi". Rubric: xin lỗi chỉ bắt buộc khi từ chối hoặc có sự cố. |

Cách đọc kết quả: judge bỏ sót phần lớn là giọng điệu tinh tế (suồng sã, ra lệnh, emoji); judge báo nhầm do rubric chưa nói rõ (refund, xin lỗi). Cả hai đều sửa được bằng rubric cụ thể hơn, nên tone_ok đáng dùng.

## Kết luận
- **helpful bị loại.** Recall chỉ 0.30 (bắt 9 trong 30 lỗi thật), κ=0.375, đều dưới sàn. Ma trận nhầm lẫn cho thấy 21 lần bỏ sót. Phần lớn là reply nói một số tiền còn ledger ghi số khác (ví dụ HL-015 nói 55.000đ, ledger 40.000đ) và các câu trả lời cụt kiểu "Ok bạn, đơn … xử lý rồi nhé". Judge không nhìn thấy ledger, nên không thể phát hiện lỗi số tiền. Precision 1.0 không cứu được: judge không bao giờ báo nhầm, nhưng bỏ lọt phần lớn lỗi, nên một gate dựa vào nó sẽ cho qua hầu hết bản tệ.
- **Hệ quả cho gate:** lỗi "reply nói số tiền khác ledger" (FM-08) phải chấm bằng code so sánh số trong reply với ledger (metric ở M3), không dùng judge.
- **Tỉ lệ lỗi helpful** quan sát 0.09 nhưng thực tế khoảng 0.30 sau hiệu chỉnh: nếu tin judge, ta tưởng agent tốt gấp ba lần thực tế.
- **Rủi ro còn lại:** judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có tập held-out thật. Một số nhãn người cũng có thể sai (H-081).
