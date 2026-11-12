"""Admission Setu API.

College list, one college, and the rank predictor.
The predictor uses prediction/match.py against the seats table.

From the project folder:

    python -m pip install -r api\\requirements.txt
    python -m uvicorn main:app --app-dir api --host 127.0.0.1 --port 8000
"""

import hashlib
import hmac
import os
import re
import secrets
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "prediction"))

from dekho_pages import card_facts, college_media, saved_pages  # noqa: E402
from institutes import HOME_STATES  # noqa: E402
from match import family_counts, predict, shortlist  # noqa: E402
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
        "rating": str(row.get("card_rating") or "").strip(),
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
                SELECT {COLLEGE_FIELDS}, profile->>'rating' AS card_rating, count(*) OVER() AS total
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
    branch: str = ""
    student_id: str = ""
    record: bool = False
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class StudentIn(BaseModel):
    name: str
    mobile: str
    consent: bool = False


CONSENT_TEXT = (
    "I agree that Admission Setu can save my name and mobile number "
    "to show this result in my name and keep this prediction. "
    "I can withdraw this on the result page."
)


def clean_name(value):
    name = " ".join(str(value or "").split())
    if len(name) < 2 or len(name) > 80 or not re.search(r"[A-Za-z]", name):
        raise HTTPException(status_code=400, detail="Enter your name.")
    return name


def clean_mobile(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise HTTPException(status_code=400, detail="Enter a 10-digit Indian mobile number.")
    return digits


def new_public_id():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "AS-" + "".join(secrets.choice(alphabet) for _ in range(6))


_students_ready = False


def ensure_students():
    """Create the student tables on the database this site already uses."""
    global _students_ready
    if _students_ready:
        return
    statements = (
        """
        CREATE TABLE IF NOT EXISTS students (
            id              bigserial PRIMARY KEY,
            public_id       text NOT NULL UNIQUE,
            name            text NOT NULL,
            mobile          text NOT NULL UNIQUE,
            consent_at      timestamptz,
            consent_text    text NOT NULL DEFAULT '',
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """,
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS consent_at timestamptz",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS consent_text text NOT NULL DEFAULT ''",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'student'",
        "UPDATE students SET role = 'admin' WHERE mobile = '8320936486'",
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id          bigserial PRIMARY KEY,
            student_id  bigint NOT NULL REFERENCES students (id) ON DELETE CASCADE,
            exam        text NOT NULL,
            rank        integer NOT NULL,
            category    text NOT NULL,
            gender      text NOT NULL,
            home_state  text NOT NULL,
            course      text NOT NULL DEFAULT '',
            created_at  timestamptz NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS predictions_student
            ON predictions (student_id, created_at DESC)
        """,
    )
    with connection() as conn:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
    _students_ready = True


def upsert_student(name, mobile):
    """Create an ID, or keep the ID already stored for this mobile number."""
    ensure_students()
    for _ in range(3):
        try:
            with connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO students (public_id, name, mobile, consent_at, consent_text, role)
                        VALUES (%(public_id)s, %(name)s, %(mobile)s, now(), %(consent_text)s, %(role)s)
                        ON CONFLICT (mobile) DO UPDATE
                        SET name = EXCLUDED.name,
                            consent_at = now(),
                            consent_text = EXCLUDED.consent_text,
                            role = CASE
                                WHEN EXCLUDED.role = 'admin' THEN 'admin'
                                WHEN students.role = 'staff' THEN 'staff'
                                ELSE students.role
                            END
                        RETURNING public_id, name, mobile, role
                        """,
                        {
                            "public_id": new_public_id(),
                            "name": name,
                            "mobile": mobile,
                            "consent_text": CONSENT_TEXT,
                            "role": "admin" if mobile == ADMIN_MOBILE else "student",
                        },
                    )
                    return cursor.fetchone()
        except UniqueViolation:
            continue
    raise HTTPException(status_code=503, detail="The student ID could not be created. Try again.")


def find_student(public_id):
    ensure_students()
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, public_id, name, mobile, role FROM students WHERE public_id = %(public_id)s",
                {"public_id": public_id},
            )
            return cursor.fetchone()


def find_student_mobile(mobile):
    ensure_students()
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, public_id, name, mobile, role FROM students WHERE mobile = %(mobile)s",
                {"mobile": mobile},
            )
            return cursor.fetchone()


ADMIN_MOBILE = "8320936486"
STUDENT_COOKIE = "setu_session"


def session_secret():
    return os.environ.get("ADMIN_PASSWORD", "").strip() or "admission-setu-session"


def sign_session(public_id):
    mac = hmac.new(session_secret().encode(), public_id.encode(), hashlib.sha256).hexdigest()
    return f"{public_id}.{mac}"


def account_role(row):
    if not row:
        return "student"
    if row.get("mobile") == ADMIN_MOBILE:
        return "admin"
    if row.get("role") == "staff":
        return "staff"
    return "student"


def student_public(row):
    return {
        "id": row["public_id"],
        "name": row["name"],
        "mobile": row["mobile"],
        "role": account_role(row),
    }


def write_session(response, row):
    response.set_cookie(
        STUDENT_COOKIE,
        sign_session(row["public_id"]),
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="lax",
        path="/",
    )
    if account_role(row) != "admin":
        return
    import admin as admin_mod

    if not admin_mod.password():
        return
    issued = str(int(time.time()))
    response.set_cookie(
        admin_mod.COOKIE,
        admin_mod.sign(issued),
        max_age=admin_mod.MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def current_account(request: Request):
    raw = request.cookies.get(STUDENT_COOKIE, "")
    if not raw or "." not in raw:
        return None
    public_id, mac = raw.rsplit(".", 1)
    expected = sign_session(public_id).rsplit(".", 1)[1]
    if not hmac.compare_digest(expected, mac):
        return None
    return find_student(public_id)


def require_admin(request: Request):
    student = current_account(request)
    if student is None or account_role(student) != "admin":
        raise HTTPException(status_code=401, detail="Only the admin can do this.")
    return student


class LoginIn(BaseModel):
    mobile: str
    otp: str = ""
    name: str = ""
    consent: bool = False


WHATSAPP_OTP = "1234"


class MobileIn(BaseModel):
    mobile: str


@app.post("/auth/otp")
def request_otp(body: MobileIn):
    """Accept a mobile number. WhatsApp delivery is not connected yet."""
    clean_mobile(body.mobile)
    return {"sent": True}


@app.post("/auth/login")
def login_student(body: LoginIn, response: Response):
    mobile = clean_mobile(body.mobile)
    if body.otp.strip() != WHATSAPP_OTP:
        raise HTTPException(status_code=400, detail="That code is not correct.")
    found = find_student_mobile(mobile)
    if found:
        write_session(response, found)
        return student_public(found)
    if not body.name.strip():
        return {"needs_name": True}
    if not body.consent:
        raise HTTPException(status_code=400, detail="Tick the box to agree before we save your name and mobile number.")
    row = upsert_student(clean_name(body.name), mobile)
    write_session(response, row)
    return student_public(row)


@app.post("/auth/logout")
def logout_student(response: Response):
    response.delete_cookie(STUDENT_COOKIE, path="/")
    response.delete_cookie("setu_admin", path="/")
    return {"ok": True}


class StaffIn(BaseModel):
    name: str = ""
    mobile: str
    role: str = "staff"


def set_member_role(mobile, role, name=""):
    ensure_students()
    mobile = clean_mobile(mobile)
    if mobile == ADMIN_MOBILE:
        raise HTTPException(status_code=400, detail="That number is the admin.")
    if role not in ("staff", "student"):
        raise HTTPException(status_code=400, detail="Choose staff or student.")
    found = find_student_mobile(mobile)
    if found is None:
        if role != "staff":
            raise HTTPException(status_code=404, detail="That number is not a student yet.")
        if not str(name).strip():
            raise HTTPException(status_code=400, detail="Enter the staff name.")
        upsert_student(clean_name(name), mobile)
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE students
                SET role = %(role)s,
                    name = CASE WHEN %(name)s = '' THEN name ELSE %(name)s END
                WHERE mobile = %(mobile)s AND mobile <> %(admin)s
                RETURNING public_id, name, mobile, role
                """,
                {
                    "role": role,
                    "name": str(name).strip(),
                    "mobile": mobile,
                    "admin": ADMIN_MOBILE,
                },
            )
            row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=400, detail="That number could not be updated.")
    return row


@app.get("/team")
def list_staff(request: Request):
    require_admin(request)
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT public_id, name, mobile, role
                FROM students
                WHERE role = 'staff'
                ORDER BY lower(name)
                """
            )
            rows = cursor.fetchall()
    return {"staff": [student_public(row) for row in rows]}


@app.post("/team")
def save_staff(body: StaffIn, request: Request):
    require_admin(request)
    role = "staff" if body.role != "student" else "student"
    return student_public(set_member_role(body.mobile, role, body.name))


def prediction_rows(student_id):
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT exam, rank, category, gender, home_state, course, created_at
                FROM predictions
                WHERE student_id = %(student_id)s
                ORDER BY created_at DESC
                LIMIT 40
                """,
                {"student_id": student_id},
            )
            rows = cursor.fetchall()
    history = []
    for row in rows:
        item = dict(row)
        created = item.get("created_at")
        item["created_at"] = created.isoformat() if created else ""
        history.append(item)
    return history


@app.get("/students/{public_id}")
def student_account(public_id: str):
    student = find_student(public_id.strip())
    if student is None:
        raise HTTPException(status_code=404, detail="This ID was not found.")
    payload = student_public(student)
    payload["predictions"] = prediction_rows(student["id"])
    return payload


class ProfileIn(BaseModel):
    name: str
    mobile: str


@app.patch("/students/{public_id}")
def update_student(public_id: str, body: ProfileIn):
    student = find_student(public_id.strip())
    if student is None:
        raise HTTPException(status_code=404, detail="This ID was not found.")
    name = clean_name(body.name)
    mobile = clean_mobile(body.mobile)
    if mobile == ADMIN_MOBILE and student["mobile"] != ADMIN_MOBILE:
        raise HTTPException(status_code=400, detail="That number is the admin.")
    if student["mobile"] == ADMIN_MOBILE and mobile != ADMIN_MOBILE:
        raise HTTPException(status_code=400, detail="The admin number stays on this account.")
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE students
                    SET name = %(name)s, mobile = %(mobile)s
                    WHERE public_id = %(public_id)s
                    RETURNING public_id, name, mobile, role
                    """,
                    {"name": name, "mobile": mobile, "public_id": student["public_id"]},
                )
                row = cursor.fetchone()
    except UniqueViolation:
        raise HTTPException(status_code=400, detail="That mobile number is already used.")
    return student_public(row)


@app.post("/students")
def save_student(body: StudentIn):
    if not body.consent:
        raise HTTPException(status_code=400, detail="Tick the box to agree before we save your name and mobile number.")
    row = upsert_student(clean_name(body.name), clean_mobile(body.mobile))
    return {"id": row["public_id"], "name": row["name"]}


@app.delete("/students/{public_id}")
def withdraw_student(public_id: str):
    """Delete the name, mobile number, and saved predictions for this ID."""
    ensure_students()
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM students WHERE public_id = %(public_id)s RETURNING id",
                {"public_id": public_id.strip()},
            )
            row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="This ID is already removed.")
    return {"deleted": True}


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
    student = find_student(body.student_id.strip())
    if student is None:
        raise HTTPException(status_code=400, detail="Enter your name and mobile number.")
    if body.record:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO predictions (
                        student_id, exam, rank, category, gender, home_state, course
                    )
                    VALUES (
                        %(student_id)s, %(exam)s, %(rank)s, %(category)s, %(gender)s, %(home_state)s, %(course)s
                    )
                    """,
                    {
                        "student_id": student["id"],
                        "exam": body.exam,
                        "rank": body.rank,
                        "category": category,
                        "gender": body.gender,
                        "home_state": home_state,
                        "course": course,
                    },
                )

    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT institute, state, program, quota, category, gender,
                       opening_rank, closing_rank, exam
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
            "opening_rank": row["opening_rank"],
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
    shown, counts = shortlist(rows, body.rank)
    branches = family_counts(shown)
    chosen = body.branch.strip()
    if chosen and any(item["name"] == chosen for item in branches):
        shown = [row for row in shown if row["family"] == chosen]
    else:
        chosen = ""
    start = (body.page - 1) * body.page_size
    page_rows = shown[start : start + body.page_size]
    facts = {}
    for row in page_rows:
        row["slug"] = slug_for_institute(row["college"])
        slug = row["slug"]
        if slug not in facts:
            if slug:
                logo, highest, nirf = card_facts(slug)
                facts[slug] = (logo or "", highest or "", nirf)
            else:
                facts[slug] = ("", "", None)
        row["logo"], row["highest_package"], row["nirf_rank"] = facts[slug]
    round_label = "MCC 2026" if body.exam == "NEET" else "JoSAA 2026, round 5"
    return {
        "exam": body.exam,
        "rank": body.rank,
        "category": category,
        "gender": body.gender,
        "home_state": home_state,
        "course": course,
        "student_id": student["public_id"],
        "student_name": student["name"],
        "round_label": round_label,
        "branch": chosen,
        "branches": branches,
        "total": len(shown),
        "matched": len(rows),
        "counts": counts,
        "page": body.page,
        "page_size": body.page_size,
        "results": page_rows,
    }


from admin import router as admin_router  # noqa: E402

app.include_router(admin_router)
app.mount("/assets", StaticFiles(directory=WEB), name="assets")
