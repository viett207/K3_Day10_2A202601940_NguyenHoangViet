from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from html import unescape
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


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


def _first_text(value) -> str:
    if isinstance(value, list) and value:
        return normalize_whitespace(str(value[0]))
    if isinstance(value, str):
        return normalize_whitespace(value)
    return ""


def _strip_markup(value: str) -> str:
    text = unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _extract_authors(item: dict) -> list[str]:
    authors: list[str] = []
    for author in item.get("author", []) or []:
        if not isinstance(author, dict):
            continue
        full_name = normalize_whitespace(
            f"{author.get('given', '')} {author.get('family', '')}"
        )
        if full_name and full_name not in authors:
            authors.append(full_name)
    return authors


def _extract_date(value) -> str:
    if not value:
        return ""
    if isinstance(value, dict):
        parts_groups = value.get("date-parts")
        if isinstance(parts_groups, list) and parts_groups:
            parts = parts_groups[0]
            try:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
                return date(year, month, day).isoformat()
            except (TypeError, ValueError, IndexError):
                return ""
        value = value.get("date-time") or value.get("timestamp")
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000).date().isoformat()
        except (OSError, OverflowError, ValueError):
            return ""
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return ""
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref works payload into normalized paper records.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items", [])
    if not isinstance(items, list):
        raise ValueError("Crossref payload message.items must be a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = normalize_whitespace(str(item.get("DOI", ""))).lower()
        title = _first_text(item.get("title"))
        if not paper_id or not title or paper_id in seen_ids:
            continue

        categories = []
        for category in item.get("subject", []) or []:
            normalized = normalize_whitespace(str(category))
            if normalized and normalized not in categories:
                categories.append(normalized)

        published = (
            _extract_date(item.get("published-print"))
            or _extract_date(item.get("published-online"))
            or _extract_date(item.get("published"))
            or _extract_date(item.get("issued"))
        )
        updated = _extract_date(item.get("indexed")) or _extract_date(item.get("created"))

        pdf_url = ""
        for link in item.get("link", []) or []:
            if not isinstance(link, dict):
                continue
            content_type = str(link.get("content-type", "")).lower()
            candidate = normalize_whitespace(str(link.get("URL", "")))
            if candidate and (content_type == "application/pdf" or candidate.lower().endswith(".pdf")):
                pdf_url = candidate
                break

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=_strip_markup(str(item.get("abstract", ""))),
                authors=_extract_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=normalize_whitespace(str(item.get("URL", ""))),
                pdf_url=pdf_url,
                comment=_first_text(item.get("subtitle")),
            )
        )
        seen_ids.add(paper_id)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data, persist the raw payload, and return parsed records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,published-print,published-online,issued,indexed,created,URL,link,subtitle",
    }
    headers = {"User-Agent": "day10-data-pipeline-lab/1.0 (educational use)"}
    retry_statuses = {429, 500, 502, 503, 504}
    last_error: Exception | None = None

    for attempt in range(4):
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params=params,
                headers=headers,
                timeout=30,
            )
            if response.status_code in retry_statuses:
                raise requests.HTTPError(
                    f"Crossref temporary error: HTTP {response.status_code}", response=response
                )
            response.raise_for_status()
            payload = response.json()
            write_json(settings.paths.raw_api_response, payload)
            records = parse_crossref_payload(payload)
            if not records:
                raise RuntimeError("Crossref returned no usable paper records.")
            write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
            return records
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            retryable = not isinstance(exc, requests.HTTPError) or (
                exc.response is not None and exc.response.status_code in retry_statuses
            )
            if attempt == 3 or not retryable:
                break
            retry_after = None
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                retry_after = exc.response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else float(2**attempt)
            except ValueError:
                delay = float(2**attempt)
            time.sleep(min(delay, 30.0))

    raise RuntimeError(f"Unable to fetch Crossref records after retries: {last_error}") from last_error


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a parsed raw JSON snapshot and map it to PaperRecord objects."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw record snapshot must contain a JSON list: {path}")
    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at index {index} is not an object.")
        try:
            records.append(PaperRecord(**item))
        except TypeError as exc:
            raise ValueError(f"Raw record at index {index} does not match PaperRecord schema.") from exc
    return records
