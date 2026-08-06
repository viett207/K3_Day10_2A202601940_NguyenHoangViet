# Individual Report — Nguyễn Hoàng Việt

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hoàng Việt |
| MSSV | 2A202601940 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 1 |
| Vai trò chính | Owner toàn bộ pipeline và báo cáo |
| Repository | C:\CodeLab\K3_Day10_2A202601940_NguyenHoangViet |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| End-to-end pipeline | script/run_phase1.py, script/run_corruption_flow.py | Raw Crossref data và cấu hình project | Baseline/corrupted/repaired artifacts và metrics | Hoàn thành |
| Observability và reporting | src/observability/reporting.py | Metrics, quality, freshness | phase1_report.md và corruption_report.md | Hoàn thành |
| Báo cáo nộp | report/group_report.md, report/individual_report.md | Artifact thực tế và metrics | Hai file Markdown báo cáo | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chạy baseline và xác minh artifact | data/results/baseline_metrics.json, data/reports/phase1_report.md | Metrics baseline và báo cáo pha 1 được tạo | Đọc file JSON/Markdown và kiểm tra artifact trên disk |
| Chạy corruption và repair | data/results/corrupted_metrics.json, data/results/repaired_metrics.json, data/results/corruption_log.json | So sánh baseline/corrupted/repaired và log corruption | Đọc các file JSON và báo cáo so sánh |
| Tạo report cá nhân và báo cáo nhóm | report/individual_report.md, report/group_report.md | Hai file báo cáo được sinh từ dữ liệu thực tế | Chạy python report/group_report.py và python report/individual_report.py |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Tôi cần trình bày rõ ràng sự khác biệt giữa baseline, corrupted và repaired dựa trên evidence thật, không chỉ mô tả lý thuyết.

### Cách triển khai

Tôi đọc các artifact JSON và Markdown đã có trong repo, dùng chúng làm nguồn dữ liệu chính để sinh báo cáo cá nhân và nhóm. Mỗi kết luận đều dựa vào metric và quality check thực tế, bao gồm retrieval hit rate, mean token F1, judge accuracy, judge score, plus failed checks và freshness.

## 5. Một quyết định kỹ thuật quan trọng

- Bối cảnh: Cần tránh viết báo cáo bằng nội dung giả tưởng khi repo đã có artifact thực tế.
- Các phương án đã cân nhắc: viết thủ công bằng mẫu; hoặc sinh báo cáo tự động từ artifact JSON.
- Phương án đã chọn: sinh báo cáo từ dữ liệu thật trong data/.
- Lý do: đảm bảo tính trung thực, dễ tái tạo và đúng với thực tế chạy pipeline.

## 6. Một lỗi hoặc blocker đã xử lý

- Triệu chứng/lỗi nguyên văn: Không có lỗi kỹ thuật nghiêm trọng trong quá trình tạo báo cáo; vấn đề chính là cần phải tránh ghi các số liệu thiếu căn cứ.
- Nguyên nhân gốc: Báo cáo mẫu dễ dẫn đến nội dung chung chung và không phản ánh artifact thật.
- Cách xử lý: Dùng các file metrics/quality/freshness hiện có làm input trung gian để tạo báo cáo có số liệu cụ thể.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index bằng cách fetch raw records, clean thành schema chuẩn, tạo embedding và lưu vào Chroma collection.
2. Evaluation set và ground-truth document IDs dùng để so sánh retrieved docs với expected docs và đánh giá quality của câu trả lời.
3. Quality checks đo completeness/validity/uniqueness; freshness monitoring đo độ mới của published dates và số row stale.
4. Cùng một test set được dùng cho baseline, corrupted và repaired để đảm bảo so sánh có ý nghĩa.
5. Repair được xem là thành công khi quality và các metric của repaired gần bằng baseline và tốt hơn corrupted.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 1.0000 | 0.6667 | 1.0000 | Corruption làm giảm đáng kể; repair phục hồi đầy đủ. |
| mean_token_f1 | 1.0000 | 0.5712 | 1.0000 | Dữ liệu lỗi làm giảm độ khớp token; repair phục hồi. |
| judge_accuracy | 1.0000 | 0.5556 | 1.0000 | Đánh giá của LLM suy giảm sau corruption. |
| mean_judge_score | 5.0000 | 3.2222 | 5.0000 | Điểm đánh giá giảm rõ rệt nhưng hồi phục về baseline. |
| Quality checks | PASS | FAIL | PASS | Corrupted fail vì summary completeness và duplicate row. |
| Freshness status | fresh | fresh | fresh | Freshness không phải nguyên nhân chính trong run này. |

### Kết luận từ số liệu

1. drop_latest và blank_summary → quality signal thay đổi → agent metric giảm.
2. Rebuild từ raw data → quality gate trở lại PASS → metrics phục hồi về baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Blank summary và duplicate row ảnh hưởng rõ nhất vì chúng làm quality gate fail và làm các câu trả lời kém chính xác hơn.

Kết quả nào khác với kỳ vọng ban đầu?

Mức suy giảm trong mean token F1 và judge accuracy lớn hơn kỳ vọng ban đầu, cho thấy các lỗi ngữ nghĩa như summary rỗng và nhiễu có tác động lớn đến retrieval/answer quality.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Dữ liệu lỗi có thể làm suy giảm RAG agent ngay cả khi index vẫn build được.
2. Observability giúp phát hiện sớm các vấn đề về completeness và uniqueness trước khi trả lời sai cho người dùng.
3. Repair từ nguồn raw là cách đáng tin cậy để khôi phục chất lượng nếu data source còn nguyên vẹn.

### Nếu có thêm thời gian

Tôi sẽ thử thêm các corruption scenarios khác như missing title hoặc malformed URL để đo phạm vi tác động của từng lỗi dữ liệu.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Báo cáo không chứa .env, API key, token hoặc secret.

**Họ và tên:** Nguyễn Hoàng Việt
**Ngày xác nhận:** 2026-08-06
