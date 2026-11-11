-- Admission Setu, first database.
-- Safe to run again: existing tables are left as they are.
--
-- Money: fee_per_year is rupees. Package columns are lakhs per year (LPA).
-- Prediction reads the seats table only. That table is the official JoSAA and MCC files.
-- College pages read colleges, courses, and the profile JSON.

CREATE TABLE IF NOT EXISTS colleges (
    id                  bigserial PRIMARY KEY,
    source              text NOT NULL,
    source_slug         text NOT NULL,
    name                text NOT NULL,
    city                text NOT NULL DEFAULT '',
    state               text NOT NULL DEFAULT '',
    ownership           text NOT NULL DEFAULT '',
    streams             text[] NOT NULL DEFAULT '{}',
    exams               text[] NOT NULL DEFAULT '{}',
    established         integer,
    website             text NOT NULL DEFAULT '',
    phone               text NOT NULL DEFAULT '',
    overview            text NOT NULL DEFAULT '',
    fee_per_year        bigint,
    fee_label           text NOT NULL DEFAULT '',
    avg_package_lpa     numeric(8, 2),
    highest_package_lpa numeric(8, 2),
    median_package_lpa  numeric(8, 2),
    nirf_rank           integer,
    nirf_year           integer,
    nirf_category       text NOT NULL DEFAULT '',
    hostel              boolean,
    profile             jsonb NOT NULL DEFAULT '{}',
    UNIQUE (source, source_slug)
);

CREATE TABLE IF NOT EXISTS courses (
    id          bigserial PRIMARY KEY,
    college_id  bigint NOT NULL REFERENCES colleges (id) ON DELETE CASCADE,
    name        text NOT NULL,
    level       text NOT NULL DEFAULT '',
    duration    text NOT NULL DEFAULT '',
    fee_amount  bigint,
    eligibility text NOT NULL DEFAULT ''
);

-- One row is one counselling seat: college + branch + quota + category + gender.
CREATE TABLE IF NOT EXISTS seats (
    id            bigserial PRIMARY KEY,
    year          integer NOT NULL,
    round         text NOT NULL,
    exam          text NOT NULL,
    institute     text NOT NULL,
    state         text NOT NULL,
    program       text NOT NULL,
    quota         text NOT NULL,
    category      text NOT NULL,
    gender        text NOT NULL,
    opening_rank  integer NOT NULL,
    closing_rank  integer NOT NULL,
    preparatory   boolean NOT NULL DEFAULT false,
    UNIQUE (year, round, exam, institute, program, quota, category, gender)
);

-- Admin edits. Import does not touch this table, so a later import keeps the changes.
CREATE TABLE IF NOT EXISTS college_overrides (
    source_slug       text PRIMARY KEY,
    name              text NOT NULL DEFAULT '',
    city              text NOT NULL DEFAULT '',
    state             text NOT NULL DEFAULT '',
    ownership         text NOT NULL DEFAULT '',
    overview          text NOT NULL DEFAULT '',
    fee_label         text NOT NULL DEFAULT '',
    nirf_rank         integer,
    established_year  text NOT NULL DEFAULT '',
    average_package   text NOT NULL DEFAULT '',
    highest_package   text NOT NULL DEFAULT '',
    rating            text NOT NULL DEFAULT '',
    reviews           text NOT NULL DEFAULT '',
    image             text NOT NULL DEFAULT '',
    logo              text NOT NULL DEFAULT '',
    website           text NOT NULL DEFAULT '',
    phone             text NOT NULL DEFAULT '',
    streams           text[] NOT NULL DEFAULT '{}',
    hidden            boolean NOT NULL DEFAULT false,
    content           jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at        timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE college_overrides ADD COLUMN IF NOT EXISTS content jsonb NOT NULL DEFAULT '{}'::jsonb;

-- One student. The same mobile number keeps the same public_id.
CREATE TABLE IF NOT EXISTS students (
    id          bigserial PRIMARY KEY,
    public_id   text NOT NULL UNIQUE,
    name        text NOT NULL,
    mobile      text NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- One row is one click on Predict colleges.
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
);

CREATE INDEX IF NOT EXISTS colleges_name_lower ON colleges (lower(name));
CREATE INDEX IF NOT EXISTS colleges_state ON colleges (state);
CREATE INDEX IF NOT EXISTS courses_college ON courses (college_id);
CREATE INDEX IF NOT EXISTS seats_lookup ON seats (exam, category, preparatory, closing_rank);
CREATE INDEX IF NOT EXISTS seats_institute ON seats (institute);
CREATE INDEX IF NOT EXISTS predictions_student ON predictions (student_id, created_at DESC);
