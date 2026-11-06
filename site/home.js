const list = document.querySelector("#list");
const count = document.querySelector("#count");
const none = document.querySelector("#none");
const search = document.querySelector("#q");
const headerSearch = document.querySelector("#q-header");
const streamGrid = document.querySelector("#stream-grid");
let stream = "All";

const streamMeta = [
  {
    name: "Engineering",
    text: "B.Tech fees, JEE, and packages",
    icon: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 3 4 7v5c0 4.2 2.8 7.2 8 9 5.2-1.8 8-4.8 8-9V7l-8-4Z" stroke="#6d4aff" stroke-width="1.8"/></svg>`
  },
  {
    name: "Medical",
    text: "NEET colleges and course fees",
    icon: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="#6d4aff" stroke-width="1.8" stroke-linecap="round"/></svg>`
  },
  {
    name: "Management",
    text: "MBA fees, exams, and placements",
    icon: `<svg viewBox="0 0 24 24" fill="none"><rect x="4" y="7" width="16" height="12" rx="2" stroke="#6d4aff" stroke-width="1.8"/><path d="M9 7V5h6v2" stroke="#6d4aff" stroke-width="1.8"/></svg>`
  }
];

function countStream(name) {
  const total = window.SETU.filter((college) => college.streams.includes(name)).length;
  return total === 1 ? "1 college" : `${total} colleges`;
}

streamGrid.innerHTML = streamMeta
  .map(
    (item) => `<button class="stream-card" type="button" data-stream="${item.name}">
      <span class="stream-icon" aria-hidden="true">${item.icon}</span>
      <strong>${item.name}</strong>
      <span>${countStream(item.name)}</span>
      <em>${item.text}</em>
    </button>`
  )
  .join("");

function matches(college) {
  const query = search.value.trim().toLowerCase();
  const haystack = [college.name, college.city, college.state, college.fullName, ...college.exams, ...college.streams]
    .join(" ")
    .toLowerCase();
  if (query && !haystack.includes(query)) return false;
  if (stream === "All") return true;
  if (stream === "JEE") return college.exams.some((exam) => /jee/i.test(exam));
  if (stream === "NEET") return college.exams.some((exam) => /neet/i.test(exam));
  if (stream === "MBA") return college.streams.includes("Management");
  return college.streams.includes(stream);
}

function initials(name) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function card(college) {
  const link = document.createElement("a");
  link.className = "card college-card";
  link.href = `college.html?college=${college.slug}`;
  const factCells = [
    [college.feeLabel, college.feeNote],
    college.avgPackage ? [college.avgPackage, "avg package"] : null,
    college.nirf.rank ? [`#${college.nirf.rank}`, "NIRF"] : [college.exams[0], "exam"]
  ].filter(Boolean);
  link.innerHTML = `
    <div class="card-top">
      <span class="avatar">${initials(college.name)}</span>
      <div>
        <h3>${college.name}</h3>
        <p class="place">${college.city}, ${college.state}</p>
      </div>
      <span class="own">${college.ownership}</span>
    </div>
    <div class="facts" style="grid-template-columns: repeat(${factCells.length}, 1fr)">
      ${factCells.map(([value, label]) => `<div><strong>${value}</strong><span>${label}</span></div>`).join("")}
    </div>
    <div class="tags">${college.exams.map((exam) => `<span class="tag">${exam}</span>`).join("")}<span class="tag muted-tag">${college.streams[0]}</span></div>
  `;
  return link;
}

function setPressed() {
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.setAttribute("aria-pressed", String(chip.dataset.stream === stream));
  });
  document.querySelectorAll(".stream-card").forEach((cardButton) => {
    cardButton.classList.toggle("active", cardButton.dataset.stream === stream);
  });
}

function render() {
  const shown = window.SETU.filter(matches);
  list.replaceChildren(...shown.map(card));
  count.textContent = `${shown.length} of ${window.SETU.length}`;
  none.hidden = shown.length > 0;
  setPressed();
}

function choose(next) {
  stream = next;
  render();
}

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => choose(chip.dataset.stream));
});
document.querySelectorAll(".stream-card, [data-jump]").forEach((item) => {
  item.addEventListener("click", () => {
    choose(item.dataset.stream || item.dataset.jump);
    document.querySelector("#colleges").scrollIntoView({ behavior: "smooth" });
  });
});

function sync(from, to) {
  from.addEventListener("input", () => {
    to.value = from.value;
    render();
  });
}
sync(search, headerSearch);
sync(headerSearch, search);
document.querySelector(".search").addEventListener("submit", (event) => event.preventDefault());
document.querySelector(".header-search").addEventListener("submit", (event) => event.preventDefault());

render();
