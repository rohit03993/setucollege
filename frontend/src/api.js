export const STUDENT_KEY = "setu-student";

export async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : "That request could not be completed.");
  }
  return data;
}

export function loadStudent() {
  try {
    const saved = JSON.parse(localStorage.getItem(STUDENT_KEY) || "null");
    if (saved && saved.id && saved.name) return saved;
  } catch (error) {
    return null;
  }
  return null;
}

export function saveStudent(student) {
  localStorage.setItem(STUDENT_KEY, JSON.stringify(student));
}

export function clearStudent() {
  localStorage.removeItem(STUDENT_KEY);
}

export function num(value) {
  return Number(value).toLocaleString("en-IN");
}

export function place(college) {
  return [college.city, college.state].filter(Boolean).join(", ");
}

export function lettersOf(name) {
  return String(name || "")
    .split(/\s+/)
    .filter((word) => /[A-Za-z]/.test(word))
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
}

export function shownFee(label) {
  const text = String(label || "").trim();
  if (!text || text === "—" || text === "-") return "";
  return text.includes("₹") ? text : `₹${text}`;
}

export function packageText(college) {
  const written = String(college.highest_package || "").trim();
  if (written) return written;
  const value = Number(college.highest_package_lpa);
  if (!value) return "";
  if (value >= 100) return `₹${String(value / 100).replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "")} Cr`;
  const text = value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  return `₹${text} LPA`;
}

export function digitsOnly(value) {
  let digits = String(value || "").replace(/\D/g, "");
  if (digits.startsWith("91") && digits.length > 10) digits = digits.slice(2);
  if (digits.startsWith("0") && digits.length > 10) digits = digits.slice(1);
  return digits.slice(0, 10);
}
