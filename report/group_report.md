# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 1 |
| Repository | C:\CodeLab\K3_Day10_2A202601940_NguyenHoangViet |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Hoàng Việt | 2A202601940 | Owner toàn bộ pipeline | Ingestion, cleaning, evaluation, observability, corruption/repair và report |

## 2. Tóm tắt kết quả

Nhóm 1 đã hoàn thành toàn bộ chuỗi baseline → corruption → repair cho bài lab data pipeline. Baseline tạo đầy đủ artifact raw, clean, embeddings, evaluation set, metrics, quality/freshness và báo cáo pha 1. Sau khi inject corruption, chất lượng dữ liệu giảm rõ rệt với 2 check fail và metrics agent suy giảm; repair từ raw data đã phục hồi lại đầy đủ các metric về baseline.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API và payload raw | Fetch, parse, lưu raw artifacts | data/raw/ | Nguyễn Hoàng Việt |
| Cleaning | Raw records | Standardize schema, tạo text_for_embedding, age_days | data/clean/ | Nguyễn Hoàng Việt |
| Embedding/index | Clean dataset | Build vector index và embedding manifest | data/embeddings/ | Nguyễn Hoàng Việt |
| Evaluation | Clean dataset và test set | Chạy retrieval/answer evaluation | data/results/*.json | Nguyễn Hoàng Việt |
| Observability | Clean, corrupted, repaired datasets | Quality checks và freshness | data/quality/ | Nguyễn Hoàng Việt |
| Corruption/repair | Baseline clean data và raw source | Inject lỗi và repair từ raw | data/results/corruption_log.json | Nguyễn Hoàng Việt |
| Orchestration | Settings và artifact | Chạy baseline và corruption flow | data/reports/*.md | Nguyễn Hoàng Việt |

## 4. Cách tái hiện kết quả

### Lệnh chạy

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Bằng chứng |
| --- | --- | --- |
| Baseline pipeline | Thành công | data/results/baseline_metrics.json và data/reports/phase1_report.md |
| Corruption flow | Thành công | data/results/corrupted_metrics.json, data/results/repaired_metrics.json và data/reports/corruption_report.md |

## 5. Ingestion, cleaning và data contract

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Số record nhận được | 24 |
| Schema clean | paper_id, title, summary, published, authors_joined, categories_joined, text_for_embedding, age_days |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Kết quả |
| --- | --- | --- |
| Loại bỏ record không có title/summary/text_for_embedding hợp lệ | Completeness | 0 record bị loại bỏ ở baseline; 3 summary missing ở corrupted |
| Tạo age_days từ published date | Validity | Baseline và repaired đều hợp lệ |
| Tạo document ID cố định từ paper_id | Uniqueness | Baseline/repaired pass, corrupted fail do duplicate |

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 18 |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Retrieval top_k | 4 |
| Test set dùng chung cho ba trạng thái | data/eval/test_set.json |

## 7. Kết quả baseline

| Artifact | Đường dẫn | Trạng thái |
| --- | --- | --- |
| Raw response/records | data/raw/ | Có |
| Cleaned dataset | data/clean/ | Có |
| Embedding manifest/index | data/embeddings/ | Có |
| Evaluation set | data/eval/ | Có |
| Baseline metrics | data/results/baseline_metrics.json | Có |
| Quality/freshness | data/quality/ | Có |
| Baseline report | data/reports/phase1_report.md | Có |

### Baseline metrics

| Metric | Giá trị |
| --- | ---: |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |

## 8. Data quality và freshness

| Check | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Quality overall | PASS | FAIL | PASS |
| Summary completeness | 0 missing | 3 missing | 0 missing |
| Duplicate rows | 0 | 1 | 0 |
| Freshness status | fresh | fresh | fresh |
| Stale rows | 0 | 1 | 0 |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- |
| drop_latest | Xóa 2 row mới nhất | 2 | Giảm số lượng record và làm mất coverage | Dùng lại raw data để tạo dataset clean mới |
| blank_summary | Làm rỗng summary 2 row | 2 | Giảm completeness và làm quality fail | Rebuild clean data từ raw records |
| summary_noise | Thêm nhiễu vào summary | 1 | Metric retrieval/answer giảm | Rebuild clean data từ raw records |
| truncate_title | Cắt ngắn title | 1 | Không làm fail quality nhưng làm giảm độ khớp | Rebuild clean data từ raw records |
| stale_date | Đặt published date cũ hơn ngưỡng | 1 | Tạo stale row | Rebuild clean data từ raw records |
| duplicate_row | Bổ sung duplicate | 1 | Tạo duplicate và fail uniqueness | Rebuild clean data từ raw records |

## 10. So sánh baseline, corrupted và repaired

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| retrieval_hit_rate | 1.0000 | 0.6667 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.5712 | 1.0000 |
| judge_accuracy | 1.0000 | 0.5556 | 1.0000 |
| mean_judge_score | 5 | 3.2222 | 5 |

### Kết luận có căn cứ

- Corruption làm giảm retrieval hit rate từ 1.0000 xuống 0.6667 và giảm mean token F1 từ 1.0000 xuống 0.5712, cho thấy dữ liệu lỗi làm suy giảm chất lượng trả lời của agent.
- Quality gate từ PASS chuyển sang FAIL ở trạng thái corrupted do summary completeness và duplicate row; repair từ raw data đưa lại quality về PASS và phục hồi metrics về mức baseline.
- Freshness không phải nguyên nhân chính trong run này vì cả baseline và repaired đều ở trạng thái fresh; tác động chính đến metrics đến từ corruption content và schema quality.

## 11. Kết luận cuối cùng

Nhóm 1 đã hoàn thành bài lab end-to-end, từ ingestion đến reporting. Báo cáo này được xây dựng từ các artifact thực tế trong data/ và cho thấy sai lệch dữ liệu có thể làm suy giảm hiệu quả retrieval/answer của RAG, trong khi repair từ nguồn raw có thể khôi phục lại kết quả gần như ban đầu.

