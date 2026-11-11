"""Create the students and predictions tables. Safe to run again.

From the project folder:

    python db/apply_students.py
"""

import os
from pathlib import Path

import psycopg

ENV_FILE = Path(__file__).resolve().parent / ".env"
STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS students (
        id          bigserial PRIMARY KEY,
        public_id   text NOT NULL UNIQUE,
        name        text NOT NULL,
        mobile      text NOT NULL UNIQUE,
        created_at  timestamptz NOT NULL DEFAULT now()
    )
    """,
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


def load_env(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def main():
    load_env(ENV_FILE)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit(f"Add DATABASE_URL to {ENV_FILE}")
    with psycopg.connect(url) as conn:
        for statement in STATEMENTS:
            conn.execute(statement)
    print("students and predictions are ready")


if __name__ == "__main__":
    main()
