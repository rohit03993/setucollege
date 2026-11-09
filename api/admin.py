"""Password-protected college editor.

The public site reads college_overrides after the saved college data.
Import does not write this table, so an edit stays until Restore saved data.
Set ADMIN_PASSWORD in db/.env, then open /admin.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from html import escape
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from psycopg.types.json import Json

router = APIRouter()
COOKIE = "setu_admin"
MAX_AGE = 60 * 60 * 24 * 14


def app():
    import main

    return main


def password():
    return os.environ.get("ADMIN_PASSWORD", "").strip()


def same(left, right):
    left = left.encode()
    right = right.encode()
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def sign(issued):
    mac = hmac.new(password().encode(), issued.encode(), hashlib.sha256).hexdigest()
    return f"{issued}.{mac}"


def valid_cookie(raw):
    if not password() or not raw or "." not in raw:
        return False
    issued, mac = raw.rsplit(".", 1)
    expected = sign(issued).rsplit(".", 1)[1]
    if not same(expected, mac):
        return False
    try:
        return time.time() - int(issued) < MAX_AGE
    except ValueError:
        return False


def signed_in(request: Request):
    return valid_cookie(request.cookies.get(COOKIE, ""))


def page(title, body):
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="en-IN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="/assets/styles.css?v=19">
  <link rel="stylesheet" href="/assets/admin.css?v=3">
  <style>
    .admin {{ width: min(1080px, calc(100% - 32px)); margin: 24px auto 48px; }}
    .admin-bar h1 {{ font-size: 32px; margin: 0; }}
    .admin-bar {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 16px; }}
    .admin table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 16px; overflow: hidden; }}
    .admin th, .admin td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    .admin th {{ font-size: 12px; color: var(--muted); }}
    .admin form.stack {{ display: grid; gap: 12px; }}
    .admin textarea {{ width: 100%; min-height: 140px; padding: 12px; border-radius: 14px; border: 1px solid var(--line); font: inherit; }}
    .check {{ display: flex; gap: 8px; align-items: center; font-weight: 700; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #efeaff; font-size: 12px; font-weight: 800; }}
    .badge.off {{ background: #fde8ef; color: #9f1239; }}
  </style>
</head>
<body>
  <header class="topbar"><div class="topbar-inner">
    <a class="brand" href="/"><img src="/assets/logo.jpg?v=2" alt="Admission Setu"></a>
    <nav class="desktop-nav"><a href="/admin">Colleges</a></nav>
  </div></header>
  <main class="admin">{body}</main>
</body>
</html>"""
    )


def login_page(message=""):
    note = f'<p class="status" role="alert">{escape(message)}</p>' if message else ""
    ready = ""
    if not password():
        ready = "<p class=\"status\" role=\"alert\">Add ADMIN_PASSWORD to db/.env, then restart the site.</p>"
    elif not app().overrides_ready():
        ready = "<p class=\"status\" role=\"alert\">The edit table is not in the database yet. Run db/schema.sql, then restart the site.</p>"
    return page(
        "Admin login",
        f"""<h1>Admin login</h1>
        <p class="lede">Edit a college here and the public page uses that version.</p>
        {ready}{note}
        <form class="panel form" method="post" action="/admin/login">
          <label class="field wide"><span>Password</span>
            <input name="password" type="password" autocomplete="current-password" required>
          </label>
          <button class="button" type="submit">Log in</button>
        </form>""",
    )


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_form():
    return login_page()


@router.post("/admin/login")
async def admin_login(request: Request):
    form = await request.form()
    given = str(form.get("password") or "")
    if not password() or not same(password(), given):
        return login_page("That password is not right.")
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(COOKIE, sign(str(int(time.time()))), httponly=True, samesite="lax", max_age=MAX_AGE, path="/")
    return response


@router.post("/admin/logout")
def admin_logout():
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(COOKIE, path="/")
    return response


def guard(request: Request):
    if signed_in(request):
        return None
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/admin", response_class=HTMLResponse)
def admin_list(request: Request, q: str = "", page_no: int = 1):
    blocked = guard(request)
    if blocked:
        return blocked
    if not app().overrides_ready():
        return page("Admin", "<h1>Colleges</h1><p class=\"status\" role=\"alert\">Run db/schema.sql, then restart the site.</p>")
    page_no = max(1, page_no)
    size = 30
    query = q.strip()
    with app().connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.source_slug,
                       CASE WHEN o.source_slug IS NULL THEN c.name ELSE COALESCE(NULLIF(o.name, ''), c.name) END AS name,
                       CASE WHEN o.source_slug IS NULL THEN c.city ELSE o.city END AS city,
                       CASE WHEN o.source_slug IS NULL THEN c.state ELSE o.state END AS state,
                       CASE WHEN o.source_slug IS NULL THEN c.fee_label ELSE o.fee_label END AS fee_label,
                       CASE WHEN o.source_slug IS NULL THEN c.nirf_rank ELSE o.nirf_rank END AS nirf_rank,
                       o.source_slug IS NOT NULL AS edited,
                       COALESCE(o.hidden, false) AS hidden,
                       count(*) OVER() AS total
                FROM colleges c
                LEFT JOIN college_overrides o ON o.source_slug = c.source_slug
                WHERE (%(q)s = '' OR c.name ILIKE %(like)s OR c.city ILIKE %(like)s
                       OR c.state ILIKE %(like)s OR o.name ILIKE %(like)s)
                ORDER BY lower(c.name)
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                {"q": query, "like": f"%{query}%", "limit": size, "offset": (page_no - 1) * size},
            )
            rows = cursor.fetchall()
    total = rows[0]["total"] if rows else 0
    pages = max(1, (total + size - 1) // size)
    body_rows = []
    for row in rows:
        marks = []
        if row["edited"]:
            marks.append('<span class="badge">Edited</span>')
        if row["hidden"]:
            marks.append('<span class="badge off">Hidden</span>')
        fee = escape(row["fee_label"] or "—")
        nirf = escape(str(row["nirf_rank"])) if row["nirf_rank"] else "—"
        place = escape(", ".join(part for part in (row["city"], row["state"]) if part))
        slug = escape(row["source_slug"])
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/admin/colleges/{slug}\"><strong>{escape(row['name'])}</strong></a>"
            f"<div class=\"muted\">{place}</div></td>"
            f"<td>{fee}</td><td>{nirf}</td><td>{' '.join(marks)}</td>"
            f"<td><a href=\"/admin/colleges/{slug}\">Edit</a></td>"
            "</tr>"
        )
    empty = '<tr><td colspan="5">No college matches that search.</td></tr>'
    table = (
        "<table><thead><tr><th>College</th><th>Yearly fee</th><th>NIRF</th><th></th><th></th></tr></thead>"
        f"<tbody>{''.join(body_rows) or empty}</tbody></table>"
    )
    prev_link = f'<a class="ghost" href="/admin?q={escape(query)}&page_no={page_no - 1}">Previous</a>' if page_no > 1 else ""
    next_link = f'<a class="ghost" href="/admin?q={escape(query)}&page_no={page_no + 1}">Next</a>' if page_no < pages else ""
    return page(
        "Admin",
        f"""        <div class="admin-bar"><h1>Colleges</h1>
          <div class="row-actions">
            <a class="button" href="/admin/new">Add college</a>
            <form method="post" action="/admin/logout"><button class="ghost" type="submit">Log out</button></form>
          </div></div>
        <p class="lede">{total} colleges. Edited rows are what visitors see for those facts.</p>
        <form class="search" method="get" action="/admin">
          <input name="q" value="{escape(query)}" placeholder="College, city, or state">
          <button class="button" type="submit">Search</button>
        </form>
        {table}
        <div class="pager">{prev_link}<p>Page {page_no} of {pages}</p>{next_link}</div>""",
    )


JUNK = re.compile(
    r"by degree|similar college|photo gallery|choose course|next application date|admission updates",
    re.I,
)
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEVELS = (
    r"B\.Tech\+M\.Tech|Integrated M\.Tech|B\.Tech|M\.Tech|B\.Arch|M\.Arch|"
    r"B\.Sc|M\.Sc|MBA|MCA|PG Diploma|PhD|M\.Plan|B\.Plan|M\.Des|B\.Des|"
    r"Doctor of Philosophy|BS|MS"
)
UPLOADS = Path(__file__).resolve().parents[1] / "web" / "uploads"
MAX_IMAGE = 4 * 1024 * 1024


def public_slug(value):
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text[:80]


def image_suffix(data):
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(data) > 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ""


def fallback_groups(pages):
    pattern = re.compile(
        rf"({LEVELS})Fees \(Yearly\)₹([\d,.\-– ]+?)Number of courses:(\d+)([\s\S]*?)(?=(?:{LEVELS})Fees \(Yearly\)|$)"
    )
    name_split = re.compile(rf"(?=(?:{LEVELS})\b)")
    grouped = []
    for section in (pages.get("courses") or {}).get("sections") or []:
        text = section.get("content") or ""
        if "Fees (Yearly)" not in text:
            continue
        for match in pattern.finditer(text):
            level, fee, _count, blob = match.groups()
            names = []
            for part in name_split.split(blob):
                name = re.sub(r"\+\d+\s*More", "", " ".join(part.split()), flags=re.I).strip()
                if not (name.startswith(level) and 3 < len(name) < 90):
                    continue
                short = re.sub(rf"^{re.escape(level)}\.?\s*(in\s*)?", "", name, count=1, flags=re.I).strip(" .")
                if short:
                    names.append(clip(short, 120))
            if len(names) < 2:
                continue
            grouped.append({"degree": clip(level, 80), "fee": clip(f"₹{fee.strip()}", 80), "courses": names[:80]})
            if len(grouped) >= 40:
                return grouped
    return grouped


def clip(value, limit):
    text = " ".join(str(value or "").split())
    return text[:limit]


def how_admission(exams):
    blob = " ".join(exams or [])
    if "JEE Advanced" in blob:
        return "Qualify JEE Advanced, then take a seat through JoSAA."
    if "JEE Main" in blob:
        return "Qualify JEE Main, then take a seat through JoSAA."
    if "NEET" in blob:
        return "Qualify NEET, then take a seat through counselling."
    if exams:
        return "Take the listed exam, then complete that exam's counselling."
    return ""


def visible_tables(pages, key, limit):
    tables = []
    for table in (pages.get(key) or {}).get("tables") or []:
        rows = [row for row in (table.get("rows") or []) if row]
        title = table.get("title") or ""
        if not rows or JUNK.search(title):
            continue
        columns = list(table.get("columns") or [])
        if not columns and len(rows) > 1 and re.search(r"rank|category|course|fee|branch", " ".join(map(str, rows[0])), re.I):
            columns = [clip(cell, 80) for cell in rows[0]]
            rows = rows[1:]
        tables.append(
            {
                "title": clip(title, 160) or "Details",
                "columns": [clip(cell, 80) for cell in columns],
                "rows": [[clip(cell, 120) for cell in row] for row in rows[:40]],
            }
        )
        if len(tables) >= limit:
            break
    return tables


def editor_document(college, slug):
    pages = college.get("pages") or {}
    groups = []
    for group in (pages.get("course_groups") or [])[:40]:
        names = [clip(name, 120) for name in (group.get("courses") or [])[:80] if str(name or "").strip()]
        if not group.get("degree") and not names:
            continue
        groups.append({"degree": clip(group.get("degree"), 80), "fee": clip(group.get("fee"), 80), "courses": names})
    if not groups and not college.get("managed"):
        groups = fallback_groups(pages)
    admission = []
    line = how_admission(college.get("exams") or [])
    if line and not college.get("managed"):
        admission.append({"title": "How admission works", "content": line})
    for section in (pages.get("admission") or {}).get("sections") or []:
        title = section.get("title") or ""
        content = section.get("content") or ""
        if not content or title.endswith("?") or JUNK.search(title) or JUNK.search(content[:300]):
            continue
        admission.append({"title": clip(title, 160), "content": clip(content, 8000)})
        if len(admission) >= 12:
            break
    answers = []
    for item in (pages.get("faqs") or [])[:40]:
        if item.get("question") and item.get("answer"):
            answers.append({"question": clip(item["question"], 200), "answer": clip(item["answer"], 4000)})
    recruiters = college.get("recruiters") or ""
    if not recruiters:
        text = " ".join(section.get("content") or "" for section in (pages.get("placement") or {}).get("sections") or [])
        found = re.search(r"top recruiters include ([^.]+)", text, re.I)
        recruiters = clip(found.group(1), 300) if found else ""
    video = college.get("video_id") or ""
    return {
        "slug": slug,
        "hidden": bool(college.get("hidden")),
        "name": college.get("name") or "",
        "city": college.get("city") or "",
        "state": college.get("state") or "",
        "ownership": college.get("ownership") or "",
        "fee_label": college.get("fee_label") or "",
        "nirf_rank": "" if college.get("nirf_rank") in (None, "") else str(college.get("nirf_rank")),
        "established_year": str(college.get("established_year") or ""),
        "average_package": college.get("average_package") or "",
        "highest_package": college.get("highest_package") or "",
        "rating": str(college.get("rating") or ""),
        "reviews": str(college.get("reviews") or ""),
        "course_count": str(college.get("course_count") or ""),
        "website": college.get("website") or "",
        "phone": college.get("phone") or "",
        "streams": list(college.get("streams") or []),
        "exams": list(college.get("exams") or []),
        "overview": college.get("overview") or "",
        "image": college.get("image") or "",
        "logo": college.get("logo") or "",
        "video": f"https://youtu.be/{video}" if video else "",
        "course_groups": groups,
        "admission": admission,
        "cutoff": visible_tables(pages, "cutoff", 8),
        "placements": visible_tables(pages, "placement", 6),
        "recruiters": recruiters,
        "answers": answers,
    }


def editor_page(request: Request, doc, creating):
    payload = json.dumps(doc).replace("<", "\\u003c")
    slug = doc.get("slug") or ""
    title = "New college" if creating else (doc.get("name") or "College")
    mode = "new" if creating else "edit"
    view = "" if creating else f'<a class="ghost" href="/college/{escape(slug)}">View on site</a>'
    restore = ""
    if not creating:
        restore = (
            f'<form method="post" action="/admin/colleges/{escape(slug)}/restore">'
            f'<input type="hidden" name="token" value="{escape(request.cookies.get(COOKIE, ""))}">'
            '<button class="ghost" type="submit">Restore saved data</button></form>'
        )
    return page(
        title,
        f"""<div class="editor-top">
          <div>
            <a class="back" href="/admin">All colleges</a>
            <h1>{escape(title)}</h1>
          </div>
          <div class="row-actions">{view}{restore}<button class="button" id="save" type="button">Save college</button></div>
        </div>
        <p id="save-note" class="hint">{'Fill in each part of the college page, then save. The web address becomes its public link.' if creating else 'Edit each part of the college page, then save. Saving publishes this version. Restore saved data brings back the imported college.'}</p>
        <nav id="tabs" class="editor-tabs" aria-label="College sections"></nav>
        <div id="panel"></div>
        <div id="editor" data-mode="{mode}" data-slug="{escape(slug)}" data-token="{escape(request.cookies.get(COOKIE, ""))}"></div>
        <script id="college-doc" type="application/json">{payload}</script>
        <script src="/assets/admin.js?v=2"></script>""",
    )


@router.get("/admin/new", response_class=HTMLResponse)
def admin_new(request: Request):
    blocked = guard(request)
    if blocked:
        return blocked
    blank = editor_document({"pages": {}, "exams": [], "streams": []}, "")
    return editor_page(request, blank, True)


@router.get("/admin/colleges/{slug}", response_class=HTMLResponse)
def admin_edit(request: Request, slug: str):
    blocked = guard(request)
    if blocked:
        return blocked
    college = app().load_college(slug, include_hidden=True)
    if college is None:
        return page("Not found", "<h1>College not found</h1><p><a href=\"/admin\">Back</a></p>")
    return editor_page(request, editor_document(college, slug), False)


def check_token(request: Request, token: str):
    return same(request.cookies.get(COOKIE, ""), token) if signed_in(request) and token else False


@router.post("/admin/api/upload")
async def admin_upload(request: Request, token: str = Form(""), file: UploadFile = File(...)):
    if not check_token(request, token):
        return JSONResponse({"error": "Log in again."}, status_code=401)
    data = await file.read(MAX_IMAGE + 1)
    suffix = image_suffix(data)
    if not suffix:
        return JSONResponse({"error": "Use a JPG, PNG, WEBP, or GIF picture."}, status_code=400)
    if len(data) > MAX_IMAGE:
        return JSONResponse({"error": "That picture is larger than 4 MB."}, status_code=400)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(12)}{suffix}"
    (UPLOADS / name).write_bytes(data)
    return JSONResponse({"url": f"/assets/uploads/{name}"})


def whole(value):
    text = str(value or "").strip()
    if not text:
        return None
    return int(text)


def clean_lines(values, limit, length):
    cleaned = []
    for value in values or []:
        text = clip(value, length)
        if text:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def clean_tables(tables, limit):
    cleaned = []
    for table in tables or []:
        if not isinstance(table, dict):
            continue
        rows = []
        for row in table.get("rows") or []:
            if isinstance(row, list):
                cells = clean_lines(row, 12, 120)
                if cells:
                    rows.append(cells)
            if len(rows) >= 40:
                break
        title = clip(table.get("title"), 160)
        if not title and not rows:
            continue
        cleaned.append({"title": title or "Details", "columns": clean_lines(table.get("columns"), 12, 80), "rows": rows})
        if len(cleaned) >= limit:
            break
    return cleaned


def content_ready(cursor):
    cursor.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'college_overrides' AND column_name = 'content'
        """
    )
    return cursor.fetchone() is not None


@router.post("/admin/api/college")
async def admin_save_json(request: Request):
    if not signed_in(request):
        return JSONResponse({"error": "Log in again."}, status_code=401)
    body = await request.json()
    if not check_token(request, str(body.get("token") or "")):
        return JSONResponse({"error": "Log in again."}, status_code=401)
    name = clip(body.get("name"), 200)
    slug = public_slug(body.get("slug"))
    if not slug and body.get("creating"):
        slug = public_slug(name)
    original = str(body.get("original_slug") or "").strip()
    if not name:
        return JSONResponse({"error": "The college needs a name."}, status_code=400)
    if not SLUG.fullmatch(slug):
        return JSONResponse({"error": "The web address can use lowercase letters, numbers, and hyphens."}, status_code=400)
    try:
        rank = whole(body.get("nirf_rank"))
    except ValueError:
        return JSONResponse({"error": "NIRF rank must be a whole number."}, status_code=400)
    year_text = clip(body.get("established_year"), 12)
    try:
        established = int(year_text) if year_text.isdigit() else None
    except ValueError:
        established = None
    streams = clean_lines(body.get("streams"), 12, 40)
    exams = clean_lines(body.get("exams"), 8, 40)
    groups = []
    for group in (body.get("course_groups") or [])[:40]:
        if not isinstance(group, dict):
            continue
        names = clean_lines(group.get("courses"), 80, 120)
        degree = clip(group.get("degree"), 80)
        if not degree and not names:
            continue
        groups.append({"degree": degree, "fee": clip(group.get("fee"), 80), "count": str(len(names)), "courses": names})
    content = {
        "managed": True,
        "video_id": clip(body.get("video_id"), 11),
        "course_count": clip(body.get("course_count"), 12),
        "exams": exams,
        "recruiters": clip(body.get("recruiters"), 300),
        "course_groups": groups,
        "admission": [
            {"title": clip(item.get("title"), 160), "content": clip(item.get("content"), 8000)}
            for item in (body.get("admission") or [])[:12]
            if isinstance(item, dict) and (item.get("title") or item.get("content"))
        ],
        "cutoff": clean_tables(body.get("cutoff"), 8),
        "placements": clean_tables(body.get("placements"), 6),
        "answers": [
            {"question": clip(item.get("question"), 200), "answer": clip(item.get("answer"), 4000)}
            for item in (body.get("answers") or [])[:40]
            if isinstance(item, dict) and item.get("question") and item.get("answer")
        ],
    }
    record = {
        "slug": slug,
        "name": name,
        "city": clip(body.get("city"), 80),
        "state": clip(body.get("state"), 80),
        "ownership": clip(body.get("ownership"), 40),
        "overview": clip(body.get("overview"), 2000),
        "fee_label": clip(body.get("fee_label"), 80),
        "nirf_rank": rank,
        "established_year": year_text,
        "established": established,
        "average_package": clip(body.get("average_package"), 40),
        "highest_package": clip(body.get("highest_package"), 40),
        "rating": clip(body.get("rating"), 12),
        "reviews": clip(body.get("reviews"), 20),
        "image": clip(body.get("image"), 500),
        "logo": clip(body.get("logo"), 500),
        "website": clip(body.get("website"), 300),
        "phone": clip(body.get("phone"), 40),
        "streams": streams,
        "exams": exams,
        "hidden": bool(body.get("hidden")),
        "content": Json(content),
    }
    with app().connection() as conn:
        with conn.cursor() as cursor:
            if not content_ready(cursor):
                return JSONResponse(
                    {"error": "Run db/schema.sql so the page content can be saved, then try again."},
                    status_code=400,
                )
            if body.get("creating"):
                cursor.execute("SELECT 1 FROM colleges WHERE source_slug = %(slug)s", record)
                if cursor.fetchone():
                    return JSONResponse({"error": "That web address is already used."}, status_code=400)
                cursor.execute(
                    """
                    INSERT INTO colleges (
                        source, source_slug, name, city, state, ownership, streams, exams,
                        established, website, phone, overview, fee_label, nirf_rank
                    ) VALUES (
                        'admin', %(slug)s, %(name)s, %(city)s, %(state)s, %(ownership)s, %(streams)s, %(exams)s,
                        %(established)s, %(website)s, %(phone)s, %(overview)s, %(fee_label)s, %(nirf_rank)s
                    )
                    """,
                    record,
                )
            else:
                cursor.execute(
                    """
                    SELECT id FROM colleges
                    WHERE source_slug = %(original)s
                    ORDER BY source
                    LIMIT 1
                    """,
                    {"original": original},
                )
                row = cursor.fetchone()
                if row is None:
                    return JSONResponse({"error": "College not found."}, status_code=404)
                cursor.execute(
                    "SELECT 1 FROM colleges WHERE source_slug = %(slug)s AND id <> %(id)s",
                    {"slug": slug, "id": row["id"]},
                )
                if cursor.fetchone():
                    return JSONResponse({"error": "That web address is already used."}, status_code=400)
                cursor.execute(
                    """
                    UPDATE colleges SET
                        source_slug = %(slug)s, name = %(name)s, city = %(city)s, state = %(state)s,
                        ownership = %(ownership)s, streams = %(streams)s, exams = %(exams)s,
                        established = %(established)s, website = %(website)s, phone = %(phone)s,
                        overview = %(overview)s, fee_label = %(fee_label)s, nirf_rank = %(nirf_rank)s
                    WHERE id = %(id)s
                    """,
                    {**record, "id": row["id"]},
                )
                if original != slug:
                    cursor.execute(
                        "UPDATE college_overrides SET source_slug = %(slug)s WHERE source_slug = %(original)s",
                        {"slug": slug, "original": original},
                    )
            cursor.execute(
                """
                INSERT INTO college_overrides (
                    source_slug, name, city, state, ownership, overview, fee_label, nirf_rank,
                    established_year, average_package, highest_package, rating, reviews,
                    image, logo, website, phone, streams, hidden, content, updated_at
                ) VALUES (
                    %(slug)s, %(name)s, %(city)s, %(state)s, %(ownership)s, %(overview)s, %(fee_label)s, %(nirf_rank)s,
                    %(established_year)s, %(average_package)s, %(highest_package)s, %(rating)s, %(reviews)s,
                    %(image)s, %(logo)s, %(website)s, %(phone)s, %(streams)s, %(hidden)s, %(content)s, now()
                )
                ON CONFLICT (source_slug) DO UPDATE SET
                    name = EXCLUDED.name, city = EXCLUDED.city, state = EXCLUDED.state,
                    ownership = EXCLUDED.ownership, overview = EXCLUDED.overview, fee_label = EXCLUDED.fee_label,
                    nirf_rank = EXCLUDED.nirf_rank, established_year = EXCLUDED.established_year,
                    average_package = EXCLUDED.average_package, highest_package = EXCLUDED.highest_package,
                    rating = EXCLUDED.rating, reviews = EXCLUDED.reviews, image = EXCLUDED.image,
                    logo = EXCLUDED.logo, website = EXCLUDED.website, phone = EXCLUDED.phone,
                    streams = EXCLUDED.streams, hidden = EXCLUDED.hidden, content = EXCLUDED.content,
                    updated_at = now()
                """,
                record,
            )
        conn.commit()
    app().saved_pages.cache_clear()
    return JSONResponse({"slug": slug})



@router.post("/admin/colleges/{slug}/restore")
def admin_restore(request: Request, slug: str, token: str = Form("")):
    if not signed_in(request) or not check_token(request, token):
        return RedirectResponse("/admin/login", status_code=303)
    with app().connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM college_overrides WHERE source_slug = %(slug)s", {"slug": slug})
        conn.commit()
    app().saved_pages.cache_clear()
    return RedirectResponse(f"/admin/colleges/{slug}", status_code=303)
