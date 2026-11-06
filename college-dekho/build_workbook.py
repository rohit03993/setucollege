"""Build the CollegeDekho workbook from pages already saved on disk.

Reads data/listing.json and each college's courses, admission, placement,
cutoff, scholarship, and ranking HTML once. Every table cell is kept, in
order, up to Excel's cell limit.
Written sections on those pages are kept too. Student reviews and the public
question box are skipped.

Stop the old hung command first (Ctrl+C in that terminal), then run:

    .\\.venv\\Scripts\\python.exe build_workbook.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from lxml import html
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
COLLEGE_DIR = DATA_DIR / "colleges"
LISTING_PATH = DATA_DIR / "listing.json"
OUTPUT_PATH = ROOT / "output" / "collegedekho_btech.xlsx"

ILLEGAL_EXCEL = re.compile(r"[\000-\010\013\014\016-\037]")
SKIP_HEADING = re.compile(
    r"student preferred|similar college|related question|explore more|"
    r"share your college|table of contents|top courses at",
    re.I,
)
NOISE = (
    './/*[contains(@class,"studentFeedback") or contains(@class,"studentQa")'
    ' or contains(@class,"similarCollege") or contains(@class,"relatedQuestion")]'
)
MAX_CELL = 32000
NAMED_VALUES = 40

COLLEGE_COLUMNS = [
    "college_name",
    "slug",
    "city",
    "state",
    "ownership",
    "approval",
    "rating",
    "review_count",
    "fee_range",
    "nirf_rank",
    "exams",
    "more_exams",
    "average_package",
    "course_count_on_card",
    "shortlisted_by",
    "profile_url",
    "courses_url",
    "admission_url",
    "placement_url",
    "cutoff_url",
    "scholarship_url",
    "ranking_url",
]
TABLE_LEAD = ["college_name", "slug", "city", "state", "page", "table_heading", "columns"]
SECTION_COLUMNS = ["college_name", "slug", "city", "state", "page", "heading", "content"]
PAGES = ("courses", "admission", "placement", "cutoff", "scholarship", "ranking")
SHEET_FOR_PAGE = {
    "courses": "Courses and Fees",
    "admission": "Admission",
    "placement": "Placement",
    "cutoff": "Cutoff",
    "scholarship": "Scholarship",
    "ranking": "Ranking",
}
EXTRA_PAGES = ("cutoff", "scholarship", "ranking")


def clean(value) -> str:
    text = ILLEGAL_EXCEL.sub("", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_CELL:
        return text[: MAX_CELL - 16] + " [truncated]"
    return text


def text_without_tables(node) -> str:
    tables = [table for table in node.xpath(".//table") if isinstance(table.tag, str)]
    if not tables:
        return clean(node.text_content())
    anchors = []
    for table in reversed(tables):
        parent = table.getparent()
        if parent is None:
            continue
        anchors.append((parent, table.getprevious(), table))
        parent.remove(table)
    text = clean(node.text_content())
    for parent, previous, table in reversed(anchors):
        if previous is None:
            parent.insert(0, table)
        else:
            previous.addnext(table)
    return text


def cell_text(cell) -> str:
    return text_without_tables(cell)


def nearest_heading(table) -> str:
    nodes = table.xpath("preceding::*[self::h2 or self::h3][1]")
    if not nodes:
        return ""
    return clean("".join(nodes[0].itertext()))[:180]


def table_rows(table) -> list[list[str]]:
    rows = []
    for tr in table.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr"):
        cells = [cell_text(cell) for cell in tr.xpath("./th | ./td")]
        if any(cells):
            rows.append(cells)
    return rows


def append_table(sheet, college: dict, page: str, table) -> int:
    heading = nearest_heading(table)
    if heading and SKIP_HEADING.search(heading):
        return 0
    matrix = table_rows(table)
    if not matrix:
        return 0
    first = table.xpath("(./tr | ./thead/tr | ./tbody/tr)[1]")
    header_cells = first[0].xpath("./th") if first else []
    data_cells = first[0].xpath("./td") if first else []
    if header_cells and not data_cells and len(matrix) > 1:
        column_names = " | ".join(matrix[0])
        body = matrix[1:]
    else:
        column_names = ""
        body = matrix
    base = [
        college.get("college_name", ""),
        college.get("slug", ""),
        college.get("city", ""),
        college.get("state", ""),
        page,
        heading,
        column_names,
    ]
    written = 0
    for cells in body:
        sheet.append(base + cells)
        written += 1
    return written


def append_sections(sheet, college: dict, page: str, root) -> int:
    written = 0
    base = [
        college.get("college_name", ""),
        college.get("slug", ""),
        college.get("city", ""),
        college.get("state", ""),
        page,
    ]
    for heading in root.xpath(".//h2 | .//h3"):
        title = clean("".join(heading.itertext()))[:180]
        if not title or SKIP_HEADING.search(title):
            continue
        parts = []
        for sibling in heading.itersiblings():
            if not isinstance(sibling.tag, str):
                continue
            if sibling.tag in {"h2", "h3"}:
                break
            piece = text_without_tables(sibling)
            if piece:
                parts.append(piece)
        content = clean(" ".join(parts))
        if len(content) < 15:
            continue
        sheet.append(base + [title, content])
        written += 1
    return written


def prepare(root):
    for node in root.xpath(".//script | .//style | .//noscript"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in root.xpath(NOISE):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def parse_page(path: Path, college: dict, page: str, table_sheet, section_sheet) -> tuple[int, int]:
    if not path.exists() or path.stat().st_size == 0:
        return 0, 0
    document = html.parse(str(path))
    mains = document.xpath('//*[contains(@class, "collegeDetailMainContainer")]')
    root = mains[0] if mains else document.getroot()
    prepare(root)
    tables = 0
    for table in root.xpath(".//table"):
        tables += append_table(table_sheet, college, page, table)
    sections = append_sections(section_sheet, college, page, root)
    return tables, sections


def with_extra_urls(college: dict) -> dict:
    row = dict(college)
    slug = college.get("slug") or ""
    if slug:
        for page in EXTRA_PAGES:
            row[f"{page}_url"] = f"https://www.collegedekho.com/colleges/{slug}-{page}"
    return row


def build_from_disk() -> None:
    colleges = json.loads(LISTING_PATH.read_text(encoding="utf-8"))
    if not isinstance(colleges, list) or not colleges:
        raise SystemExit("No saved college list was found.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook(write_only=True)
    college_sheet = workbook.create_sheet("Colleges")
    college_sheet.append(COLLEGE_COLUMNS)
    table_header = TABLE_LEAD + [f"value_{number}" for number in range(1, NAMED_VALUES + 1)]
    page_sheets = {}
    for page in PAGES:
        sheet = workbook.create_sheet(SHEET_FOR_PAGE[page])
        sheet.append(table_header)
        page_sheets[page] = sheet
    section_sheet = workbook.create_sheet("Sections")
    section_sheet.append(SECTION_COLUMNS)

    table_counts = {page: 0 for page in PAGES}
    section_count = 0
    total = len(colleges)
    for number, college in enumerate(colleges, start=1):
        row = with_extra_urls(college)
        college_sheet.append([clean(row.get(column, "")) for column in COLLEGE_COLUMNS])
        folder = COLLEGE_DIR / college["slug"]
        for page in PAGES:
            tables, sections = parse_page(
                folder / f"{page}.html",
                college,
                page,
                page_sheets[page],
                section_sheet,
            )
            table_counts[page] += tables
            section_count += sections
        if number % 100 == 0 or number == total:
            print(f"Built {number}/{total} colleges", flush=True)

    print("Writing workbook...", flush=True)
    workbook.save(OUTPUT_PATH)
    print(f"\nWorkbook: {OUTPUT_PATH}", flush=True)
    print(f"  Colleges: {total} rows", flush=True)
    for page in PAGES:
        print(f"  {SHEET_FOR_PAGE[page]}: {table_counts[page]} rows", flush=True)
    print(f"  Sections: {section_count} rows", flush=True)


if __name__ == "__main__":
    build_from_disk()
