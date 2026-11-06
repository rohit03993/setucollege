const list = document.querySelector("#list");
const count = document.querySelector("#count");
const none = document.querySelector("#none");
const search = document.querySelector("#q");
let mode = "fee";
let stream = "All";

function lakhs(text) {
  if (!text) return null;
  const match = String(text).replace(/,/g, "").match(/[\d.]+/);
  if (!match) return null;
  const value = Number(match[0]);
  if (!value) return null;
  if (/l/i.test(text)) return value;
  if (value >= 1000) return value / 100000;
  return value;
}

function sortValue(college) {
  if (mode === "fee") return lakhs(college.feeLabel);
  if (mode === "package") return lakhs(college.avgPackage);
  return college.nirf && college.nirf.rank ? college.nirf.rank : null;
}

function matches(college) {
  const query = search.value.trim().toLowerCase();
  const haystack = [college.name, college.city, college.state, ...college.exams, ...college.streams].join(" ").toLowerCase();
  if (query && !haystack.includes(query)) return false;
  if (stream === "All") return true;
  return college.streams.includes(stream);
}

function compare(a, b) {
  const left = sortValue(a);
  const right = sortValue(b);
  if (left == null && right == null) return a.name.localeCompare(b.name);
  if (left == null) return 1;
  if (right == null) return -1;
  if (mode === "package") return right - left;
  return left - right;
}

function cell(value, label, key) {
  const missing = !value;
  return `<div class="${mode === key ? "on" : ""} ${missing ? "missing" : ""}"><b>${value || "Not listed"}</b><span>${label}</span></div>`;
}

function row(college) {
  const link = document.createElement("a");
  link.className = "row";
  link.href = `college.html?college=${college.slug}`;
  const hostel = college.hostel === "Yes" ? " · Hostel on campus" : "";
  link.innerHTML = `
    <div>
      <h2>${college.name}</h2>
      <p class="where">${college.city}, ${college.state} · ${college.ownership} · ${college.exams[0] || college.streams[0]}${hostel}</p>
    </div>
    <div class="nums">
      ${cell(college.feeLabel, "a year", "fee")}
      ${cell(college.avgPackage, "avg package", "package")}
      ${cell(college.nirf.rank ? `#${college.nirf.rank}` : "", "NIRF", "rank")}
    </div>
  `;
  return link;
}

function render() {
  const shown = window.SETU.filter(matches).sort(compare);
  list.replaceChildren(...shown.map(row));
  const line = {
    fee: "lowest yearly fee",
    package: "highest average package",
    rank: "best NIRF rank"
  };
  const course = stream === "All" ? "" : ` in ${stream}`;
  count.textContent = `${shown.length} ${shown.length === 1 ? "college" : "colleges"}${course}, ${line[mode]} first.`;
  none.hidden = shown.length > 0;
}

document.querySelectorAll(".choices button").forEach((button) => {
  button.addEventListener("click", () => {
    mode = button.dataset.mode;
    document.querySelectorAll(".choices button").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
    render();
  });
});

document.querySelectorAll(".streams button").forEach((button) => {
  button.addEventListener("click", () => {
    stream = button.dataset.stream;
    document.querySelectorAll(".streams button").forEach((item) => {
      item.setAttribute("aria-pressed", String(item === button));
    });
    render();
  });
});

search.addEventListener("input", render);
document.querySelector(".search").addEventListener("submit", (event) => event.preventDefault());
render();
