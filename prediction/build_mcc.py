"""Build NEET closing ranks from the official MCC 2026 PDFs.

MCC does not publish an opening-and-closing-rank file. This reads:

- Revised Round 1 allotment, which has the seat category
- Admitted and joined candidates through Round 3, which has the final college
- Stray vacancy allotment, which is the last round

The PDFs list individual candidates, so they are not kept in this folder.
The output is one row per college, course, quota, and category.

Sources, from https://mcc.nic.in/ :

- Round 1 result II, 24 August 2026
- Admitted/joined up to Round 3
- Stray vacancy final allotment
"""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "_mcc_source"
OUT = HERE / "mcc-2026-final-orcr.csv"

QUOTAS = [
    "Employees State Insurance Scheme Nursing Quota (ESI-IP Quota Nursing)",
    "Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) DU Quota",
    "Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) IP Quota",
    "B.Sc Nursing Delhi NCR CW  Quota",
    "B.Sc Nursing Delhi NCR",
    "B.Sc Nursing All India",
    "B.Sc Nursing IP CW  Quota",
    "Aligarh Muslim University (AMU) Quota",
    "Employees State Insurance Scheme(ESI)",
    "Internal -Puducherry UT Domicile",
    "Non-Resident Indian(AMU)Quota",
    "Self-Financed Merit Seat",
    "Delhi University Quota",
    "Jain Minority Quota",
    "Jamia Internal Quota",
    "Muslim Minority Quota",
    "Muslim OBC Quota",
    "Muslim Women Quota",
    "Muslim ST Quota",
    "Muslim Quota",
    "IP University Quota",
    "Foreign Country Quota",
    "Non-Resident Indian",
    "Open Seat Quota",
    "(AMU) Self finance All India",
    "(AMU)Self finance internal",
    "Self finance All India",
    "All India",
]
SEAT_CATEGORIES = [
    "Open PwD",
    "OBC PwD",
    "EWS PwD",
    "SC PwD",
    "ST PwD",
    "Open",
    "OBC",
    "EWS",
    "SC",
    "ST",
]
CANDIDATE_CATEGORIES = [
    "General PwD",
    "EWS PwD",
    "OBC PwD",
    "SC PwD",
    "ST PwD",
    "General",
    "OBC",
    "EWS",
    "SC",
    "ST",
    "GNYes",
]
COURSES = r"MBBS|BDS|B\.Sc\.? Nursing"

SEAT_TYPE = {
    "Open": "OPEN",
    "OBC": "OBC-NCL",
    "EWS": "EWS",
    "SC": "SC",
    "ST": "ST",
    "Open PwD": "OPEN (PwD)",
    "OBC PwD": "OBC-NCL (PwD)",
    "EWS PwD": "EWS (PwD)",
    "SC PwD": "SC (PwD)",
    "ST PwD": "ST (PwD)",
}


def pdf_text(path):
    reader = PdfReader(str(path))
    parts = []
    for index, page in enumerate(reader.pages):
        if index and index % 400 == 0:
            print(f"  {path.name} page {index}/{len(reader.pages)}")
        parts.append(page.extract_text() or "")
    text = "\n".join(parts)
    text = re.sub(r"Page No\.\s*\d+.*", " ", text)
    text = re.sub(r"Page \d+ of \d+", " ", text)
    text = re.sub(r"ADMITTED/JOINED CANDIDATES UPTO ROUND 3 UG COUNSELING 2026", " ", text)
    text = re.sub(r"Rollno QuotaName AIR Institute Code Institute Subject AdmittedRound", " ", text)
    text = re.sub(r"SNo Rank Allotted Quota Allotted Institute Course AllotedCategory CandidateCategory Remarks", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def quota_pattern():
    names = sorted(QUOTAS, key=len, reverse=True)
    return "|".join(re.escape(name) for name in names)


def parse_allotment(text):
    """Round 1 and stray lists: rank, quota, institute, course, seat category."""
    start = re.compile(rf"(?:(?<=\s)|^)(\d+) (\d+) ({quota_pattern()}) ")
    tail = re.compile(
        rf"(.+?) ({COURSES}) ({'|'.join(SEAT_CATEGORIES)}) ({'|'.join(CANDIDATE_CATEGORIES)}) Allotted"
    )
    starts = list(start.finditer(text))
    rows = []
    failed = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        body = text[match.end() : end].strip()
        found = tail.match(body)
        if not found:
            if len(failed) < 8:
                failed.append(body[:140])
            continue
        rows.append(
            {
                "air": int(match.group(2)),
                "quota": match.group(3),
                "institute": found.group(1).strip(" ,"),
                "course": found.group(2).replace("B.Sc. Nursing", "B.Sc Nursing"),
                "category": found.group(3),
            }
        )
    return rows, failed


def parse_joined(text):
    """Joined list: final college and course, no category."""
    start = re.compile(rf"(\d{{7,12}}) ({quota_pattern()}) (\d+) (\d{{5,8}}) ")
    tail = re.compile(rf"(.+?) ({COURSES}) ([123])(?:\s|$)")
    starts = list(start.finditer(text))
    rows = []
    failed = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        body = text[match.end() : end].strip()
        found = tail.match(body)
        if not found:
            if len(failed) < 8:
                failed.append(body[:140])
            continue
        rows.append(
            {
                "air": int(match.group(3)),
                "quota": match.group(2),
                "code": match.group(4),
                "institute": found.group(1).strip(" ,"),
                "course": found.group(2).replace("B.Sc. Nursing", "B.Sc Nursing"),
            }
        )
    return rows, failed


def round3_categories(path):
    """Seat category for candidates who were allotted in Round 3.

    The Round 3 file is a wide table. The category sits in the right-hand
    columns, and only when that round gave the candidate a seat.
    """
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer, LTTextLine

    found = {}
    for page_index, page in enumerate(extract_pages(str(path))):
        if page_index and page_index % 400 == 0:
            print(f"  round3 layout page {page_index}")
        lines = []
        for element in page:
            if not isinstance(element, LTTextContainer):
                continue
            for line in element:
                if not isinstance(line, LTTextLine):
                    continue
                text = line.get_text().strip()
                if text:
                    lines.append((line.x0, line.y0, text))
        ranks = sorted(
            ((y, text) for x, y, text in lines if x < 40 and text.isdigit()),
            key=lambda item: -item[0],
        )
        for index, (y, rank) in enumerate(ranks):
            y_next = ranks[index + 1][0] if index + 1 < len(ranks) else -1
            tokens = [
                text
                for x, yy, text in lines
                if y_next + 2 < yy <= y + 8 and 970 <= x <= 1025
            ]
            course = [
                text
                for x, yy, text in lines
                if y_next + 2 < yy <= y + 8 and 890 <= x <= 940 and text in ("MBBS", "BDS")
            ]
            if not course or not tokens:
                continue
            label = " ".join(tokens)
            if label in SEAT_CATEGORIES:
                found[int(rank)] = label
    return found


def short_name(raw):
    parts = [part.strip() for part in re.sub(r"\s+", " ", raw).split(",") if part.strip()]
    if not parts:
        return raw.strip()
    if len(parts) == 1 or len(parts[0]) >= 18:
        return parts[0]
    return parts[0] + ", " + parts[1]


def build():
    print("reading round 1")
    round1, fail1 = parse_allotment(pdf_text(SOURCE / "round1.pdf"))
    print("round 1", len(round1), "unparsed", len(fail1))
    for sample in fail1[:3]:
        print("  FAIL", sample)

    print("reading joined")
    joined, failj = parse_joined(pdf_text(SOURCE / "joined.pdf"))
    print("joined", len(joined), "unparsed", len(failj))
    for sample in failj[:3]:
        print("  FAIL", sample)

    print("reading stray")
    stray, fails = parse_allotment(pdf_text(SOURCE / "stray.pdf"))
    print("stray", len(stray), "unparsed", len(fails))
    for sample in fails[:3]:
        print("  FAIL", sample)

    print("reading round 3 categories")
    round3 = round3_categories(SOURCE / "round3.pdf")
    print("round 3 categories", len(round3))

    category_by_air = {row["air"]: row["category"] for row in round1}
    category_by_air.update(round3)
    for row in stray:
        category_by_air[row["air"]] = row["category"]

    people = []
    missing_category = 0
    for row in joined:
        category = category_by_air.get(row["air"])
        if category is None:
            missing_category += 1
            continue
        people.append({**row, "category": category})
    joined_airs = {row["air"] for row in joined}
    for row in stray:
        if row["air"] in joined_airs:
            continue
        people.append(
            {
                "air": row["air"],
                "quota": row["quota"],
                "code": "",
                "institute": row["institute"],
                "course": row["course"],
                "category": row["category"],
            }
        )
    print("people", len(people), "joined without a category", missing_category)

    code_name = defaultdict(Counter)
    for person in people:
        if person["code"]:
            code_name[person["code"]][short_name(person["institute"])] += 1
    name_to_code = {}
    for code, counts in code_name.items():
        name_to_code[counts.most_common(1)[0][0]] = code

    groups = defaultdict(list)
    labels = {}
    for person in people:
        name = short_name(person["institute"])
        code = person["code"] or name_to_code.get(name, "")
        key = (code or name, person["course"], person["quota"], person["category"])
        groups[key].append(person["air"])
        labels[key] = name if not code else code_name[code].most_common(1)[0][0]

    fieldnames = [
        "Year",
        "Round",
        "Exam",
        "Institute",
        "State",
        "Academic Program Name",
        "Quota",
        "Seat Type",
        "Gender",
        "Opening Rank",
        "Closing Rank",
        "Preparatory",
    ]
    written = 0
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key, airs in sorted(groups.items(), key=lambda item: (labels[item[0]], item[0][1], item[0][2])):
            category = key[3]
            if category not in SEAT_TYPE:
                continue
            writer.writerow(
                {
                    "Year": "2026",
                    "Round": "Final",
                    "Exam": "NEET",
                    "Institute": labels[key],
                    "State": "All India",
                    "Academic Program Name": key[1],
                    "Quota": key[2],
                    "Seat Type": SEAT_TYPE[category],
                    "Gender": "Gender-Neutral",
                    "Opening Rank": min(airs),
                    "Closing Rank": max(airs),
                    "Preparatory": "No",
                }
            )
            written += 1
    print("wrote", written, "to", OUT.name)


if __name__ == "__main__":
    build()
