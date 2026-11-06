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


def chance(student_rank, closing_rank):
    if student_rank <= closing_rank * 0.85:
        return "safer"
    if student_rank <= closing_rank:
        return "possible"
    return "unlikely"


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
                "closing_rank": seat["closing_rank"],
                "chance": chance(student["rank"], seat["closing_rank"]),
            }
        )
    rows.sort(key=lambda row: (CHANCE_ORDER[row["chance"]], row["closing_rank"]))
    return rows
