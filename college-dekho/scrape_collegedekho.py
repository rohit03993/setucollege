"""Export CollegeDekho B.Tech colleges to Excel.

Reads the public B.Tech listing, then the Course and Fee, Admission, and
Placement pages linked from each card. It also saves Cutoff, Scholarship,
and Ranking from the same college address. Brochure and shortlist actions
are ignored.

Saved pages stay in data/ so a stopped run can continue.

From this folder, try two colleges first:

    python -m venv .venv
    .venv\\Scripts\\python.exe -m pip install -r requirements.txt
    .venv\\Scripts\\python.exe scrape_collegedekho.py --limit 2

Then the full list:

    .venv\\Scripts\\python.exe scrape_collegedekho.py
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://www.collegedekho.com"
LISTING = f"{BASE}/btech-colleges-in-india/"

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
COLLEGE_DIR = DATA_DIR / "colleges"
LISTING_PATH = DATA_DIR / "listing.json"
OUTPUT_PATH = ROOT / "output" / "collegedekho_btech.xlsx"
FAILURES_PATH = ROOT / "output" / "collegedekho_failed.txt"

IDENTITY = ["college_name", "slug", "city", "state"]
ILLEGAL_EXCEL = re.compile(r"[\000-\010\013\014\016-\037]")
SKIP_HEADING = re.compile(
    r"student preferred|similar college|related question|explore more|"
    r"share your college|table of contents|top courses at",
    re.I,
)
MAX_CELL = 32000
MAX_PAGES = 250


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export CollegeDekho B.Tech colleges to Excel.")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between requests. Default: 0.5")
    parser.add_argument("--refresh", action="store_true", help="Download pages again even if a copy exists.")
    parser.add_argument("--limit", type=int, default=0, help="Stop after this many colleges. 0 means the full list.")
    return parser.parse_args()


def clean_cell(value):
    if isinstance(value, str):
        value = ILLEGAL_EXCEL.sub("", value)
        if len(value) > MAX_CELL:
            return value[: MAX_CELL - 16] + " [truncated]"
    return value


def squash(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def absolute(href: str) -> str:
    href = (href or "").strip()
    if not href or href.startswith("javascript"):
        return ""
    return urljoin(BASE, href)


def slug_from(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "colleges":
        slug = parts[1].strip()
    elif parts:
        slug = parts[-1]
    else:
        slug = ""
    return re.sub(r'[<>:"/\\|?*]', "_", slug)


def header_name(value: str, used: set[str]) -> str:
    name = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:40] or "value"
    base = name
    number = 2
    while name in used:
        name = f"{base}_{number}"
        number += 1
    used.add(name)
    return name


def fetch_text(session: requests.Session, url: str) -> str | None:
    last_error = "unknown error"
    for attempt in range(4):
        try:
            response = session.get(url, timeout=45)
            if response.status_code == 404:
                return None
            if response.status_code == 429 or response.status_code >= 500:
                last_error = f"HTTP {response.status_code}"
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return response.text
        except requests.RequestException as exc:
            last_error = str(exc)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(last_error)


def listing_url(page: int) -> str:
    if page <= 1:
        return LISTING
    return f"{LISTING}?page={page}"


def parse_card(card) -> dict | None:
    title = card.select_one(".titleSection")
    name_link = title.select_one("a") if title else None
    if name_link is None:
        return None
    profile_url = absolute(name_link.get("href", ""))
    slug = slug_from(profile_url)
    name = squash(name_link.get_text(" ", strip=True))
    if not slug or not name:
        return None

    rating = squash(card.select_one(".collegeRate").get_text(" ", strip=True)) if card.select_one(".collegeRate") else ""
    reviews = ""
    review_link = card.select_one('a[href*="-reviews"]')
    if review_link:
        match = re.search(r"(\d+)", review_link.get_text(" ", strip=True))
        reviews = match.group(1) if match else ""

    city = state = ownership = approval = ""
    for item in card.select(".collegeinfo li"):
        image = item.select_one("img")
        source = image.get("src", "") if image else ""
        value = squash(item.get_text(" ", strip=True))
        if "location-listing" in source:
            if "," in value:
                city, state = [part.strip() for part in value.split(",", 1)]
            else:
                city = value
        elif "flag." in source:
            ownership = value
        elif "batch" in source:
            approval = value

    body = squash(card.get_text(" ", strip=True))
    fee_match = re.search(r"(\d[\d,]*\s*-\s*\d[\d,]*)", body)
    nirf_match = re.search(r"#\s*(\d+)\s*NIRF", body, re.I)
    exam_match = re.search(r"([A-Z][A-Za-z0-9.&/+ -]{1,40}?)\s+Exams", body)
    extra_match = re.search(r"\.\.\.\+(\d+)", body)
    package_match = re.search(
        r"(\d[\d.]*)\s*(Lacs|Lakhs|Lakh|LPA|Cr)\s*Avg Package",
        body,
        re.I,
    )
    course_match = re.search(r"Course and Fee\s*\((\d+)\)", body, re.I)
    shortlist_match = re.search(r"Shortlisted by\s+([0-9,+]+)", body, re.I)

    links = {"courses": "", "admission": "", "placement": ""}
    for link in card.select("ul.links a"):
        label = squash(link.get_text(" ", strip=True)).lower()
        href = absolute(link.get("href", ""))
        if label.startswith("course"):
            links["courses"] = href
        elif label.startswith("admission"):
            links["admission"] = href
        elif "placement" in label:
            links["placement"] = href

    return {
        "college_name": name,
        "slug": slug,
        "profile_url": profile_url,
        "city": city,
        "state": state,
        "ownership": ownership,
        "approval": approval,
        "rating": rating,
        "review_count": reviews,
        "fee_range": fee_match.group(1) if fee_match else "",
        "nirf_rank": nirf_match.group(1) if nirf_match else "",
        "exams": exam_match.group(1).strip() if exam_match else "",
        "more_exams": extra_match.group(1) if extra_match else "",
        "average_package": (
            f"{package_match.group(1)} {package_match.group(2)}" if package_match else ""
        ),
        "course_count_on_card": course_match.group(1) if course_match else "",
        "shortlisted_by": shortlist_match.group(1) if shortlist_match else "",
        "courses_url": links["courses"],
        "admission_url": links["admission"],
        "placement_url": links["placement"],
    }


def parse_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    cards = []
    seen = set()
    for card in soup.select(".collegeCardBox"):
        parsed = parse_card(card)
        if parsed is None or parsed["slug"] in seen:
            continue
        seen.add(parsed["slug"])
        cards.append(parsed)
    return cards


def collect_listing(session: requests.Session, limit: int, refresh: bool) -> list[dict]:
    if LISTING_PATH.exists() and not refresh and limit == 0:
        saved = json.loads(LISTING_PATH.read_text(encoding="utf-8"))
        if isinstance(saved, list) and saved:
            print(f"Using saved listing: {len(saved)} colleges", flush=True)
            return saved

    colleges = []
    seen_slugs = set()
    seen_pages = set()
    for page in range(1, MAX_PAGES + 1):
        html = fetch_text(session, listing_url(page))
        if html is None:
            break
        cards = parse_listing(html)
        signature = tuple(card["slug"] for card in cards)
        if not cards or signature in seen_pages:
            break
        seen_pages.add(signature)
        added = 0
        for card in cards:
            if card["slug"] in seen_slugs:
                continue
            seen_slugs.add(card["slug"])
            colleges.append(card)
            added += 1
            if limit and len(colleges) >= limit:
                break
        print(f"Listing page {page}: {len(cards)} cards, {added} new, total {len(colleges)}", flush=True)
        if limit and len(colleges) >= limit:
            break
        time.sleep(session.delay)

    if limit == 0:
        LISTING_PATH.parent.mkdir(parents=True, exist_ok=True)
        LISTING_PATH.write_text(json.dumps(colleges, ensure_ascii=False), encoding="utf-8")
    return colleges


def college_folder(slug: str) -> Path:
    folder = COLLEGE_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    return folder


EXTRA_PAGES = ("cutoff", "scholarship", "ranking")


def download_college(session: requests.Session, college: dict, refresh: bool, failures: list[str]) -> None:
    folder = college_folder(college["slug"])
    (folder / "card.json").write_text(json.dumps(college, ensure_ascii=False), encoding="utf-8")
    pages = {
        "courses": college.get("courses_url", ""),
        "admission": college.get("admission_url", ""),
        "placement": college.get("placement_url", ""),
    }
    slug = college.get("slug") or ""
    if slug:
        for name in EXTRA_PAGES:
            pages[name] = f"{BASE}/colleges/{slug}-{name}"
    for name, url in pages.items():
        path = folder / f"{name}.html"
        if not url:
            continue
        if path.exists() and not refresh:
            continue
        try:
            html = fetch_text(session, url)
        except RuntimeError as exc:
            failures.append(f"{college['slug']}\t{name}\t{exc}")
            print(f"  FAILED {college['college_name']} {name}: {exc}", flush=True)
            continue
        if html is None:
            failures.append(f"{college['slug']}\t{name}\t404")
            continue
        path.write_text(html, encoding="utf-8")
        time.sleep(session.delay)


def main_soup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one(".collegeDetailMainContainer") or soup.body or soup
    for tag in main.select("script, style, noscript"):
        tag.decompose()
    return main


def heading_text(node) -> str:
    heading = node.find_previous(["h2", "h3"])
    if heading is None:
        return ""
    return squash(heading.get_text(" ", strip=True))[:180]


def table_rows(html: str, college: dict, page: str) -> list[dict]:
    if not html:
        return []
    main = main_soup(html)
    rows = []
    for table in main.select("table"):
        heading = heading_text(table)
        if SKIP_HEADING.search(heading):
            continue
        header_cells = table.select("tr th")
        headers = [squash(cell.get_text(" ", strip=True)) for cell in header_cells]
        body_rows = table.select("tr")
        if not headers and body_rows:
            headers = [squash(cell.get_text(" ", strip=True)) for cell in body_rows[0].select("td, th")]
            body_rows = body_rows[1:]
        elif headers:
            body_rows = [row for row in body_rows if row.select("td")]
        for table_row in body_rows:
            cells = [squash(cell.get_text(" ", strip=True)) for cell in table_row.select("td")]
            if not any(cells):
                continue
            record = {
                "college_name": college["college_name"],
                "slug": college["slug"],
                "city": college.get("city", ""),
                "state": college.get("state", ""),
                "page": page,
                "table_heading": clean_cell(heading),
            }
            used = set(record)
            if headers and len(headers) == len(cells):
                for header, cell in zip(headers, cells):
                    record[header_name(header, used)] = clean_cell(cell)
            else:
                for index, cell in enumerate(cells, start=1):
                    record[f"column_{index}"] = clean_cell(cell)
            rows.append(record)
    return rows


def section_rows(html: str, college: dict, page: str) -> list[dict]:
    if not html:
        return []
    main = main_soup(html)
    rows = []
    for heading in main.select("h2, h3"):
        title = squash(heading.get_text(" ", strip=True))
        if not title or SKIP_HEADING.search(title):
            continue
        parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name in {"h2", "h3"}:
                break
            piece = squash(sibling.get_text(" ", strip=True))
            if piece:
                parts.append(piece)
        content = clean_cell(" ".join(parts))
        if len(content) < 40:
            continue
        rows.append(
            {
                "college_name": college["college_name"],
                "slug": college["slug"],
                "city": college.get("city", ""),
                "state": college.get("state", ""),
                "page": page,
                "heading": clean_cell(title[:180]),
                "content": content,
            }
        )
    return rows


def load_html(folder: Path, name: str) -> str:
    path = folder / f"{name}.html"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_tables(colleges: list[dict]) -> dict[str, pd.DataFrame]:
    college_rows = []
    courses = []
    admission = []
    placement = []
    sections = []
    pages = (
        ("courses", courses),
        ("admission", admission),
        ("placement", placement),
    )
    for college in colleges:
        college_rows.append(college)
        folder = COLLEGE_DIR / college["slug"]
        for page, bucket in pages:
            html = load_html(folder, page)
            bucket.extend(table_rows(html, college, page))
            sections.extend(section_rows(html, college, page))

    tables = {
        "Colleges": frame(college_rows, IDENTITY),
        "Courses and Fees": frame(courses, IDENTITY + ["table_heading"]),
        "Admission": frame(admission, IDENTITY + ["table_heading"]),
        "Placement": frame(placement, IDENTITY + ["table_heading"]),
        "Sections": frame(sections, IDENTITY + ["page", "heading", "content"]),
    }
    if not tables["Colleges"].empty:
        tables["Colleges"] = tables["Colleges"].sort_values(["college_name", "city"], kind="stable")
    return tables


def frame(rows: list[dict], leading: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=leading)
    table = pd.DataFrame(rows).map(lambda value: clean_cell(value) if isinstance(value, str) else value)
    front = [column for column in leading if column in table.columns]
    rest = [column for column in table.columns if column not in front]
    return table[front + rest]


def write_workbook(tables: dict[str, pd.DataFrame]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        for name, table in tables.items():
            table.to_excel(writer, sheet_name=name[:31], index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            if sheet.dimensions:
                sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = 24


def main() -> None:
    args = parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en;q=0.9",
        }
    )
    session.delay = args.delay

    colleges = collect_listing(session, args.limit, args.refresh)
    if args.limit:
        colleges = colleges[: args.limit]
    if not colleges:
        raise SystemExit("No colleges were found on the B.Tech listing.")

    print(f"Colleges in this run: {len(colleges)}", flush=True)
    failures: list[str] = []
    for number, college in enumerate(colleges, start=1):
        print(f"[{number}/{len(colleges)}] {college['college_name']}", flush=True)
        download_college(session, college, args.refresh, failures)

    FAILURES_PATH.write_text("\n".join(failures), encoding="utf-8")
    print(f"Failed section downloads: {len(failures)}", flush=True)
    from build_workbook import build_from_disk

    build_from_disk()


if __name__ == "__main__":
    main()
