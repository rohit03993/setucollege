"""Read the saved CollegeDekho courses, admission, and placement pages.

Those HTML files are the full college record. The card in the database is only the short summary.
A matching College For Me file can add a photo, a YouTube video, NIRF, and packages.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
COLLEGE_DIR = ROOT / "college-dekho" / "data" / "colleges"
CFM_DIR = ROOT / "college-for-me" / "data" / "collegeforme" / "raw"
STOP_WORDS = {
    "of", "and", "the", "for", "in", "at", "a", "an",
    "institute", "indian", "college", "university", "technology", "national",
}
PAGES = ("courses", "admission", "placement", "cutoff")
SKIP_HEADING = re.compile(
    r"student preferred|similar college|related question|explore more|"
    r"share your college|table of contents|top courses at|"
    r"upcoming events|expired events|admission updates",
    re.I,
)
PROMO = re.compile(r"next application date|choose course", re.I)
NOISE = (
    './/*[contains(@class,"studentFeedback") or contains(@class,"studentQa")'
    ' or contains(@class,"similarCollege") or contains(@class,"relatedQuestion")'
    ' or contains(@class,"exploreCollege") or contains(@class,"preferredCollege")'
    ' or contains(@class,"exploreSimilar")]'
)
MAX_CELL = 500
MAX_SECTION = 2500
MAX_ROWS = 120
MAX_TABLES = 16
MAX_SECTIONS = 24


def clean(value) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


def clip(text, limit):
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


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


def nearest_heading(table) -> str:
    nodes = table.xpath("preceding::*[self::h2 or self::h3][1]")
    if not nodes:
        return ""
    return clip(clean("".join(nodes[0].itertext())), 180)


def table_rows(table):
    rows = []
    for tr in table.xpath("./tr | ./thead/tr | ./tbody/tr | ./tfoot/tr"):
        cells = [clip(clean(text_without_tables(cell)), MAX_CELL) for cell in tr.xpath("./th | ./td")]
        if any(cells):
            rows.append(cells)
    return rows


def prepare(root):
    for node in root.xpath(".//script | .//style | .//noscript"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    for node in root.xpath(NOISE):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def read_tables(root):
    tables = []
    for table in root.xpath(".//table"):
        title = nearest_heading(table)
        if title and SKIP_HEADING.search(title):
            continue
        matrix = table_rows(table)
        if not matrix:
            continue
        first = table.xpath("(./tr | ./thead/tr | ./tbody/tr)[1]")
        header_cells = first[0].xpath("./th") if first else []
        data_cells = first[0].xpath("./td") if first else []
        if header_cells and not data_cells and len(matrix) > 1:
            columns = matrix[0]
            body = matrix[1:]
        else:
            columns = []
            body = matrix
        width = max((len(row) for row in body), default=len(columns))
        columns = columns[:width]
        tables.append(
            {
                "title": title,
                "columns": columns,
                "rows": [row[:width] for row in body[:MAX_ROWS]],
                "truncated": len(body) > MAX_ROWS,
            }
        )
        if len(tables) >= MAX_TABLES:
            break
    return tables


def read_sections(root):
    sections = []
    for heading in root.xpath(".//h2 | .//h3"):
        title = clip(clean("".join(heading.itertext())), 180)
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
        content = clip(clean(" ".join(parts)), MAX_SECTION)
        if len(content) < 40 or PROMO.search(content):
            continue
        sections.append({"title": title, "content": content})
        if len(sections) >= MAX_SECTIONS:
            break
    return sections


def read_page(path: Path):
    document = load_document(path)
    if document is None:
        return {"sections": [], "tables": []}
    root = page_root(document)
    prepare(root)
    return {"sections": read_sections(root), "tables": read_tables(root)}


def load_document(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    parser = html.HTMLParser(recover=True, huge_tree=True)
    return html.fromstring(text.encode("utf-8"), parser=parser)


def page_root(document):
    mains = document.xpath('//*[contains(@class, "collegeDetailMainContainer")]')
    return mains[0] if mains else document


def money_label(value):
    text = clean(re.sub(r"<[^>]+>", " ", str(value or "")))
    if not text or text.lower() in {"none", "null", "na", "n/a"}:
        return ""
    text = re.sub(r"^rs\.?\s*", "", text, flags=re.I)
    parts = [part.strip() for part in re.split(r"\s*[–-]\s*", text) if part.strip()]
    if not parts:
        return ""
    labeled = []
    for part in parts:
        part = re.sub(r"^rs\.?\s*", "", part, flags=re.I)
        labeled.append(part if part.startswith("₹") else f"₹{part}")
    return " – ".join(labeled)


def plain_overview(value):
    text = clean(re.sub(r"<[^>]+>", " ", str(value or "")))
    if len(text) <= 280:
        return text
    cut = text.rfind(". ", 80, 280)
    if cut > 0:
        return text[: cut + 1]
    return text[:277].rstrip() + "…"


def usable_image(url):
    image = good_image(url)
    if not image or "/None/" in image:
        return ""
    return image


def header_block(text):
    marker = '"topheader":'
    index = text.find(marker)
    if index < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[index + len(marker) :])
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def rank_value(block, key):
    ranking = block.get("ranking") if isinstance(block.get("ranking"), dict) else {}
    item = ranking.get(key) if isinstance(ranking.get(key), dict) else {}
    rank = item.get("rank")
    return rank if isinstance(rank, int) and rank > 0 else None


def course_groups(root):
    groups = []
    for box in root.xpath('//*[contains(@class,"courseCardBox__")]'):
        degree = clean("".join(box.xpath('.//*[contains(@class,"cardHeading")]//text()')))
        courses = []
        for item in box.xpath('.//*[contains(@class,"cardChips")]//li'):
            name = clean(item.text_content())
            if name and not name.startswith("+") and "more" not in name.lower():
                courses.append(name)
        fee = ""
        count = ""
        for node in box.xpath('.//*[contains(@class,"detailBold")]'):
            value = clean(node.text_content())
            if re.fullmatch(r"\d+", value):
                count = value
            elif re.search(r"\d", value):
                fee = money_label(value)
        if degree:
            groups.append({"degree": degree, "fee": fee, "count": count, "courses": courses[:30]})
    return groups


def page_faqs(root):
    items = []
    for block in root.xpath('//*[contains(@class,"accordionInner")]'):
        question = clean("".join(block.xpath("./h3//text()")))
        answer = clean("".join(block.xpath('.//*[contains(@class,"accordion_content")]//text()')))
        if len(question) < 12 or len(answer) < 20:
            continue
        items.append({"question": question, "answer": clip(answer, 1200)})
    return items


def stat_value(tables, needle):
    for table in tables:
        for row in table.get("rows") or []:
            if len(row) >= 2 and needle in row[0].lower():
                return money_label(row[1])
    return ""


def blank_highlight():
    return {
        "overview": "",
        "established_year": "",
        "highest_package": "",
        "average_package": "",
        "nirf_overall": None,
        "nirf_engineering": None,
        "ownership": "",
        "rating": "",
        "reviews": "",
        "image": "",
        "logo": "",
    }


def merge_highlight(current, text, root):
    block = header_block(text)
    placement = block.get("placement") if isinstance(block.get("placement"), dict) else {}
    reviews = block.get("review_summary") if isinstance(block.get("review_summary"), dict) else {}
    institute = block.get("institute_type") if isinstance(block.get("institute_type"), dict) else {}
    banner = block.get("banner") if isinstance(block.get("banner"), dict) else {}
    logos = root.xpath('//*[contains(@class,"logoBlock")]//img/@src')
    year = block.get("established_year")
    overview = plain_overview(block.get("overview") or "")
    course_blurb = bool(re.search(r"offers \d+ courses", current["overview"], re.I))
    if overview and (not current["overview"] or (course_blurb and not re.search(r"offers \d+ courses", overview, re.I))):
        current["overview"] = overview
    if isinstance(year, int) and year > 1800 and not current["established_year"]:
        current["established_year"] = str(year)
    if not current["highest_package"]:
        current["highest_package"] = money_label(placement.get("highest_package"))
    if not current["average_package"]:
        current["average_package"] = money_label(placement.get("average_package"))
    if not current["nirf_overall"]:
        current["nirf_overall"] = rank_value(block, "overall")
    if not current["nirf_engineering"]:
        current["nirf_engineering"] = rank_value(block, "engineering")
    if not current["ownership"]:
        current["ownership"] = clean(institute.get("name") or "")
    if reviews.get("rating") and not current["rating"]:
        current["rating"] = reviews.get("rating")
        current["reviews"] = reviews.get("count") or ""
    if not current["image"]:
        current["image"] = usable_image(banner.get("url"))
    if not current["image"]:
        match = re.search(r'(?:property="og:image"|name="twitter:image") content="(https:[^"]+)"', text)
        current["image"] = usable_image(match.group(1) if match else "")
    if not current["logo"] and logos:
        current["logo"] = good_image(logos[0])
    return current


def empty_pages():
    return {page: {"sections": [], "tables": []} for page in PAGES}


def youtube_id(url):
    if not url or "placeholder" in str(url).lower():
        return ""
    match = re.search(r"(?:youtu\.be/|youtube\.com/(?:embed/|watch\?v=|shorts/))([\w-]{11})", str(url))
    return match.group(1) if match else ""


def good_image(url):
    if not isinstance(url, str) or not url.startswith("http"):
        return ""
    if "placeholder" in url:
        return ""
    return url


def as_package(value):
    if value is None or value == "":
        return ""
    if isinstance(value, str) and not re.fullmatch(r"[\d.]+", value.strip()):
        return value.strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number <= 0:
        return ""
    if number >= 10000:
        number = number / 100000
    if number >= 100:
        crore = number / 100
        text = f"{crore:.2f}".rstrip("0").rstrip(".")
        return f"₹{text}Cr"
    text = f"{number:.2f}".rstrip("0").rstrip(".")
    return f"₹{text}L"


def name_tokens(name):
    words = re.findall(r"[a-z0-9]+", (name or "").lower())
    return [word for word in words if word not in STOP_WORDS and len(word) > 1]


def cfm_records():
    if getattr(cfm_records, "cache", None) is not None:
        return cfm_records.cache
    records = []
    if CFM_DIR.exists():
        for path in CFM_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            images = data.get("bannerImages") or data.get("images") or []
            image = good_image(data.get("bannerImage"))
            if not image:
                image = next((good_image(item) for item in images if good_image(item)), "")
            if not image:
                image = good_image(data.get("logoUrl"))
            placement = data.get("placement") if isinstance(data.get("placement"), dict) else {}
            ranking = data.get("ranking") if isinstance(data.get("ranking"), dict) else {}
            records.append(
                {
                    "tokens": set(name_tokens(data.get("name"))),
                    "image": image,
                    "video": youtube_id(data.get("videoUrl")),
                    "average": as_package(placement.get("averagePackage")),
                    "highest": as_package(placement.get("highestPackage")),
                    "nirf": ranking.get("nirfRank"),
                    "nirf_year": ranking.get("nirfYear"),
                }
            )
    cfm_records.cache = records
    return records


def match_cfm(name):
    want = name_tokens(name)
    if len(want) < 2:
        return None
    best = None
    for record in cfm_records():
        if all(token in record["tokens"] for token in want):
            if best is None or len(record["tokens"]) < len(best["tokens"]):
                best = record
    return best


def html_media(slug):
    image = ""
    video = ""
    folder = COLLEGE_DIR / slug
    if not folder.is_dir():
        return image, video
    for page in PAGES:
        path = folder / f"{page}.html"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not image:
            match = re.search(r'(?:property="og:image"|name="twitter:image") content="(https:[^"]+)"', text)
            image = good_image(match.group(1) if match else "")
        if not video:
            match = re.search(r"(?:youtu\.be/|youtube\.com/(?:embed/|watch\?v=|shorts/))([\w-]{11})", text)
            if match and "placeholder" not in match.group(0):
                video = match.group(1)
        if image and video:
            break
    return image, video


@lru_cache(maxsize=512)
def college_media(slug: str, name: str):
    image, video = ("", "")
    if re.fullmatch(r"[a-z0-9-]+", slug or ""):
        image, video = html_media(slug)
    extra = match_cfm(name) or {}
    return {
        "image": image or extra.get("image") or "",
        "video_id": video or extra.get("video") or "",
        "average_package": extra.get("average") or "",
        "highest_package": extra.get("highest") or "",
        "nirf_rank": extra.get("nirf"),
        "nirf_year": extra.get("nirf_year"),
    }


@lru_cache(maxsize=256)
def saved_pages(slug: str):
    pages = empty_pages()
    if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
        return pages
    folder = COLLEGE_DIR / slug
    if not folder.is_dir():
        return pages
    groups = []
    faqs = []
    seen = set()
    highlight = blank_highlight()
    for page in PAGES:
        path = folder / f"{page}.html"
        if not path.exists() or path.stat().st_size == 0:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        parser = html.HTMLParser(recover=True, huge_tree=True)
        document = html.fromstring(text.encode("utf-8"), parser=parser)
        root = page_root(document)
        merge_highlight(highlight, text, root)
        prepare(root)
        pages[page] = {"sections": read_sections(root), "tables": read_tables(root)}
        if page == "courses":
            groups = course_groups(root)
        for item in page_faqs(root):
            key = item["question"].lower()
            if key in seen:
                continue
            seen.add(key)
            faqs.append(item)
    if not highlight["highest_package"]:
        highlight["highest_package"] = stat_value(pages["placement"]["tables"], "highest package")
    if not highlight["average_package"]:
        highlight["average_package"] = stat_value(pages["placement"]["tables"], "average package")
    pages["highlight"] = highlight
    pages["course_groups"] = groups
    pages["faqs"] = faqs[:24]
    return pages
