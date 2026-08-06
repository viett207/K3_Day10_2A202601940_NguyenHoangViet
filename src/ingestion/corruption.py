"""Cố tình làm hỏng cleaned data để đo tác động lên hệ thống RAG.

File này thuộc tầng ingestion vì nó biến đổi dữ liệu trước khi dữ liệu được
đưa sang embedding/index. Hàm công khai ``corrupt_clean_dataframe`` được gọi
từ ``src/pipelines/corruption_flow.py``.

Các kiểu và phương thức xuất hiện trong file:

- ``pd.DataFrame``: kiểu bảng hai chiều của thư viện Pandas.
- ``pd.Series``: kiểu dữ liệu một chiều, thường là một cột hoặc một hàng.
- ``df.copy``/``df.drop``/``df.apply``: method của class Pandas DataFrame.
- ``df.loc``/``df.iloc``/``df.at``: các indexer do DataFrame cung cấp.
- ``pd.to_datetime``/``pd.to_numeric``/``pd.concat``: hàm cấp module Pandas.
- ``list``/``dict``/``set``/``len``/``min``/``max``/``str``: built-in Python.
- ``write_json``: utility nội bộ được định nghĩa trong ``src/core/utils.py``.

Ký hiệu gọi phương thức:

- ``pd.to_datetime(...)``: gọi hàm ``to_datetime`` từ module Pandas đã import
  với bí danh ``pd``.
- ``df.copy(...)``: gọi method ``copy`` trên object DataFrame ``df``.
- ``text.strip()``: gọi method ``strip`` được class ``str`` của Python cung cấp.
"""

from __future__ import annotations

from pathlib import Path

# Import thư viện Pandas và đặt bí danh là `pd`. Vì vậy các hàm cấp module
# được gọi bằng cú pháp `pd.tên_hàm`, ví dụ `pd.concat(...)`.
import pandas as pd

# `write_json` không thuộc Pandas hay Python chuẩn. Đây là hàm của project,
# nằm trong `src/core/utils.py`; nó tạo thư mục cha và ghi payload thành JSON.
from core.utils import write_json


def _rebuild_embedding_text(df: pd.DataFrame) -> None:
    """Tính lại các cột phụ thuộc sau khi title/summary/published bị sửa.

    Hàm sửa trực tiếp DataFrame được truyền vào. Nếu không chạy bước này,
    dữ liệu hiển thị đã bị corrupt nhưng text đưa vào ChromaDB vẫn có thể
    giữ nội dung baseline cũ, khiến phép thử corruption không có ý nghĩa.
    """
    # `df["summary"]` dùng toán tử [] của DataFrame để lấy cột summary dưới
    # dạng một Pandas Series.
    #
    # `Series.fillna("")` là method Pandas: thay NaN/None bằng chuỗi rỗng.
    # `Series.astype(str)` là method Pandas: ép mọi phần tử thành Python string.
    # `Series.str` là bộ truy cập các phép xử lý chuỗi theo từng phần tử.
    # `Series.str.len()` tính độ dài từng summary và trả về một Series mới.
    # Gán vào `df["summary_chars"]` sẽ tạo mới hoặc ghi đè cột này.
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()

    # `DataFrame.apply(function, axis=1)` là method Pandas gọi function một lần
    # cho mỗi hàng. Với `axis=1`, biến `row` trong lambda là một Pandas Series
    # chứa toàn bộ cột của hàng hiện tại.
    df["text_for_embedding"] = df.apply(
        # `lambda` là hàm ẩn danh của Python. Hàm này nhận một row và trả về
        # một chuỗi duy nhất để embedding.
        lambda row: "\n".join(
            # `str.join(iterable)` là method của Python string. Nó nối các phần
            # hợp lệ bằng ký tự xuống dòng `\n`.
            part
            for part in [
                # `row.get(key, default)` là method của Pandas Series có cách
                # dùng tương tự dict.get: nếu thiếu cột thì trả default "".
                # `str(...)` là built-in Python dùng để ép kiểu về chuỗi.
                # `.strip()` là method của str để bỏ khoảng trắng hai đầu.
                f"Title: {str(row.get('title', '')).strip()}",
                f"Summary: {str(row.get('summary', '')).strip()}",
                f"Authors: {str(row.get('authors_joined', '')).strip()}",
                f"Categories: {str(row.get('categories_joined', '')).strip()}",
                f"Published: {str(row.get('published', '')).strip()}",
            ]
            # `split(":", 1)` chỉ tách một lần tại dấu `:` đầu tiên. `[-1]`
            # lấy phần giá trị; `lower()` đổi về chữ thường để loại chuỗi "nan".
            if part.split(":", 1)[-1].strip()
            and part.split(":", 1)[-1].strip().lower() != "nan"
        ),
        # axis=1 nghĩa là áp dụng theo hàng; axis=0 sẽ áp dụng theo cột.
        axis=1,
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Tạo lỗi dữ liệu có kiểm soát và ghi nhật ký để truy vết.

    Input:
        df: cleaned DataFrame của baseline.
        output_log_path: nơi lưu JSON mô tả từng corruption.

    Output:
        Một DataFrame mới đã bị corrupt. DataFrame baseline không bị sửa.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    # `{...}` ở đây là set literal của Python. Set phù hợp vì cần kiểm tra tên
    # cột và thực hiện phép hiệu, không cần giữ thứ tự hay giá trị trùng.
    required = {
        "paper_id",
        "title",
        "summary",
        "published",
        "age_days",
        "authors_joined",
        "categories_joined",
        "text_for_embedding",
    }
    # `df.columns` là thuộc tính Index do Pandas DataFrame cung cấp.
    # `set(df.columns)` chuyển Index đó thành built-in set của Python.
    # Phép trừ hai set trả về những cột bắt buộc chưa có trong DataFrame.
    missing = required - set(df.columns)
    if missing:
        # `sorted` là built-in Python sắp xếp tên cột để thông báo ổn định.
        # `raise ValueError` chủ động dừng hàm vì input vi phạm data contract.
        raise ValueError(f"Cannot corrupt dataframe; missing columns: {sorted(missing)}")

    # `df.empty` là property bool của DataFrame: True nếu bảng không có phần tử.
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    # `DataFrame.copy(deep=True)` là method Pandas tạo DataFrame mới để các phép
    # gán phía dưới không sửa object baseline mà caller đang giữ.
    # `reset_index(drop=True)` tạo lại index 0..n-1; `drop=True` không giữ index
    # cũ thành một cột dữ liệu mới.
    corrupted = df.copy(deep=True).reset_index(drop=True)
    # `len` là built-in Python. Với DataFrame, nó trả số hàng.
    baseline_rows = len(corrupted)
    # `events: list[dict]` là type hint: một list chứa các dictionary.
    events: list[dict] = []

    # Scenario 1: xóa một số bài mới nhất để mô phỏng thiếu dữ liệu mới.
    # Chỉ thực hiện với dataset đủ lớn để không xóa sạch corpus nhỏ.
    if len(corrupted) >= 6:
        # `pd.to_datetime` là hàm cấp module Pandas, chuyển Series chuỗi ngày
        # thành datetime. `errors="coerce"` biến ngày lỗi thành NaT thay vì crash.
        # `Series.sort_values` sắp ngày mới nhất trước vì ascending=False.
        published_order = pd.to_datetime(corrupted["published"], errors="coerce").sort_values(ascending=False)
        # `//` là phép chia lấy phần nguyên của Python. min/max là built-in dùng
        # để giới hạn số row bị xóa trong khoảng từ 1 đến 2.
        drop_count = max(1, min(2, len(corrupted) // 8))
        # `published_order.index` là Pandas Index theo thứ tự đã sort; slicing
        # `[:drop_count]` lấy index của các bài mới nhất. `list(...)` đổi sang list.
        drop_indices = list(published_order.index[:drop_count])
        # `.loc[row_labels, column_label]` là label-based indexer của DataFrame.
        # `astype(str)` ép ID thành chuỗi; `tolist()` đổi Series thành Python list.
        dropped_ids = corrupted.loc[drop_indices, "paper_id"].astype(str).tolist()
        # `DataFrame.drop(index=...)` trả bảng mới không có các row chỉ định.
        corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)
        # `list.append` là method built-in để thêm một event vào cuối danh sách.
        events.append(
            {"type": "drop_latest", "paper_ids": dropped_ids, "affected_rows": len(dropped_ids)}
        )

    # Scenario 2: làm rỗng summary để quality check phát hiện completeness fail.
    if not corrupted.empty:
        # `corrupted.index` là Index hiện tại. Slicing lấy tối đa hai row đầu.
        blank_indices = list(corrupted.index[: min(2, len(corrupted))])
        blank_ids = corrupted.loc[blank_indices, "paper_id"].astype(str).tolist()
        # `.loc` ở vế trái cho phép gán cùng giá trị "" vào nhiều row của một cột.
        corrupted.loc[blank_indices, "summary"] = ""
        events.append(
            {"type": "blank_summary", "paper_ids": blank_ids, "affected_rows": len(blank_ids)}
        )

    # Scenario 3: thêm token vô nghĩa để làm giảm chất lượng semantic text.
    if len(corrupted) >= 2:
        # Lấy label index ở vị trí thứ 3 nếu có; min bảo vệ dataset nhỏ.
        noise_index = corrupted.index[min(2, len(corrupted) - 1)]
        # `.at[row_label, column_label]` là scalar label-based indexer của Pandas,
        # tối ưu cho việc đọc hoặc gán đúng một ô.
        noise_id = str(corrupted.at[noise_index, "paper_id"])
        corrupted.at[noise_index, "summary"] = (
            str(corrupted.at[noise_index, "summary"])
            + " zxqv unrelated noise 93847 random tokens navigation advertisement"
        # `.strip()` thuộc class str và loại khoảng trắng thừa sau khi nối.
        ).strip()
        events.append({"type": "summary_noise", "paper_ids": [noise_id], "affected_rows": 1})

    # Scenario 4: cắt title để mô phỏng dữ liệu bị truncate khi truyền/lưu.
    if len(corrupted) >= 3:
        title_index = corrupted.index[min(3, len(corrupted) - 1)]
        title_id = str(corrupted.at[title_index, "paper_id"])
        title = str(corrupted.at[title_index, "title"])
        # `title[:n]` là string slicing của Python, giữ n ký tự đầu.
        # `rstrip()` chỉ bỏ khoảng trắng phía bên phải chuỗi bị cắt.
        truncated_length = max(8, min(24, len(title) // 2))
        corrupted.at[title_index, "title"] = title[:truncated_length].rstrip()
        events.append({"type": "truncate_title", "paper_ids": [title_id], "affected_rows": 1})

    # Scenario 5: lùi ngày 10 năm và tăng age_days để tạo tín hiệu stale.
    if len(corrupted) >= 4:
        stale_index = corrupted.index[min(4, len(corrupted) - 1)]
        stale_id = str(corrupted.at[stale_index, "paper_id"])
        # `pd.to_datetime` ở đây nhận một scalar nên trả Pandas Timestamp hoặc NaT.
        published = pd.to_datetime(corrupted.at[stale_index, "published"], errors="coerce")
        # `pd.isna` là hàm Pandas kiểm tra None/NaN/NaT một cách thống nhất.
        if not pd.isna(published):
            # `pd.DateOffset(years=10)` là object độ lệch thời gian của Pandas.
            # Trừ nó khỏi Timestamp để lùi ngày 10 năm. `.date()` lấy Python date,
            # còn `.isoformat()` chuyển ngày thành chuỗi YYYY-MM-DD.
            corrupted.at[stale_index, "published"] = (published - pd.DateOffset(years=10)).date().isoformat()
            # `pd.Series([...])` tạo Series một phần tử để dùng `pd.to_numeric`.
            # `errors="coerce"` biến giá trị tuổi lỗi thành NaN.
            # `.iloc[0]` là position-based indexer, lấy phần tử ở vị trí 0.
            current_age = pd.to_numeric(pd.Series([corrupted.at[stale_index, "age_days"]]), errors="coerce").iloc[0]
            # Toán tử ba ngôi của Python chọn 0 nếu age bị thiếu; `int` ép về số nguyên.
            # 3652 xấp xỉ 10 năm và có tính đến năm nhuận.
            corrupted.at[stale_index, "age_days"] = int(0 if pd.isna(current_age) else current_age) + 3652
            events.append({"type": "stale_date", "paper_ids": [stale_id], "affected_rows": 1})

    # Scenario 6: chép lại một row để kiểm tra uniqueness/duplicate detection.
    # `.iloc[[0]]` là position-based indexer lấy row đầu nhưng vẫn trả DataFrame;
    # nếu dùng `.iloc[0]` thì kết quả sẽ là Series.
    duplicate_source = corrupted.iloc[[0]].copy()
    # Ở đây `.iloc[0]` lấy row đầu thành Series, sau đó `["paper_id"]` lấy field ID.
    duplicate_id = str(duplicate_source.iloc[0]["paper_id"])
    # `pd.concat` là hàm cấp module Pandas dùng để nối hai DataFrame theo hàng.
    # `ignore_index=True` tạo index mới liên tục cho bảng kết quả.
    corrupted = pd.concat([corrupted, duplicate_source], ignore_index=True)
    events.append({"type": "duplicate_row", "paper_ids": [duplicate_id], "affected_rows": 1})

    # Gọi helper được định nghĩa ở phía trên trong cùng module Python này.
    _rebuild_embedding_text(corrupted)
    # Log là bằng chứng để nối corruption với quality signal và metric change.
    payload = {
        "baseline_rows": baseline_rows,
        "corrupted_rows": len(corrupted),
        "events": events,
    }
    # Gọi utility của project đã import từ core.utils để ghi corruption log.
    write_json(output_log_path, payload)
    # `return` trả DataFrame corrupted cho corruption_flow tiếp tục build index.
    return corrupted
