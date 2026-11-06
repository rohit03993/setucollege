"""Load saved colleges and the official cutoff files into PostgreSQL.

The database and tables must already exist (db/schema.sql).
The connection string is read from db/.env, then from DATABASE_URL.
From the project folder:

    python db\\import_data.py

Running it again updates the same colleges and seats. It does not duplicate them.
"""

import csv
import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Json

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path(__file__).resolve().parent / ".env"
COLLEGEFORME = ROOT / "college-for-me" / "data" / "collegeforme" / "raw"
COLLEGEDEKHO = ROOT / "college-dekho" / "data" / "colleges"
JOSAA = ROOT / "prediction" / "josaa-2026-round-5-orcr.csv"
MCC = ROOT / "prediction" / "mcc-2026-final-orcr.csv"

EXAM_NAMES = ("JEE Advanced", "JEE Main", "NEET", "CUET", "GATE", "CAT", "MAT", "NMAT")

COLLEGE_SQL = """
INSERT INTO colleges (
    source, source_slug, name, city, state, ownership, streams, exams,
    established, website, phone, overview, fee_per_year, fee_label,
    avg_package_lpa, highest_package_lpa, median_package_lpa,
    nirf_rank, nirf_year, nirf_category, hostel, profile
) VALUES (
    %(source)s, %(source_slug)s, %(name)s, %(city)s, %(state)s, %(ownership)s,
    %(streams)s, %(exams)s, %(established)s, %(website)s, %(phone)s, %(overview)s,
    %(fee_per_year)s, %(fee_label)s, %(avg_package_lpa)s, %(highest_package_lpa)s,
    %(median_package_lpa)s, %(nirf_rank)s, %(nirf_year)s, %(nirf_category)s,
    %(hostel)s, %(profile)s
)
ON CONFLICT (source, source_slug) DO UPDATE SET
    name = EXCLUDED.name,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    ownership = EXCLUDED.ownership,
    streams = EXCLUDED.streams,
    exams = EXCLUDED.exams,
    established = EXCLUDED.established,
    website = EXCLUDED.website,
    phone = EXCLUDED.phone,
    overview = EXCLUDED.overview,
    fee_per_year = EXCLUDED.fee_per_year,
    fee_label = EXCLUDED.fee_label,
    avg_package_lpa = EXCLUDED.avg_package_lpa,
    highest_package_lpa = EXCLUDED.highest_package_lpa,
    median_package_lpa = EXCLUDED.median_package_lpa,
    nirf_rank = EXCLUDED.nirf_rank,
    nirf_year = EXCLUDED.nirf_year,
    nirf_category = EXCLUDED.nirf_category,
    hostel = EXCLUDED.hostel,
    profile = EXCLUDED.profile
"""


def text(value):
    if value is None:
        return ""
    return str(value).strip()


def whole(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def money(value):
    if value is None or value == "":
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def package_lpa(value):
    """Package columns are LPA. A figure of 10000 or more is rupees."""
    number = money(value)
    if number is None:
        return None
    if number >= 10000:
        number = round(number / 100000, 2)
    if number >= 1000000:
        return None
    return number


def words(value):
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def exams_in(value):
    blob = value if isinstance(value, str) else " ".join(words(value))
    return [name for name in EXAM_NAMES if name.lower() in blob.lower()]


def blank_college(source, slug, name):
    return {
        "source": source,
        "source_slug": slug,
        "name": name,
        "city": "",
        "state": "",
        "ownership": "",
        "streams": [],
        "exams": [],
        "established": None,
        "website": "",
        "phone": "",
        "overview": "",
        "fee_per_year": None,
        "fee_label": "",
        "avg_package_lpa": None,
        "highest_package_lpa": None,
        "median_package_lpa": None,
        "nirf_rank": None,
        "nirf_year": None,
        "nirf_category": "",
        "hostel": None,
        "profile": Json({}),
    }


def from_collegeforme(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = text(data.get("slug")) or path.stem
    name = text(data.get("name"))
    if not name:
        return None, []
    fees = data.get("feeStructure") if isinstance(data.get("feeStructure"), dict) else {}
    placement = data.get("placement") if isinstance(data.get("placement"), dict) else {}
    ranking = data.get("ranking") if isinstance(data.get("ranking"), dict) else {}
    admission = data.get("admission") if isinstance(data.get("admission"), dict) else {}
    hostel = data.get("hostel") if isinstance(data.get("hostel"), dict) else {}
    seo = data.get("seoContent") if isinstance(data.get("seoContent"), dict) else {}
    row = blank_college("collegeforme", slug, name)
    row.update(
        {
            "city": text(data.get("city")),
            "state": text(data.get("state")),
            "ownership": text(data.get("type")),
            "streams": words(data.get("streamTags")),
            "exams": exams_in(admission.get("entranceExams")),
            "established": whole(data.get("established")),
            "website": text(data.get("website")),
            "phone": text(data.get("phone")),
            "overview": text(seo.get("intro")) or text(data.get("college_headLine")),
            "fee_per_year": whole(fees.get("tuitionFeePerYear")),
            "fee_label": text(fees.get("tuitionFeeNote")),
            "avg_package_lpa": package_lpa(placement.get("averagePackage")),
            "highest_package_lpa": package_lpa(placement.get("highestPackage")),
            "median_package_lpa": package_lpa(placement.get("medianPackage")),
            "nirf_rank": whole(ranking.get("nirfRank")),
            "nirf_year": whole(ranking.get("nirfYear")),
            "nirf_category": text(ranking.get("nirfCategory")),
            "hostel": hostel.get("isAvailable") if isinstance(hostel.get("isAvailable"), bool) else data.get("isHostel"),
            "profile": Json(data),
        }
    )
    courses = []
    for course in data.get("courses") or []:
        if not isinstance(course, dict) or not text(course.get("name")):
            continue
        years = whole(course.get("durationYears"))
        eligibility = course.get("eligblityCateria")
        if isinstance(eligibility, list):
            eligibility = "; ".join(text(item) for item in eligibility if text(item))
        courses.append(
            {
                "slug": slug,
                "name": text(course.get("name")),
                "level": text(course.get("level")),
                "duration": f"{years} years" if years else "",
                "fee_amount": whole(course.get("fees_college")),
                "eligibility": text(eligibility),
            }
        )
    return row, courses


def from_collegedekho(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    slug = text(data.get("slug")) or path.parent.name
    name = text(data.get("college_name"))
    if not name:
        return None
    row = blank_college("collegedekho", slug, name)
    row.update(
        {
            "city": text(data.get("city")),
            "state": text(data.get("state")),
            "ownership": text(data.get("ownership")),
            "streams": ["Engineering"],
            "exams": exams_in(text(data.get("exams")) + " " + text(data.get("more_exams"))),
            "website": text(data.get("profile_url")),
            "fee_label": text(data.get("fee_range")),
            "nirf_rank": whole(data.get("nirf_rank")),
            "profile": Json(data),
        }
    )
    return row


def load_colleges(connection):
    # College For Me stays out until the college page is ready for the detailed records.
    rows = []
    if COLLEGEDEKHO.exists():
        for path in sorted(COLLEGEDEKHO.glob("*/card.json")):
            row = from_collegedekho(path)
            if row:
                rows.append(row)
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM colleges WHERE source = 'collegeforme'")
        removed = cursor.rowcount
        cursor.executemany(COLLEGE_SQL, rows)
    return len(rows), removed


def seat_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            yield (
                int(row["Year"]),
                row["Round"].strip(),
                row["Exam"].strip(),
                row["Institute"].strip(),
                row["State"].strip(),
                row["Academic Program Name"].strip(),
                row["Quota"].strip(),
                row["Seat Type"].strip(),
                row["Gender"].strip(),
                int(row["Opening Rank"]),
                int(row["Closing Rank"]),
                row["Preparatory"].strip().lower() == "yes",
            )


def load_seats(connection, path):
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS seat_stage")
        cursor.execute(
            """
            CREATE TEMP TABLE seat_stage (
                year integer,
                round text,
                exam text,
                institute text,
                state text,
                program text,
                quota text,
                category text,
                gender text,
                opening_rank integer,
                closing_rank integer,
                preparatory boolean
            ) ON COMMIT DROP
            """
        )
        with cursor.copy(
            """
            COPY seat_stage (
                year, round, exam, institute, state, program, quota, category,
                gender, opening_rank, closing_rank, preparatory
            ) FROM STDIN
            """
        ) as copy:
            for row in seat_rows(path):
                copy.write_row(row)
        cursor.execute(
            """
            INSERT INTO seats (
                year, round, exam, institute, state, program, quota, category,
                gender, opening_rank, closing_rank, preparatory
            )
            SELECT DISTINCT ON (year, round, exam, institute, program, quota, category, gender)
                year, round, exam, institute, state, program, quota, category,
                gender, opening_rank, closing_rank, preparatory
            FROM seat_stage
            ORDER BY year, round, exam, institute, program, quota, category, gender
            ON CONFLICT (year, round, exam, institute, program, quota, category, gender)
            DO UPDATE SET
                state = EXCLUDED.state,
                opening_rank = EXCLUDED.opening_rank,
                closing_rank = EXCLUDED.closing_rank,
                preparatory = EXCLUDED.preparatory
            """
        )
        return cursor.rowcount


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def main():
    load_env(ENV_FILE)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit(f"Add DATABASE_URL to {ENV_FILE}")
    missing = [str(path) for path in (JOSAA, MCC) if not path.exists()]
    if missing:
        raise SystemExit("Missing cutoff file:\n" + "\n".join(missing))

    with psycopg.connect(url) as connection:
        colleges, removed = load_colleges(connection)
        josaa = load_seats(connection, JOSAA)
        mcc = load_seats(connection, MCC)
        connection.commit()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT source, count(*) FROM colleges GROUP BY source ORDER BY source"
            )
            by_source = cursor.fetchall()
            cursor.execute("SELECT exam, count(*) FROM seats GROUP BY exam ORDER BY exam")
            by_exam = cursor.fetchall()

    print(f"Upserted {colleges} colleges. Removed {removed} College For Me colleges.")
    print(f"Upserted {josaa} JoSAA seats and {mcc} MCC seats.")
    print("Colleges in the database:")
    for source, count in by_source:
        print(f"  {source}: {count}")
    print("Seats in the database:")
    for exam, count in by_exam:
        print(f"  {exam}: {count}")


if __name__ == "__main__":
    main()
