"""Chạy baseline pipeline trên dữ liệu sạch.

Đây là file orchestration: nó không chứa thuật toán parse, cleaning, embedding
hay evaluation. Nó import các hàm/class từ những module chuyên trách rồi gọi
chúng theo đúng thứ tự.

Luồng dữ liệu:

    Crossref/raw snapshot -> PaperRecord -> clean DataFrame -> baseline index
    -> test set -> answers/metrics -> quality/freshness -> Markdown report

Các hàm được lấy từ đâu:

- ``load_settings``: ``src/core/config.py``.
- ``now_utc``, ``write_csv``, ``write_json``: ``src/core/utils.py``.
- ``fetch_source_records``, ``load_raw_records``: ``src/ingestion/crossref.py``.
- ``build_clean_dataframe``: ``src/ingestion/cleaning.py``.
- ``build_test_set``: ``src/evaluation/testset.py``.
- ``LocalEmbeddingIndex``: class trong ``src/retrieval/index.py``.
- ``evaluate_pipeline``: ``src/evaluation/metrics.py``.
- quality/freshness functions: ``src/observability/quality.py``.
- ``generate_phase1_report``: ``src/observability/reporting.py``.

File ``script/run_phase1.py`` import hàm ``main`` trong file này và gọi nó.
"""

from __future__ import annotations

# Import hàm tạo Settings. Dấu chấm không có ở đầu `core` vì project đã được
# cài editable và thư mục `src` được nhận là package root.
from core.config import load_settings

# Đây là ba utility nội bộ của project, không phải hàm của Pandas/Python chuẩn.
from core.utils import now_utc, write_csv, write_json

# Hàm này chạy câu hỏi, tính metrics và ghi answers/metrics JSON.
from evaluation.metrics import evaluate_pipeline

# Hàm của thành viên 2 tạo đề kiểm thử từ cleaned DataFrame.
from evaluation.testset import build_test_set

# Hàm của thành viên 2 biến list[PaperRecord] thành Pandas DataFrame sạch.
from ingestion.cleaning import build_clean_dataframe

# Hai hàm của thành viên 1: một hàm gọi API, một hàm đọc raw snapshot có sẵn.
from ingestion.crossref import fetch_source_records, load_raw_records

# Hai hàm của thành viên 3 kiểm tra sức khỏe và độ mới của dữ liệu.
from observability.quality import build_freshness_report, run_data_quality_checks

# Hàm của thành viên 3 tổng hợp kết quả thành báo cáo Markdown.
from observability.reporting import generate_phase1_report

# Class quản lý embedding và ChromaDB collection baseline.
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Điều phối baseline pipeline từ raw source đến metrics và report.

    File này không tự triển khai lại parsing, cleaning hay evaluation. Vai trò
    của nó là gọi đúng module theo thứ tự, truyền đúng input/output và lưu đầy
    đủ artifact để pha corruption có thể sử dụng về sau.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    # `load_settings()` gọi hàm không tham số. Hàm tự xác định project root,
    # đọc `.env`, rồi trả một object Settings. Ta có thể truy cập thuộc tính
    # bằng cú pháp `settings.paths.clean_csv` hoặc `settings.refresh_source`.
    settings = load_settings()

    # Bước 2: chỉ gọi Crossref khi chưa có snapshot hoặc REFRESH_SOURCE=true.
    # Việc tái sử dụng snapshot giúp các lần chạy có cùng dữ liệu đầu vào.
    # `Path.exists()` là method của class pathlib.Path trong Python standard
    # library. Nó trả True nếu raw JSON đã tồn tại trên ổ đĩa.
    # `not` đảo giá trị bool; `or` chỉ cần một vế đúng để đi vào nhánh fetch.
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        # Gọi hàm được import từ crossref.py và nhận list[PaperRecord].
        records = fetch_source_records(settings)
    else:
        # Không gọi Internet; đọc lại đúng raw snapshot đã lưu từ lần trước.
        records = load_raw_records(settings.paths.raw_records_json)

    # `now_utc()` trả datetime hiện tại theo UTC. Cleaning dùng cùng một mốc
    # này để tính age_days nhất quán cho mọi record.
    run_date = now_utc()

    # Truyền list records và run_date vào hàm cleaning. Giá trị trả về là
    # `pd.DataFrame`, được lưu trong biến clean_df.
    clean_df = build_clean_dataframe(records, run_date)

    # `write_csv` nhận DataFrame và Path; bên trong gọi `df.to_csv` của Pandas.
    write_csv(clean_df, settings.paths.clean_csv)

    # `DataFrame.to_dict(orient="records")` là method Pandas chuyển mỗi hàng
    # thành một dictionary và toàn bảng thành list[dict], phù hợp để ghi JSON.
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    # Bước 4: tạo embedding và collection `papers-baseline` trong ChromaDB.
    # embeddings_json là manifest mô tả model, collection và documents.
    # `build` là classmethod của LocalEmbeddingIndex. Ta gọi qua tên class thay
    # vì tạo object trước. Method này tạo embeddings, Chroma collection, ghi
    # manifest rồi trả một LocalEmbeddingIndex đã sẵn sàng để search.
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    # Bước 5: giữ nguyên test set cũ trừ khi chưa có hoặc được yêu cầu refresh.
    # Đây là điều kiện để baseline/corrupted/repaired so sánh công bằng.
    # Chỉ tạo đề mới khi REFRESH_TEST_SET=true hoặc file chưa tồn tại. Nếu file
    # đã có thì giữ nguyên để pha corrupted/repaired dùng đúng cùng một đề.
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)

    # Bước 6: trả lời từng câu hỏi rồi ghi answers và baseline metrics.
    # Dùng keyword arguments (`settings=...`) để thể hiện rõ ý nghĩa từng đối
    # số. Hàm trả EvaluationBundle gồm `.summary` và `.answers`.
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    # Bước 7: đo sức khỏe dữ liệu độc lập với chất lượng câu trả lời RAG.
    # Chuỗi "baseline" trở thành report_name, giúp output có tên riêng và
    # không bị nhầm với corrupted/repaired quality.
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(
        clean_df,
        settings,
        settings.paths.freshness_report,
    )
    # Bước 8: tổng hợp source, metrics, quality và freshness thành Markdown.
    # `source_summary={...}` là dictionary literal của Python. Nó gom metadata
    # nguồn và số record để report có thể truy vết lần chạy.
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary={
            "source": settings.source_api,
            "query": settings.source_query,
            "filter": settings.source_filter,
            # `len` là built-in Python: với list/DataFrame đều trả số phần tử/hàng.
            "raw_records": len(records),
            "clean_records": len(clean_df),
            # `datetime.isoformat()` là method của datetime chuẩn Python.
            "run_date_utc": run_date.isoformat(),
            "embedding_model": settings.embedding_model,
            "collection_name": settings.baseline_collection_name,
        },
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    # In vị trí output để người chạy biết cần kiểm tra artifact nào.
    # `print` là built-in Python; f-string chèn giá trị nằm trong `{...}`.
    print(f"Baseline complete: {len(clean_df)} cleaned records")
    print(f"Metrics: {settings.paths.baseline_metrics}")
    print(f"Report: {settings.paths.baseline_report}")
