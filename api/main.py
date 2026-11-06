"""Admission Setu API.

College list, one college, and the rank predictor.
The predictor uses prediction/match.py against the seats table.

From the project folder:

    python -m pip install -r api\\requirements.txt
    python -m uvicorn main:app --app-dir api --host 127.0.0.1 --port 8000
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "prediction"))

from dekho_pages import college_media, saved_pages  # noqa: E402
from institutes import HOME_STATES  # noqa: E402
from match import predict  # noqa: E402
from predict import CATEGORIES  # noqa: E402

ENV_FILE = ROOT / "db" / ".env"
EXAMS = ("JEE Main", "JEE Advanced", "NEET")
NEET_COURSES = {"mbbs": "MBBS", "bds": "BDS", "b.sc nursing": "B.Sc Nursing"}
SORTS = {
    "name": "lower(name)",
    "nirf": "nirf_rank NULLS LAST, lower(name)",
    "fee": "fee_per_year NULLS LAST, lower(name)",
}
COLLEGE_FIELDS = """
    source_slug, name, city, state, ownership, streams, exams,
    established, website, phone, overview, fee_per_year, fee_label,
    avg_package_lpa, highest_package_lpa, median_package_lpa,
    nirf_rank, nirf_year, nirf_category, hostel
"""
STATES = {name.lower(): name for name in HOME_STATES}


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def number(value):
    if value is None:
        return None
    return float(value)


def college_out(row):
    return {
        "slug": row["source_slug"],
        "name": row["name"],
        "city": row["city"],
        "state": row["state"],
        "ownership": row["ownership"],
        "streams": row["streams"],
        "exams": row["exams"],
        "established": row["established"],
        "website": row["website"],
        "phone": row["phone"],
        "overview": row["overview"],
        "fee_per_year": row["fee_per_year"],
        "fee_label": row["fee_label"],
        "avg_package_lpa": number(row["avg_package_lpa"]),
        "highest_package_lpa": number(row["highest_package_lpa"]),
        "median_package_lpa": number(row["median_package_lpa"]),
        "nirf_rank": row["nirf_rank"],
        "nirf_year": row["nirf_year"],
        "nirf_category": row["nirf_category"],
        "hostel": row["hostel"],
    }


load_env(ENV_FILE)
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise SystemExit(f"Add DATABASE_URL to {ENV_FILE}")

pool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    open=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="Admission Setu", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def connection():
    return pool.connection()


def site_page(name: str):
    return FileResponse(WEB / name)


@app.get("/", include_in_schema=False)
def home_page():
    return site_page("index.html")


@app.get("/browse", include_in_schema=False)
def browse_page():
    return site_page("browse.html")


@app.get("/college/{slug}", include_in_schema=False)
def college_site(slug: str):
    return site_page("college.html")


@app.get("/chances", include_in_schema=False)
def chances_page():
    return site_page("chances.html")


@app.get("/colleges")
def list_colleges(
    q: str = "",
    stream: str = "",
    sort: str = "name",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    order = SORTS.get(sort)
    if order is None:
        raise HTTPException(status_code=400, detail="Sort must be name, nirf, or fee.")
    query = q.strip()
    where = """
        WHERE (%(q)s = '' OR name ILIKE %(like)s OR city ILIKE %(like)s OR state ILIKE %(like)s)
          AND (%(stream)s = '' OR EXISTS (
                SELECT 1 FROM unnest(streams) AS stream_name
                WHERE lower(stream_name) = lower(%(stream)s)
              ))
    """
    params = {
        "q": query,
        "like": f"%{query}%",
        "stream": stream.strip(),
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {COLLEGE_FIELDS}, count(*) OVER() AS total
                FROM colleges
                {where}
                ORDER BY {order}
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                params,
            )
            rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT stream_name, count(*) AS total
                FROM colleges, unnest(streams) AS stream_name
                GROUP BY stream_name
                ORDER BY stream_name
                """
            )
            stream_counts = {row["stream_name"]: row["total"] for row in cursor.fetchall()}
    total = rows[0]["total"] if rows else 0
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "stream_counts": stream_counts,
        "colleges": [college_out(row) for row in rows],
    }


@app.get("/colleges/{slug}")
def college_page(slug: str):
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, profile, {COLLEGE_FIELDS}
                FROM colleges
                WHERE source_slug = %(slug)s
                ORDER BY source
                LIMIT 1
                """,
                {"slug": slug},
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="College not found.")
    college = college_out(row)
    profile = row["profile"] if isinstance(row["profile"], dict) else {}
    college["approval"] = profile.get("approval") or ""
    college["rating"] = profile.get("rating") or ""
    college["course_count"] = profile.get("course_count_on_card") or ""
    media = college_media(slug, college["name"])
    pages = saved_pages(slug)
    highlight = pages.get("highlight") or {}
    college["logo"] = highlight.get("logo") or ""
    college["image"] = highlight.get("image") or media["image"]
    college["video_id"] = media["video_id"]
    college["overview"] = highlight.get("overview") or ""
    college["established_year"] = highlight.get("established_year") or ""
    college["reviews"] = highlight.get("reviews") or ""
    college["nirf_overall"] = highlight.get("nirf_overall") or ""
    if highlight.get("rating"):
        college["rating"] = highlight["rating"]
    if highlight.get("ownership"):
        college["ownership"] = highlight["ownership"]
    listed_package = str(profile.get("average_package") or "").strip()
    college["average_package"] = listed_package or highlight.get("average_package") or media["average_package"]
    college["highest_package"] = highlight.get("highest_package") or media["highest_package"]
    if not college["nirf_rank"]:
        college["nirf_rank"] = highlight.get("nirf_engineering") or media["nirf_rank"] or ""
        college["nirf_year"] = media["nirf_year"]
    college["pages"] = pages
    return college


class PredictIn(BaseModel):
    rank: int = Field(ge=1)
    category: str
    gender: str
    home_state: str
    exam: str
    course: str = ""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


@app.get("/predict/options")
def predict_options():
    return {
        "exams": list(EXAMS),
        "categories": ["OPEN", "EWS", "OBC-NCL", "SC", "ST"],
        "genders": ["male", "female"],
        "states": list(HOME_STATES),
        "neet_courses": ["MBBS", "BDS", "B.Sc Nursing"],
    }


@app.post("/predict")
def predict_colleges(body: PredictIn):
    if body.exam not in EXAMS:
        raise HTTPException(status_code=400, detail="Exam must be JEE Main, JEE Advanced, or NEET.")
    if body.gender not in ("male", "female"):
        raise HTTPException(status_code=400, detail="Gender must be male or female.")
    category = CATEGORIES.get(body.category.strip().upper())
    if category is None:
        raise HTTPException(status_code=400, detail="Category must be OPEN, EWS, OBC-NCL, SC, or ST.")
    home_state = STATES.get(body.home_state.strip().lower())
    if home_state is None:
        raise HTTPException(status_code=400, detail="Home state is not in the state list.")
    course = ""
    if body.exam == "NEET":
        course = NEET_COURSES.get(body.course.strip().lower())
        if course is None:
            raise HTTPException(status_code=400, detail="NEET needs a course: MBBS, BDS, or B.Sc Nursing.")

    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT institute, state, program, quota, category, gender, closing_rank, exam
                FROM seats
                WHERE exam = %(exam)s AND category = %(category)s AND preparatory = false
                """,
                {"exam": body.exam, "category": category},
            )
            seat_rows = cursor.fetchall()

    seats = [
        {
            "college": row["institute"],
            "college_state": row["state"],
            "branch": row["program"],
            "quota": row["quota"],
            "category": row["category"],
            "gender": row["gender"],
            "closing_rank": row["closing_rank"],
            "course": row["program"] if body.exam == "NEET" else "",
            "exam": row["exam"],
            "preparatory": "No",
        }
        for row in seat_rows
    ]
    rows = predict(
        {
            "rank": body.rank,
            "category": category,
            "gender": body.gender,
            "home_state": home_state,
            "exam": body.exam,
            "course": course,
        },
        seats,
    )
    counts = {"safer": 0, "possible": 0, "unlikely": 0}
    for row in rows:
        counts[row["chance"]] += 1
    start = (body.page - 1) * body.page_size
    return {
        "exam": body.exam,
        "rank": body.rank,
        "category": category,
        "gender": body.gender,
        "home_state": home_state,
        "course": course,
        "total": len(rows),
        "counts": counts,
        "page": body.page,
        "page_size": body.page_size,
        "results": rows[start : start + body.page_size],
    }


app.mount("/assets", StaticFiles(directory=WEB), name="assets")
