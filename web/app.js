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

function lettersOf(name) {
  return String(name || "")
    .split(/\s+/)
    .filter((word) => /[A-Za-z]/.test(word))
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
}

function packageText(college) {
  const written = String(college.highest_package || "").trim();
  if (written) return written;
  const value = Number(college.highest_package_lpa);
  if (!value) return "—";
  if (value >= 100) return `₹${String(value / 100).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "")} Cr`;
  return `₹${String(value).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "")} LPA`;
}

function collegeCard(college) {
  const letters = lettersOf(college.name) || "•";
  const logo = college.logo ? `<img src="${esc(college.logo)}" alt="" onerror="this.remove()">` : "";
  const badge = college.nirf_rank ? `<span class="rank-badge" title="NIRF rank">#${num(college.nirf_rank)}</span>` : "";
  const rating = /^\d/.test(String(college.rating || "").trim()) ? String(college.rating).trim() : "";
  const highest = packageText(college);
  const facts = [
    rating ? `<span class="card-rating">★ ${esc(rating)}</span>` : "",
    highest !== "—" ? `<span>Highest ${esc(highest)}</span>` : ""
  ].filter(Boolean).join("");
  const streams = (college.streams || []).filter(Boolean);
  const shown = streams.slice(0, 3);
  const extra = streams.length - shown.length;
  const tags = shown.length
    ? `<div class="card-tags">${shown.map((stream) => `<span>${esc(stream)}</span>`).join("")}${extra ? `<span>+${extra}</span>` : ""}</div>`
    : "";
  return `<a class="college${badge ? " has-rank" : ""}" href="/college/${encodeURIComponent(college.slug)}">
    ${badge}
    <span class="mark">${logo}${esc(letters)}</span>
    <span class="college-id">
      <h3>${esc(college.name)}</h3>
      <p class="place">${esc(place(college))}</p>
    </span>
    ${facts ? `<p class="card-line">${facts}</p>` : ""}
    ${tags}
    <span class="explore">Explore college</span>
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

function degreeKind(name) {
  const key = degreeKey(name);
  if (/mbbs|bds|nursing|pharm|medical/.test(key)) return "plus";
  if (/mba|pgdm|bba|management/.test(key)) return "case";
  if (/btech|mtech|bearch|engineering|barch|diploma/.test(key) || key === "be") return "cap";
  if (/msc|bsc|phd|science/.test(key)) return "flask";
  return "book";
}

function degreeIcon(kind) {
  const paths = {
    cap: `<path d="M3 10 12 5l9 5-9 5-9-5Z"/><path d="M7 12.2V17c1.4 1.3 3.2 2 5 2s3.6-.7 5-2v-4.8"/>`,
    case: `<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5.5A1.5 1.5 0 0 1 9.5 4h5A1.5 1.5 0 0 1 16 5.5V7"/><path d="M3 12h18"/>`,
    flask: `<path d="M9 3h6"/><path d="M10 3v5.5L5 19.2A1.8 1.8 0 0 0 6.6 22h10.8A1.8 1.8 0 0 0 19 19.2L14 8.5V3"/>`,
    plus: `<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/>`,
    book: `<path d="M5 19.5A2.5 2.5 0 0 1 7.5 17H20"/><path d="M7.5 3H20v18H7.5A2.5 2.5 0 0 1 5 18.5v-13A2.5 2.5 0 0 1 7.5 3Z"/>`
  };
  return `<span class="degree-icon" aria-hidden="true"><svg viewBox="0 0 24 24">${paths[kind] || paths.book}</svg></span>`;
}

function degreeList(groups) {
  return `<div class="degree-list">${groups
    .map((group, index) => {
      const names = group.courses || [];
      const count = names.length === 1 ? "1 course" : names.length ? `${names.length} courses` : "";
      const fee = group.fee ? shownFee(group.fee) || group.fee : "";
      const items = names.map((name) => `<li><i aria-hidden="true"></i><span>${esc(name)}</span></li>`).join("");
      return `<article class="degree tone-${index % 6}">
        <header>
          ${degreeIcon(degreeKind(group.degree))}
          <div class="degree-name"><h3>${esc(group.degree)}</h3>${count ? `<p>${esc(count)}</p>` : ""}</div>
          ${fee ? `<div class="degree-fee"><span>Yearly fee</span><strong>${esc(fee)}</strong></div>` : ""}
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

const BAND_LABEL = {
  "very-high": "Very high",
  high: "High",
  medium: "Medium",
  low: "Low",
  "very-low": "Very low"
};
const CATEGORY_LABEL = {
  OPEN: "General",
  EWS: "EWS",
  "OBC-NCL": "OBC-NCL",
  SC: "SC",
  ST: "ST"
};
const CHOICE_KEY = "setu-choices";
const STUDENT_KEY = "setu-student";

function loadStudent() {
  try {
    const saved = JSON.parse(localStorage.getItem(STUDENT_KEY) || "null");
    if (saved && saved.id && saved.name) return saved;
  } catch (error) {
    return null;
  }
  return null;
}

function saveStudent(student) {
  localStorage.setItem(STUDENT_KEY, JSON.stringify(student));
}

function historyList(rows) {
  if (!rows || !rows.length) return `<p class="consent-note">No predictions yet.</p>`;
  return `<ul class="history-list">${rows.map((row) => {
    const when = new Date(row.created_at);
    const label = Number.isNaN(when.getTime())
      ? ""
      : when.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    const category = CATEGORY_LABEL[row.category] || row.category;
    return `<li><strong>${esc(row.exam)}</strong><span>Rank ${num(row.rank)} · ${esc(category)} · ${esc(row.home_state)}</span><small>${esc(label)}</small></li>`;
  }).join("")}</ul>`;
}

function digitsOnly(value) {
  let digits = String(value || "").replace(/\D/g, "");
  if (digits.startsWith("91") && digits.length > 10) digits = digits.slice(2);
  if (digits.startsWith("0") && digits.length > 10) digits = digits.slice(1);
  return digits.slice(0, 10);
}

function poolText(gender) {
  return String(gender || "").startsWith("Female-only") ? "Female-only" : gender || "";
}

function loadChoices() {
  try {
    const saved = JSON.parse(localStorage.getItem(CHOICE_KEY) || "[]");
    return Array.isArray(saved) ? saved.filter((item) => item && item.id && item.college && item.branch) : [];
  } catch (error) {
    return [];
  }
}

function saveChoices(items) {
  try {
    localStorage.setItem(CHOICE_KEY, JSON.stringify(items));
  } catch (error) {
    return;
  }
}

function bandLabel(band) {
  return BAND_LABEL[band] || band;
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
      ? `<section class="sheet" id="courses" hidden><h2>Courses and fees</h2><p class="sheet-note">Each card is one degree. The fee is the yearly range for that degree, and the branches are listed under it.</p>${degreeList(groups)}</section>`
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
    const site = String(college.website || "").trim();
    const publicSite = /^https?:\/\//i.test(site) && !/collegedekho\.com/i.test(site) ? site : "";
    const phoneText = String(college.phone || "").trim();
    const phoneHref = phoneText.replace(/[^\d+]/g, "");
    const links = [
      publicSite ? `<a class="text-link" href="${esc(publicSite)}" target="_blank" rel="noopener">Website</a>` : "",
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
  const choicesBox = document.querySelector("#choices");
  const summary = document.querySelector("#summary");
  const status = document.querySelector("#status");
  const more = document.querySelector("#more");
  const historyBox = document.querySelector("#history");
  let page = 1;
  let branch = "";
  let choices = loadChoices();
  let student = loadStudent();
  const shownSeats = new Map();

  function choiceId(row, data) {
    return [data.exam, row.college, row.branch, row.quota, row.gender, data.category].join("|");
  }

  function paintChoices() {
    if (!choices.length) {
      choicesBox.hidden = true;
      choicesBox.innerHTML = "";
      return;
    }
    choicesBox.hidden = false;
    const counselling = choices.some((item) => item.exam === "NEET") ? "Counselling" : "JoSAA";
    choicesBox.innerHTML = `<section class="choice-board" aria-label="Your choice list">
      <div class="choice-head">
        <div>
          <p class="eyebrow">In your order</p>
          <h2>Choice list</h2>
        </div>
        <button class="choice-clear" type="button" data-choice-clear>Clear</button>
      </div>
      <ul class="choice-rules">
        <li><strong>Put the seat you want most at the top.</strong> A lower chance can sit above a safer seat.</li>
        <li><strong>${counselling} offers the highest choice your rank clears</strong> for that quota, category, and gender pool.</li>
        <li><strong>After a round, choose Freeze, Float, or Slide.</strong> Freeze keeps the seat. Float waits for a higher choice in a later round. Slide waits for a better branch in the same college.</li>
      </ul>
      <ol class="choice-items">${choices.map((item, index) => {
        const href = item.slug ? `/college/${encodeURIComponent(item.slug)}` : `/browse?q=${encodeURIComponent(item.college)}`;
        const category = CATEGORY_LABEL[item.category] || item.category;
        return `<li class="choice-item">
          <span class="choice-index">${index + 1}</span>
          <div>
            <h3><a href="${href}">${esc(item.college)}</a></h3>
            <p>${esc(item.branch)}</p>
            <span class="seat-sub">${esc(quotaText(item.quota))} · ${esc(poolText(item.gender))} · ${esc(category)} · ${esc(item.exam)}</span>
            <span class="seat-sub">Checked at rank ${num(item.rank)}</span>
          </div>
          <div class="rank-pair">
            <span><small>Opening</small><b>${item.opening_rank ? num(item.opening_rank) : "—"}</b></span>
            <span><small>Closing</small><b>${num(item.closing_rank)}</b></span>
          </div>
          <div class="choice-side">
            <span class="pill ${esc(item.probability)}">${esc(bandLabel(item.probability))}</span>
            <div class="choice-moves">
              <button type="button" data-choice-up="${index}" ${index === 0 ? "disabled" : ""}>Up</button>
              <button type="button" data-choice-down="${index}" ${index === choices.length - 1 ? "disabled" : ""}>Down</button>
              <button type="button" data-choice-remove="${index}">Remove</button>
            </div>
          </div>
        </li>`;
      }).join("")}</ol>
    </section>`;
  }

  function markAdded() {
    results.querySelectorAll(".choice-add").forEach((button) => {
      const added = choices.some((item) => item.id === button.dataset.choice);
      button.setAttribute("aria-pressed", added ? "true" : "false");
      button.textContent = added ? "Added" : "Add";
    });
  }

  function toggleChoice(id) {
    const index = choices.findIndex((item) => item.id === id);
    if (index >= 0) choices.splice(index, 1);
    else {
      const seat = shownSeats.get(id);
      if (!seat) return;
      if (choices.length >= 40) {
        status.textContent = "The choice list holds 40 seats. Remove one to add another.";
        return;
      }
      choices.push(seat);
    }
    saveChoices(choices);
    paintChoices();
    markAdded();
  }

  paintChoices();
  let lastBody = null;

  try {
    const options = await api("/predict/options");
    stateSelect.innerHTML = options.states
      .map((state) => `<option${state === "Uttar Pradesh" ? " selected" : ""}>${esc(state)}</option>`)
      .join("");
  } catch (error) {
    status.textContent = error.message;
    status.setAttribute("role", "alert");
    return;
  }

  function showCourse() {
    const picked = form.querySelector('input[name="exam"]:checked');
    courseWrap.classList.toggle("hidden", !picked || picked.value !== "NEET");
  }
  form.addEventListener("change", (event) => {
    if (event.target.name === "exam") showCourse();
  });
  showCourse();

  async function paintHistory() {
    if (!historyBox) return;
    if (!student || !student.id) {
      historyBox.hidden = true;
      historyBox.innerHTML = "";
      return;
    }
    try {
      const data = await api(`/students/${encodeURIComponent(student.id)}`);
      historyBox.hidden = false;
      historyBox.innerHTML = `<section class="choice-board"><div class="choice-head"><div><p class="eyebrow">Your ID ${esc(data.id)}</p><h2>${esc(data.name)}</h2></div></div><div class="history-wrap">${historyList(data.predictions)}</div></section>`;
    } catch (error) {
      historyBox.hidden = true;
    }
  }

  document.addEventListener("setu-student", (event) => {
    student = event.detail;
    if (!student) {
      results.innerHTML = "";
      summary.innerHTML = "";
      more.hidden = true;
    }
    paintHistory();
  });
  paintHistory();

  async function run(nextPage, append, record) {
    if (!student || !student.id) {
      window.setuOpenAccount(() => run(nextPage, append, record));
      return;
    }
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
      branch,
      student_id: student.id,
      record: Boolean(record),
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
      const counts = data.counts || {};
      const reachable = (counts["very-high"] || 0) + (counts.high || 0) + (counts.medium || 0);
      summary.innerHTML = "";
      const category = CATEGORY_LABEL[data.category] || data.category;
      const gender = data.gender === "female" ? "Female" : "Male";
      const chips = [data.exam, category, gender, data.home_state]
        .filter(Boolean)
        .map((item) => `<span>${esc(item)}</span>`)
        .join("");
      let statusClass = "ok";
      let statusTitle = "";
      let statusBody = "";
      if (!data.matched) {
        statusClass = "empty";
        statusTitle = "No matching seat";
        statusBody = "Nothing in this round fits that category, state, and gender.";
      } else if (!reachable && !data.total) {
        statusClass = "empty";
        statusTitle = "No seat is close to this rank";
        statusBody = `The nearest closing rank in ${data.round_label} is more than 15% better than ${num(data.rank)}.`;
      } else if (!reachable) {
        statusClass = "empty";
        statusTitle = "No seat closed at this rank or later";
        statusBody = `These seats closed within 15% of your rank. ${data.round_label}.`;
      } else {
        statusTitle = `${num(reachable)} ${reachable === 1 ? "seat is" : "seats are"} inside your rank`;
        statusBody = `Only seats your rank would have cleared are listed. ${data.round_label}.`;
      }
      if (data.exam === "JEE Advanced") {
        statusBody = `${statusBody} These are IIT seats. NIT, IIIT, and GFTI seats are under JEE Main.`;
      }
      const banner = `<section class="result-hero">
        <div class="result-top">
          <div>
            <div class="result-chips">${chips}</div>
            <p class="result-who"><strong>${esc(data.student_name || student.name)}</strong><span>${esc(data.student_id || student.id)}</span><button type="button" data-edit-profile>Edit profile</button><button type="button" data-logout>Log out</button><button type="button" data-withdraw>Withdraw consent</button></p>
            <p class="result-kicker">Your rank</p>
            <h2>${num(data.rank)}</h2>
          </div>
          <p class="result-round">${esc(data.round_label || "")}</p>
        </div>
        <div class="result-status ${statusClass}">
          <strong>${esc(statusTitle)}</strong>
          <span>${esc(statusBody)}</span>
        </div>
        <div class="result-stats">
          <div><b>${num(reachable)}</b><span>Inside your rank</span></div>
          <div><b>${num(data.total)}</b><span>In this list</span></div>
          <div><b>${num(data.matched || 0)}</b><span>Seats checked</span></div>
        </div>
      </section>`;
      const groups = [];
      data.results.forEach((row) => {
        const last = groups[groups.length - 1];
        if (last && last.college === row.college) last.seats.push(row);
        else {
          groups.push({
            college: row.college,
            state: row.college_state,
            slug: row.slug,
            logo: row.logo,
            nirf: row.nirf_rank,
            package: row.highest_package,
            seats: [row]
          });
        }
      });
      const start = append ? results.querySelectorAll(".college-result").length : 0;
      let seenStretch = append && Boolean(results.querySelector(".predict-split"));
      const cards = groups.map((group, index) => {
        const href = group.slug
          ? `/college/${encodeURIComponent(group.slug)}`
          : `/browse?q=${encodeURIComponent(group.college)}`;
        const meta = [
          group.state,
          group.nirf ? `NIRF #${num(group.nirf)}` : "",
          group.package ? `Highest ${group.package}` : ""
        ].filter(Boolean).join(" · ");
        const stretch = group.seats.every((row) => row.probability === "low" || row.probability === "very-low");
        const split = stretch && !seenStretch && reachable
          ? `<p class="predict-split">Closest seats past your rank</p>`
          : "";
        if (split) seenStretch = true;
        const logo = group.logo ? `<img src="${esc(group.logo)}" alt="" onerror="this.remove()">` : "";
        const lines = group.seats.map((row) => {
          const id = choiceId(row, data);
          shownSeats.set(id, {
            id,
            exam: data.exam,
            college: row.college,
            slug: row.slug || "",
            branch: row.branch,
            quota: row.quota,
            gender: row.gender,
            category: data.category,
            opening_rank: row.opening_rank,
            closing_rank: row.closing_rank,
            probability: row.probability,
            rank: data.rank
          });
          const added = choices.some((item) => item.id === id);
          return `<div class="branch-line ${esc(row.probability)}">
            <div class="branch-id">
              <p class="branch-name">${esc(row.branch)}</p>
              <span class="seat-sub">${esc(quotaText(row.quota))} · ${esc(poolText(row.gender))}</span>
            </div>
            <div class="rank-pair">
              <span><small>Opening</small><b>${row.opening_rank ? num(row.opening_rank) : "—"}</b></span>
              <span><small>Closing</small><b>${num(row.closing_rank)}</b></span>
            </div>
            <div class="branch-actions">
              <span class="pill ${esc(row.probability)}">${esc(bandLabel(row.probability))}</span>
              <button type="button" class="choice-add" data-choice="${esc(id)}" aria-pressed="${added ? "true" : "false"}">${added ? "Added" : "Add"}</button>
            </div>
          </div>`;
        }).join("");
        return `${split}<article class="college-result tone-${(start + index) % 6}">
          <a class="college-result-head" href="${href}">
            <span class="college-mark">${logo}${esc(lettersOf(group.college) || "•")}</span>
            <span class="college-id"><strong>${esc(group.college)}</strong><span>${esc(meta)}</span></span>
            <span class="open-chip">Open</span>
          </a>
          <div class="branch-list">${lines}</div>
        </article>`;
      }).join("");
      if (!append) {
        const families = data.branches || [];
        const allCount = families.reduce((sum, item) => sum + item.count, 0);
        let picks = "";
        if (families.length > 1) {
          const selected = data.branch || "";
          const chips = [`<button type="button" class="branch-chip" data-branch="" aria-pressed="${selected ? "false" : "true"}">All <b>${num(allCount)}</b></button>`]
            .concat(families.map((item) => `<button type="button" class="branch-chip" data-branch="${esc(item.name)}" aria-pressed="${item.name === selected ? "true" : "false"}">${esc(item.name)} <b>${num(item.count)}</b></button>`))
            .join("");
          picks = `<div class="branch-picks">${chips}</div>`;
        }
        results.innerHTML = banner.replace("</section>", `${picks}</section>`) + (data.total ? cards : "");
      } else results.insertAdjacentHTML("beforeend", cards);
      const shown = Math.min(data.total, data.page * data.page_size);
      more.hidden = !data.total || shown >= data.total;
      more.textContent = `Show more · ${num(shown)} of ${num(data.total)}`;
      if (record) paintHistory();
    } catch (error) {
      status.textContent = error.message;
      status.setAttribute("role", "alert");
    }
  }

  function begin() {
    branch = "";
    results.innerHTML = "";
    summary.innerHTML = "";
    run(1, false, true);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!student || !student.id) {
      window.setuOpenAccount(() => begin());
      return;
    }
    begin();
  });
  results.addEventListener("click", async (event) => {
    if (event.target.closest("[data-logout]")) {
      window.setuLogout();
      return;
    }
    if (event.target.closest("[data-edit-profile]")) {
      window.setuOpenAccount(null, "edit");
      return;
    }
    if (event.target.closest("[data-withdraw]")) {
      const id = student && student.id;
      try {
        if (id) await api(`/students/${encodeURIComponent(id)}`, { method: "DELETE" });
        window.setuLogout();
        results.innerHTML = "";
        summary.innerHTML = "";
        more.hidden = true;
        status.textContent = "Your name, mobile number, and saved predictions have been deleted.";
      } catch (error) {
        status.textContent = error.message;
        status.setAttribute("role", "alert");
      }
      return;
    }
    const add = event.target.closest(".choice-add");
    if (add) {
      toggleChoice(add.dataset.choice);
      return;
    }
    const button = event.target.closest(".branch-chip");
    if (!button) return;
    branch = button.dataset.branch || "";
    results.innerHTML = "";
    run(1, false);
  });
  choicesBox.addEventListener("click", (event) => {
    const clear = event.target.closest("[data-choice-clear]");
    const up = event.target.closest("[data-choice-up]");
    const down = event.target.closest("[data-choice-down]");
    const remove = event.target.closest("[data-choice-remove]");
    if (clear) choices = [];
    else if (up) {
      const index = Number(up.dataset.choiceUp);
      if (index > 0) [choices[index - 1], choices[index]] = [choices[index], choices[index - 1]];
    } else if (down) {
      const index = Number(down.dataset.choiceDown);
      if (index < choices.length - 1) [choices[index + 1], choices[index]] = [choices[index], choices[index + 1]];
    } else if (remove) choices.splice(Number(remove.dataset.choiceRemove), 1);
    else return;
    saveChoices(choices);
    paintChoices();
    markAdded();
  });
  more.addEventListener("click", () => run(page + 1, true));
}

function initAccount() {
  const dialog = document.createElement("dialog");
  dialog.className = "student-dialog account-dialog";
  dialog.innerHTML = `<form id="account-form" novalidate>
      <div class="student-head">
        <h2>Log in</h2>
        <button class="student-close" type="button" data-account-close>Close</button>
      </div>
      <div data-step="mobile">
        <p>Enter your mobile number. The code arrives on WhatsApp.</p>
        <label class="field"><span>Mobile number</span><input name="mobile" inputmode="numeric" maxlength="10" autocomplete="tel" placeholder="10-digit Indian number"></label>
      </div>
      <div data-step="otp" hidden>
        <p>Enter the 4-digit WhatsApp code. Until WhatsApp is connected, the code is 1234.</p>
        <label class="field"><span>Code</span><input name="otp" inputmode="numeric" maxlength="4" autocomplete="one-time-code" placeholder="1234"></label>
      </div>
      <div data-step="name" hidden>
        <p>This number is new. Your name is shown on the result, and the mobile number creates your ID.</p>
        <label class="field"><span>Name</span><input name="name" maxlength="80" autocomplete="name" placeholder="Your name"></label>
        <label class="consent-row"><input type="checkbox" name="consent" value="yes"><span>I agree that Admission Setu can save my name and mobile number to show this result in my name and keep this prediction. I can withdraw this on the result page.</span></label>
        <p class="consent-note">This number is not used for calls or messages. Withdraw deletes your name, number, and saved predictions. You can also complain to the Data Protection Board of India.</p>
      </div>
      <div data-step="home" hidden>
        <p class="account-id"><strong data-account-name></strong><span class="role-badge" data-account-role data-role="student">Student</span><span data-account-id></span></p>
        <p data-admin-desk hidden><a class="button" href="/admin">Open college desk</a></p>
        <section data-team hidden>
          <h3>Staff</h3>
          <p class="consent-note">Add a staff number. That person logs in with their mobile and the WhatsApp code. Only this admin number can add or remove staff.</p>
          <label class="field"><span>Staff name</span><input name="staff_name" maxlength="80" placeholder="Name"></label>
          <label class="field"><span>Staff mobile</span><input name="staff_mobile" inputmode="numeric" maxlength="10" placeholder="10-digit number"></label>
          <button class="button" type="button" data-add-staff>Make staff</button>
          <div data-staff-list></div>
        </section>
        <h3>Your predictions</h3>
        <div data-account-history></div>
        <div class="account-actions">
          <button class="ghost" type="button" data-account-edit>Edit profile</button>
          <button class="ghost" type="button" data-account-logout>Log out</button>
        </div>
      </div>
      <div data-step="edit" hidden>
        <p>Your ID stays the same.</p>
        <label class="field"><span>Name</span><input name="edit_name" maxlength="80" autocomplete="name"></label>
        <label class="field"><span>Mobile number</span><input name="edit_mobile" inputmode="numeric" maxlength="10" autocomplete="tel"></label>
      </div>
      <p class="status" data-account-error></p>
      <button class="button" type="submit" data-account-submit>Continue</button>
    </form>`;
  document.body.appendChild(dialog);
  const form = dialog.querySelector("form");
  const error = dialog.querySelector("[data-account-error]");
  const submit = dialog.querySelector("[data-account-submit]");
  let pending = null;
  let mobile = "";

  function paintMenu() {
    const student = loadStudent();
    document.querySelectorAll("[data-account-open]").forEach((button) => {
      const label = student && student.name ? student.name.split(" ")[0] : "Log in";
      button.textContent = label;
    });
  }

  function mount(nav) {
    if (!nav || nav.querySelector("[data-account-open]")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "account-link";
    button.dataset.accountOpen = "1";
    button.textContent = "Log in";
    nav.appendChild(button);
  }

  document.querySelectorAll(".desktop-nav, .tabbar").forEach(mount);
  paintMenu();

  function show(step) {
    dialog.querySelectorAll("[data-step]").forEach((panel) => {
      panel.hidden = panel.dataset.step !== step;
    });
    const titles = { mobile: "Log in", otp: "WhatsApp code", name: "Create your ID", home: "Your account", edit: "Edit profile" };
    const buttons = { mobile: "Send code", otp: "Log in", name: "Create my ID", home: "", edit: "Save profile" };
    dialog.querySelector("h2").textContent = titles[step] || "Log in";
    submit.hidden = step === "home";
    submit.textContent = buttons[step] || "Continue";
    submit.disabled = step === "name" && !form.elements.consent.checked;
  }

  function paintAccount(student) {
    const role = student.role === "admin" || student.role === "staff" ? student.role : "student";
    const labels = { admin: "Admin", staff: "Staff", student: "Student" };
    dialog.querySelector("[data-account-name]").textContent = student.name;
    dialog.querySelector("[data-account-id]").textContent = student.id;
    const badge = dialog.querySelector("[data-account-role]");
    badge.textContent = labels[role];
    badge.dataset.role = role;
    dialog.querySelector("[data-admin-desk]").hidden = role !== "admin";
    dialog.querySelector("[data-team]").hidden = role !== "admin";
  }

  function staffList(rows) {
    if (!rows.length) return `<p class="consent-note">No staff yet.</p>`;
    return `<ul class="staff-list">${rows.map((row) => `
      <li>
        <span><strong>${esc(row.name)}</strong><small>${esc(row.mobile)}</small></span>
        <button class="ghost" type="button" data-drop-staff="${esc(row.mobile)}">Remove</button>
      </li>`).join("")}</ul>`;
  }

  async function loadStaff() {
    const list = dialog.querySelector("[data-staff-list]");
    list.innerHTML = `<p class="consent-note">Loading staff…</p>`;
    try {
      const data = await api("/team");
      list.innerHTML = staffList(data.staff || []);
    } catch (failure) {
      list.innerHTML = `<p class="consent-note">${esc(failure.message)} Log out and log in again with the admin number.</p>`;
    }
  }

  async function showHome(student) {
    show("home");
    paintAccount(student);
    const list = dialog.querySelector("[data-account-history]");
    list.innerHTML = `<p class="consent-note">Loading history…</p>`;
    try {
      const data = await api(`/students/${encodeURIComponent(student.id)}`);
      student = {
        id: data.id,
        name: data.name,
        mobile: data.mobile,
        role: data.role || student.role || "student"
      };
      saveStudent(student);
      paintAccount(student);
      paintMenu();
      if (student.role === "admin") loadStaff();
      list.innerHTML = historyList(data.predictions);
    } catch (failure) {
      if ((student.role || "") === "admin") loadStaff();
      list.innerHTML = `<p class="consent-note">${esc(failure.message)}</p>`;
    }
  }

  function finish(student) {
    saveStudent(student);
    paintMenu();
    document.dispatchEvent(new CustomEvent("setu-student", { detail: student }));
    if (pending) {
      const next = pending;
      pending = null;
      dialog.close();
      next();
      return;
    }
    showHome(student);
  }

  function fail(message) {
    error.textContent = message;
    error.setAttribute("role", "alert");
  }

  async function open(next, mode) {
    pending = typeof next === "function" ? next : null;
    error.textContent = "";
    error.removeAttribute("role");
    const student = loadStudent();
    if (mode === "edit" && student) {
      let current = student;
      if (!current.mobile) {
        const data = await api(`/students/${encodeURIComponent(current.id)}`);
        current = { id: data.id, name: data.name, mobile: data.mobile, role: data.role || "student" };
        saveStudent(current);
      }
      form.elements.edit_name.value = current.name || "";
      form.elements.edit_mobile.value = current.mobile || "";
      show("edit");
    } else if (student && mode !== "login") {
      await showHome(student);
    } else {
      show("mobile");
      form.elements.mobile.focus();
    }
    if (!dialog.open) dialog.showModal();
  }

  form.elements.mobile.addEventListener("input", () => {
    form.elements.mobile.value = digitsOnly(form.elements.mobile.value);
  });
  form.elements.edit_mobile.addEventListener("input", () => {
    form.elements.edit_mobile.value = digitsOnly(form.elements.edit_mobile.value);
  });
  form.elements.staff_mobile.addEventListener("input", () => {
    form.elements.staff_mobile.value = digitsOnly(form.elements.staff_mobile.value);
  });
  form.elements.otp.addEventListener("input", () => {
    form.elements.otp.value = form.elements.otp.value.replace(/\D/g, "").slice(0, 4);
  });
  form.elements.consent.addEventListener("change", () => {
    if (dialog.querySelector("[data-step='name']").hidden) return;
    submit.disabled = !form.elements.consent.checked;
  });
  dialog.querySelector("[data-account-close]").addEventListener("click", () => dialog.close());
  dialog.querySelector("[data-account-edit]").addEventListener("click", () => {
    const student = loadStudent();
    if (!student) return;
    form.elements.edit_name.value = student.name || "";
    form.elements.edit_mobile.value = student.mobile || "";
    show("edit");
  });
  dialog.querySelector("[data-account-logout]").addEventListener("click", () => window.setuLogout());
  dialog.querySelector("[data-add-staff]").addEventListener("click", async () => {
    error.textContent = "";
    const staffMobile = digitsOnly(form.elements.staff_mobile.value);
    if (!form.elements.staff_name.value.trim() || !/^[6-9]\d{9}$/.test(staffMobile)) {
      fail("Enter the staff name and a 10-digit Indian mobile number.");
      return;
    }
    try {
      await api("/team", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.elements.staff_name.value, mobile: staffMobile, role: "staff" })
      });
      form.elements.staff_name.value = "";
      form.elements.staff_mobile.value = "";
      await loadStaff();
    } catch (failure) {
      fail(failure.message);
    }
  });
  dialog.querySelector("[data-staff-list]").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-drop-staff]");
    if (!button) return;
    error.textContent = "";
    try {
      await api("/team", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile: button.dataset.dropStaff, role: "student" })
      });
      await loadStaff();
    } catch (failure) {
      fail(failure.message);
    }
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-account-open]")) open(null, loadStudent() ? "home" : "login");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    error.removeAttribute("role");
    const step = dialog.querySelector("[data-step]:not([hidden])").dataset.step;
    if (step === "home") return;
    try {
      if (step === "mobile") {
        mobile = digitsOnly(form.elements.mobile.value);
        if (!/^[6-9]\d{9}$/.test(mobile)) {
          fail("Enter a 10-digit Indian mobile number.");
          return;
        }
        await api("/auth/otp", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mobile })
        });
        show("otp");
        form.elements.otp.focus();
        return;
      }
      if (step === "otp" || step === "name") {
        const otp = form.elements.otp.value.trim();
        const payload = { mobile, otp };
        if (step === "name") {
          if (!form.elements.consent.checked) {
            fail("Tick the box to agree before we save your name and mobile number.");
            return;
          }
          payload.name = form.elements.name.value;
          payload.consent = true;
        }
        const result = await api("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (result.needs_name) {
          show("name");
          form.elements.name.focus();
          return;
        }
        finish(result);
        return;
      }
      if (step === "edit") {
        const student = loadStudent();
        const nextMobile = digitsOnly(form.elements.edit_mobile.value);
        if (!/^[6-9]\d{9}$/.test(nextMobile)) {
          fail("Enter a 10-digit Indian mobile number.");
          return;
        }
        const updated = await api(`/students/${encodeURIComponent(student.id)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: form.elements.edit_name.value, mobile: nextMobile })
        });
        finish(updated);
      }
    } catch (failure) {
      fail(failure.message);
    }
  });

  window.setuOpenAccount = open;
  window.setuLogout = () => {
    api("/auth/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem(STUDENT_KEY);
    paintMenu();
    pending = null;
    document.dispatchEvent(new CustomEvent("setu-student", { detail: null }));
    show("mobile");
    if (dialog.open) dialog.close();
  };
}

const page = document.body.dataset.page;
initAccount();
if (page === "home") initHome();
if (page === "browse") initBrowse();
if (page === "college") initCollege();
if (page === "chances") initChances();
