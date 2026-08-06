# Hướng dẫn chi tiết Day 10 — Data Pipeline & Data Observability

Tài liệu này dành cho người mới bắt đầu. Không cần hiểu sẵn Data Pipeline, RAG, Pandas, ChromaDB hay LangChain. Hãy làm đúng thứ tự, chạy kiểm tra sau mỗi bước và chỉ chuyển bước khi kết quả hiện tại đã đúng.

---

## 0. Luồng làm việc của bạn để tạo ra sản phẩm cuối

Đây là lộ trình bạn cần đi theo từ lúc mới mở project đến khi có bài hoàn chỉnh. Không nên mở một file bất kỳ rồi code ngay. Mỗi bước tạo đầu vào cho bước sau, vì vậy nếu bước trước sai thì lỗi sẽ lan xuống toàn bộ pipeline.

### 0.1. Sơ đồ các bước thực hiện

```text
BƯỚC 1 — Chuẩn bị môi trường
    ↓
BƯỚC 2 — Đọc cấu hình và hiểu các đường dẫn
    ↓
BƯỚC 3 — Lấy và parse dữ liệu Crossref
    ↓
BƯỚC 4 — Làm sạch dữ liệu
    ↓
BƯỚC 5 — Tạo bộ câu hỏi kiểm thử cố định
    ↓
BƯỚC 6 — Tạo embedding và ChromaDB baseline
    ↓
BƯỚC 7 — Hỏi thử và kiểm tra retrieval
    ↓
BƯỚC 8 — Đánh giá baseline
    ↓
BƯỚC 9 — Kiểm tra quality/freshness và tạo báo cáo baseline
    ↓
BƯỚC 10 — Ghép và chạy baseline end-to-end
    ↓
BƯỚC 11 — Cố tình làm hỏng dữ liệu
    ↓
BƯỚC 12 — Tạo index và đánh giá corrupted data
    ↓
BƯỚC 13 — Phục hồi lại từ raw data
    ↓
BƯỚC 14 — Đánh giá repaired data và so sánh ba trạng thái
    ↓
BƯỚC 15 — Kiểm tra artifact, hoàn thiện báo cáo và nộp bài
```

Sản phẩm cuối cùng không chỉ là source code. Bạn cần bàn giao cả:

```text
Code đã hoàn thiện
+ raw/clean/evaluation artifacts
+ ba Chroma indexes hoặc manifests
+ answers và metrics
+ quality/freshness reports
+ corruption log
+ comparison report
+ báo cáo nhóm và báo cáo cá nhân
```

### 0.2. Bước 1 — Chuẩn bị môi trường

**Bạn làm gì?**

1. Kích hoạt `.venv`.
2. Cài project và dependency.
3. Kiểm tra import các thư viện chính.
4. Kiểm tra `.env` tồn tại nhưng không công khai API key.

**Vì sao phải làm trước?**

Nếu môi trường chưa có `pandas`, `requests` hoặc `chromadb`, code đúng vẫn không chạy. Cần phân biệt lỗi setup với lỗi do mình viết code.

**File liên quan:**

```text
pyproject.toml
requirements.txt
.env.example
.env
```

**Đầu ra mong đợi:**

```text
Python 3.11–3.13
Môi trường ảo hoạt động
Import package thành công
```

**Chỉ chuyển bước khi:** lệnh kiểm tra in `Môi trường OK`.

### 0.3. Bước 2 — Đọc cấu hình và hiểu đường dẫn

**Bạn làm gì?**

1. Đọc `src/core/config.py`.
2. Xác định Crossref query, `max_results`, `top_k` và freshness threshold.
3. Xác định artifact của baseline, corrupted và repaired được lưu ở đâu.
4. Đọc các hàm có sẵn trong `src/core/utils.py`.

**Vì sao?**

Bạn phải dùng cùng data contract và đường dẫn với các module đã có. Nếu tự hard-code đường dẫn hoặc đổi tên cột, `index.py`, `metrics.py` và các pipeline sau sẽ không đọc được dữ liệu.

**File liên quan:**

```text
src/core/config.py
src/core/utils.py
```

**Đầu ra mong đợi:** bạn giải thích được `Settings`, `Paths` và biết không nên tự viết lại hàm đọc/ghi đã có.

### 0.4. Bước 3 — Lấy và parse dữ liệu Crossref

**Bạn làm gì?**

1. Hoàn thiện `parse_crossref_payload`.
2. Test parser bằng một payload giả, chưa cần Internet.
3. Hoàn thiện `load_raw_records`.
4. Hoàn thiện `fetch_source_records` có retry/backoff.
5. Gọi Crossref và lưu hai raw artifacts.

**Vì sao?**

Crossref JSON có nhiều object/list lồng nhau. Các bước phía sau cần một schema đơn giản và thống nhất là `PaperRecord`.

**File chính:**

```text
src/ingestion/crossref.py
```

**Đầu ra mong đợi:**

```text
data/raw/crossref_response.json
data/raw/crossref_records.json
```

**Chỉ chuyển bước khi:** đọc được ít nhất một `PaperRecord` có `paper_id`, title và published hợp lệ.

### 0.5. Bước 4 — Làm sạch dữ liệu

**Bạn làm gì?**

1. Chuẩn hóa title, summary, authors và categories.
2. Parse ngày xuất bản.
3. Tính `age_days`.
4. Loại record không hợp lệ và record trùng.
5. Tạo `authors_joined`, `categories_joined`, `summary_chars`.
6. Tạo `text_for_embedding`.
7. Lưu clean CSV và JSON.

**Vì sao?**

Raw data phù hợp để truy vết nhưng chưa phù hợp để embedding. Cleaning tạo bảng ổn định mà test set, ChromaDB và quality checks đều có thể sử dụng.

**File chính:**

```text
src/ingestion/cleaning.py
```

**Đầu ra mong đợi:**

```text
data/clean/papers_clean.csv
data/clean/papers_clean.json
```

**Chỉ chuyển bước khi:** DataFrame không rỗng, `paper_id` unique, ngày đọc được và `text_for_embedding` không rỗng.

### 0.6. Bước 5 — Tạo bộ câu hỏi kiểm thử

**Bạn làm gì?**

1. Chọn một số paper thật từ cleaned DataFrame.
2. Tạo câu hỏi về summary, authors, date và categories.
3. Dùng dữ liệu thật làm `ground_truth`.
4. Dùng `paper_id` thật làm `ground_truth_doc_ids`.
5. Lưu test set và giữ nguyên file này cho ba lần đánh giá.

**Vì sao?**

Muốn biết hệ thống tốt hay xấu phải có đề thi và đáp án chuẩn. Nếu đổi đề giữa baseline và corrupted thì metric không thể so sánh công bằng.

**File chính:**

```text
src/evaluation/testset.py
```

**Đầu ra mong đợi:**

```text
data/eval/test_set.json
```

**Chỉ chuyển bước khi:** mọi ground-truth ID đều tồn tại trong clean data.

### 0.7. Bước 6 — Tạo embedding và ChromaDB baseline

**Bạn làm gì?**

1. Đưa `text_for_embedding` vào MiniLM.
2. Tạo vector cho từng paper.
3. Lưu vector và metadata vào collection `papers-baseline`.
4. Ghi embedding manifest.

**Vì sao?**

Embedding giúp tìm tài liệu theo ý nghĩa thay vì chỉ so khớp từ khóa. ChromaDB là kho lưu vector và thực hiện semantic search.

**File đã có sẵn để sử dụng:**

```text
src/retrieval/embeddings.py
src/retrieval/index.py
```

**Đầu ra mong đợi:**

```text
data/embeddings/papers_embeddings.json
Chroma collection: papers-baseline
```

**Chỉ chuyển bước khi:** collection có document và manifest ghi đúng số document, model, path và collection name.

### 0.8. Bước 7 — Hỏi thử và kiểm tra retrieval

**Bạn làm gì?**

1. Thử semantic search bằng một chủ đề có trong corpus.
2. Thử exact lookup bằng `paper_id`.
3. Thử exact lookup bằng title.
4. Gọi `answer_question` với một câu trong test set.
5. Kiểm tra document ID và context được lấy ra.

**Vì sao?**

Nếu retrieval sai, evaluation phía sau cũng sai. Cần sửa clean/index contract trước khi chạy toàn bộ pipeline.

**File liên quan:**

```text
src/retrieval/index.py
src/retrieval/qa.py
src/retrieval/agent.py
```

**Đầu ra mong đợi:** semantic search và exact lookup đều trả document có nguồn; câu trả lời dựa trên metadata của document đó.

### 0.9. Bước 8 — Đánh giá baseline

**Bạn làm gì?**

1. Chạy từng câu trong test set qua `answer_question`.
2. Ghi answer, retrieved document IDs và contexts.
3. Tính retrieval hit, token F1 và judge score.
4. Đọc thử ít nhất một câu đúng và một câu sai nếu có.

**Vì sao?**

Baseline metrics là mốc tham chiếu. Sau này phải chứng minh corrupted giảm và repaired phục hồi so với mốc này.

**File đã có logic chính:**

```text
src/evaluation/metrics.py
```

**Đầu ra mong đợi:**

```text
data/results/baseline_answers.json
data/results/baseline_metrics.json
```

**Chỉ chuyển bước khi:** metrics được tạo từ answers thật, không phải giá trị hard-code.

### 0.10. Bước 9 — Kiểm tra chất lượng, freshness và tạo report

**Bạn làm gì?**

1. Kiểm tra row count, null, duplicate và các cột bắt buộc.
2. Đếm record stale theo `age_days`.
3. Ghi quality/freshness JSON.
4. Tổng hợp source, metrics và quality thành Markdown report.

**Vì sao?**

RAG metrics cho biết hệ thống trả lời ra sao; quality/freshness cho biết dữ liệu đầu vào khỏe hay có vấn đề. Cần cả hai để giải thích nguyên nhân.

**File chính:**

```text
src/observability/quality.py
src/observability/reporting.py
```

**Đầu ra mong đợi:**

```text
data/quality/
data/reports/phase1_report.md
```

### 0.11. Bước 10 — Ghép và chạy baseline end-to-end

**Bạn làm gì?**

Trong `phase1.py`, gọi lại các module đúng thứ tự:

```text
settings → raw → clean → index → test set → evaluate → quality → report
```

Sau đó chạy entrypoint baseline.

**File chính:**

```text
src/pipelines/phase1.py
script/run_phase1.py
```

**Vì sao?**

Chạy từng module chứng minh từng phần đúng. Chạy end-to-end chứng minh các phần kết nối với nhau đúng và người khác có thể tái hiện sản phẩm.

**Chỉ chuyển sang corruption khi:** script kết thúc thành công và toàn bộ baseline artifacts thực sự tồn tại, đọc được và khớp báo cáo.

### 0.12. Bước 11 — Cố tình làm hỏng dữ liệu

**Bạn làm gì?**

1. Copy cleaned DataFrame baseline.
2. Xóa một số record.
3. Làm rỗng hoặc thêm noise vào summary.
4. Cắt title, làm ngày cũ hoặc thêm duplicate.
5. Tính lại các derived columns.
6. Ghi chi tiết từng thay đổi vào corruption log.

**Vì sao?**

Đây là fault injection: chủ động tạo lỗi có thể kiểm soát để kiểm tra hệ thống có phát hiện được không và RAG bị ảnh hưởng thế nào.

**File chính:**

```text
src/ingestion/corruption.py
```

**Đầu ra mong đợi:** corrupted data khác baseline đúng như log, trong khi baseline và raw data không bị thay đổi.

### 0.13. Bước 12 — Đánh giá corrupted data

**Bạn làm gì?**

1. Lưu corrupted CSV/JSON.
2. Tạo collection `papers-corrupted` riêng.
3. Dùng lại đúng test set baseline.
4. Chạy evaluation và quality/freshness.
5. Tìm ít nhất một trường hợp dữ liệu lỗi làm signal hoặc metric thay đổi.

**Vì sao?**

Bước này tạo bằng chứng liên kết lỗi dữ liệu với tác động downstream:

```text
corruption → quality signal → retrieval/answer metric
```

**Đầu ra mong đợi:** corrupted index, answers, metrics và quality report; không artifact baseline nào bị ghi đè.

### 0.14. Bước 13 — Phục hồi từ raw data

**Bạn làm gì?**

1. Đọc lại `crossref_records.json`.
2. Chạy lại cùng hàm cleaning.
3. Lưu repaired CSV/JSON.
4. Tạo collection `papers-repaired`.

**Vì sao?**

Repair đúng là tái tạo sản phẩm từ nguồn đáng tin cậy. Không copy baseline và không sửa tay corrupted metrics, vì những cách đó không chứng minh pipeline có khả năng phục hồi.

**Đầu ra mong đợi:** repaired data có lineage quay về đúng raw snapshot ban đầu.

### 0.15. Bước 14 — Đánh giá repaired và so sánh

**Bạn làm gì?**

1. Dùng lại test set cũ để đánh giá repaired index.
2. Chạy repaired quality/freshness.
3. So sánh baseline, corrupted và repaired.
4. Tính mức giảm do corruption và mức phục hồi sau repair.
5. Ghi rõ metric nào chưa phục hồi hoàn toàn.

**File chính:**

```text
src/pipelines/corruption_flow.py
src/observability/reporting.py
```

**Đầu ra mong đợi:**

```text
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/corruption_log.json
data/reports/corruption_report.md
```

### 0.16. Bước 15 — Kiểm tra và hoàn thiện bài nộp

**Bạn làm gì?**

1. Chạy lại hai entrypoint trên phiên bản cuối.
2. Đối chiếu toàn bộ metrics trong report với JSON thật.
3. Kiểm tra không có API key, token hoặc `.env` trong Git.
4. Đối chiếu `Rubric.md`.
5. Điền báo cáo nhóm bằng kết quả chung.
6. Điền báo cáo cá nhân đúng phần việc mình thực hiện.

**File báo cáo:**

```text
report/group_report.md
report/individual_report.md
```

**Sản phẩm cuối cùng đạt yêu cầu khi:** người khác có thể cài project, chạy baseline, chạy corruption flow và đối chiếu được mọi kết luận bằng artifact thật.

### 0.17. Quy tắc dừng sau mỗi bước

Sau mỗi bước, hãy tự hỏi bốn câu:

1. Input của bước này là gì?
2. Output thật đã được tạo ở đâu?
3. Tôi đã chạy lệnh nào để kiểm tra output?
4. Nếu output sai, tôi có biết phải quay lại file nào không?

Nếu chưa trả lời được một trong bốn câu, chưa nên chuyển sang bước tiếp theo.

---

## 1. Dự án này làm gì?

Dự án lấy metadata bài báo khoa học từ Crossref, làm sạch dữ liệu, đưa dữ liệu vào một hệ thống tìm kiếm ngữ nghĩa và dùng dữ liệu đó để trả lời câu hỏi.

Sau khi xây dựng trạng thái hoạt động bình thường, dự án cố tình làm hỏng dữ liệu để đo xem khả năng tìm kiếm và trả lời giảm như thế nào. Cuối cùng, dữ liệu được phục hồi từ bản raw và hệ thống được đánh giá lại.

Luồng tổng thể:

```text
Crossref API
    → raw response
    → list[PaperRecord]
    → cleaned DataFrame
    → embedding + ChromaDB
    → hỏi đáp và evaluation
    → quality/freshness report
    → làm hỏng dữ liệu
    → đánh giá lại
    → phục hồi từ raw data
    → so sánh baseline/corrupted/repaired
```

Ba trạng thái cần phân biệt:

- **Baseline:** dữ liệu sạch ban đầu.
- **Corrupted:** dữ liệu đã bị làm hỏng có chủ đích.
- **Repaired:** dữ liệu được dựng lại từ raw data đáng tin cậy.

Mục tiêu quan trọng nhất:

> Chứng minh bằng artifact và metric rằng chất lượng dữ liệu ảnh hưởng đến chất lượng của hệ thống RAG, đồng thời chứng minh pipeline có thể phát hiện và phục hồi sau lỗi dữ liệu.

---

## 2. Những khái niệm cần biết

### 2.1. Data pipeline

Data pipeline là dây chuyền đưa dữ liệu từ nguồn tới nơi sử dụng:

```text
Nguồn dữ liệu → lấy dữ liệu → làm sạch → lưu trữ → sử dụng → giám sát
```

Trong bài này:

- **Extract:** lấy dữ liệu từ Crossref.
- **Transform:** parse, chuẩn hóa, loại dữ liệu xấu và tạo `text_for_embedding`.
- **Load:** lưu file và nạp dữ liệu vào ChromaDB.

### 2.2. RAG

RAG là viết tắt của Retrieval-Augmented Generation. Trước khi trả lời, hệ thống tìm tài liệu liên quan trong một kho kiến thức rồi dùng tài liệu đó làm căn cứ.

```text
Câu hỏi
    → tìm tài liệu liên quan
    → lấy nội dung tài liệu
    → tạo câu trả lời
```

### 2.3. Embedding

Embedding biến văn bản thành vector số:

```text
"Retrieval augmented generation"
    → [0.12, -0.45, 0.31, ...]
```

Các văn bản gần nhau về ý nghĩa thường có vector gần nhau. Project dùng `sentence-transformers/all-MiniLM-L6-v2`.

### 2.4. ChromaDB

ChromaDB là vector database. Nó lưu vector, nội dung và metadata, sau đó tìm những document gần câu hỏi nhất.

Project sử dụng ba collection riêng:

```text
papers-baseline
papers-corrupted
papers-repaired
```

### 2.5. Data quality và freshness

Data quality trả lời các câu hỏi:

- Có record nào thiếu ID không?
- ID có bị trùng không?
- Title hoặc summary có rỗng không?
- Dữ liệu có đúng schema không?

Freshness trả lời:

- Dữ liệu mới nhất là ngày nào?
- Có bao nhiêu record quá cũ?
- Dataset có đạt ngưỡng độ mới không?

### 2.6. Evaluation

Evaluation dùng một bộ câu hỏi có đáp án chuẩn để chấm hệ thống.

Một test sample có dạng:

```json
{
  "id": "summary-001",
  "question_type": "summary",
  "question": "What is 'Example Paper' about?",
  "ground_truth": "This paper studies RAG.",
  "ground_truth_doc_ids": ["10.1234/example"]
}
```

Các metric chính:

- `retrieval_hit_rate`: tỷ lệ tìm thấy đúng document.
- `mean_token_f1`: mức độ trùng khớp giữa câu trả lời và đáp án chuẩn.
- `judge_accuracy`: tỷ lệ câu trả lời được judge đánh giá đúng.
- `mean_judge_score`: điểm judge trung bình.

### 2.7. Crossref

Crossref là tổ chức cung cấp metadata của các công trình học thuật như bài báo, sách và kỷ yếu hội nghị. Metadata là dữ liệu mô tả tài liệu, chẳng hạn DOI, tiêu đề, tác giả, abstract, chủ đề, ngày xuất bản và URL.

Crossref thường không cung cấp toàn bộ nội dung bài báo. Trong project này, Crossref đóng vai trò **nguồn dữ liệu đầu vào**:

```text
Crossref API → raw JSON → PaperRecord → clean data → RAG
```

Endpoint được sử dụng:

```text
https://api.crossref.org/works
```

### 2.8. DOI

DOI là viết tắt của Digital Object Identifier, tức mã định danh số ổn định của một công trình học thuật.

Ví dụ:

```text
10.1234/example-paper
```

Có thể truy cập DOI qua:

```text
https://doi.org/10.1234/example-paper
```

Trong project, DOI được ưu tiên dùng làm `paper_id`. Nhờ vậy một bài báo có cùng ID từ raw data, cleaned data, ChromaDB đến evaluation set.

### 2.9. API, HTTP và JSON

API là giao diện để hai phần mềm trao đổi dữ liệu. Project gửi một HTTP GET request tới Crossref và nhận response ở dạng JSON.

- **HTTP GET:** yêu cầu đọc dữ liệu từ server.
- **Request:** yêu cầu do project gửi đi.
- **Response:** kết quả Crossref trả về.
- **Status code:** mã cho biết request thành công hay lỗi, ví dụ `200`, `429`, `503`.
- **JSON:** định dạng văn bản gồm object, list, key và value.

Ví dụ JSON:

```json
{
  "DOI": "10.1234/example",
  "title": ["Example Paper"]
}
```

Khi gọi `response.json()`, thư viện `requests` chuyển JSON thành dictionary/list của Python.

### 2.10. Schema và data contract

Schema mô tả dữ liệu có những trường nào và kiểu dữ liệu của chúng. Ví dụ `PaperRecord` yêu cầu `paper_id` là chuỗi và `authors` là danh sách chuỗi.

Data contract rộng hơn schema. Nó còn quy định:

- Trường nào bắt buộc.
- Cách xử lý dữ liệu thiếu.
- Cách tạo ID.
- Module nào tạo và module nào sử dụng dữ liệu.
- Artifact được lưu ở đường dẫn nào.

### 2.11. Artifact và raw snapshot

Artifact là file hoặc output được pipeline tạo ra, chẳng hạn cleaned CSV, metrics JSON hoặc Markdown report.

Raw snapshot là bản sao dữ liệu nguồn được lưu tại một thời điểm cụ thể. Project lưu raw snapshot để:

- Truy vết dữ liệu gốc.
- Chạy lại pipeline mà không gọi API.
- Repair từ đúng nguồn đã dùng cho baseline.
- Tránh kết quả Crossref thay đổi giữa các lần đánh giá.

### 2.12. Pandas và DataFrame

Pandas là thư viện Python dùng để xử lý dữ liệu dạng bảng. DataFrame là cấu trúc bảng của Pandas:

| paper_id | title | summary |
|---|---|---|
| `10.1/a` | Paper A | Summary A |
| `10.1/b` | Paper B | Summary B |

- Mỗi hàng là một record.
- Mỗi cột là một thuộc tính.
- `df["title"]` lấy một cột.
- `df.head()` xem các hàng đầu.
- `df.drop_duplicates(...)` loại hàng trùng.

### 2.13. Baseline, corruption và repair

- **Baseline:** kết quả tham chiếu trên dữ liệu sạch.
- **Corruption:** lỗi dữ liệu được tạo có kiểm soát để đo tác động.
- **Repair:** dựng lại dữ liệu từ raw/source đáng tin cậy.

Ba trạng thái phải dùng cùng test set và cấu hình đánh giá để phép so sánh có ý nghĩa.

---

## 3. Bản đồ source code

```text
src/
├── core/
│   ├── config.py       # cấu hình và đường dẫn
│   └── utils.py        # hàm đọc/ghi và xử lý chuỗi
├── ingestion/
│   ├── crossref.py     # lấy và parse dữ liệu Crossref
│   ├── cleaning.py     # làm sạch dữ liệu
│   └── corruption.py   # cố tình làm hỏng dữ liệu
├── retrieval/
│   ├── embeddings.py   # biến text thành vector
│   ├── index.py        # lưu/tìm trong ChromaDB
│   ├── qa.py           # tạo câu trả lời từ kết quả tìm kiếm
│   ├── llm.py          # chọn LLM provider
│   └── agent.py        # agent có search/lookup tools
├── evaluation/
│   ├── testset.py      # tạo đề kiểm thử
│   └── metrics.py      # chấm retrieval và câu trả lời
├── observability/
│   ├── quality.py      # quality và freshness checks
│   └── reporting.py    # xuất Markdown report
└── pipelines/
    ├── phase1.py       # điều phối baseline
    └── corruption_flow.py # điều phối corrupt/repair/compare
```

Hai lệnh chạy chính:

```text
script/run_phase1.py
script/run_corruption_flow.py
```

---

## 4. Nguyên tắc bắt buộc

1. Chỉ chạy corruption sau khi baseline đã tạo đủ artifact.
2. Dùng cùng test set, ground truth, evaluator và `top_k` cho cả ba trạng thái.
3. Không ghi đè collection hoặc artifact baseline bằng corrupted/repaired.
4. Repair phải chạy lại từ raw data; không sửa tay answers hay metrics.
5. Không hard-code API key hoặc đường dẫn.
6. Không commit `.env`.
7. Không kết luận “thành công” nếu chưa có artifact và metric thực tế.

---

## 5. Bước 1 — Chuẩn bị môi trường

Trạng thái đã kiểm tra trong project:

- Python `3.12.10`: đạt yêu cầu.
- Đã có `.venv`.
- Đã có `.env`.
- Chưa cài `uv`, nhưng có thể dùng `pip`.
- `.venv` hiện chưa có `pandas`, vì vậy cần cài dependency.

### 5.1. Kích hoạt môi trường ảo

Tại thư mục gốc project, chạy:

```powershell
# Kích hoạt môi trường Python riêng của project trong PowerShell.
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn script:

```powershell
# Chỉ cho phép chạy script trong cửa sổ PowerShell hiện tại.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Kích hoạt lại môi trường ảo sau khi đã cấp quyền tạm thời.
.\.venv\Scripts\Activate.ps1
```

Kiểm tra Python đang sử dụng:

```powershell
# In đường dẫn Python để xác nhận terminal đang dùng Python trong `.venv`.
python -c "import sys; print(sys.executable)"
```

Đường dẫn phải chứa:

```text
.venv\Scripts\python.exe
```

### 5.2. Cài project và dependency

```powershell
# Cài project cùng toàn bộ dependency ở chế độ editable.
python -m pip install -e .
```

Ý nghĩa:

- `python`: Python của `.venv`.
- `-m pip`: chạy trình quản lý package pip.
- `install`: cài package.
- `-e`: editable mode; sửa source không cần cài lại.
- `.`: project trong thư mục hiện tại.

### 5.3. Kiểm tra

```powershell
# Import các package quan trọng; nếu không có exception thì môi trường đã sẵn sàng.
python -c "import pandas, requests, chromadb; import core, ingestion, retrieval; print('Môi trường OK')"
```

Kết quả đúng:

```text
Môi trường OK
```

Không chuyển sang bước 2 nếu import còn lỗi.

---

## 6. Bước 2 — Hiểu cấu hình trước khi code

Đọc `src/core/config.py`.

### 6.1. `Paths`

`Paths` chứa tất cả đường dẫn artifact. Ví dụ:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
settings.paths.raw_api_response
settings.paths.raw_records_json
settings.paths.clean_csv
settings.paths.baseline_metrics
```

Luôn dùng đường dẫn từ `settings.paths`, không tự viết chuỗi đường dẫn trong module.

### 6.2. `Settings`

`Settings` chứa:

- LLM provider/model.
- Embedding model.
- Tên collection.
- Crossref query/filter.
- Số record tối đa.
- `top_k`.
- Ngưỡng freshness.
- Các cờ refresh.

Tạo settings bằng:

```python
# Nạp hàm tạo đối tượng cấu hình của project.
from core.config import load_settings

# Đọc `.env`, tạo các đường dẫn và trả về Settings.
settings = load_settings()
```

### 6.3. Các utility có sẵn

Trong `src/core/utils.py`:

```python
# Các utility có sẵn; hãy gọi lại thay vì tự viết logic đọc/ghi tương tự.
normalize_whitespace(text)  # chuẩn hóa khoảng trắng
write_json(path, payload)   # ghi JSON
read_json(path)             # đọc JSON
write_csv(df, path)         # ghi DataFrame thành CSV
write_text(path, text)      # ghi text/Markdown
now_utc()                   # thời gian UTC hiện tại
first_sentence(text)        # lấy câu đầu tiên
compact_join(items)         # nối các chuỗi không rỗng
```

Tái sử dụng các hàm này thay vì tự viết lại.

---

## 7. Bước 3 — Hoàn thiện `src/ingestion/crossref.py`

Đây là file đầu tiên phải code.

### Khái niệm cần biết: ingestion

Ingestion là quá trình đưa dữ liệu từ nguồn bên ngoài vào hệ thống nội bộ. Trong bước này, ingestion bao gồm gọi Crossref, lưu response gốc và chuyển từng item thành schema mà project hiểu được.

### 7.1. `PaperRecord` là gì?

`PaperRecord` là schema chuẩn của một bài báo sau khi parse từ JSON Crossref:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str
```

Crossref JSON có nhiều object/list lồng nhau. `PaperRecord` biến chúng thành một cấu trúc mà các module phía sau hiểu thống nhất.

`@dataclass` là tiện ích của Python tự tạo constructor, cách hiển thị và phép so sánh cho class chứa dữ liệu. Nhờ đó có thể tạo record bằng `PaperRecord(...)` mà không phải tự viết `__init__` dài.

`frozen=True` có nghĩa là không được gán lại thuộc tính sau khi object được tạo. Mục đích là xem raw record như dữ liệu chỉ đọc và tránh thay đổi ngoài ý muốn.

Type hint như `authors: list[str]` cho biết `authors` phải là danh sách chuỗi. Type hint giúp người đọc và công cụ kiểm tra hiểu data contract; Python không tự động bảo đảm dữ liệu luôn đúng kiểu khi chương trình chạy.

### 7.2. Thêm import

Bạn sẽ cần những import tương tự:

```python
# Import những thư viện cần cho parser, HTTP request và đọc/ghi artifact.
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json
```

### 7.3. Helper lấy text đầu tiên

Crossref thường trả title dưới dạng list:

```json
"title": ["Example Paper"]
```

Helper:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
def _first_text(value) -> str:
    # Crossref thường chứa title trong một list; lấy phần tử đầu nếu có.
    if isinstance(value, list) and value:
        return normalize_whitespace(str(value[0]))
    # Một số payload có thể cung cấp trực tiếp một chuỗi.
    if isinstance(value, str):
        return normalize_whitespace(value)
    # Dữ liệu thiếu hoặc sai kiểu được biểu diễn bằng chuỗi rỗng.
    return ""
```

Giải thích:

- `isinstance(value, list)`: kiểm tra value là danh sách.
- `and value`: danh sách không rỗng.
- `value[0]`: phần tử đầu tiên.
- `str(...)`: chuyển về chuỗi.
- `normalize_whitespace`: bỏ khoảng trắng thừa.

### 7.4. Helper bỏ XML/JATS trong abstract

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
def _strip_markup(value: str) -> str:
    # Thay các thẻ XML/JATS như <jats:p> bằng khoảng trắng.
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    # Thu gọn các khoảng trắng phát sinh sau khi bỏ thẻ.
    return normalize_whitespace(without_tags)
```

`re.sub` thay những phần giống `<jats:p>` hoặc `</jats:p>` bằng khoảng trắng.

### 7.5. Helper lấy tác giả

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
def _extract_authors(item: dict) -> list[str]:
    # Tạo danh sách để chứa tên tác giả đã chuẩn hóa.
    authors: list[str] = []
    # `.get(..., [])` giúp payload thiếu author không gây KeyError.
    for author in item.get("author", []):
        given = normalize_whitespace(str(author.get("given", "")))
        family = normalize_whitespace(str(author.get("family", "")))
        # Ghép tên và họ, sau đó loại khoảng trắng thừa.
        full_name = normalize_whitespace(f"{given} {family}")
        if full_name:
            authors.append(full_name)
    return authors
```

`item.get("author", [])` trả danh sách rỗng nếu không có trường author, tránh `KeyError`.

### 7.6. Helper lấy ngày

Crossref lưu ngày như:

```json
"date-parts": [[2025, 3, 10]]
```

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
def _extract_date(value) -> str:
    try:
        # Crossref lưu ngày trong phần tử đầu của `date-parts`.
        parts = value.get("date-parts", [[]])[0]
        if not parts:
            return ""
        year = int(parts[0])
        # Nếu thiếu tháng/ngày, dùng ngày đầu năm hoặc đầu tháng.
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        # Trả ngày theo chuẩn YYYY-MM-DD.
        return date(year, month, day).isoformat()
    except (TypeError, ValueError, IndexError, AttributeError):
        # Payload ngày lỗi không được làm dừng toàn bộ parser.
        return ""
```

Nếu chỉ có năm, code dùng tháng 1 ngày 1. Nếu dữ liệu lỗi, helper trả chuỗi rỗng thay vì làm crash toàn pipeline.

### 7.7. `parse_crossref_payload`

Nhiệm vụ:

```text
Crossref JSON → list[PaperRecord]
```

**Parse** nghĩa là đọc dữ liệu ở một cấu trúc đầu vào và chuyển sang cấu trúc có ý nghĩa với chương trình. Parser ở đây không gọi API; nó chỉ nhận một dictionary đã có và chuyển `message.items` thành các `PaperRecord`.

Khung logic:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    # Đi tới danh sách bài báo; dùng mặc định rỗng nếu payload thiếu trường.
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        # DOI được chuẩn hóa thành chữ thường để dùng làm paper_id ổn định.
        doi = normalize_whitespace(str(item.get("DOI", ""))).lower()
        title = _first_text(item.get("title"))

        # Bỏ record không đủ danh tính tối thiểu.
        if not doi or not title:
            continue

        # Chuyển các cấu trúc Crossref thành kiểu dữ liệu đơn giản.
        summary = _strip_markup(str(item.get("abstract", "")))
        authors = _extract_authors(item)
        categories = [
            normalize_whitespace(str(value))
            for value in item.get("subject", [])
            if normalize_whitespace(str(value))
        ]

        # Ưu tiên ngày bản in, rồi bản online, cuối cùng là ngày published chung.
        published = (
            _extract_date(item.get("published-print"))
            or _extract_date(item.get("published-online"))
            or _extract_date(item.get("published"))
        )
        updated = _extract_date(item.get("indexed"))
        abs_url = normalize_whitespace(str(item.get("URL", "")))

        # Tìm đường dẫn có MIME type PDF trong danh sách link.
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = normalize_whitespace(str(link.get("URL", "")))
                break

        # Tạo một PaperRecord chuẩn cho module cleaning sử dụng.
        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment="",
            )
        )

    # Trả toàn bộ record hợp lệ đã parse.
    return records
```

### 7.8. Kiểm tra parser không cần Internet

```powershell
# Mở Python tương tác để thử parser với payload giả.
python
```

Trong Python shell:

```python
# Import đúng hàm đang cần kiểm tra.
from ingestion.crossref import parse_crossref_payload

# Tạo một response Crossref tối giản, không cần gọi Internet.
payload = {
    "message": {
        "items": [
            {
                "DOI": "10.1234/example",
                "title": ["Example Paper"],
                "abstract": "<jats:p>This paper discusses RAG.</jats:p>",
                "author": [{"given": "Hoang", "family": "Nguyen"}],
                "subject": ["Artificial Intelligence"],
                "published": {"date-parts": [[2025, 3, 10]]},
                "URL": "https://doi.org/10.1234/example",
                "link": [
                    {
                        "URL": "https://example.com/paper.pdf",
                        "content-type": "application/pdf"
                    }
                ]
            }
        ]
    }
}

# Parse payload rồi quan sát từng trường quan trọng.
records = parse_crossref_payload(payload)
print(records[0])
print(records[0].paper_id)
print(records[0].authors)
print(records[0].published)
```

Kỳ vọng:

```text
10.1234/example
['Hoang Nguyen']
2025-03-10
```

### 7.9. `load_raw_records`

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
def load_raw_records(path: Path) -> list[PaperRecord]:
    # Đọc nội dung JSON snapshot từ ổ đĩa.
    payload = read_json(path)
    # Snapshot đúng phải là một danh sách các dictionary.
    if not isinstance(payload, list):
        raise ValueError("Raw records JSON must contain a list.")
    # `**item` ánh xạ các key trong dictionary vào constructor PaperRecord.
    return [PaperRecord(**item) for item in payload]
```

`**item` truyền từng key trong dictionary thành tham số của `PaperRecord`.

### 7.10. `fetch_source_records`

Nhiệm vụ:

1. Gọi Crossref API.
2. Retry lỗi tạm thời.
3. Lưu raw response.
4. Parse thành `PaperRecord`.
5. Lưu parsed records.

**Retry** là thử gửi request lại sau lỗi tạm thời. **Backoff** là tăng thời gian chờ giữa các lần thử. Ví dụ `2 ** attempt` tạo thời gian chờ 1 giây, 2 giây rồi 4 giây. Cách này giảm áp lực lên API khi server đang quá tải hoặc giới hạn tần suất gọi.

Các status thường gặp:

- `200`: request thành công.
- `429`: gọi quá nhiều request trong một khoảng thời gian.
- `500`: lỗi nội bộ server.
- `503`: dịch vụ tạm thời không sẵn sàng.
- `response.raise_for_status()`: ném exception nếu response là lỗi HTTP.

Khung:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    # Endpoint tra cứu danh sách scholarly works của Crossref.
    url = "https://api.crossref.org/works"
    # Dùng query/filter/giới hạn đã cấu hình tập trung trong Settings.
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    # User-Agent giúp nguồn API nhận diện ứng dụng gọi dữ liệu.
    headers = {"User-Agent": "data-pipeline-lab/1.0"}
    # Đây là các HTTP status thường có thể thử lại.
    retry_statuses = {429, 500, 502, 503, 504}

    response = None
    for attempt in range(3):
        # Gửi GET request và giới hạn thời gian chờ ở 30 giây.
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code not in retry_statuses:
            response.raise_for_status()
            break
        if attempt < 2:
            # Exponential backoff: chờ 1 giây rồi 2 giây.
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError("Crossref request failed after retries.")

    # Lưu response nguyên bản trước khi parse để đảm bảo lineage.
    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    # Chuyển payload thành schema PaperRecord của project.
    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref returned no usable records.")

    # `asdict` chuyển dataclass thành dictionary có thể ghi JSON.
    write_json(
        settings.paths.raw_records_json,
        [asdict(record) for record in records],
    )
    return records
```

Kiểm tra:

```powershell
# Gọi Crossref thật, in số record và record đầu để kiểm tra ingestion.
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print('Records:', len(r)); print(r[0])"
```

Artifact cần có:

```text
data/raw/crossref_response.json
data/raw/crossref_records.json
```

---

## 8. Bước 4 — Hoàn thiện `src/ingestion/cleaning.py`

Đầu vào:

```text
list[PaperRecord]
```

Đầu ra:

```text
Pandas DataFrame sạch
```

### Khái niệm cần biết: cleaning, normalization và deduplication

- **Cleaning:** phát hiện, sửa hoặc loại dữ liệu không phù hợp.
- **Normalization:** đưa nhiều cách biểu diễn về một dạng thống nhất, ví dụ thu gọn khoảng trắng và chuẩn hóa ngày thành `YYYY-MM-DD`.
- **Deduplication:** loại các record trùng danh tính, trong bài này chủ yếu dựa trên `paper_id`.
- **Derived column:** cột được tính từ cột khác, ví dụ `age_days` hoặc `summary_chars`.
- **UTC:** múi giờ chuẩn dùng để tránh tính ngày khác nhau giữa các máy.
- **NaT:** “Not a Time”, giá trị Pandas dùng khi ngày không hợp lệ hoặc bị thiếu.

### 8.1. Các cột cần tạo

```text
paper_id
title
summary
authors
categories
primary_category
published
updated
abs_url
pdf_url
comment
authors_joined
categories_joined
summary_chars
age_days
text_for_embedding
```

### 8.2. Logic

1. Chuẩn hóa title và summary.
2. Chuẩn hóa authors/categories.
3. Parse ngày published.
4. Tính `age_days`.
5. Tạo các cột helper.
6. Bỏ record thiếu ID/title.
7. Deduplicate theo `paper_id`.
8. Sort và reset index.

Khung tham khảo:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
from core.utils import normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []

    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(x) for x in record.authors if normalize_whitespace(x)]
        categories = [normalize_whitespace(x) for x in record.categories if normalize_whitespace(x)]

        if not record.paper_id or not title:
            continue

        published_dt = pd.to_datetime(record.published, errors="coerce", utc=True)
        if pd.isna(published_dt):
            continue

        run_timestamp = pd.Timestamp(run_date)
        if run_timestamp.tzinfo is None:
            run_timestamp = run_timestamp.tz_localize("UTC")
        else:
            run_timestamp = run_timestamp.tz_convert("UTC")

        published = published_dt.date().isoformat()
        age_days = max(0, (run_timestamp - published_dt).days)
        authors_joined = ", ".join(dict.fromkeys(authors))
        categories_joined = ", ".join(dict.fromkeys(categories))

        text_for_embedding = (
            f"Title: {title}\n"
            f"Summary: {summary}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {published}"
        )

        rows.append(
            {
                "paper_id": record.paper_id.strip().lower(),
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(record.primary_category),
                "published": published,
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No valid records remained after cleaning.")

    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(["published", "paper_id"], ascending=[False, True])
    return df.reset_index(drop=True)
```

Kiểm tra:

```powershell
# Chú thích: chạy lệnh này trong PowerShell tại thư mục gốc của project và kiểm tra output trước khi chuyển bước.
python -c "from core.config import load_settings; from core.utils import now_utc; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); r=load_raw_records(s.paths.raw_records_json); df=build_clean_dataframe(r, now_utc()); print(df.shape); print(df.columns.tolist()); print(df[['paper_id','title','age_days']].head())"
```

Điều kiện hoàn thành:

- DataFrame không rỗng.
- `paper_id` không trùng.
- `text_for_embedding` không rỗng.
- Có `age_days`.

---

## 9. Bước 5 — Hoàn thiện `src/evaluation/testset.py`

Test set là đề thi cố định của hệ thống.

### Khái niệm cần biết: test set và ground truth

- **Test set:** tập câu hỏi dùng để đánh giá hệ thống.
- **Ground truth:** đáp án đúng được dùng làm chuẩn so sánh.
- **Ground-truth document ID:** ID của tài liệu chứa bằng chứng đúng.
- **Question type:** nhóm câu hỏi, ví dụ summary, authors, date hoặc categories.

Test set phải được “đóng băng” sau khi tạo baseline. Nếu dùng đề khác cho corrupted hoặc repaired, thay đổi metric có thể đến từ đề thi chứ không phải chất lượng dữ liệu.

### 9.1. Tại sao câu hỏi phải theo mẫu tiếng Anh?

`src/retrieval/qa.py` hiện nhận diện câu hỏi bằng các cụm:

```text
who authored
when was
publication date
what categories
```

Nó cũng tìm exact title nằm trong dấu nháy đơn `'...'`.

Nên tạo câu hỏi:

```text
What is 'TITLE' about?
Who authored 'TITLE'?
When was 'TITLE' published?
What categories are associated with 'TITLE'?
```

### 9.2. Khung triển khai

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    required = {
        "paper_id", "title", "summary", "authors_joined",
        "categories_joined", "published"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing test-set columns: {sorted(missing)}")

    samples: list[dict[str, Any]] = []
    selected = df.head(min(6, len(df)))

    for row_index, row in selected.iterrows():
        paper_id = str(row["paper_id"])
        title = str(row["title"])

        question_specs = [
            ("summary", f"What is '{title}' about?", first_sentence(str(row["summary"]))),
            ("authors", f"Who authored '{title}'?", str(row["authors_joined"])),
            ("date", f"When was '{title}' published?", str(row["published"])),
            ("categories", f"What categories are associated with '{title}'?", str(row["categories_joined"])),
        ]

        for question_type, question, ground_truth in question_specs:
            if not ground_truth:
                continue
            samples.append(
                {
                    "id": f"{question_type}-{row_index + 1:03d}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    if not samples:
        raise ValueError("Could not build any evaluation samples.")

    write_json(output_path, samples)
    return samples
```

Điều kiện hoàn thành:

- File `data/eval/test_set.json` tồn tại.
- Mỗi `ground_truth_doc_ids` là ID thật trong clean data.
- Test set không được đổi giữa baseline/corrupted/repaired.

---

## 10. Bước 6 — Hiểu phần retrieval đã có sẵn

### Khái niệm cần biết: retrieval và `top_k`

Retrieval là bước tìm tài liệu liên quan tới câu hỏi. `top_k` là số tài liệu tốt nhất được lấy ra. Với `top_k=4`, hệ thống trả tối đa bốn document có độ tương đồng cao nhất.

`top_k` quá nhỏ có thể bỏ sót tài liệu đúng. `top_k` quá lớn có thể đưa thêm context không liên quan. Khi so sánh ba trạng thái, phải giữ nguyên `top_k`.

**Semantic search** tìm theo ý nghĩa nhờ embedding. **Exact lookup** chỉ thành công khi `paper_id` hoặc title khớp chính xác.

### 10.1. `embeddings.py`

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
MiniLMEmbeddings.embed_documents(texts)
MiniLMEmbeddings.embed_query(text)
```

Hai hàm biến document và query thành vector.

### 10.2. `index.py`

Tạo baseline index:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
index = LocalEmbeddingIndex.build(
    df,
    settings,
    settings.paths.embeddings_json,
)
```

`LocalEmbeddingIndex.build` cần các cột:

```text
paper_id, title, text_for_embedding, published,
authors_joined, categories_joined, summary, abs_url, pdf_url
```

Tìm kiếm:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
results = index.search("retrieval augmented generation", top_k=4)
```

Exact lookup:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
record = index.lookup("10.1234/example")
record = index.lookup("Exact Paper Title")
```

### 10.3. `qa.py`

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
result = answer_question(question, settings, index)
```

Kết quả chứa:

```text
answer
retrieved_doc_ids
retrieved_contexts
retrieved_titles
```

---

## 11. Bước 7 — Hoàn thiện `src/observability/quality.py`

### Khái niệm cần biết: observability và quality gate

Data observability là khả năng quan sát sức khỏe dữ liệu thông qua metric, check, log và report. Quality gate là điều kiện dữ liệu phải vượt qua trước khi được xem là đủ tốt cho bước tiếp theo.

Ví dụ: nếu `paper_id` bị trùng hoặc `text_for_embedding` bị rỗng, quality gate nên fail thay vì để pipeline âm thầm tạo một index kém chất lượng.

### 11.1. `run_data_quality_checks`

Các check tối thiểu:

```text
row_count > 0
paper_id không null
paper_id unique
title không rỗng
summary không rỗng
text_for_embedding không rỗng
age_days hợp lệ
```

Mỗi check nên có:

```json
{
  "name": "paper_id_unique",
  "passed": true,
  "value": 0,
  "expected": "duplicate_count == 0"
}
```

Payload tổng:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
{
    "report_name": report_name,
    "total_rows": len(df),
    "passed": all(check["passed"] for check in checks),
    "checks": checks,
}
```

Ghi tại:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
settings.paths.quality_dir / f"{report_name}_quality.json"
```

### 11.2. `build_freshness_report`

Tính:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
published = pd.to_datetime(df["published"], errors="coerce")
stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
```

Payload:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
{
    "latest_published": ...,
    "oldest_published": ...,
    "stale_rows": stale_rows,
    "total_rows": len(df),
    "is_fresh": stale_rows == 0,
}
```

Phải xử lý DataFrame rỗng/ngày lỗi mà không tạo kết quả sai giả.

---

## 12. Bước 8 — Hoàn thiện báo cáo baseline

Trong `src/observability/reporting.py`, `generate_phase1_report` nhận:

```text
source_summary
metrics
quality
freshness
```

Tạo Markdown gồm:

1. Source API/query/filter.
2. Raw count và clean count.
3. Bảng metrics.
4. Danh sách quality checks.
5. Freshness.
6. Artifact paths hoặc giới hạn.

Ghi bằng:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
from core.utils import write_text

write_text(report_path, markdown)
```

Không hard-code kết quả pass hoặc metric.

---

## 13. Bước 9 — Ghép baseline trong `src/pipelines/phase1.py`

File pipeline không nên chứa lại logic parse/clean. Nó chỉ gọi các module theo đúng thứ tự.

### Khái niệm cần biết: orchestration và idempotency

Orchestration là việc điều phối các module chạy đúng thứ tự, truyền đúng input/output và dừng khi một bước quan trọng thất bại.

Idempotency là đặc tính cho phép chạy lại một bước mà không tạo trạng thái sai hoặc nhân đôi dữ liệu ngoài ý muốn. Ví dụ index baseline được tạo lại có chủ đích thay vì cộng dồn document sau mỗi lần chạy.

Luồng:

```text
load settings
→ fetch/load raw
→ clean
→ save clean CSV/JSON
→ build baseline index
→ create/load test set
→ evaluate
→ quality/freshness
→ Markdown report
```

Khung:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    settings = load_settings()

    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    df = build_clean_dataframe(records, now_utc())
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(
        df,
        settings,
        settings.paths.embeddings_json,
    )

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(df, settings.paths.eval_testset)

    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(
        df,
        settings,
        settings.paths.freshness_report,
    )

    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_records": len(df),
    }

    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )
```

Lưu ý: nếu DataFrame chứa list hoặc Timestamp không JSON-serializable, cần chuẩn hóa trước khi gọi `write_json`.

Chạy:

```powershell
# Chú thích: chạy lệnh này trong PowerShell tại thư mục gốc của project và kiểm tra output trước khi chuyển bước.
python script/run_phase1.py
```

Artifact phải có:

```text
data/raw/crossref_response.json
data/raw/crossref_records.json
data/clean/papers_clean.csv
data/clean/papers_clean.json
data/embeddings/papers_embeddings.json
data/eval/test_set.json
data/results/baseline_metrics.json
data/results/baseline_answers.json
data/quality/
data/reports/phase1_report.md
```

---

## 14. Bước 10 — Hoàn thiện `src/ingestion/corruption.py`

Chỉ làm sau khi baseline hoàn tất.

### Khái niệm cần biết: fault injection và reproducibility

Fault injection là chủ động đưa lỗi vào hệ thống để kiểm tra khả năng phát hiện và phục hồi. Lỗi phải có chủ đích, có log và đo được; không phải sửa dữ liệu ngẫu nhiên chỉ để tạo file corrupted.

Reproducibility nghĩa là người khác có thể chạy lại cùng dữ liệu và cấu hình để tái hiện kết quả. Vì vậy corruption nên deterministic hoặc sử dụng random seed cố định.

Bắt đầu bằng copy:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
corrupted = df.copy(deep=True)
```

Không sửa trực tiếp baseline DataFrame.

Các corruption:

1. Xóa một số record mới nhất.
2. Làm rỗng summary.
3. Thêm noise vào summary.
4. Cắt ngắn title.
5. Làm published date cũ đi.
6. Thêm duplicate.

Sau khi sửa phải tính lại:

```text
summary_chars
age_days
text_for_embedding
```

Nên chọn row deterministic, không random hoặc dùng seed cố định.

Log mẫu:

```json
{
  "baseline_rows": 24,
  "corrupted_rows": 23,
  "events": [
    {
      "type": "blank_summary",
      "paper_ids": ["10.1234/example"],
      "affected_rows": 1
    }
  ]
}
```

Log phải mô tả sự thay đổi thật, không ghi chung chung.

---

## 15. Bước 11 — Ghép `src/pipelines/corruption_flow.py`

Luồng corrupted:

```text
load baseline clean data
→ corrupt
→ save corrupted CSV/JSON
→ build papers-corrupted
→ evaluate bằng test set cũ
→ corrupted quality/freshness
```

Luồng repaired:

```text
load raw records
→ chạy cleaning lại
→ save repaired CSV/JSON
→ build papers-repaired
→ evaluate bằng test set cũ
→ repaired quality/freshness
```

Sau đó tạo comparison report.

Tuyệt đối không repair bằng:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
repaired_df = baseline_df.copy()
```

Repair đúng:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
raw_records = load_raw_records(settings.paths.raw_records_json)
repaired_df = build_clean_dataframe(raw_records, now_utc())
```

Chroma collection được chọn qua manifest path:

```python
# Chú thích: đoạn Python dưới đây minh họa logic cần dùng; đọc các comment nội tuyến và phần giải thích ngay phía trên trước khi chạy.
LocalEmbeddingIndex.build(
    corrupted_df,
    settings,
    settings.paths.corrupted_embeddings_json,
)

LocalEmbeddingIndex.build(
    repaired_df,
    settings,
    settings.paths.repaired_embeddings_json,
)
```

Chạy:

```powershell
# Chú thích: chạy lệnh này trong PowerShell tại thư mục gốc của project và kiểm tra output trước khi chuyển bước.
python script/run_corruption_flow.py
```

Artifact cần có:

```text
data/clean/papers_clean_corrupted.csv
data/clean/papers_clean_repaired.csv
data/embeddings/papers_embeddings_corrupted.json
data/embeddings/papers_embeddings_repaired.json
data/results/corruption_log.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/corrupted_answers.json
data/results/repaired_answers.json
data/reports/corruption_report.md
```

---

## 16. Bước 12 — Báo cáo comparison

`generate_corruption_report` cần bảng:

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | ... | ... | ... |
| Mean token F1 | ... | ... | ... |
| Judge accuracy | ... | ... | ... |
| Mean judge score | ... | ... | ... |

Nên tính:

```text
corruption delta = corrupted - baseline
recovery delta = repaired - corrupted
```

Kết luận phải theo chuỗi bằng chứng:

```text
Corruption cụ thể
    → quality/freshness signal thay đổi
    → retrieval/answer metric thay đổi
```

Nếu metric không đổi, phải ghi rõ không quan sát được tác động thay vì khẳng định tác động.

---

## 17. Thứ tự làm thực tế

Không làm tất cả cùng lúc. Thứ tự an toàn:

1. Cài dependency và kiểm tra import.
2. Làm `parse_crossref_payload`.
3. Test parser bằng payload giả.
4. Làm `load_raw_records`.
5. Làm `fetch_source_records`.
6. Kiểm tra hai raw artifacts.
7. Làm `build_clean_dataframe`.
8. Kiểm tra clean schema.
9. Làm `build_test_set`.
10. Build baseline Chroma index và thử search.
11. Làm quality/freshness.
12. Làm phase-1 report.
13. Ghép `phase1.py`.
14. Chạy baseline end-to-end.
15. Làm corruption.
16. Ghép corruption/repaired flow.
17. Tạo comparison report.
18. Đối chiếu Rubric và điền báo cáo.

---

## 18. Checklist debug

### `No module named ...`

Đảm bảo đã kích hoạt `.venv` và chạy:

```powershell
# Chú thích: chạy lệnh này trong PowerShell tại thư mục gốc của project và kiểm tra output trước khi chuyển bước.
python -m pip install -e .
```

### `NotImplementedError`

Bạn đang chạm tới một hàm TODO chưa làm. Tìm bằng:

```powershell
# Chú thích: chạy lệnh này trong PowerShell tại thư mục gốc của project và kiểm tra output trước khi chuyển bước.
rg -n "TODO\(student\)|NotImplementedError" src
```

### Crossref trả `429` hoặc `503`

Đây là lỗi tạm thời/rate limit. Cần retry/backoff, không bỏ bước lưu raw data.

### DataFrame rỗng

Kiểm tra lần lượt:

```text
Crossref có items không?
Parser có bỏ hết record không?
Record có DOI/title/published không?
Cleaning đang filter theo điều kiện nào?
```

### Retrieval không tìm thấy document đúng

Kiểm tra:

```text
paper_id có giữ nguyên không?
text_for_embedding có rỗng không?
test-set ID có tồn tại trong index không?
title trong câu hỏi có đúng tuyệt đối không?
```

### Metrics đẹp bất thường

Kiểm tra answers artifact. Exact title lookup có thể làm test set quá dễ. Báo cáo phải mô tả đúng cách evaluation đang hoạt động.

---

## 19. Definition of Done

Baseline hoàn thành khi:

- Raw response và raw records tồn tại.
- Cleaned CSV/JSON đọc được.
- `paper_id` unique.
- `text_for_embedding` không rỗng.
- Test set dùng ID thật.
- Baseline Chroma collection tồn tại.
- Answers và metrics tồn tại.
- Quality/freshness report tồn tại.
- Phase-1 report khớp artifacts.

Toàn bài hoàn thành khi:

- Corrupted data khác baseline đúng như log.
- Baseline không bị ghi đè.
- Corrupted/repaired dùng cùng test set với baseline.
- Repaired data được dựng lại từ raw records.
- Có đủ metrics của ba trạng thái.
- Comparison report khớp JSON artifacts.
- Không có secret hoặc `.env` trong Git.

---

## 20. Việc cần làm ngay bây giờ

Chỉ thực hiện bước môi trường:

```powershell
# Chú thích: chạy lệnh này trong PowerShell tại thư mục gốc của project và kiểm tra output trước khi chuyển bước.
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -c "import pandas, requests, chromadb; import core, ingestion, retrieval; print('Môi trường OK')"
```

Khi thấy:

```text
Môi trường OK
```

mới bắt đầu chỉnh `src/ingestion/crossref.py`, trước hết là `parse_crossref_payload` và test bằng payload giả.
