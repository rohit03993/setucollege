# College predictor research

Looked at on 26 October 2026:

- https://collegedunia.com/college-predictor
- https://collegedunia.com/jee-main-college-predictor
- https://collegedunia.com/neet-college-predictor

This note records how that public tool works, and what Admission Setu can calculate with the college data already saved.

## What their hub page does

The hub is a menu, not the calculation. The student picks a course and an exam, or opens one exam card. Each card shows how many colleges they cover, the exam date, and whether the exam is national or state-level. JEE Main, CUET, JEE Advanced, TS EAMCET, NEET, CAT, GATE, MAT, NMAT, and several others each have their own predictor.

Each exam is a separate tool because the rank lists are different. A JEE Main rank cannot be compared with a NEET rank.

## What the student enters

JEE Main form (JoSAA-style, for NITs, IIITs, and GFTIs):

- Marks out of 300, or a rank. One of the two.
- Category: General, SC, ST, EWS, OBC-NCL.
- Home state.
- Gender: male or female.

NEET form:

- Marks out of 720, or a rank.
- Category: General, SC, ST, OBC, EWS.
- State.
- Course: MBBS or BDS.

After Check results, the college list sits behind a register form (name, email, mobile, city, course). That form collects a lead. It is not part of the rank maths.

Their own page says the JEE Main tool uses previous years' admission data, opening ranks, and closing ranks, and that the result changes with category, gender, and home state. They also say this JEE Main tool does not predict IITs, because IIT seats use JEE Advanced.

## How a prediction is actually calculated

There is no hidden score built from fees or packages. The comparison is against last year's closing rank for the same seat.

A counselling table (JoSAA for engineering, MCC and state lists for NEET) has one row per seat type:

- year
- round (round 1, round 2, and so on)
- college
- branch or course
- quota (home state, other state, or all India)
- category (open, EWS, OBC-NCL, SC, ST, and PwD variants)
- gender pool (gender-neutral, or female-only)
- opening rank
- closing rank

The student's rank is a number where a smaller number is a better rank. For one seat:

- Student rank is comfortably better than last year's closing rank: safer chance.
- Student rank is close to that closing rank: possible, often decided by the round.
- Student rank is worse than that closing rank: unlikely on last year's trend.

Home state matters for NITs because the same branch has a different closing rank for home-state seats and for other-state seats. Gender matters because female-only seats have their own closing rank. Category matters because each category has its own list.

If the student types marks instead of a rank, the tool first estimates a rank from last year's marks-to-rank table, then does the same comparison. That estimate is weaker than a real rank, because marks shift by shift and by year.

A useful result row is: college, branch, quota, last year's closing rank, the student's rank, and a chance label. Fees, average package, and NIRF belong beside that row so the family can judge the college. They do not create the chance label.

## What our saved data can and cannot do

College For Me (261 colleges) and CollegeDekho (about 4,405 B.Tech colleges) are college profiles: name, city, fees, courses, admission notes, placements, and rankings.

College For Me has a Cutoffs sheet, and some CollegeDekho admission pages mention cutoffs. Those rows are whatever the college page published. They are not a full JoSAA or MCC table. Most rows will be missing the year, the round, the quota, the category, the gender pool, or the branch. A predictor that only uses those sheets will miss most seats and will mix unlike ranks together.

Fees, packages, and NIRF from those two sites are the right facts to show after a college matches. They are the wrong facts to calculate the match.

## Where the latest ranks come from

Checked on 26 October 2026.

JEE Main seats at NITs, IIITs, and GFTIs, and JEE Advanced seats at IITs, use the JoSAA 2026 opening and closing ranks. Round 5 is the last round for 2026. The official pages are:

- https://josaa.nic.in/or-cr/
- https://josaa.nic.in/document/opening-and-closing-ranks-2026/
- https://josaa.admissions.nic.in/applicant/seatmatrix/OpeningClosingRankArchieve.aspx

The full Round 5 table is saved as `prediction\josaa-2026-round-5-orcr.csv`. It has 12,936 seats. Each institute now has its campus state. Columns are year, round, exam, institute, state, program, quota, seat type, gender, opening rank, closing rank, and whether the rank is from the preparatory list. A student from that state is compared with the home-state quota. A student from any other state is compared with the other-state quota. All-India quota is kept for every student. NIT Srinagar uses the Jammu and Kashmir quota, the Ladakh quota, or the other-state quota. NIT Goa also has a Goa quota for a student from Goa. IIT and IISc rows are marked JEE Advanced (3,380 seats). NIT, IIIT, IIEST, and GFTI rows are marked JEE Main (9,556 seats). Open seats use the common rank list. EWS, OBC-NCL, SC, and ST seats use that category's own rank. A JEE Main rank is only compared with JEE Main rows. A JEE Advanced rank is only compared with JEE Advanced rows.

NEET all-India seats are in `prediction\mcc-2026-final-orcr.csv`. MCC does not publish an opening-and-closing-rank file. The rows are calculated from the official 2026 Round 1 allotment (this carries the seat category), the list of candidates who joined through Round 3 (this carries the final college), the Round 3 allotment category where that round gave the seat, and the stray-vacancy allotment. A row is one college, one course (MBBS, BDS, or B.Sc Nursing), one quota, and one category. All India, Open Seat Quota, and Self-Financed Merit Seat apply to a student from any state. Delhi University, IP University, ESI, minority, and NRI quotas stay in the file and are not offered to every student. The 85 percent state-quota medical seats are not in this file. The official pages are on https://mcc.nic.in/.

## CollegeDekho is not the rank source

The files already saved under `college-dekho` are B.Tech college pages: course and fee, admission, and placement. Those pages describe how a college admits students. They do not hold the full JoSAA or MCC rank table, and they contain no NEET college list.

CollegeDekho does publish cutoff articles, and it sometimes hosts an older JoSAA PDF. Those articles are short extracts. Some rows leave out the branch, mix rounds, or show an opening rank that is worse than the closing rank. Use them only as a hint that a college took JEE or NEET. Download the rank rows from JoSAA and MCC.

## A first version we can build

Start with one exam: JEE Main, latest JoSAA year, NITs, IIITs, and GFTIs.

1. Store the official closing ranks as rows with the columns above.
2. Ask for rank, category, home state, and gender. Marks can wait.
3. Keep only rows for that category and the gender pool that applies.
4. For a college in the student's state, show the home-state quota. For every other college, show the other-state quota.
5. Compare the student's rank with the closing rank and label the row safer, possible, or unlikely.
6. Where we already have that college, attach yearly fee, average package, and NIRF from our catalogue and link to the college page.

Say clearly on the page that the label follows last year's closing rank, and that a new year's counselling can move. Do not present it as a guaranteed seat.

NEET is the same shape with different columns (marks out of 720, MBBS or BDS, all-India versus state). Add it after the JEE Main table is trustworthy. State and private exams come later, one rank list each.
