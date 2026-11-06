# College For Me

Site: https://www.collegeforme.in  
Colleges page: https://www.collegeforme.in/colleges  
Observed: 23 October 2026

College For Me is one custom web application. Colleges, counselling, exams, PG listings, online degrees, and Talk to Students are routes in that same app. It is not a WordPress, Wix, or other site-builder site.

---

## Platform

| Layer | Platform |
|---|---|
| Application | Next.js with React (App Router) |
| Build | Turbopack |
| Styling | Tailwind CSS |
| Icons | Lucide |
| Hosting | Vercel |
| Images | Cloudinary |
| Data | Next.js route handlers under `/api` |
| Sign-in | Firebase Authentication with Google |
| Language | English, India (`en-IN`) |

How this was identified on https://www.collegeforme.in/colleges and the rest of the site:

| Layer | Evidence |
|---|---|
| Next.js, React, App Router | Pages load from `/_next`, and the browser requests React Server Component payloads |
| Turbopack | A turbopack script is included in the page |
| Tailwind CSS | Controls use utility classes such as `flex`, `h-11`, and `rounded-lg` |
| Lucide | The name `lucide` is inside the shipped JavaScript |
| Vercel | Response header `server: Vercel`, cache HIT, asset query `dpl_` deployment id. The edge path seen was Mumbai (`bom1`) to US East (`iad1`) |
| Cloudinary | College and mentor images load from `res.cloudinary.com`, across more than one Cloudinary account |
| Site API | Colleges: `/api/colleges/index` and `/api/college/{slug}`. Mentors: `/api/student-connect/...` |
| Firebase Google sign-in | Page scripts include `firebase` and `identitytoolkit`. Mentor signup says “Continue with Google” |
| Analytics | Pages post to `/api/analytics/track`. College search also requests `/api/ads` |

Record ids are CUID-shaped. That shape is commonly produced by Prisma. The database package itself is not visible from the browser, so Prisma is an inference.

These two services belong to Talk to Students, not to the college catalogue:

| Service | Role |
|---|---|
| Razorpay | Payment for a mentor call. The booking sheet says “Secured by Razorpay” |
| Google Meet | The call itself. The profile says the Meet link is sent after payment |

Public areas in the same app: All Colleges, Online Degree, Counselling, MBBS in Nepal, Streams, PG and Hostel, Exams, Scholarship, Admissions, Courses, Blog, and Tools (JEE rank predictor, NEET college predictor, compare colleges, scholarship finder, psychometric test).

---

## College catalogue already saved

The public college directory on https://www.collegeforme.in/colleges contains **261 colleges**, across every stream that directory lists. The page headline says 5000+. The list and its API return 261.

Everything from this College For Me pass lives in this folder:

- `overview.md` — this note
- `scrape_collegeforme.py` — the export script
- `requirements.txt` — Python packages for that script
- `.venv` — the Python environment used to run it
- `output/collegeforme_colleges.xlsx` — the workbook
- `output/collegeforme_failed.txt` — colleges that failed, empty when the run succeeded
- `data/collegeforme/raw` — one JSON file per college

The workbook sheets are Colleges, Streams, Courses, Sections, Facilities, Campus Life, Images, Admissions, Fee Structure, Scholarships, Cutoffs, and FAQs. Reviews were left out.

Engineering is the largest stream tag, on about 170 colleges. The same 261 also include medical, management, law, pharmacy, design, nursing, and agriculture. About 71 colleges were saved with a blank stream tag, including AIIMS, IIMs, NIFT, and NIPER. Those rows are on the Colleges sheet and do not appear when the Streams sheet is filtered.

A college can carry several stream tags, so the same college appears once on the Colleges sheet and once per tag on the Streams sheet.

---

## Talk to Students

Source: https://www.collegeforme.in/talk-to-students  
No account was used, and no payment was made.

Talk to Students is a paid introduction between a college aspirant and a current student.

- The visitor browses mentor cards without signing in.
- A call is 10 minutes on Google Meet.
- The mentor sets the price. On the day this was checked, prices ran from ₹49 to ₹149.
- Payment goes through Razorpay. The page says the amount is held until the call is confirmed, a no-show is refunded, and credits do not expire.
- The first message to a mentor is marked free.
- A current student can apply to become a guide, set a price, and take calls.

Page address: https://www.collegeforme.in/talk-to-students  
Mentor profile pattern: https://www.collegeforme.in/talk-to-students/{id}  
Apply to be a guide: https://www.collegeforme.in/become-student

Public data feed: `GET /api/student-connect/students?page=1&limit=50`  
One mentor: `GET /api/student-connect/students/{id}`  
Calendar: `GET /api/student-connect/students/{id}/availability`  
Posts: `GET /api/student-connect/posts?studentId={id}`  
Reviews: `GET /api/student-connect/students/{id}/reviews`

### What was live on 23 October 2026

| Fact | Value |
|---|---|
| Verified mentors | 15 |
| Colleges represented | 10 |
| Listed college-name spellings | 11 (Uttaranchal is stored twice, with different spelling) |
| Call length sold | 10 minutes |
| Price range | ₹49 to ₹149 |
| Most common price | ₹99 (7 of 15 mentors) |
| Completed sessions on the mentor list | 1 |
| Ratings | None. Every public rating field was empty |

The landing page invites people to talk to students from IIT, NIT, BITS, and VIT. The 15 mentors actually listed are from private and state engineering colleges. None of those four shortcut chips matched a mentor who was online.

### How a visitor uses it

1. **Browse.** Search by college, course, or name. Shortcut chips: IIT, NIT, BITS, VIT. A Filters button is also on the page. The directory said “15 verified students”.
2. **Open a profile.** The card shows a short name, course, year, college, bio, topics, price, and a Book call action. Cards also offer a free Message action.
3. **Read the profile.** Bio, topics, a 30-day hourly calendar, posts, and reviews. The sample profile showed sessions completed, a “New” rating, an approximate reply time, post count, and the starting price.
4. **Book.** Choose a date, then an hour. An optional note asks what to discuss. The button becomes “Book & Pay” at that mentor’s price.
5. **Pay.** Razorpay. The profile says a Google Meet link is sent as soon as the booking is paid.
6. **Message.** Separate from booking. The profile labels the first message as free.

Trust lines shown on the profile:

- ID-verified — presented as a real student, not an agent
- Google Meet link sent on booking
- Full refund if the mentor does not show up
- Credits never expire
- Secured by Razorpay

The “How it works” block on the main page is the same path in four labels: Browse Students, Pick a Slot, Secure Payment, Join and Learn.

### Prices

| Price | Mentors |
|---|---|
| ₹49 | 3 |
| ₹79 | 1 |
| ₹89 | 1 |
| ₹99 | 7 |
| ₹109 | 1 |
| ₹149 | 2 |

The checkout opened on one profile did not offer a 20-minute or 30-minute option. The product sold one duration: 10 minutes at `pricePerCall`.

### Who the mentors are

| Year | Mentors |
|---|---|
| 1st year | 4 |
| 2nd year | 3 |
| 3rd year | 5 |
| 4th year | 3 |

| College name as stored | Mentors |
|---|---|
| Shivalik College of Engineering | 4 |
| Rungta College of Engineering and Technology | 2 |
| Uttaranchal University, spelling “Uttaranchal university” | 1 |
| Uttaranchal University, spelling “Uttranchal university” | 1 |
| NIET, Noida | 1 |
| PW Institute of Innovation | 1 |
| Dayananda Sagar University | 1 |
| School of Studies of Engineering and Technology, Guru Ghasidas Vishwavidyalaya, Bilaspur | 1 |
| Galgotias University | 1 |
| Manipal University Jaipur | 1 |
| Aditya University | 1 |

The two Uttaranchal spellings are one campus stored as two names. A college filter can split them.

Topics a visitor is invited to ask about. One mentor can list several, so the counts add up to more than 15:

| Topic | Mentors who list it |
|---|---|
| Placements | 14 |
| Hostel life | 12 |
| Academic life | 12 |
| Faculty | 11 |
| Campus culture | 10 |
| Fees and scholarship | 9 |
| Clubs and activities | 6 |
| Infrastructure | 4 |
| Research | 3 |
| City life | 2 |
| Entrance preparation | 1 |
| Student exchange | 1 |

Each public mentor record contains: id, display name, college name, course, year, bio, expertise list, price per call, rating, total calls, selfie image URL, and a college link. The college link was empty on the records checked.

### Booking rules seen on a live profile

| Rule | What was on the page |
|---|---|
| Call length | 10 minutes |
| Hours | 09:00 through 20:00, one slot each hour |
| Window | 30 days ahead |
| Sample calendar | 23 Oct 2026 through 21 Nov 2026, reported as 360 open slots |
| Slot flags | Each hour has `isBooked` and `isUnavailable`. On the sample, both were false for every hour |
| Same day | The calendar still listed 23 Oct. The booking sheet said that day had no bookable slot. The next day opened all 12 hours |
| Checkout fields | Date, time, optional “what to discuss”, then Book & Pay |
| After payment | Product copy says the Google Meet link is sent immediately |

Profile extras besides the call: share, bookmark, posts with likes, and a reviews block. The sample had one post and no reviews.

### How someone becomes a mentor

https://www.collegeforme.in/become-student

The form has five steps: Sign in, Basic info, Verification, Pricing, Submit.

Step 1 is Google sign-in. The page says Google is used to verify identity. Steps 2 to 5 stay behind that sign-in, so the ID documents and the price form were not visible without an account.

The main page also links “Become a Student Guide” and says a student can help aspirants, earn per call, and build a profile.

The college workbook is the catalogue. Talk to Students is a separate marketplace on top of it: mentor profile, topics, hourly calendar, one 10-minute price, Razorpay, and Google Meet. On this date the mentor directory had 15 people and one recorded session.
