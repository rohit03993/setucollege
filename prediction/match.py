import re

"""Compare a student with one JoSAA seat.

A smaller rank number is a better rank.
Safer: clearly better than last year's closing rank.
Possible: still inside that closing rank.
Unlikely: worse than that closing rank.
"""

NIT_SRINAGAR = "National Institute of Technology, Srinagar"

# MCC seats with these quotas are open to a student from any state.
# State-quota MBBS seats are not in the MCC file.
NEET_NATIONAL_QUOTAS = {
    "All India",
    "Open Seat Quota",
    "Self-Financed Merit Seat",
}

CHANCE_ORDER = {"safer": 0, "possible": 1, "unlikely": 2}
BAND_ORDER = {"very-high": 0, "high": 1, "medium": 2, "low": 3, "very-low": 4}
REACHABLE = {"very-high", "high", "medium"}
# Seats past the rank stay in the list, but only the ones nearest the student.
STRETCH_LIMIT = 12
# First matching family wins, so a specific name is not swallowed by a broader one.
BRANCH_FAMILIES = (
    ("Architecture", ("architecture", "planning")),
    ("Computer Science", (
        "computer science", "computer engineering", "information technology", "data science",
        "artificial intelligence", "machine learning", "software", "computing",
    )),
    ("Biotechnology", ("biotech", "bio-technology", "biological", "biomedical")),
    ("Chemical", ("chemical", "petrochemical", "polymer")),
    ("Electrical & Electronics", (
        "electrical", "electronic", "instrumentation", "electric mobility", "vlsi", "microelectronic",
    )),
    ("Aerospace", ("aerospace", "aeronautical", "aviation")),
    ("Mechanical", (
        "mechanical", "production", "industrial", "manufacturing",
        "automobile", "mechatronics", "engineering design", "robotics", "automation",
    )),
    ("Civil", ("civil", "structural", "construction", "infrastructure")),
    ("Materials", ("metallurg", "material")),
    ("Mining", ("mining", "mineral")),
    ("Food & Agriculture", ("food", "agricultur", "dairy")),
    ("Textile & Design", (
        "textile", "handloom", "carpet", "fashion", "apparel",
        "design", "printing", "packaging",
    )),
    ("Naval & Ocean", ("naval", "ocean", "marine")),
    ("Energy & Environment", ("energy", "environment")),
    ("Sciences", ("physics", "mathematics", "chemistry", "engineering science", "geology")),
    ("Pharmacy", ("pharmac",)),
)
FAMILY_ORDER = [label for label, _keys in BRANCH_FAMILIES] + [
    "General Engineering", "MBBS", "BDS", "Nursing", "Other",
]
# JoSAA printed a few names wrong. Correct them before grouping or display.
SPELLING = (
    ("elctrical", "Electrical"),
    ("electical", "Electrical"),
    ("enginering", "Engineering"),
    ("technolgy", "Technology"),
)
# Whole words only. "ai" must not match inside "main", and "cse" is not "computer science".
ABBREVIATIONS = (
    ("Computer Science", {"cse", "cs", "it", "ai", "ml", "ds"}),
    ("Electrical & Electronics", {"ece", "eee", "ee", "vlsi", "entc"}),
    ("Mechanical", {"mech"}),
    ("Chemical", {"chem"}),
)


def chance(student_rank, closing_rank):
    if student_rank <= closing_rank * 0.85:
        return "safer"
    if student_rank <= closing_rank:
        return "possible"
    return "unlikely"


def probability(student_rank, closing_rank):
    """How the rank sits against one closing rank.

    Very high and High are clearly inside it. Medium is still inside it.
    Low is just past it. Very low is well past it.
    """
    if student_rank <= closing_rank * 0.70:
        return "very-high"
    if student_rank <= closing_rank * 0.85:
        return "high"
    if student_rank <= closing_rank:
        return "medium"
    if student_rank <= closing_rank * 1.15:
        return "low"
    return "very-low"


def tidy_branch(name):
    """Correct known spelling mistakes in an official programme name."""
    text = " ".join(str(name or "").split())
    for wrong, right in SPELLING:
        text = re.sub(wrong, right, text, flags=re.IGNORECASE)
    return text


def branch_family(name):
    """Group an official programme name into a short branch family.

    Abbreviations are read as whole words, so CSE (AI and ML) is Computer Science
    and a word like "main" is not treated as AI.
    """
    text = " ".join(str(name or "").lower().replace("&", " and ").split())
    if text == "mbbs" or text.startswith("mbbs "):
        return "MBBS"
    if text == "bds" or text.startswith("bds ") or "dental" in text:
        return "BDS"
    if "nursing" in text:
        return "Nursing"
    words = set(re.findall(r"[a-z0-9]+", text))
    for label, shorts in ABBREVIATIONS:
        if words & shorts:
            return label
    for label, keys in BRANCH_FAMILIES:
        if any(key in text for key in keys):
            return label
    if "general engineering" in text:
        return "General Engineering"
    return "Other"


def family_counts(rows):
    """Families present in this list, common branches first."""
    counts = {}
    for row in rows:
        label = row.get("family") or "Other"
        counts[label] = counts.get(label, 0) + 1
    order = {label: index for index, label in enumerate(FAMILY_ORDER)}
    names = sorted(counts, key=lambda label: (order.get(label, len(order)), -counts[label], label))
    return [{"name": label, "count": counts[label]} for label in names]


def shortlist(rows, student_rank, stretch_limit=STRETCH_LIMIT):
    """Seats inside the rank, or the nearest seats within 15 percent when none are.

    A closing rank more than 15 percent better than the student is left off the list.
    """
    ranked = []
    counts = {name: 0 for name in BAND_ORDER}
    for row in rows:
        item = dict(row)
        item["branch"] = tidy_branch(row.get("branch"))
        item["probability"] = probability(student_rank, row["closing_rank"])
        item["family"] = branch_family(item["branch"])
        counts[item["probability"]] += 1
        ranked.append(item)
    reachable = [row for row in ranked if row["probability"] in REACHABLE]
    reachable.sort(
        key=lambda row: (
            BAND_ORDER[row["probability"]],
            abs(row["closing_rank"] - student_rank),
            row["closing_rank"],
        )
    )
    if reachable:
        return reachable, counts
    near = [row for row in ranked if row["probability"] == "low"]
    near.sort(key=lambda row: (abs(row["closing_rank"] - student_rank), -row["closing_rank"]))
    return near[:stretch_limit], counts


def quota_matches(home_state, institute_state, quota, institute=""):
    """True when this student is allowed to compete for this quota."""
    if quota == "AI" or quota in NEET_NATIONAL_QUOTAS:
        return True
    if quota == "HS":
        return home_state == institute_state
    if quota == "OS":
        # Srinagar has no home-state row. JK and Ladakh use their own quotas.
        if institute == NIT_SRINAGAR:
            return home_state not in ("Jammu and Kashmir", "Ladakh")
        return home_state != institute_state
    if quota == "GO":
        return home_state == "Goa"
    if quota == "JK":
        return home_state == "Jammu and Kashmir"
    if quota == "LA":
        return home_state == "Ladakh"
    return False


def gender_matches(student_gender, seat_gender):
    if student_gender == "male":
        return seat_gender == "Gender-Neutral"
    if student_gender == "female":
        return seat_gender == "Gender-Neutral" or seat_gender.startswith("Female-only")
    return False


def matches(student, seat):
    if seat.get("exam") and seat["exam"] != student["exam"]:
        return False
    if seat.get("preparatory") == "Yes":
        return False
    if student.get("course") and seat.get("course") and seat["course"] != student["course"]:
        return False
    if seat["category"] != student["category"]:
        return False
    if not gender_matches(student["gender"], seat["gender"]):
        return False
    return quota_matches(
        student["home_state"],
        seat["college_state"],
        seat["quota"],
        seat["college"],
    )


def predict(student, seats):
    rows = []
    for seat in seats:
        if not matches(student, seat):
            continue
        rows.append(
            {
                "college": seat["college"],
                "college_state": seat["college_state"],
                "branch": seat["branch"],
                "quota": seat["quota"],
                "gender": seat["gender"],
                "opening_rank": seat.get("opening_rank"),
                "closing_rank": seat["closing_rank"],
                "chance": chance(student["rank"], seat["closing_rank"]),
            }
        )
    rows.sort(key=lambda row: (CHANCE_ORDER[row["chance"]], row["closing_rank"]))
    return rows
