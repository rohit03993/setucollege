"""Predict a college from the JoSAA or MCC 2026 rank files.

Examples, from the project folder:

python prediction\\predict.py --rank 15000 --category OPEN --gender male --home-state Delhi --exam "JEE Main"
python prediction\\predict.py --rank 5000 --category OPEN --gender female --home-state Delhi --exam NEET --course MBBS
"""

import argparse
import csv
from pathlib import Path

from institutes import HOME_STATES
from match import predict

HERE = Path(__file__).resolve().parent
RANK_FILE = HERE / "josaa-2026-round-5-orcr.csv"
MCC_FILE = HERE / "mcc-2026-final-orcr.csv"
RESULT_FILE = HERE / "last-result.csv"

CATEGORIES = {
    "OPEN": "OPEN",
    "GENERAL": "OPEN",
    "EWS": "EWS",
    "OBC-NCL": "OBC-NCL",
    "OBC": "OBC-NCL",
    "OBCNCL": "OBC-NCL",
    "SC": "SC",
    "ST": "ST",
}


def load_seats(path=RANK_FILE):
    seats = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            seats.append(
                {
                    "college": row["Institute"],
                    "college_state": row["State"],
                    "branch": row["Academic Program Name"],
                    "quota": row["Quota"],
                    "category": row["Seat Type"],
                    "gender": row["Gender"],
                    "closing_rank": int(row["Closing Rank"]),
                    "course": row["Academic Program Name"] if row["Exam"] == "NEET" else "",
                    "exam": row["Exam"],
                    "preparatory": row["Preparatory"],
                }
            )
    return seats


def load_all_seats():
    seats = load_seats(RANK_FILE)
    if MCC_FILE.exists():
        seats.extend(load_seats(MCC_FILE))
    return seats


def write_result(rows):
    with RESULT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "chance",
                "college",
                "college_state",
                "branch",
                "quota",
                "gender",
                "closing_rank",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Match a student to JoSAA 2026 Round 5 seats.")
    parser.add_argument("--rank", type=int, required=True)
    parser.add_argument("--category", required=True, help="OPEN, EWS, OBC-NCL, SC, or ST")
    parser.add_argument("--gender", required=True, choices=("male", "female"))
    parser.add_argument("--home-state", required=True, dest="home_state")
    parser.add_argument("--exam", default="JEE Main", choices=("JEE Main", "JEE Advanced", "NEET"))
    parser.add_argument("--course", default="", help="MBBS, BDS, or B.Sc Nursing. Required for NEET.")
    args = parser.parse_args()

    category = CATEGORIES.get(args.category.strip().upper())
    if category is None:
        raise SystemExit("Category must be OPEN, EWS, OBC-NCL, SC, or ST.")
    if args.home_state not in HOME_STATES:
        raise SystemExit("Home state must be one of: " + ", ".join(HOME_STATES))
    if args.rank < 1:
        raise SystemExit("Rank must be 1 or more.")
    course = args.course.strip()
    if args.exam == "NEET" and course not in ("MBBS", "BDS", "B.Sc Nursing"):
        raise SystemExit("NEET needs --course MBBS, BDS, or B.Sc Nursing.")

    student = {
        "rank": args.rank,
        "category": category,
        "gender": args.gender,
        "home_state": args.home_state,
        "exam": args.exam,
        "course": course,
    }
    rows = predict(student, load_all_seats())
    write_result(rows)
    counts = {"safer": 0, "possible": 0, "unlikely": 0}
    for row in rows:
        counts[row["chance"]] += 1
    print(
        f"{args.exam} rank {args.rank}, {category}, {args.gender}, {args.home_state}"
    )
    print(
        f"{counts['safer']} safer, {counts['possible']} possible, {counts['unlikely']} unlikely"
    )
    shown = [row for row in rows if row["chance"] in ("safer", "possible")][:20]
    if not shown:
        shown = rows[:10]
    for row in shown:
        print(
            f"{row['chance']:9} {row['closing_rank']:7} {row['quota']:3} {row['college']} | {row['branch']}"
        )
    print(f"Full list: {RESULT_FILE}")


if __name__ == "__main__":
    main()
