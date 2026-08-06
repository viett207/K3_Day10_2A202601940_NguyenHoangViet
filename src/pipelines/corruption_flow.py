"""Chạy thí nghiệm corrupted data và phục hồi từ raw snapshot.

File này là orchestration của pha 2. Nó không tự tạo thuật toán embedding,
evaluation hay quality check; nó gọi lại những module đã có và thay input/index
để tạo ba trạng thái có thể so sánh:

    baseline -> corrupted -> repaired

Điểm khác nhau giữa ba trạng thái là dữ liệu và Chroma collection. Test set,
evaluator và cấu hình top_k được giữ nguyên.

Các thành phần quan trọng:

- ``pd.read_csv``: hàm Pandas đọc baseline CSV thành DataFrame.
- ``corrupt_clean_dataframe``: hàm trong ``src/ingestion/corruption.py``.
- ``LocalEmbeddingIndex.build``: tạo collection corrupted/repaired.
- ``evaluate_pipeline``: chấm cùng test set và ghi metrics/answers riêng.
- ``load_raw_records`` + ``build_clean_dataframe``: thực hiện repair từ raw.
- ``generate_corruption_report``: tạo báo cáo so sánh cuối cùng.

File ``script/run_corruption_flow.py`` import và gọi hàm ``main`` ở đây.
"""

from __future__ import annotations

# Pandas là thư viện bên thứ ba. Bí danh `pd` cho phép gọi `pd.read_csv(...)`.
import pandas as pd

# Cấu hình và các utility đọc/ghi nội bộ của project.
from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json

# Hàm chấm RAG trên test set cố định.
from evaluation.metrics import evaluate_pipeline

# Cleaning được gọi lại khi repair từ raw snapshot.
from ingestion.cleaning import build_clean_dataframe

# Hàm corruption công khai được định nghĩa trong file bạn phụ trách.
from ingestion.corruption import corrupt_clean_dataframe

# Đọc raw PaperRecord mà thành viên 1 đã lưu.
from ingestion.crossref import load_raw_records

# Quality/freshness functions do thành viên 3 cung cấp.
from observability.quality import build_freshness_report, run_data_quality_checks

# Hàm ghi bảng so sánh baseline/corrupted/repaired.
from observability.reporting import generate_corruption_report

# Class tạo và truy vấn ChromaDB index.
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Điều phối corruption, đánh giá, repair và báo cáo so sánh.

    Flow này chỉ được chạy sau baseline. Corrupted và repaired sử dụng test set
    cũ nhưng có cleaned artifact, embedding manifest và Chroma collection riêng.
    Repair được tạo lại từ raw snapshot, không copy baseline hay sửa tay metrics.

    Pseudo-code:
    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records.
    7. Evaluate repaired dataset.
    8. Tao comparison report.
    """
    # Bước 1: đọc cùng cấu hình và artifact paths đã dùng ở baseline.
    # Tạo object Settings giống baseline để dùng cùng query, model, top_k và paths.
    settings = load_settings()

    # Những artifact này chứng minh baseline đã sẵn sàng cho pha 2.
    # `[...]` tạo Python list chứa bốn Path bắt buộc phải có trước pha 2.
    required_baseline = [
        settings.paths.clean_csv,
        settings.paths.raw_records_json,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
    ]
    # Đây là list comprehension của Python: duyệt từng Path, giữ lại những Path
    # chưa tồn tại và chuyển chúng thành chuỗi để tạo thông báo dễ đọc.
    missing = [str(path) for path in required_baseline if not path.exists()]
    # Dừng sớm với thông báo rõ thay vì chạy flow trên input không đầy đủ.
    if missing:
        # `", ".join(missing)` là method của str, nối các path bằng dấu phẩy.
        raise RuntimeError(
            "Baseline artifacts are required before corruption flow. Missing: " + ", ".join(missing)
        )

    # Bước 2: đọc mốc so sánh và cleaned baseline đã được đóng băng.
    # `read_json` là utility trong core.utils, trả dictionary metrics baseline.
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # `pd.read_csv` là hàm cấp module Pandas. Nó đọc CSV và trả pd.DataFrame.
    baseline_df = pd.read_csv(settings.paths.clean_csv)

    # Bước 3: tạo corrupted DataFrame và corruption_log có thể audit.
    # Hàm corruption tự copy baseline_df; object baseline_df ở đây vẫn giữ sạch.
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)

    # Corrupted artifacts dùng tên riêng, không ghi đè cleaned baseline.
    # Ghi bản lỗi vào path riêng. Không dùng settings.paths.clean_csv vì đó là
    # file baseline cần bảo vệ.
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)

    # `to_dict(orient="records")` là method DataFrame đã giải thích ở phase1.py.
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # Manifest path khiến index.py chọn collection `papers-corrupted`.
    # Đường dẫn corrupted_embeddings_json được index.py ánh xạ tự động sang
    # collection name `papers-corrupted`.
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    # Bước 4: đánh giá corrupted index bằng đúng test set của baseline.
    # Lưu ý test_set_path vẫn là `eval_testset` của baseline. Chỉ index và hai
    # output paths thay đổi thành corrupted.
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    # Bước 5: đo các quality/freshness signal do corruption tạo ra.
    # Kết quả là dictionary chứa overall passed và danh sách checks.
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")

    # Toán tử `/` của pathlib.Path đã được overload để ghép đường dẫn an toàn.
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness.json"
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, corrupted_freshness_path
    )

    # Bước 6: repair đúng nghĩa bằng cách quay lại raw snapshot đáng tin cậy.
    # Không dùng `baseline_df.copy()` vì cách đó không kiểm chứng khả năng repair.
    # Đây là điểm bắt đầu repair: đọc raw snapshot chưa từng bị corruption sửa.
    raw_records = load_raw_records(settings.paths.raw_records_json)

    # Chạy lại đúng cleaning function của baseline. `now_utc()` cung cấp mốc
    # hiện tại để tính lại age_days.
    repaired_df = build_clean_dataframe(raw_records, now_utc())

    # Lưu repaired artifacts riêng để giữ đủ lineage của ba trạng thái.
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    # Manifest path khiến index.py chọn collection `papers-repaired`.
    # repaired_embeddings_json ánh xạ sang collection `papers-repaired`.
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    # Bước 7: tiếp tục dùng test set cũ để phép so sánh không bị đổi đề.
    # Vẫn cùng eval_testset, nhưng answers/metrics được ghi vào repaired paths.
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    # Đo xem quality/freshness đã trở về gần baseline hay chưa.
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)

    # Bước 8: so sánh metrics và signals của cả ba trạng thái.
    # `.summary` là thuộc tính của EvaluationBundle do evaluate_pipeline trả về.
    # Hàm report nhận ba metrics dictionaries và hai bộ quality/freshness để
    # tạo bảng delta và các nhận xét dựa trên số liệu thật.
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    # In tóm tắt và vị trí comparison report cho người chạy kiểm tra.
    # Thông báo tóm tắt cho terminal; artifact JSON/Markdown mới là bằng chứng.
    print(f"Corruption flow complete: {len(corrupted_df)} corrupted rows")
    print(f"Repaired rows: {len(repaired_df)}")
    print(f"Comparison report: {settings.paths.comparison_report}")
