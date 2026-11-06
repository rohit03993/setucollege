"""Test the predictor match.

The made-up rows check the labels. The JoSAA file check confirms each
institute has a state and that home state, Srinagar, and Goa pick the right quota.
Run from the project folder: python prediction\\test_match.py
"""

from pathlib import Path

from institutes import INSTITUTE_STATE
from match import NIT_SRINAGAR, chance, predict
from predict import MCC_FILE, RANK_FILE, load_seats


# Invented seats. Two colleges, two branches, so home state and gender can be checked.
SEATS = [
    {
        "college": "NIT Karnataka",
        "college_state": "Karnataka",
        "branch": "CSE",
        "quota": "HS",
        "category": "OPEN",
        "gender": "Gender-Neutral",
        "closing_rank": 3000,
    },
    {
        "college": "NIT Karnataka",
        "college_state": "Karnataka",
        "branch": "CSE",
        "quota": "OS",
        "category": "OPEN",
        "gender": "Gender-Neutral",
        "closing_rank": 1500,
    },
    {
        "college": "NIT Karnataka",
        "college_state": "Karnataka",
        "branch": "CSE",
        "quota": "OS",
        "category": "OPEN",
        "gender": "Female-only",
        "closing_rank": 2500,
    },
    {
        "college": "NIT Karnataka",
        "college_state": "Karnataka",
        "branch": "CSE",
        "quota": "OS",
        "category": "SC",
        "gender": "Gender-Neutral",
        "closing_rank": 8000,
    },
    {
        "college": "NIT Rourkela",
        "college_state": "Odisha",
        "branch": "Mechanical",
        "quota": "OS",
        "category": "OPEN",
        "gender": "Gender-Neutral",
        "closing_rank": 20000,
    },
    {
        "college": "NIT Rourkela",
        "college_state": "Odisha",
        "branch": "Mechanical",
        "quota": "HS",
        "category": "OPEN",
        "gender": "Gender-Neutral",
        "closing_rank": 28000,
    },
]


def one(rows, college, branch):
    found = [row for row in rows if row["college"] == college and row["branch"] == branch]
    assert len(found) == 1, found
    return found[0]


def test_safer_possible_unlikely():
    # Closing rank 20000. 15000 is under 85 percent, 18000 is inside, 25000 is outside.
    assert chance(15000, 20000) == "safer"
    assert chance(18000, 20000) == "possible"
    assert chance(25000, 20000) == "unlikely"


def test_home_state_uses_home_quota():
    student = {
        "rank": 2000,
        "category": "OPEN",
        "home_state": "Karnataka",
        "gender": "male",
    }
    row = one(predict(student, SEATS), "NIT Karnataka", "CSE")
    assert row["quota"] == "HS"
    assert row["closing_rank"] == 3000
    assert row["chance"] == "safer"


def test_other_state_uses_other_quota():
    student = {
        "rank": 1400,
        "category": "OPEN",
        "home_state": "Delhi",
        "gender": "male",
    }
    row = one(predict(student, SEATS), "NIT Karnataka", "CSE")
    assert row["quota"] == "OS"
    assert row["closing_rank"] == 1500
    assert row["chance"] == "possible"


def test_category_does_not_mix():
    student = {
        "rank": 5000,
        "category": "SC",
        "home_state": "Delhi",
        "gender": "male",
    }
    row = one(predict(student, SEATS), "NIT Karnataka", "CSE")
    assert row["closing_rank"] == 8000
    assert row["chance"] == "safer"


def test_male_skips_female_only_seat():
    student = {
        "rank": 2000,
        "category": "OPEN",
        "home_state": "Delhi",
        "gender": "male",
    }
    row = one(predict(student, SEATS), "NIT Karnataka", "CSE")
    assert row["gender"] == "Gender-Neutral"
    assert row["chance"] == "unlikely"


def test_female_can_use_female_only_seat():
    student = {
        "rank": 2000,
        "category": "OPEN",
        "home_state": "Delhi",
        "gender": "female",
    }
    rows = predict(student, SEATS)
    nitk = [row for row in rows if row["college"] == "NIT Karnataka"]
    assert {row["gender"] for row in nitk} == {"Gender-Neutral", "Female-only"}
    female_only = [row for row in nitk if row["gender"] == "Female-only"][0]
    # 2000 is within 85 percent of 2500, so this seat is safer.
    assert female_only["chance"] == "safer"


def seat(college, state, quota, closing, category="OPEN", gender="Gender-Neutral", branch="CSE"):
    return {
        "college": college,
        "college_state": state,
        "branch": branch,
        "quota": quota,
        "category": category,
        "gender": gender,
        "closing_rank": closing,
    }


def test_all_india_quota_is_kept_for_every_state():
    seats = [seat("IIIT Guwahati", "Assam", "AI", 10000)]
    student = {"rank": 5000, "category": "OPEN", "home_state": "Delhi", "gender": "male"}
    assert predict(student, seats)[0]["quota"] == "AI"


def test_srinagar_uses_jk_ladakh_or_other_state():
    seats = [
        seat(NIT_SRINAGAR, "Jammu and Kashmir", "OS", 50000),
        seat(NIT_SRINAGAR, "Jammu and Kashmir", "JK", 80000),
        seat(NIT_SRINAGAR, "Jammu and Kashmir", "LA", 90000),
    ]
    jk = {"rank": 10000, "category": "OPEN", "home_state": "Jammu and Kashmir", "gender": "male"}
    ladakh = {"rank": 10000, "category": "OPEN", "home_state": "Ladakh", "gender": "male"}
    delhi = {"rank": 10000, "category": "OPEN", "home_state": "Delhi", "gender": "male"}
    assert {row["quota"] for row in predict(jk, seats)} == {"JK"}
    assert {row["quota"] for row in predict(ladakh, seats)} == {"LA"}
    assert {row["quota"] for row in predict(delhi, seats)} == {"OS"}


def test_goa_student_keeps_home_and_goa_quota():
    college = "National Institute of Technology Goa"
    seats = [
        seat(college, "Goa", "HS", 20000),
        seat(college, "Goa", "OS", 10000),
        seat(college, "Goa", "GO", 30000),
    ]
    goa = {"rank": 5000, "category": "OPEN", "home_state": "Goa", "gender": "male"}
    delhi = {"rank": 5000, "category": "OPEN", "home_state": "Delhi", "gender": "male"}
    assert {row["quota"] for row in predict(goa, seats)} == {"HS", "GO"}
    assert {row["quota"] for row in predict(delhi, seats)} == {"OS"}


def test_real_file_states_and_quotas():
    assert RANK_FILE == Path(__file__).resolve().parent / "josaa-2026-round-5-orcr.csv"
    seats = load_seats()
    names = {seat["college"] for seat in seats}
    assert names == set(INSTITUTE_STATE)
    for seat in seats:
        assert seat["college_state"] == INSTITUTE_STATE[seat["college"]]

    def quotas(home_state, college):
        student = {
            "rank": 1,
            "category": "OPEN",
            "home_state": home_state,
            "gender": "male",
            "exam": "JEE Main",
        }
        return {
            row["quota"]
            for row in predict(student, seats)
            if row["college"] == college and row["gender"] == "Gender-Neutral"
        }

    surathkal = "National Institute of Technology Karnataka, Surathkal"
    goa = "National Institute of Technology Goa"
    assert quotas("Karnataka", surathkal) == {"HS"}
    assert quotas("Delhi", surathkal) == {"OS"}
    assert quotas("Jammu and Kashmir", NIT_SRINAGAR) == {"JK"}
    assert quotas("Ladakh", NIT_SRINAGAR) == {"LA"}
    assert quotas("Delhi", NIT_SRINAGAR) == {"OS"}
    assert quotas("Goa", goa) == {"HS", "GO"}
    assert quotas("Delhi", goa) == {"OS"}
    jee_main = predict(
        {
            "rank": 15000,
            "category": "OPEN",
            "home_state": "Delhi",
            "gender": "male",
            "exam": "JEE Main",
        },
        seats,
    )
    assert jee_main
    assert all("Indian Institute of Technology" not in row["college"] for row in jee_main)


def test_neet_all_india_seat():
    seats = load_seats(MCC_FILE)
    assert seats
    assert all(seat["exam"] == "NEET" for seat in seats)
    student = {
        "rank": 1000,
        "category": "OPEN",
        "home_state": "Kerala",
        "gender": "female",
        "exam": "NEET",
        "course": "MBBS",
    }
    rows = predict(student, seats)
    aiims = [
        row
        for row in rows
        if row["college"] == "AIIMS, New Delhi" and row["quota"] == "Open Seat Quota"
    ]
    assert len(aiims) == 1
    assert aiims[0]["closing_rank"] <= 200
    assert aiims[0]["chance"] == "unlikely"
    assert all(
        row["quota"] in ("All India", "Open Seat Quota", "Self-Financed Merit Seat")
        for row in rows
    )


if __name__ == "__main__":
    test_safer_possible_unlikely()
    test_home_state_uses_home_quota()
    test_other_state_uses_other_quota()
    test_category_does_not_mix()
    test_male_skips_female_only_seat()
    test_female_can_use_female_only_seat()
    test_all_india_quota_is_kept_for_every_state()
    test_srinagar_uses_jk_ladakh_or_other_state()
    test_goa_student_keeps_home_and_goa_quota()
    test_real_file_states_and_quotas()
    test_neet_all_india_seat()
    print("11 checks passed. JoSAA home state and MCC all-India seats both match.")