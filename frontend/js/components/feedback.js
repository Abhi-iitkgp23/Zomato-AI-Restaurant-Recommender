import { h, icon } from "../dom.js";

const BANNER_TONES = {
  info: { box: "bg-secondary-container/25 border-secondary/40", icon: "text-secondary", name: "info" },
  warn: { box: "bg-amber/10 border-amber/40", icon: "text-amber", name: "warning" },
  error: { box: "bg-error-container/30 border-error/50", icon: "text-error", name: "error" },
  success: { box: "bg-tertiary/10 border-tertiary/40", icon: "text-tertiary-fixed", name: "check_circle" },
};

export function Banner({ tone = "info", title, body, iconName }) {
  const t = BANNER_TONES[tone] || BANNER_TONES.info;
  return h(
    "div",
    { role: tone === "error" ? "alert" : "status", class: `fade-in flex gap-space-sm items-start rounded border px-space-md py-3 ${t.box}` },
    icon(iconName || t.name, `${t.icon} text-[20px] mt-0.5`),
    h(
      "div",
      { class: "min-w-0" },
      title ? h("p", { class: "text-label-lg text-on-surface", text: title }) : null,
      body ? h("p", { class: "text-body-md text-on-surface-variant", text: body }) : null,
    ),
  );
}

export function SkeletonCard() {
  const bar = (w, hgt = "h-4") => h("div", { class: `shimmer rounded-full ${hgt} ${w}` });
  return h(
    "div",
    { class: "glass rounded-lg p-space-lg space-y-space-md", "aria-hidden": "true" },
    h("div", { class: "shimmer rounded h-28 w-full" }),
    bar("w-2/3", "h-6"),
    bar("w-1/3"),
    h("div", { class: "flex gap-2" }, bar("w-16", "h-6"), bar("w-20", "h-6"), bar("w-14", "h-6")),
    bar("w-full"),
    bar("w-5/6"),
  );
}

export function EmptyState({ iconName = "search_off", title, body, action }) {
  return h(
    "div",
    { class: "fade-in glass rounded-lg px-space-lg py-12 text-center flex flex-col items-center" },
    h(
      "div",
      { class: "h-16 w-16 rounded-full grid place-items-center bg-gradient-to-br from-primary-container/30 to-secondary-container/40 border border-white/10 mb-space-md" },
      icon(iconName, "text-[32px] text-primary"),
    ),
    h("h3", { class: "font-display text-headline-md text-white", text: title }),
    body ? h("p", { class: "mt-space-sm text-body-lg text-on-surface-variant max-w-md", text: body }) : null,
    action || null,
  );
}
