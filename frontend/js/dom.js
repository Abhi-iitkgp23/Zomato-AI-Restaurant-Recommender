/**
 * Tiny element factory. All string children become text nodes, so API data is
 * never parsed as HTML.
 */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") {
      el.className = value;
    } else if (key === "text") {
      el.textContent = value;
    } else if (key === "dataset") {
      Object.assign(el.dataset, value);
    } else if (key === "style" && typeof value === "object") {
      Object.assign(el.style, value);
    } else if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key in el && typeof value !== "string") {
      el[key] = value;
    } else {
      el.setAttribute(key, value === true ? "" : String(value));
    }
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function icon(name, cls = "") {
  return h("span", { class: `material-symbols-outlined ${cls}`, "aria-hidden": "true", text: name });
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

/** The API HTML-escapes free text; decode it back so textContent shows it verbatim. */
export function decodeEntities(value) {
  if (!value) return "";
  const doc = new DOMParser().parseFromString(`<!doctype html><body>${value}`, "text/html");
  return doc.body.textContent || "";
}

export function safeZomatoUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:") return null;
    if (url.hostname !== "zomato.com" && !url.hostname.endsWith(".zomato.com")) return null;
    return url.href;
  } catch {
    return null;
  }
}

export function titleCase(value) {
  return String(value || "")
    .split(/\s+/)
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");
}

export function formatInr(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  return `₹${Math.round(Number(value)).toLocaleString("en-IN")}`;
}

let idCounter = 0;
export function uid(prefix = "c") {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
}
