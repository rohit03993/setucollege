const QUOTA = {
  HS: "Home state",
  OS: "Other state",
  AI: "All India",
  GO: "Goa",
  JK: "Jammu and Kashmir",
  LA: "Ladakh"
};

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function num(value) {
  return Number(value).toLocaleString("en-IN");
}

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : "That request could not be completed.");
  }
  return data;
}

function place(college) {
  return [college.city, college.state].filter(Boolean).join(", ");
}

function collegeCard(college) {
  const fee = shownFee(college.fee_label) || "—";
  const nirf = college.nirf_rank ? `#${num(college.nirf_rank)}` : "—";
  const where = [place(college), college.ownership].filter(Boolean).join(" · ");
  return `<a class="college" href="/college/${encodeURIComponent(college.slug)}">
    <div class="college-id">
      <h3>${esc(college.name)}</h3>
      <p class="place">${esc(where)}</p>
    </div>
    <dl class="college-metrics">
      <div><dt>Yearly fee</dt><dd>${esc(fee)}</dd></div>
      <div><dt>NIRF</dt><dd>${esc(nirf)}</dd></div>
    </dl>
  </a>`;
}

function quotaText(quota) {
  return QUOTA[quota] || quota;
}

function homePick(college) {
  const fee = shownFee(college.fee_label) || "—";
  const nirf = college.nirf_rank ? `#${num(college.nirf_rank)}` : "—";
  const where = [place(college), college.ownership].filter(Boolean).join(" · ");
  return `<a class="pick" href="/college/${encodeURIComponent(college.slug)}">
    <span class="pick-rank">${esc(nirf)}</span>
    <span class="pick-id"><strong>${esc(college.name)}</strong><span>${esc(where)}</span></span>
    <span class="pick-fee"><small>Yearly fee</small>${esc(fee)}</span>
  </a>`;
}

async function initHome() {
  const featured = document.querySelector("#featured");
  const count = document.querySelector("#college-count");
  try {
    const data = await api("/colleges?sort=nirf&page_size=6");
    count.textContent = num(data.total);
    featured.innerHTML = data.colleges.map(homePick).join("");
  } catch (error) {
    featured.innerHTML = `<p class="status" role="alert">${esc(error.message)}</p>`;
  }
}

function readBrowse() {
  const params = new URLSearchParams(location.search);
  return {
    q: params.get("q") || "",
    stream: params.get("stream") || "",
    sort: params.get("sort") || "name",
    page: Math.max(1, Number(params.get("page") || 1))
  };
}

function writeBrowse(state) {
  const params = new URLSearchParams();
  if (state.q) params.set("q", state.q);
  if (state.stream) params.set("stream", state.stream);
  if (state.sort && state.sort !== "name") params.set("sort", state.sort);
  if (state.page > 1) params.set("page", String(state.page));
  const query = params.toString();
  history.pushState({}, "", query ? `/browse?${query}` : "/browse");
}

async function initBrowse() {
  const form = document.querySelector("#find");
  const input = document.querySelector("#q");
  const sort = document.querySelector("#sort");
  const chips = document.querySelector("#chips");
  const list = document.querySelector("#list");
  const status = document.querySelector("#status");
  const pageLabel = document.querySelector("#page-label");
  const prev = document.querySelector("#prev");
  const next = document.querySelector("#next");
  let state = readBrowse();

  function paintControls() {
    input.value = state.q;
    sort.value = state.sort;
    chips.querySelectorAll("button").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.stream === state.stream));
    });
  }

  async function load() {
    paintControls();
    status.textContent = "Loading colleges…";
    list.innerHTML = "";
    const params = new URLSearchParams({
      q: state.q,
      stream: state.stream,
      sort: state.sort,
      page: String(state.page),
      page_size: "20"
    });
    try {
      const data = await api(`/colleges?${params}`);
      const pages = Math.max(1, Math.ceil(data.total / data.page_size));
      status.textContent = data.total === 1 ? "1 college" : `${num(data.total)} colleges`;
      list.innerHTML = data.colleges.length
        ? data.colleges.map(collegeCard).join("")
        : `<p class="empty">Nothing matches that search.</p>`;
      pageLabel.textContent = `Page ${data.page} of ${pages}`;
      prev.disabled = data.page <= 1;
      next.disabled = data.page >= pages;
    } catch (error) {
      status.innerHTML = `<span role="alert">${esc(error.message)}</span>`;
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    state = { ...state, q: input.value.trim(), page: 1 };
    writeBrowse(state);
    load();
  });
  sort.addEventListener("change", () => {
    state = { ...state, sort: sort.value, page: 1 };
    writeBrowse(state);
    load();
  });
  chips.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    state = { ...state, stream: button.dataset.stream, page: 1 };
    writeBrowse(state);
    load();
  });
  prev.addEventListener("click", () => {
    state = { ...state, page: state.page - 1 };
    writeBrowse(state);
    load();
  });
  next.addEventListener("click", () => {
    state = { ...state, page: state.page + 1 };
    writeBrowse(state);
    load();
  });
  window.addEventListener("popstate", () => {
    state = readBrowse();
    load();
  });
  load();
}

const LEVELS = "B\\.Tech\\+M\\.Tech|Integrated M\\.Tech|B\\.Tech|M\\.Tech|B\\.Arch|M\\.Arch|B\\.Sc|M\\.Sc|MBA|MCA|PG Diploma|PhD|M\\.Plan|B\\.Plan|M\\.Des|B\\.Des|Doctor of Philosophy|BS|MS";
const JUNK = /by degree|by special|by course|upcoming events|expired events|similar college|photo gallery|choose course|next application date|colleges in |admission updates/i;

function tidyName(value) {
  return value.replace(/\+\d+\s*More/gi, "").replace(/\s+/g, " ").trim();
}

function splitCourses(text) {
  if (!text.includes("Fees (Yearly)")) return [];
  const groupRe = new RegExp(
    `(${LEVELS})Fees \\(Yearly\\)₹([\\d,.\\-– ]+?)Number of courses:(\\d+)([\\s\\S]*?)(?=(?:${LEVELS})Fees \\(Yearly\\)|$)`,
    "g"
  );
  const nameRe = new RegExp(`(?=(?:${LEVELS})\\b)`, "g");
  const groups = [];
  for (const match of text.matchAll(groupRe)) {
    const names = match[4]
      .split(nameRe)
      .map(tidyName)
      .filter((name) => name.startsWith(match[1]) && name.length > 3 && name.length < 90);
    if (names.length < 2) continue;
    groups.push({
      level: match[1],
      fee: `₹${match[2].trim()}`,
      count: match[3],
      names
    });
  }
  return groups;
}

function splitFaqs(text) {
  const parts = text.split(/(?=(?:What|Which|How|Does|Do|Is|Are|Can|Will|When|Where|Why)\b)/);
  const items = [];
  parts.forEach((part) => {
    const cut = part.indexOf("?");
    if (cut < 12) return;
    const question = part.slice(0, cut + 1).trim();
    const answer = part.slice(cut + 1).trim();
    if (answer.length < 30) return;
    items.push({ question, answer });
  });
  return items.length >= 2 ? items : [];
}

function shortCourse(name, level) {
  const escaped = level.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return name.replace(new RegExp(`^${escaped}\\.?\\s*(in\\s*)?`, "i"), "").replace(/^\.\s*/, "").trim() || name;
}

function isRealFee(label) {
  const parts = String(label || "").match(/\d[\d,]*/g) || [];
  return parts.some((part) => Number(part.replace(/,/g, "")) >= 1000);
}

function shownFee(label) {
  if (!isRealFee(label)) return "";
  const text = String(label).trim();
  return text.includes("₹") ? text : `₹${text}`;
}

function twoLines(text) {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= 160) return clean;
  const cut = clean.lastIndexOf(". ", 150);
  return cut > 40 ? clean.slice(0, cut + 1) : `${clean.slice(0, 157).trim()}…`;
}

function courseRows(pages) {
  const rows = [];
  const seen = new Set();
  for (const section of pages.courses?.sections || []) {
    for (const group of splitCourses(section.content || "")) {
      const fee = shownFee(group.fee) || "—";
      for (const name of group.names) {
        const course = shortCourse(name, group.level);
        const key = `${group.level}|${course}`.toLowerCase();
        if (!course || seen.has(key) || JUNK.test(course)) continue;
        seen.add(key);
        rows.push({ course, degree: group.level, fee });
      }
    }
  }
  return rows;
}

function admissionCopy(college) {
  const exams = (college.exams || []).filter(Boolean);
  const blob = exams.join(" ");
  let how = "Take the listed exam, then complete that exam's counselling.";
  if (/jee advanced/i.test(blob)) how = "Qualify JEE Advanced, then take a seat through JoSAA.";
  else if (/jee main/i.test(blob)) how = "Qualify JEE Main, then take a seat through JoSAA.";
  else if (/neet/i.test(blob)) how = "Qualify NEET, then take a seat through counselling.";
  else if (!exams.length) how = "The entrance exam for this college was not saved.";
  return { examLine: exams.join(", "), how };
}

function findAmount(text, label) {
  const match = text.match(new RegExp(`${label}[\\s\\S]{0,70}?(?:₹|Rs\\.?|INR)\\s*([\\d,.]+(?:\\s*(?:LPA|lakh|lakhs|crore|cr))?)`, "i"));
  if (!match) return "";
  const amount = match[1].replace(/\s+/g, " ").trim();
  const digits = Number((amount.match(/\d[\d,]*/)?.[0] || "0").replace(/,/g, ""));
  if (digits < 1) return "";
  return `₹${amount.replace(/^₹/, "")}`;
}

function placementFacts(pages) {
  const text = (pages.placement?.sections || []).map((section) => section.content || "").join(" ");
  const average = findAmount(text, "average package") || findAmount(text, "avg\\.? package");
  const highest = findAmount(text, "highest package");
  const found = text.match(/top recruiters include ([^.]+)/i);
  let names = found ? found[1].replace(/\s+/g, " ").trim() : "";
  if (names.length > 140) names = `${names.slice(0, 137).trim()}…`;
  if (JUNK.test(names)) names = "";
  return { average, highest, names };
}

function collegeAnswers(pages) {
  const items = [];
  const seen = new Set();
  for (const key of ["courses", "admission", "placement"]) {
    for (const section of pages[key]?.sections || []) {
      for (const item of splitFaqs(section.content || "")) {
        const question = item.question.replace(/\s+/g, " ").trim();
        const id = question.toLowerCase();
        if (seen.has(id) || JUNK.test(question) || JUNK.test(item.answer)) continue;
        if (question.length < 15 || question.length > 150) continue;
        seen.add(id);
        items.push({ question, answer: item.answer });
      }
    }
  }
  return items;
}

function sectionBody(section) {
  const text = section.content || "";
  if (text.length <= 320) return `<p>${esc(text)}</p>`;
  const cut = text.lastIndexOf(". ", 300);
  const head = cut > 80 ? text.slice(0, cut + 1) : text.slice(0, 300);
  return `<p>${esc(head)}</p><details class="more-answers"><summary>Read the rest</summary><p>${esc(text)}</p></details>`;
}

function storySections(sections) {
  return (sections || [])
    .filter((section) => {
      const title = section.title || "";
      const content = section.content || "";
      if (!title || !content || title.endsWith("?")) return false;
      if (JUNK.test(title) || JUNK.test(content)) return false;
      if (/faq|table of contents|related question|reviews and rating|share your college|^\d\.\d$/i.test(title)) return false;
      return true;
    })
    .slice(0, 4);
}

function tableStat(tables, needle) {
  for (const table of tables || []) {
    if (JUNK.test(table.title || "")) continue;
    for (const row of table.rows || []) {
      if (row.length >= 2 && String(row[0]).toLowerCase().includes(needle)) {
        const value = String(row[1]).replace(/\s+/g, " ").trim();
        if (value && !/^na$/i.test(value)) return value.replace(/^Rs\.?\s*/i, "₹");
      }
    }
  }
  return "";
}

function degreeKey(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9+]/g, "");
}

function listedGroups(groups, pages) {
  const fuller = new Map();
  for (const section of pages.courses?.sections || []) {
    for (const group of splitCourses(section.content || "")) {
      const key = degreeKey(group.level);
      const current = fuller.get(key);
      if (!current || group.names.length > current.names.length) fuller.set(key, group);
    }
  }
  return (groups || []).map((group) => {
    const saved = group.courses || [];
    const extra = fuller.get(degreeKey(group.degree));
    const names = extra && extra.names.length > saved.length ? extra.names : saved;
    return { ...group, courses: names };
  });
}

function degreeList(groups) {
  return `<div class="degree-list">${groups
    .map((group) => {
      const names = group.courses || [];
      const count = names.length === 1 ? "1 course" : names.length ? `${names.length} courses` : "";
      const fee = group.fee ? shownFee(group.fee) || group.fee : "";
      const items = names.map((name) => `<li>${esc(name)}</li>`).join("");
      return `<article class="degree">
        <header>
          <div><h3>${esc(group.degree)}</h3>${count ? `<p>${esc(count)}</p>` : ""}</div>
          ${fee ? `<strong>${esc(fee)}<span>/ year</span></strong>` : ""}
        </header>
        ${items ? `<ul>${items}</ul>` : ""}
      </article>`;
    })
    .join("")}</div>`;
}

function plainTable(table, limit = 12) {
  let columns = table.columns || [];
  let rows = table.rows || [];
  if (!columns.length && rows.length > 1 && /rank|category|course|special|fee|branch/i.test(rows[0].join(" "))) {
    columns = rows[0];
    rows = rows.slice(1);
  }
  const head = columns.length ? `<thead><tr>${columns.map((cell) => `<th>${esc(cell)}</th>`).join("")}</tr></thead>` : "";
  const body = rows
    .slice(0, limit)
    .map((row) => `<tr>${row.map((cell, index) => `<td${columns[index] ? ` data-label="${esc(columns[index])}"` : ""}>${esc(cell)}</td>`).join("")}</tr>`)
    .join("");
  if (!body) return "";
  const more = rows.length > limit ? `<p class="recruiters">Showing ${limit} of ${rows.length} rows.</p>` : "";
  return `<h3>${esc(table.title || "Details")}</h3><div class="table-scroll"><table class="course-table">${head}<tbody>${body}</tbody></table></div>${more}`;
}

function courseTable(rows) {
  const body = rows
    .map(
      (row, index) =>
        `<tr ${index >= 8 ? "hidden" : ""}><td data-label="Course">${esc(row.course)}</td><td data-label="Degree">${esc(row.degree)}</td><td data-label="Yearly fee">${esc(row.fee)}</td></tr>`
    )
    .join("");
  const more = rows.length > 8 ? `<button class="ghost" id="show-courses" type="button">Show all ${rows.length} courses</button>` : "";
  return `<div class="table-scroll"><table class="course-table">
    <thead><tr><th>Course</th><th>Degree</th><th>Yearly fee</th></tr></thead>
    <tbody>${body}</tbody>
  </table></div>${more}`;
}

function answerList(items) {
  return `<div class="faq-list">${items
    .slice(0, 8)
    .map(
      (item) =>
        `<details class="faq"><summary>${esc(item.question)}</summary><p>${esc(item.answer)}</p></details>`
    )
    .join("")}</div>`;
}

function rankGap(studentRank, closingRank) {
  const diff = closingRank - studentRank;
  if (diff >= 0) return `${num(diff)} ranks inside last year's close`;
  return `${num(Math.abs(diff))} ranks past last year's close`;
}

function showSection(root, id) {
  root.querySelectorAll(".section-nav button").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.section === id));
  });
  root.querySelectorAll(".sheet").forEach((panel) => {
    panel.hidden = panel.id !== id;
  });
}

async function initCollege() {
  const root = document.querySelector("#college");
  const slug = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop());
  try {
    const college = await api(`/colleges/${encodeURIComponent(slug)}`);
    document.title = `${college.name} — Admission Setu`;
    const pages = college.pages || {};
    const exams = (college.exams || []).filter(Boolean);
    const fee = shownFee(college.fee_label);
    const placed = placementFacts(pages);
    const officialAverage = tableStat(pages.placement?.tables, "average package");
    const officialHighest = tableStat(pages.placement?.tables, "highest package");
    const average = college.edited
      ? college.average_package
      : officialAverage || placed.average || college.average_package;
    const highest = college.edited
      ? college.highest_package
      : officialHighest || placed.highest || college.highest_package;
    const nirf = college.nirf_overall
      ? `#${num(college.nirf_overall)}`
      : college.nirf_rank
        ? `#${num(college.nirf_rank)}${college.nirf_year ? ` · ${college.nirf_year}` : ""}`
        : "";
    const facts = [
      fee ? ["Yearly fee", fee] : null,
      nirf ? ["NIRF", nirf] : null,
      average ? ["Average package", average] : null,
      highest ? ["Highest package", highest] : null,
      college.rating && /^\d/.test(String(college.rating)) ? ["Rating", String(college.rating)] : null,
      college.course_count && Number(String(college.course_count).replace(/[^\d]/g, "")) > 0
        ? ["Courses", String(college.course_count)]
        : null
    ].filter(Boolean);
    const managed = Boolean(college.managed);
    const groups = listedGroups(pages.course_groups || [], managed ? {} : pages);
    const rows = groups.length || managed ? [] : courseRows(pages);
    const stories = managed
      ? (pages.admission?.sections || []).filter((section) => section.title || section.content)
      : storySections(pages.admission?.sections);
    const answers = managed
      ? (pages.faqs || []).filter((item) => item.question && item.answer)
      : (pages.faqs && pages.faqs.length ? pages.faqs : collegeAnswers(pages)).filter(
          (item) => item.question && item.answer && !JUNK.test(item.question)
        );
    const placeTables = (pages.placement?.tables || []).filter(
      (table) => table.rows && table.rows.length && (managed || !JUNK.test(table.title || ""))
    );
    const cutoffTables = (pages.cutoff?.tables || []).filter(
      (table) => table.rows && table.rows.length && (managed || !JUNK.test(table.title || ""))
    );
    const recruiterLine = managed ? college.recruiters || "" : placed.names;
    const blocks = [];
    if (groups.length || rows.length) blocks.push(["courses", "Courses"]);
    blocks.push(["admission", "Admission"]);
    if (cutoffTables.length) blocks.push(["cutoff", "Cutoff"]);
    if (average || highest || placed.names || placeTables.length) blocks.push(["placements", "Placements"]);
    if (answers.length) blocks.push(["answers", "Answers"]);
    const nav = `<nav class="section-nav" aria-label="College sections">${blocks
      .map(
        ([id, label]) =>
          `<button type="button" data-section="${id}" aria-pressed="false">${label}</button>`
      )
      .join("")}</nav>`;
    const courses = groups.length
      ? `<section class="sheet" id="courses" hidden><h2>Courses and fees</h2><p class="sheet-note">Yearly fee is shown beside each degree. Course names are the branches listed for that degree.</p>${degreeList(groups)}</section>`
      : rows.length
        ? `<section class="sheet" id="courses" hidden><h2>Courses and fees</h2><p class="sheet-note">Each row is one course and the yearly fee saved for it.</p>${courseTable(rows)}</section>`
        : "";
    const admission = `<section class="sheet" id="admission" hidden><h2>Admission</h2>
      ${managed ? "" : `<p class="sheet-note">${esc(admissionCopy(college).how)}</p>`}
      ${stories.length ? stories.map((section) => `<h3>${esc(section.title)}</h3>${sectionBody(section)}`).join("") : ""}
      <a class="button detail-cta" href="/chances">Check your rank</a></section>`;
    const cutoffLimit = managed ? cutoffTables.length : 4;
    const cutoff = cutoffTables.length
      ? `<section class="sheet" id="cutoff" hidden><h2>Cutoff</h2><p class="sheet-note">A smaller rank is a better rank. These tables are the cutoffs saved for this college.</p>${cutoffTables.slice(0, cutoffLimit).map((table) => plainTable(table, managed ? 40 : 12)).join("")}</section>`
      : "";
    const placements =
      average || highest || recruiterLine || placeTables.length
        ? `<section class="sheet" id="placements" hidden><h2>Placements</h2>
            ${average || highest ? `<dl class="metrics">
              ${average ? `<div><dt>Average package</dt><dd>${esc(average)}</dd></div>` : ""}
              ${highest ? `<div><dt>Highest package</dt><dd>${esc(highest)}</dd></div>` : ""}
            </dl>` : ""}
            ${(managed ? placeTables : placeTables.slice(0, 2)).map((table) => plainTable(table, managed ? 40 : 12)).join("")}
            ${recruiterLine ? `<p class="recruiters">Recruiters include ${esc(recruiterLine)}</p>` : ""}
          </section>`
        : "";
    const answerBlock = answers.length ? `<section class="sheet" id="answers" hidden><h2>Answers</h2><p class="sheet-note">Open a question to read the answer.</p>${answerList(answers)}</section>` : "";
    const site = /^https?:\/\//i.test(String(college.website || "").trim()) ? String(college.website).trim() : "";
    const phoneText = String(college.phone || "").trim();
    const phoneHref = phoneText.replace(/[^\d+]/g, "");
    const links = [
      site ? `<a class="text-link" href="${esc(site)}" target="_blank" rel="noopener">Website</a>` : "",
      phoneText && phoneHref ? `<a class="text-link" href="tel:${esc(phoneHref)}">${esc(phoneText)}</a>` : ""
    ].filter(Boolean);
    const letters = college.name
      .split(/\s+/)
      .filter((word) => /[A-Za-z]/.test(word))
      .slice(0, 2)
      .map((word) => word[0].toUpperCase())
      .join("");
    const videoId = /^[\w-]{11}$/.test(college.video_id || "") ? college.video_id : "";
    const photo = college.image
      ? `<img class="campus" src="${esc(college.image)}" alt="">`
      : `<div class="initials">${esc(letters || "AS")}</div>`;
    const video = videoId
      ? `<div class="video"><iframe src="https://www.youtube.com/embed/${esc(videoId)}" title="Campus video" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>`
      : "";
    const rating = college.rating && /^\d/.test(String(college.rating))
      ? `<p class="rating-line"><span class="rating-pill">${esc(String(college.rating))}</span>${college.reviews ? `<span>${esc(String(college.reviews))} reviews</span>` : ""}</p>`
      : "";
    const year = college.established_year ? `Established ${college.established_year}` : "";
    root.innerHTML = `<article class="profile">
      <div class="banner">${photo}</div>
      <div class="identity">
        ${college.logo ? `<img class="college-logo" src="${esc(college.logo)}" alt="">` : ""}
        <p class="kicker">${esc([place(college), college.ownership, year].filter(Boolean).join(" · "))}</p>
        <h1>${esc(college.name)}</h1>
        ${rating}
        ${college.overview ? `<p class="overview">${esc(college.overview)}</p>` : ""}
        <div class="tags">${(college.streams || []).map((stream) => `<span class="tag">${esc(stream)}</span>`).join("")}</div>
        ${exams.length ? `<p class="exam-line">Exams: ${esc(exams.join(", "))}</p>` : ""}
        ${links.length ? `<p class="contact-line">${links.join("")}</p>` : ""}
        ${facts.length ? `<dl class="metrics">${facts.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>` : ""}
        <a class="button detail-cta" href="/chances">Check your rank</a>
      </div>
    </article>
    ${video}
    ${nav}${courses}${admission}${cutoff}${placements}${answerBlock}`;
    const showCourses = root.querySelector("#show-courses");
    if (showCourses) {
      showCourses.addEventListener("click", () => {
        root.querySelectorAll(".course-table tr[hidden]").forEach((row) => row.removeAttribute("hidden"));
        showCourses.remove();
      });
    }
    const firstSection = root.querySelector(".section-nav button");
    if (firstSection) showSection(root, firstSection.dataset.section);
    root.querySelector(".section-nav")?.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (button) showSection(root, button.dataset.section);
    });
  } catch (error) {
    root.innerHTML = `<p class="status" role="alert">${esc(error.message)}</p>`;
  }
}

async function initChances() {
  const form = document.querySelector("#predict");
  const courseWrap = document.querySelector("#course-wrap");
  const stateSelect = document.querySelector("#home_state");
  const results = document.querySelector("#results");
  const summary = document.querySelector("#summary");
  const status = document.querySelector("#status");
  const more = document.querySelector("#more");
  let page = 1;
  let lastBody = null;

  try {
    const options = await api("/predict/options");
    stateSelect.innerHTML = options.states.map((state) => `<option>${esc(state)}</option>`).join("");
  } catch (error) {
    status.textContent = error.message;
    status.setAttribute("role", "alert");
    return;
  }

  function showCourse() {
    courseWrap.classList.toggle("hidden", form.exam.value !== "NEET");
  }
  form.exam.addEventListener("change", showCourse);
  showCourse();

  async function run(nextPage, append) {
    status.textContent = "Checking seats…";
    status.removeAttribute("role");
    const entered = new FormData(form);
    const body = {
      rank: Number(entered.get("rank")),
      category: entered.get("category"),
      gender: entered.get("gender"),
      home_state: entered.get("home_state"),
      exam: entered.get("exam"),
      course: entered.get("exam") === "NEET" ? entered.get("course") : "",
      page: nextPage,
      page_size: 20
    };
    try {
      const data = await api("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      lastBody = body;
      page = data.page;
      status.textContent = "";
      summary.innerHTML = `
        <span class="pill safer">${num(data.counts.safer)} safer</span>
        <span class="pill possible">${num(data.counts.possible)} possible</span>
        <span class="pill unlikely">${num(data.counts.unlikely)} unlikely</span>`;
      const groups = [];
      const seen = new Map();
      data.results.forEach((row) => {
        if (!seen.has(row.college)) {
          seen.set(row.college, groups.length);
          groups.push({ college: row.college, state: row.college_state, slug: row.slug, seats: [] });
        }
        groups[seen.get(row.college)].seats.push(row);
      });
      const start = append ? results.querySelectorAll(".seat-card").length : 0;
      const cards = groups.map((group, index) => {
        const href = group.slug
          ? `/college/${encodeURIComponent(group.slug)}`
          : `/browse?q=${encodeURIComponent(group.college)}`;
        const action = group.slug ? "Open college" : "Find in colleges";
        const countLabel = group.seats.length === 1 ? "1 branch" : `${group.seats.length} branches`;
        const place = [group.state, countLabel].filter(Boolean).join(" · ");
        const seats = group.seats.map((row) => `<div class="branch-row">
          <div class="result-head">
            <span class="pill ${esc(row.chance)}">${esc(row.chance)}</span>
            <span class="gap">${esc(rankGap(data.rank, row.closing_rank))}</span>
          </div>
          <p class="branch">${esc(row.branch)}</p>
          <dl class="compare">
            <div><dt>Your rank</dt><dd>${num(data.rank)}</dd></div>
            <div><dt>Closed at</dt><dd>${num(row.closing_rank)}</dd></div>
            <div><dt>Seat</dt><dd>${esc(quotaText(row.quota))} · ${esc(row.gender)}</dd></div>
          </dl>
        </div>`).join("");
        return `<article class="seat-card">
          <a class="seat-college" href="${href}">
            <span class="seat-mark">${start + index + 1}</span>
            <span class="seat-name"><strong>${esc(group.college)}</strong><span class="place">${esc(place)}</span></span>
            <span class="open-label">${action}</span>
          </a>
          ${seats}
        </article>`;
      }).join("");
      results.innerHTML = append ? results.innerHTML + cards : cards;
      if (!data.total) {
        results.innerHTML = `<p class="empty">No seat matches that category, state, and gender.</p>`;
      }
      const shown = Math.min(data.total, data.page * data.page_size);
      more.hidden = shown >= data.total;
      more.textContent = `Show more · ${num(shown)} of ${num(data.total)}`;
    } catch (error) {
      status.textContent = error.message;
      status.setAttribute("role", "alert");
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    results.innerHTML = "";
    summary.innerHTML = "";
    run(1, false);
  });
  more.addEventListener("click", () => run(page + 1, true));
}

const page = document.body.dataset.page;
if (page === "home") initHome();
if (page === "browse") initBrowse();
if (page === "college") initCollege();
if (page === "chances") initChances();
