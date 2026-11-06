"""Collect public College For Me college records into one Excel workbook.

Reads the public JSON the site already uses for its college pages, then writes
separate sheets for colleges, streams, courses, written sections, facilities,
campus life, images, and any stored admissions, fees, scholarships, cutoffs,
and FAQs. Reviews are left out.

This script lives in the college-for-me folder, next to the saved data and Excel file.

Run from that folder:
    python -m venv .venv
    .venv\\Scripts\\python.exe -m pip install -r requirements.txt
    .venv\\Scripts\\python.exe scrape_collegeforme.py
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.collegeforme.in"
INDEX_URL = f"{BASE}/api/colleges/index"
DETAIL_URL = f"{BASE}/api/college/{{slug}}"

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "collegeforme" / "raw"
OUTPUT_PATH = ROOT / "output" / "collegeforme_colleges.xlsx"
FAILURES_PATH = ROOT / "output" / "collegeforme_failed.txt"

IDENTITY = ["college_id", "college_name", "slug", "city", "state", "streams"]
ILLEGAL_EXCEL = re.compile(r"[\000-\010\013\014\016-\037]")
MAX_CELL = 32000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export College For Me colleges to Excel.")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Seconds to wait between college requests. Default: 0.4",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download every college again, even if a saved copy already exists.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after this many colleges. 0 means all colleges.",
    )
    return parser.parse_args()


def clean_cell(value):
    if isinstance(value, str):
        value = ILLEGAL_EXCEL.sub("", value)
        if len(value) > MAX_CELL:
            return value[: MAX_CELL - 16] + " [truncated]"
    return value


def blank_if_empty(value):
    if value in (None, "", [], {}):
        return ""
    return value


def plain(value):
    """Keep numbers and text as they are. Turn nested data into text."""
    value = blank_if_empty(value)
    if isinstance(value, (dict, list)):
        return join_values(value)
    return value


def blank_zero(value):
    if value in (None, "", 0, "0"):
        return ""
    return value


def yes_no(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return ""


def join_values(value) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(json.dumps(item, ensure_ascii=False))
            elif item not in (None, ""):
                parts.append(str(item))
        return " | ".join(parts)
    if isinstance(value, dict):
        if not value:
            return ""
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def stream_text(college: dict) -> str:
    tags = college.get("streamTags") or []
    if isinstance(tags, str):
        tags = [tags]
    return " | ".join(str(tag) for tag in tags if tag)


def identity(college: dict) -> dict:
    return {
        "college_id": college.get("id"),
        "college_name": college.get("name") or "",
        "slug": college.get("slug") or "",
        "city": college.get("city") or "",
        "state": college.get("state") or "",
        "streams": stream_text(college),
    }


def records_from(value) -> list[dict]:
    """Turn a list or a single object into rows. Skip empty objects."""
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        rows = []
        for item in value:
            if isinstance(item, dict):
                if any(item.get(key) not in (None, "", [], {}) for key in item):
                    rows.append(item)
            elif item not in (None, ""):
                rows.append({"value": item})
        return rows
    if isinstance(value, dict):
        if any(item not in (None, "", [], {}) for item in value.values()):
            return [value]
        return []
    return [{"value": value}]


def flatten_record(record: dict) -> dict:
    flat = {}
    for key, value in record.items():
        if isinstance(value, bool):
            flat[key] = yes_no(value)
        elif isinstance(value, (dict, list)):
            flat[key] = clean_cell(join_values(value))
        else:
            flat[key] = clean_cell(blank_if_empty(value))
    return flat


def attach(college: dict, rows: list[dict]) -> list[dict]:
    base = identity(college)
    attached = []
    for row in rows:
        item = dict(base)
        item.update(row)
        attached.append(item)
    return attached


def section_rows(college: dict) -> list[dict]:
    seo = college.get("seoContent") or {}
    if not isinstance(seo, dict):
        return []
    rows = []
    intro = seo.get("intro") or ""
    if intro:
        rows.append({"heading": "Intro", "content": clean_cell(intro)})
    for section in seo.get("sections") or []:
        if not isinstance(section, dict):
            continue
        heading = section.get("h2") or ""
        content = section.get("content") or ""
        if heading or content:
            rows.append({"heading": clean_cell(heading), "content": clean_cell(content)})
    return attach(college, rows)


def about_text(college: dict) -> str:
    seo = college.get("seoContent") or {}
    if not isinstance(seo, dict):
        return ""
    for section in seo.get("sections") or []:
        heading = (section.get("h2") or "") if isinstance(section, dict) else ""
        if heading.lower().startswith("about"):
            return clean_cell(section.get("content") or "")
    intro = seo.get("intro") or ""
    return clean_cell(intro)


def estimated_total(fee, years):
    if isinstance(fee, (int, float)) and isinstance(years, (int, float)) and years > 0:
        return round(float(fee) * float(years), 2)
    return ""


def course_rows(college: dict) -> list[dict]:
    rows = []
    for course in college.get("courses") or []:
        if not isinstance(course, dict):
            continue
        fee = course.get("fees_college")
        years = course.get("durationYears")
        rows.append(
            {
                "course_name": course.get("name") or "",
                "course_code": course.get("code") or "",
                "level": course.get("level") or "",
                "duration_years": blank_if_empty(years),
                "fee_per_year": blank_if_empty(fee),
                "estimated_total_fee": estimated_total(fee, years),
                "counselor_fee": blank_if_empty(course.get("fees_councelers")),
                "is_popular": yes_no(course.get("isPopular")),
                "eligibility": join_values(course.get("eligblityCateria")),
                "specializations": join_values(course.get("specializations")),
                "description": clean_cell(course.get("description") or ""),
            }
        )
    return attach(college, rows)


def stream_rows(college: dict) -> list[dict]:
    tags = college.get("streamTags") or []
    if isinstance(tags, str):
        tags = [tags]
    rows = [{"stream": str(tag)} for tag in tags if tag]
    return attach(college, rows)


def image_rows(college: dict) -> list[dict]:
    rows = []
    singles = {
        "logo": college.get("logoUrl"),
        "banner": college.get("bannerImage"),
        "video": college.get("videoUrl"),
    }
    for kind, url in singles.items():
        if url:
            rows.append({"kind": kind, "url": url})
    for kind, key in (("banner", "bannerImages"), ("gallery", "images"), ("gallery", "gallery")):
        for url in college.get(key) or []:
            if isinstance(url, str) and url:
                rows.append({"kind": kind, "url": url})
            elif isinstance(url, dict):
                rows.append({"kind": kind, "url": join_values(url)})
    seen = set()
    unique = []
    for row in rows:
        marker = (row["kind"], row["url"])
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(row)
    return attach(college, unique)


def facility_row(college: dict) -> dict | None:
    facilities = college.get("facilities") or {}
    if not isinstance(facilities, dict) or not facilities:
        return None
    row = identity(college)
    row.update(
        {
            "library": yes_no(facilities.get("hasLibrary")),
            "wifi": yes_no(facilities.get("hasWifi")),
            "sports": yes_no(facilities.get("hasSports")),
            "canteen": yes_no(facilities.get("hasCanteen")),
            "gym": yes_no(facilities.get("hasGym")),
            "medical": yes_no(facilities.get("hasMedical")),
            "transport": yes_no(facilities.get("hasTransport")),
            "transport_details": clean_cell(facilities.get("transportDetails") or ""),
            "nearest_hospital": facilities.get("nearestHospital") or "",
            "other_facilities": join_values(facilities.get("otherFacilities")),
        }
    )
    return row


def campus_row(college: dict) -> dict | None:
    culture = college.get("culture") or {}
    if not isinstance(culture, dict) or not culture:
        return None
    row = identity(college)
    row.update(
        {
            "campus_size": college.get("campusSize") or "",
            "clubs_count": blank_if_empty(culture.get("clubsCount")),
            "club_categories": join_values(culture.get("clubCategories")),
            "annual_fests": join_values(culture.get("annualFests")),
            "has_competitions": yes_no(culture.get("hasCompetitions")),
            "competition_details": clean_cell(culture.get("competitionDetails") or ""),
            "has_hackathons": yes_no(culture.get("hasHackathons")),
            "hackathon_details": clean_cell(culture.get("hackathonDetails") or ""),
            "has_research": yes_no(culture.get("hasResearch")),
            "research_details": clean_cell(culture.get("researchDetails") or ""),
        }
    )
    return row


def college_row(college: dict) -> dict:
    placement = college.get("placement") or {}
    ranking = college.get("ranking") or {}
    hostel = college.get("hostel") or {}
    seo = college.get("seoContent") or {}
    if not isinstance(placement, dict):
        placement = {}
    if not isinstance(ranking, dict):
        ranking = {}
    if not isinstance(hostel, dict):
        hostel = {}
    if not isinstance(seo, dict):
        seo = {}

    hostel_flag = college.get("isHostel")
    if hostel_flag is None:
        hostel_flag = hostel.get("isAvailable")

    placement_rate = placement.get("placementRate")
    if placement_rate in (None, ""):
        placement_rate = college.get("Placements")

    row = identity(college)
    row.update(
        {
            "page_url": f"{BASE}/colleges/{college.get('slug')}",
            "established": blank_if_empty(college.get("established")),
            "college_type": plain(college.get("type") or college.get("collegeType") or ""),
            "address": college.get("address") or "",
            "country": college.get("country") or "",
            "website": college.get("website") or "",
            "email": college.get("email") or "",
            "phone": college.get("phone") or "",
            "video_url": college.get("videoUrl") or "",
            "headline": clean_cell(college.get("college_headLine") or ""),
            "verified": yes_no(college.get("isVerifed")),
            "top_college": yes_no(college.get("isTopCollege")),
            "our_rating": blank_if_empty(college.get("ourRating")),
            "platform_rank": plain(blank_zero(college.get("topCollegeRank"))),
            "placement_rate_percent": blank_if_empty(placement_rate),
            "average_package_lpa": blank_if_empty(placement.get("averagePackage")),
            "highest_package_lpa": blank_if_empty(placement.get("highestPackage")),
            "median_package_lpa": blank_if_empty(placement.get("medianPackage")),
            "internship_rate": blank_if_empty(placement.get("internshipRate")),
            "top_recruiters": join_values(placement.get("topRecruiters")),
            "recruiters": join_values(placement.get("recruiters")),
            "internship_companies": join_values(placement.get("internshipCompanies")),
            "year_wise_placements": join_values(placement.get("yearWisePlacements")),
            "nirf_rank": blank_zero(ranking.get("nirfRank")),
            "nirf_year": blank_if_empty(ranking.get("nirfYear")),
            "nirf_category": ranking.get("nirfCategory") or "",
            "naac_grade": plain(ranking.get("naacGrade") or college.get("naacGrade") or ""),
            "naac_score": blank_if_empty(ranking.get("naacScore")),
            "naac_year": blank_if_empty(ranking.get("naacYear")),
            "qs_rank": plain(blank_zero(ranking.get("qsRank"))),
            "qs_year": blank_if_empty(ranking.get("qsYear")),
            "aicte_approved": yes_no(ranking.get("aicteApproved")),
            "ugc_recognized": yes_no(ranking.get("ugcRecognized")),
            "govt_approvals": join_values(ranking.get("govtApprovals")),
            "nba_programs": join_values(ranking.get("nbaPrograms")),
            "other_rankings": join_values(ranking.get("otherRankings")),
            "recognition": join_values(college.get("recognition")),
            "hostel_available": yes_no(hostel_flag),
            "hostel_cost_per_year": blank_if_empty(hostel.get("hostelCostYear")),
            "mess_cost_per_year": blank_if_empty(hostel.get("messCostYear")),
            "hostel_room_types": join_values(hostel.get("roomTypes")),
            "hostel_amenities": join_values(hostel.get("amenities")),
            "food_quality": plain(hostel.get("foodQuality") or ""),
            "campus_size": college.get("campusSize") or "",
            "course_count": len(college.get("courses") or []),
            "top_course": college.get("topCource") or "",
            "highlights": join_values(college.get("highlights")),
            "overview": about_text(college),
            "meta_title": clean_cell(seo.get("metaTitle") or ""),
            "meta_description": clean_cell(seo.get("metaDescription") or ""),
            "pros": join_values(seo.get("pros")),
            "cons": join_values(seo.get("cons")),
            "who_should_join": clean_cell(seo.get("whoShouldJoin") or ""),
            "who_should_avoid": clean_cell(seo.get("whoShouldAvoid") or ""),
            "updated_at": college.get("updatedAt") or "",
        }
    )
    return row


def generic_rows(college: dict, value) -> list[dict]:
    return attach(college, [flatten_record(record) for record in records_from(value)])


def build_tables(colleges: list[dict]) -> dict[str, pd.DataFrame]:
    college_rows = []
    streams = []
    courses = []
    sections = []
    facilities = []
    campus = []
    images = []
    admissions = []
    fee_structures = []
    scholarships = []
    cutoffs = []
    faqs = []

    for college in colleges:
        college_rows.append(college_row(college))
        streams.extend(stream_rows(college))
        courses.extend(course_rows(college))
        sections.extend(section_rows(college))
        facility = facility_row(college)
        if facility:
            facilities.append(facility)
        life = campus_row(college)
        if life:
            campus.append(life)
        images.extend(image_rows(college))
        admissions.extend(generic_rows(college, college.get("admission")))
        fee_structures.extend(generic_rows(college, college.get("feeStructure")))
        scholarships.extend(generic_rows(college, college.get("scholarships")))
        cutoffs.extend(generic_rows(college, college.get("cutoffs")))
        faqs.extend(generic_rows(college, college.get("faqs")))

    tables = {
        "Colleges": frame(college_rows, IDENTITY),
        "Streams": frame(streams, IDENTITY + ["stream"]),
        "Courses": frame(courses, IDENTITY + ["course_name"]),
        "Sections": frame(sections, IDENTITY + ["heading", "content"]),
        "Facilities": frame(facilities, IDENTITY),
        "Campus Life": frame(campus, IDENTITY),
        "Images": frame(images, IDENTITY + ["kind", "url"]),
        "Admissions": frame(admissions, IDENTITY),
        "Fee Structure": frame(fee_structures, IDENTITY),
        "Scholarships": frame(scholarships, IDENTITY),
        "Cutoffs": frame(cutoffs, IDENTITY),
        "FAQs": frame(faqs, IDENTITY),
    }
    tables["Colleges"] = tables["Colleges"].sort_values(["college_name", "city"], kind="stable")
    if not tables["Streams"].empty:
        tables["Streams"] = tables["Streams"].sort_values(["stream", "college_name"], kind="stable")
    if not tables["Courses"].empty:
        tables["Courses"] = tables["Courses"].sort_values(["college_name", "course_name"], kind="stable")
    return tables


def frame(rows: list[dict], leading: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=leading)
    table = pd.DataFrame(rows).map(lambda value: clean_cell(plain(value)))
    front = [column for column in leading if column in table.columns]
    rest = [column for column in table.columns if column not in front]
    return table[front + rest]


def write_workbook(tables: dict[str, pd.DataFrame]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        for name, table in tables.items():
            table.to_excel(writer, sheet_name=name, index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            if sheet.dimensions:
                sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = 24


def fetch_json(session: requests.Session, url: str) -> dict:
    last_error = "unknown error"
    for attempt in range(4):
        try:
            response = session.get(url, timeout=40)
            if response.status_code == 429 or response.status_code >= 500:
                last_error = f"HTTP {response.status_code}"
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and payload.get("success") is False:
                raise RuntimeError(payload.get("error") or "The site returned success=false")
            if not isinstance(payload, dict):
                raise RuntimeError("The site did not return a JSON object")
            return payload
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = str(exc)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(last_error)


def load_index(session: requests.Session) -> list[dict]:
    payload = fetch_json(session, INDEX_URL)
    colleges = payload.get("data") or []
    if not isinstance(colleges, list):
        raise RuntimeError("College index did not contain a list")
    cleaned = [college for college in colleges if isinstance(college, dict) and college.get("slug")]
    cleaned.sort(key=lambda college: (college.get("name") or "").lower())
    return cleaned


def raw_path(slug: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', "_", slug)
    return RAW_DIR / f"{safe}.json"


def load_college(session: requests.Session, slug: str, refresh: bool) -> dict:
    path = raw_path(slug)
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))

    payload = fetch_json(session, DETAIL_URL.format(slug=slug))
    college = payload.get("data")
    if not isinstance(college, dict):
        raise RuntimeError("College detail did not contain a record")
    path.write_text(json.dumps(college, ensure_ascii=False), encoding="utf-8")
    time.sleep(max(session.delay, 0))
    return college


def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "AdmissionSetuCollegeExport/1.0",
            "Accept": "application/json",
        }
    )
    session.delay = args.delay

    index = load_index(session)
    if args.limit > 0:
        index = index[: args.limit]
    print(f"Colleges in this run: {len(index)}", flush=True)

    colleges = []
    failures = []
    for number, item in enumerate(index, start=1):
        slug = item["slug"]
        name = item.get("name") or slug
        try:
            college = load_college(session, slug, args.refresh)
            colleges.append(college)
            print(f"[{number}/{len(index)}] {name}", flush=True)
        except Exception as exc:
            failures.append(f"{slug}\t{exc}")
            print(f"[{number}/{len(index)}] FAILED {name}: {exc}", flush=True)

    if not colleges:
        raise SystemExit("No college records were saved. Nothing was written to Excel.")

    tables = build_tables(colleges)
    write_workbook(tables)
    FAILURES_PATH.write_text("\n".join(failures), encoding="utf-8")

    print(f"\nWorkbook: {OUTPUT_PATH}", flush=True)
    for name, table in tables.items():
        print(f"  {name}: {len(table)} rows", flush=True)
    if failures:
        print(f"Failed colleges: {len(failures)}. See {FAILURES_PATH}", flush=True)
    else:
        print("Failed colleges: 0", flush=True)


if __name__ == "__main__":
    main()
