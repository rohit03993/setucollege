"""Admission Setu API.

College list, one college, and the rank predictor.
The predictor uses prediction/match.py against the seats table.

From the project folder:

    python -m pip install -r api\\requirements.txt
    python -m uvicorn main:app --app-dir api --host 127.0.0.1 --port 8000
"""

import os
import re
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

from dekho_pages import card_facts, college_media, saved_pages  # noqa: E402
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


_overrides_ready = False


def overrides_ready():
    global _overrides_ready
    if _overrides_ready:
        return True
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'college_overrides'
                """
            )
            _overrides_ready = cursor.fetchone() is not None
    return _overrides_ready


def fetch_overrides(slugs):
    if not slugs or not overrides_ready():
        return {}
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM college_overrides WHERE source_slug = ANY(%(slugs)s)",
                {"slugs": list(slugs)},
            )
            return {row["source_slug"]: row for row in cursor.fetchall()}


def page_content(override):
    content = override.get("content") or {}
    if isinstance(content, str):
        import json

        content = json.loads(content or "{}")
    return content if isinstance(content, dict) else {}


def apply_override(college, override, include_page=False):
    college["edited"] = False
    college["hidden"] = False
    college["managed"] = False
    if not override:
        return college
    college["name"] = override["name"] or college["name"]
    college["city"] = override["city"] or ""
    college["state"] = override["state"] or ""
    college["ownership"] = override["ownership"] or ""
    college["overview"] = override["overview"] or ""
    college["fee_label"] = override["fee_label"] or ""
    college["website"] = override["website"] or ""
    college["phone"] = override["phone"] or ""
    college["established_year"] = override["established_year"] or ""
    college["average_package"] = override["average_package"] or ""
    college["highest_package"] = override["highest_package"] or ""
    college["rating"] = override["rating"] or ""
    college["reviews"] = override["reviews"] or ""
    college["image"] = override["image"] or ""
    college["logo"] = override["logo"] or ""
    college["nirf_rank"] = override["nirf_rank"] or ""
    college["nirf_overall"] = ""
    college["nirf_year"] = ""
    college["streams"] = list(override["streams"] or [])
    college["edited"] = True
    college["hidden"] = bool(override["hidden"])
    content = page_content(override)
    if content.get("managed"):
        college["managed"] = True
        college["video_id"] = content.get("video_id") or ""
        college["recruiters"] = content.get("recruiters") or ""
        college["exams"] = content.get("exams") or []
        if content.get("course_count"):
            college["course_count"] = content["course_count"]
        if include_page:
            pages = college.setdefault("pages", {})
            pages["course_groups"] = content.get("course_groups") or []
            pages["courses"] = {"sections": []}
            pages["faqs"] = content.get("answers") or []
            pages["admission"] = {"sections": content.get("admission") or []}
            pages["cutoff"] = {"tables": content.get("cutoff") or []}
            pages["placement"] = {"tables": content.get("placements") or [], "sections": []}
    return college


def lpa_text(value):
    if not value:
        return ""
    amount = float(value)
    if amount <= 0:
        return ""
    if amount >= 100:
        crore = f"{amount / 100:.2f}".rstrip("0").rstrip(".")
        return f"₹{crore} Cr"
    text = f"{amount:.2f}".rstrip("0").rstrip(".")
    return f"₹{text} LPA"


def attach_card(item):
    has_package = bool(str(item.get("highest_package") or "").strip())
    if item.get("logo") and has_package and item.get("nirf_rank"):
        return
    logo, highest, nirf = card_facts(item["slug"])
    if not item.get("logo"):
        item["logo"] = logo
    if not has_package:
        item["highest_package"] = highest or lpa_text(item.get("highest_package_lpa"))
    if not item.get("nirf_rank") and nirf:
        item["nirf_rank"] = nirf


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
    search = "name ILIKE %(like)s OR city ILIKE %(like)s OR state ILIKE %(like)s"
    hidden = ""
    if overrides_ready():
        search += """
            OR EXISTS (
                SELECT 1 FROM college_overrides AS edited
                WHERE edited.source_slug = colleges.source_slug
                  AND (edited.name ILIKE %(like)s OR edited.city ILIKE %(like)s OR edited.state ILIKE %(like)s)
            )
        """
        hidden = """
          AND NOT EXISTS (
                SELECT 1 FROM college_overrides AS edited
                WHERE edited.source_slug = colleges.source_slug AND edited.hidden
              )
        """
    where = f"""
        WHERE (%(q)s = '' OR {search})
          AND (%(stream)s = '' OR EXISTS (
                SELECT 1 FROM unnest(streams) AS stream_name
                WHERE lower(stream_name) = lower(%(stream)s)
              ))
          {hidden}
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
    colleges = [college_out(row) for row in rows]
    found = fetch_overrides([item["slug"] for item in colleges])
    for item in colleges:
        apply_override(item, found.get(item["slug"]))
        attach_card(item)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "stream_counts": stream_counts,
        "colleges": colleges,
    }


def load_college(slug, include_hidden=False):
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
                return None
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
    override = fetch_overrides([slug]).get(slug)
    if override and override["hidden"] and not include_hidden:
        return None
    return apply_override(college, override, include_page=True)


@app.get("/colleges/{slug}")
def college_page(slug: str):
    college = load_college(slug)
    if college is None:
        raise HTTPException(status_code=404, detail="College not found.")
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


_college_names = None


def college_names():
    global _college_names
    if _college_names is not None:
        return _college_names
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT source_slug, name FROM colleges")
            rows = cursor.fetchall()
    _college_names = {re.sub(r"[^a-z0-9]+", " ", row["name"].lower()).strip(): row["source_slug"] for row in rows}
    return _college_names


_PLACES = {"tiruchirappalli": "trichy", "uttarakhand": "garwhal"}
_SPECIAL = (
    ("motilal nehru national institute of technology", "mnnit allahabad"),
    ("maulana azad national institute of technology", "manit bhopal"),
    ("sardar vallabhbhai national institute of technology", "svnit surat"),
    ("visvesvaraya national institute of technology", "vnit nagpur"),
    ("malaviya national institute of technology", "malaviya national institute of technology"),
    ("atal bihari vajpayee indian institute of information technology", "iiitm gwalior"),
    ("pt dwarka prasad mishra indian institute of information technology", "iiitdm jabalpur"),
    ("indian institute of information technology design manufacturing kurnool", "iiitdm kurnool"),
    ("indian institute of information technology design manufacturing kancheepuram", "iiitdm kancheepuram"),
    ("indian institute of information technology iiit kilohrad", "iiit sonepat"),
    ("birla institute of technology mesra", "bit mesra"),
    ("punjab engineering college", "pec chandigarh"),
    ("indian institute of engineering science and technology", "iiest shibpur"),
)


def slug_for_institute(institute):
    text = re.sub(r"[^a-z0-9]+", " ", institute.lower()).strip()
    keys = [text]
    for prefix, key in _SPECIAL:
        if text.startswith(prefix):
            keys.append(key)
    for label, short in (
        (r"indian institute of technology (.+)$", "iit"),
        (r"national institute of technology (.+)$", "nit"),
        (r"indian institute of information technology (.+)$", "iiit"),
    ):
        found = re.search(label, text)
        if not found:
            continue
        rest = found.group(1).strip()
        words = rest.split()
        place = words[1:] if words and words[0] in {"iit", "iiit", "nit"} else words
        keys.append(f"{short} {rest}")
        keys.append(f"{short} {words[-1]}")
        keys.append(f"{short} {words[0]}")
        if place:
            keys.append(f"{short} {place[0]}")
            if len(place) >= 2:
                keys.append(f"{short} {' '.join(place[:2])}")
        for word in (words[-1], words[0], place[0] if place else ""):
            if word in _PLACES:
                keys.append(f"{short} {_PLACES[word]}")
    names = college_names()
    for key in keys:
        if key in names:
            return names[key]
    best = ""
    best_slug = ""
    for name, slug in names.items():
        if len(name) >= 20 and text.startswith(name) and len(name) > len(best):
            best, best_slug = name, slug
    return best_slug


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
    page_rows = rows[start : start + body.page_size]
    for row in page_rows:
        row["slug"] = slug_for_institute(row["college"])
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
        "results": page_rows,
    }


from admin import router as admin_router  # noqa: E402

app.include_router(admin_router)
app.mount("/assets", StaticFiles(directory=WEB), name="assets")
