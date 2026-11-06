const params = new URLSearchParams(location.search);
const college = window.SETU.find((item) => item.slug === params.get("college")) || window.SETU[0];
document.title = `${college.name} — Admission Setu`;

const page = document.querySelector("#page");
const metrics = [
  ["Yearly fee", college.feeLabel, college.feeNote],
  ["Avg package", college.avgPackage, ""],
  ["NIRF rank", college.nirf.rank ? `#${college.nirf.rank}` : "", college.nirf.category || ""],
  ["Entrance exam", college.exams[0] || "", college.exams.slice(1).join(", ")]
].filter((item) => item[1]);

const sections = [];

function addSection(id, title, html) {
  if (!html) return;
  sections.push({ id, title });
  return `<section class="block" id="${id}"><h2>${title}</h2>${html}</section>`;
}

const facts = [
  ["Established", college.established],
  ["Ownership", college.ownership],
  ["Approvals", college.approvals.join(", ")],
  ["NAAC", college.naac],
  ["Campus", college.campusSize],
  ["Hostel", college.hostel],
  ["Phone", college.phone],
  ["Exams", college.exams.join(", ")]
].filter((item) => item[1]);

const overview = addSection(
  "overview",
  "Overview",
  `<p class="prose">${college.overview}</p>
   <dl class="dl">${facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join("")}</dl>`
);

const levels = [...new Set(college.courses.map((course) => course.level))];
const courseCards = college.courses
  .map(
    (course) => `<article class="course" data-level="${course.level}">
      <h3>${course.name}</h3>
      <p class="meta">${course.level} · ${course.duration} · ${course.fee}</p>
      <p class="meta">${course.eligibility}${course.note ? ` · ${course.note}` : ""}</p>
    </article>`
  )
  .join("");
const switcher =
  levels.length > 1
    ? `<div class="switch" role="group" aria-label="Course level">
        <button class="chip" type="button" data-level="All" aria-pressed="true">All</button>
        ${levels.map((level) => `<button class="chip" type="button" data-level="${level}" aria-pressed="false">${level}</button>`).join("")}
      </div>`
    : "";
const courseTitle = college.courseCount ? `Courses and fees · ${college.courseCount} courses` : "Courses and fees";
const courses = addSection("courses", courseTitle, `${switcher}<div id="courses">${courseCards}</div>`);

const admission = addSection(
  "admission",
  "Admission",
  `<dl class="dl">${college.admission.map((row) => `<div><dt>${row.label}</dt><dd>${row.value}</dd></div>`).join("")}</dl>`
);

const placementBits = [
  college.placementRate ? `<div class="metric"><strong>${college.placementRate}</strong><span>placement rate</span></div>` : "",
  college.highestPackage ? `<div class="metric"><strong>${college.highestPackage}</strong><span>highest package</span></div>` : "",
  college.medianPackage ? `<div class="metric"><strong>${college.medianPackage}</strong><span>median package</span></div>` : ""
].join("");
const placementRows = (college.placementRows || [])
  .map((row) => `<div><dt>${row.label}</dt><dd>${row.value}</dd></div>`)
  .join("");
const recruiters = college.recruiters.length
  ? `<div class="people">${college.recruiters.map((name) => `<span>${name}</span>`).join("")}</div>`
  : "";
const placementHtml = [
  placementBits ? `<div class="metrics">${placementBits}</div>` : "",
  placementRows ? `<dl class="dl">${placementRows}</dl>` : "",
  recruiters
].join("");
const placements = addSection("placements", "Placements", placementHtml.trim());

const rankings = addSection(
  "rankings",
  "Rankings",
  `<dl class="dl">
    ${college.nirf.rank ? `<div><dt>NIRF</dt><dd>#${college.nirf.rank} in ${college.nirf.category}, ${college.nirf.year}</dd></div>` : ""}
    ${college.naac ? `<div><dt>NAAC</dt><dd>${college.naac}</dd></div>` : ""}
    ${college.approvals.length ? `<div><dt>Approvals</dt><dd>${college.approvals.join(", ")}</dd></div>` : ""}
  </dl>`
);

const campus = addSection(
  "campus",
  "Campus",
  `${college.hostel ? `<p class="prose">Hostel: ${college.hostel}${college.campusSize ? `. Campus: ${college.campusSize}.` : ""}</p>` : ""}
   <div class="facility-list">${college.facilities.map((item) => `<span class="facility">${item}</span>`).join("")}</div>`
);

const scholarships = addSection(
  "scholarships",
  "Scholarships",
  college.scholarships.map((item) => `<article class="course"><h3>${item.name}</h3><p class="meta">${item.detail}</p></article>`).join("")
);

const cutoffRows = college.cutoffs
  .map((row) => `<div><dt>${row.course}</dt><dd>${row.exam} · ${row.closing}</dd></div>`)
  .join("");
const cutoffs = addSection("cutoffs", "Cutoffs", cutoffRows ? `<dl class="dl">${cutoffRows}</dl>` : "");

const faqs = addSection(
  "questions",
  "Questions",
  college.faqs.map((item) => `<details><summary>${item.q}</summary><p>${item.a}</p></details>`).join("")
);

const similar = window.SETU.filter((item) => item.slug !== college.slug && item.streams[0] === college.streams[0]).slice(0, 2);
const similarHtml = similar.length
  ? `<div class="grid similar">${similar
      .map(
        (item) => `<a class="card" href="college.html?college=${item.slug}">
          <div class="kicker"><span>${item.city}</span><span>${item.ownership}</span></div>
          <h3>${item.name}</h3>
          <p class="place">${item.feeLabel} · ${item.exams[0]}</p>
        </a>`
      )
      .join("")}</div>`
  : "";

page.innerHTML = `
  <article class="college-hero">
    <a class="back" href="option-b.html">All colleges</a>
    <p class="kicker" style="margin-top:14px"><span>${college.ownership}</span><span>${college.streams.join(" · ")}</span></p>
    <h1>${college.name}</h1>
    <p class="sub">${college.fullName}<br>${college.city}, ${college.state}</p>
    <div class="metrics">
      ${metrics.map(([label, value, note]) => `<div class="metric"><strong>${value}</strong><span>${label}${note ? ` · ${note}` : ""}</span></div>`).join("")}
    </div>
  </article>
  <nav class="sections" aria-label="On this page">
    ${sections.map((section, index) => `<a href="#${section.id}" class="${index === 0 ? "active" : ""}">${section.title.replace(/ ·.*/, "")}</a>`).join("")}
  </nav>
  <div class="layout">
    <div>
      ${[overview, courses, admission, placements, rankings, campus, scholarships, cutoffs, faqs].filter(Boolean).join("")}
      ${similarHtml ? `<section class="block"><h2>Other ${college.streams[0].toLowerCase()} colleges</h2>${similarHtml}</section>` : ""}
    </div>
    <aside class="rail">
      <h2>At a glance</h2>
      <dl class="dl">
        <div><dt>City</dt><dd>${college.city}</dd></div>
        <div><dt>Fee</dt><dd>${college.feeLabel}</dd></div>
        ${college.avgPackage ? `<div><dt>Package</dt><dd>${college.avgPackage}</dd></div>` : ""}
        <div><dt>Exam</dt><dd>${college.exams[0]}</dd></div>
      </dl>
      <a class="site" href="${college.website}" target="_blank" rel="noopener">Official website</a>
    </aside>
  </div>
`;

document.querySelectorAll(".switch button").forEach((button) => {
  button.addEventListener("click", () => {
    const level = button.dataset.level;
    document.querySelectorAll(".switch button").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
    document.querySelectorAll("#courses .course").forEach((course) => {
      course.hidden = level !== "All" && course.dataset.level !== level;
    });
  });
});

const links = [...document.querySelectorAll(".sections a")];
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      links.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`));
    });
  },
  { rootMargin: "-40% 0px -50% 0px" }
);
document.querySelectorAll(".block").forEach((block) => observer.observe(block));
