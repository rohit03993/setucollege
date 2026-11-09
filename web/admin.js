const root = document.querySelector("#editor");
const source = document.querySelector("#college-doc");
const doc = JSON.parse(source.textContent);
const token = root.dataset.token;
const original = root.dataset.slug || "";
const creating = root.dataset.mode === "new";

function field(label, name, value, wide) {
  return `<label class="field ${wide ? "wide" : ""}"><span>${label}</span><input name="${name}" value="${escapeAttr(value)}"></label>`;
}

function area(label, name, value) {
  return `<label class="field wide"><span>${label}</span><textarea name="${name}">${escapeText(value)}</textarea></label>`;
}

function escapeText(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttr(value) {
  return escapeText(value).replace(/"/g, "&quot;");
}

function lines(list) {
  return (list || []).join("\n");
}

function cells(row) {
  return (row || []).join(" | ");
}

function courseBlock(group, index) {
  return `<article class="block" data-kind="course">
    <header><h3>Degree ${index + 1}</h3><button class="ghost remove" type="button">Remove</button></header>
    <div class="grid-2">
      <label class="field"><span>Degree</span><input data-field="degree" value="${escapeAttr(group.degree)}"></label>
      <label class="field"><span>Yearly fee</span><input data-field="fee" value="${escapeAttr(group.fee)}"></label>
    </div>
    <label class="field wide"><span>Courses, one on each line</span><textarea data-field="names">${escapeText(lines(group.courses))}</textarea></label>
  </article>`;
}

function storyBlock(item, index, kind, titleLabel) {
  return `<article class="block" data-kind="${kind}">
    <header><h3>${titleLabel} ${index + 1}</h3><button class="ghost remove" type="button">Remove</button></header>
    <label class="field wide"><span>Title</span><input data-field="title" value="${escapeAttr(item.title)}"></label>
    <label class="field wide"><span>Text</span><textarea data-field="content">${escapeText(item.content)}</textarea></label>
  </article>`;
}

function tableBlock(table, index, kind) {
  const rows = (table.rows || []).map(cells).join("\n");
  return `<article class="block" data-kind="${kind}">
    <header><h3>Table ${index + 1}</h3><button class="ghost remove" type="button">Remove</button></header>
    <label class="field wide"><span>Title</span><input data-field="title" value="${escapeAttr(table.title)}"></label>
    <label class="field wide"><span>Column names, separated by |</span><input data-field="columns" value="${escapeAttr(cells(table.columns))}"></label>
    <label class="field wide"><span>Rows, one on each line, cells separated by |</span><textarea data-field="rows">${escapeText(rows)}</textarea></label>
  </article>`;
}

function answerBlock(item, index) {
  return `<article class="block" data-kind="answer">
    <header><h3>Answer ${index + 1}</h3><button class="ghost remove" type="button">Remove</button></header>
    <label class="field wide"><span>Question</span><input data-field="question" value="${escapeAttr(item.question)}"></label>
    <label class="field wide"><span>Answer</span><textarea data-field="answer">${escapeText(item.answer)}</textarea></label>
  </article>`;
}

function list(kind, items, builder, empty) {
  const cards = (items.length ? items : [empty]).map((item, index) => builder(item, index)).join("");
  return `${cards}<button class="ghost add" type="button" data-add="${kind}">Add another</button>`;
}

function picture(name, previewId, label, value, note) {
  return `<article class="media-card">
    <img class="preview" id="${previewId}" alt="">
    <label class="field wide"><span>${label} link</span><input name="${name}" value="${escapeAttr(value)}" placeholder="https://"></label>
    <label class="upload">Upload a picture<input type="file" accept="image/jpeg,image/png,image/webp,image/gif" data-upload="${name}"></label>
    <p class="hint">${note}</p>
  </article>`;
}

const panels = {
  basics: () => `<div class="grid-2">
      <label class="field wide"><span>Web address</span>
        <span class="slug-row"><span class="prefix">/college/</span><input name="slug" value="${escapeAttr(doc.slug)}" placeholder="college-name"></span>
      </label>
      ${field("Name", "name", doc.name)}
      ${field("City", "city", doc.city)}
      ${field("State", "state", doc.state)}
      ${field("Type", "ownership", doc.ownership)}
      ${field("Yearly fee, as shown", "fee_label", doc.fee_label)}
      ${field("NIRF rank", "nirf_rank", doc.nirf_rank)}
      ${field("Year established", "established_year", doc.established_year)}
      ${field("Average package", "average_package", doc.average_package)}
      ${field("Highest package", "highest_package", doc.highest_package)}
      ${field("Rating", "rating", doc.rating)}
      ${field("Review count", "reviews", doc.reviews)}
      ${field("Course count", "course_count", doc.course_count)}
      ${field("Website", "website", doc.website)}
      ${field("Phone", "phone", doc.phone)}
      ${field("Streams, separated by commas", "streams", (doc.streams || []).join(", "), true)}
      ${field("Exams, separated by commas", "exams", (doc.exams || []).join(", "), true)}
      ${area("Short introduction", "overview", doc.overview)}
    </div>
    <label class="check"><input name="hidden" type="checkbox" ${doc.hidden ? "checked" : ""}> Hide this college from the site</label>
    <p class="hint">The web address is the last part of the college link. Use lowercase letters, numbers, and hyphens.</p>`,
  media: () => `<div class="grid-2">
      ${picture("logo", "logo-preview", "Logo", doc.logo, "Shown beside the college name.")}
      ${picture("image", "photo-preview", "Campus photo", doc.image, "Shown across the top of the college page.")}
    </div>
    ${field("YouTube link", "video", doc.video, true)}
    <p class="hint">Paste a YouTube link, or leave it empty if this college has no video.</p>`,
  courses: () => list("course", doc.course_groups || [], courseBlock, { degree: "", fee: "", courses: [] }),
  admission: () => list("admission", doc.admission || [], (item, index) => storyBlock(item, index, "admission", "Section"), { title: "", content: "" }),
  cutoff: () => `<p class="hint">Separate cells with a vertical bar. Example: Computer Science | 277 | 587. Up to 8 tables are saved.</p>${list("cutoff", doc.cutoff || [], (item, index) => tableBlock(item, index, "cutoff"), { title: "", columns: [], rows: [] })}`,
  placements: () => `${area("Recruiters", "recruiters", doc.recruiters)}${list("placement", doc.placements || [], (item, index) => tableBlock(item, index, "placement"), { title: "", columns: [], rows: [] })}`,
  answers: () => list("answer", doc.answers || [], answerBlock, { question: "", answer: "" })
};

const tabs = [
  ["basics", "Basics"],
  ["media", "Photo and video"],
  ["courses", "Courses"],
  ["admission", "Admission"],
  ["cutoff", "Cutoff"],
  ["placements", "Placements"],
  ["answers", "Answers"]
];

let current = "basics";

function paint() {
  document.querySelector("#tabs").innerHTML = tabs
    .map(([id, label]) => `<button type="button" data-tab="${id}" aria-pressed="${id === current}">${label}</button>`)
    .join("");
  const label = tabs.find(([id]) => id === current)[1];
  document.querySelector("#panel").innerHTML = `<h2 class="panel-title">${label}</h2>${panels[current]()}`;
  bind();
  refreshPreviews();
}

function bind() {
  document.querySelector("#tabs").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      keep();
      current = button.dataset.tab;
      paint();
    });
  });
  const panel = document.querySelector("#panel");
  panel.querySelectorAll(".remove").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest(".block").remove();
    });
  });
  panel.querySelectorAll(".add").forEach((button) => {
    button.addEventListener("click", () => {
      keep();
      const kind = button.dataset.add;
      if (kind === "course") doc.course_groups.push({ degree: "", fee: "", courses: [] });
      if (kind === "admission") doc.admission.push({ title: "", content: "" });
      if (kind === "cutoff") doc.cutoff.push({ title: "", columns: [], rows: [] });
      if (kind === "placement") doc.placements.push({ title: "", columns: [], rows: [] });
      if (kind === "answer") doc.answers.push({ question: "", answer: "" });
      paint();
    });
  });
  panel.querySelectorAll("[name='logo'], [name='image']").forEach((input) => {
    input.addEventListener("input", refreshPreviews);
  });
  panel.querySelectorAll("[data-upload]").forEach((input) => {
    input.addEventListener("change", () => uploadPicture(input));
  });
}

async function uploadPicture(input) {
  const file = input.files && input.files[0];
  const note = document.querySelector("#save-note");
  if (!file) return;
  if (file.size > 4 * 1024 * 1024) {
    note.textContent = "That picture is larger than 4 MB.";
    note.setAttribute("role", "alert");
    input.value = "";
    return;
  }
  note.textContent = "Uploading picture…";
  note.removeAttribute("role");
  const body = new FormData();
  body.append("token", token);
  body.append("file", file);
  const response = await fetch("/admin/api/upload", { method: "POST", body });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    note.textContent = data.error || "That picture could not be uploaded.";
    note.setAttribute("role", "alert");
    return;
  }
  const target = document.querySelector(`#panel [name="${input.dataset.upload}"]`);
  if (target) target.value = data.url;
  note.textContent = "Picture added. Save the college to publish it.";
  refreshPreviews();
}

function splitList(value) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

function splitCells(value) {
  return value.split("|").map((part) => part.trim()).filter((part) => part !== "");
}

function readBlocks(kind) {
  return [...document.querySelectorAll(`[data-kind="${kind}"]`)].map((article) => {
    const data = {};
    article.querySelectorAll("[data-field]").forEach((node) => {
      data[node.dataset.field] = node.value.trim();
    });
    return data;
  });
}

function keep() {
  const named = (name) => {
    const node = document.querySelector(`#panel [name="${name}"]`);
    return node ? node.value.trim() : doc[name];
  };
  if (current === "basics") {
    ["slug", "name", "city", "state", "ownership", "fee_label", "nirf_rank", "established_year", "average_package", "highest_package", "rating", "reviews", "course_count", "website", "phone", "overview"].forEach((name) => {
      doc[name] = named(name);
    });
    doc.streams = splitList(named("streams"));
    doc.exams = splitList(named("exams"));
    const hidden = document.querySelector("#panel [name='hidden']");
    if (hidden) doc.hidden = hidden.checked;
  }
  if (current === "media") {
    doc.logo = named("logo");
    doc.image = named("image");
    doc.video = named("video");
  }
  if (current === "courses") {
    doc.course_groups = readBlocks("course").map((item) => ({
      degree: item.degree || "",
      fee: item.fee || "",
      courses: (item.names || "").split("\n").map((line) => line.trim()).filter(Boolean)
    })).filter((item) => item.degree || item.fee || item.courses.length);
  }
  if (current === "admission") {
    doc.admission = readBlocks("admission").filter((item) => item.title || item.content);
  }
  if (current === "cutoff") doc.cutoff = readTables("cutoff");
  if (current === "placements") {
    doc.recruiters = named("recruiters");
    doc.placements = readTables("placement");
  }
  if (current === "answers") {
    doc.answers = readBlocks("answer").filter((item) => item.question || item.answer);
  }
}

function readTables(kind) {
  return readBlocks(kind).map((item) => ({
    title: item.title || "",
    columns: splitCells(item.columns || ""),
    rows: (item.rows || "").split("\n").map(splitCells).filter((row) => row.length)
  })).filter((table) => table.title || table.rows.length);
}

function refreshPreviews() {
  const logo = document.querySelector("[name='logo']");
  const photo = document.querySelector("[name='image']");
  const logoPreview = document.querySelector("#logo-preview");
  const photoPreview = document.querySelector("#photo-preview");
  if (logoPreview && logo) {
    logoPreview.src = logo.value.trim();
    logoPreview.hidden = !logo.value.trim();
  }
  if (photoPreview && photo) {
    photoPreview.src = photo.value.trim();
    photoPreview.hidden = !photo.value.trim();
  }
}

function videoId(value) {
  const text = value.trim();
  if (!text) return "";
  if (/^[\w-]{11}$/.test(text)) return text;
  const match = text.match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/);
  return match ? match[1] : null;
}

async function save() {
  keep();
  const note = document.querySelector("#save-note");
  const video = videoId(doc.video || "");
  if (video === null) {
    note.textContent = "That YouTube link could not be read. Paste the full link, or leave it empty.";
    note.setAttribute("role", "alert");
    return;
  }
  note.textContent = "Saving…";
  note.removeAttribute("role");
  const response = await fetch("/admin/api/college", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      token,
      original_slug: original,
      creating,
      ...doc,
      video_id: video
    })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    note.textContent = data.error || "The college could not be saved.";
    note.setAttribute("role", "alert");
    return;
  }
  location.href = `/admin/colleges/${encodeURIComponent(data.slug)}`;
}

document.querySelector("#save").addEventListener("click", save);
paint();
