import { decodeEntities, formatInr, h, icon, safeZomatoUrl, titleCase } from "../dom.js";

const ACCENTS = [
  { badge: "bg-primary-container text-white shadow-[0_0_16px_rgba(255,76,133,0.6)]", art: "from-primary-container/60 via-secondary-container/40 to-surface-container" },
  { badge: "bg-tertiary-fixed text-black shadow-[0_0_16px_rgba(189,245,50,0.5)]", art: "from-tertiary-container/60 via-secondary-container/30 to-surface-container" },
  { badge: "bg-secondary-container text-white shadow-[0_0_16px_rgba(124,92,255,0.6)]", art: "from-secondary-container/70 via-primary-container/30 to-surface-container" },
];

function splitCuisines(value) {
  return String(value || "")
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);
}

function Pill(content, cls) {
  return h("span", { class: `inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-label-md ${cls}` }, ...content);
}

function Flag(on, label, iconName) {
  return h(
    "span",
    { class: `inline-flex items-center gap-1 text-body-sm ${on ? "text-tertiary-fixed" : "text-on-surface-variant/50 line-through"}` },
    icon(on ? iconName : "block", "text-[16px]"),
    label,
  );
}

export function RestaurantCard(item, index) {
  const accent = ACCENTS[index % ACCENTS.length];
  const name = decodeEntities(item.name) || "Unnamed spot";
  const explanation = decodeEntities(item.explanation);
  const cuisines = splitCuisines(item.cuisine);
  const cost = formatInr(item.cost_for_two);
  const url = safeZomatoUrl(item.url);
  const initial = name.trim()[0]?.toUpperCase() || "?";

  const art = h(
    "div",
    { class: `relative h-28 rounded overflow-hidden bg-gradient-to-br ${accent.art} border border-white/5` },
    h("span", {
      class: "absolute -right-2 -bottom-8 font-display font-bold text-[120px] leading-none text-white/10 select-none",
      "aria-hidden": "true",
      text: initial,
    }),
    h(
      "span",
      { class: `absolute top-3 left-3 h-10 w-10 rounded-full grid place-items-center font-display text-headline-sm ${accent.badge}`, "aria-label": `Rank ${item.rank}` },
      `#${item.rank}`,
    ),
    h(
      "div",
      { class: "absolute top-3 right-3 flex gap-2" },
      item.rating != null
        ? Pill([icon("star", "icon-fill text-[14px]"), Number(item.rating).toFixed(1)], "bg-black/50 backdrop-blur text-tertiary-fixed border border-tertiary/30")
        : Pill(["New"], "bg-black/50 backdrop-blur text-on-surface-variant border border-white/10"),
    ),
    item.rest_type
      ? h("span", { class: "absolute bottom-3 left-3 px-2.5 py-1 rounded-full bg-black/40 backdrop-blur text-label-sm uppercase tracking-widest text-on-surface", text: item.rest_type })
      : null,
  );

  const header = h(
    "div",
    { class: "flex items-start justify-between gap-space-sm" },
    h(
      "div",
      { class: "min-w-0" },
      h("h3", { class: "font-display text-headline-sm text-white truncate", title: name, text: name }),
      h(
        "p",
        { class: "flex items-center gap-1 text-body-md text-on-surface-variant truncate" },
        icon("location_on", "text-[16px] text-primary"),
        item.location || "Bangalore",
      ),
    ),
    cost
      ? h(
          "div",
          { class: "shrink-0 text-right" },
          h("p", { class: "font-display text-headline-sm text-on-surface", text: cost }),
          h("p", { class: "text-label-sm uppercase tracking-widest text-on-surface-variant/70", text: "for two" }),
        )
      : null,
  );

  const chips = cuisines.length
    ? h(
        "div",
        { class: "flex flex-wrap gap-1.5" },
        cuisines.slice(0, 4).map((c) => Pill([titleCase(c)], "bg-secondary-container/30 text-secondary border border-secondary/20")),
        cuisines.length > 4 ? Pill([`+${cuisines.length - 4}`], "bg-surface-container-high text-on-surface-variant") : null,
      )
    : null;

  const why = explanation
    ? h(
        "div",
        { class: "rounded bg-surface-container-lowest/70 border border-white/5 p-space-md" },
        h(
          "p",
          { class: "flex items-center gap-1 text-label-sm uppercase tracking-widest text-primary mb-1" },
          icon("auto_awesome", "icon-fill text-[14px]"),
          "Why it fits",
        ),
        h("p", { class: "text-body-md text-on-surface leading-relaxed", text: explanation }),
      )
    : null;

  const footer = h(
    "div",
    { class: "flex flex-wrap items-center justify-between gap-space-sm pt-space-sm border-t border-white/5 mt-auto" },
    h(
      "div",
      { class: "flex flex-wrap gap-space-md" },
      item.online_order != null ? Flag(item.online_order, "Delivery", "delivery_dining") : null,
      item.book_table != null ? Flag(item.book_table, "Table booking", "event_seat") : null,
    ),
    url
      ? h(
          "a",
          {
            href: url,
            target: "_blank",
            rel: "noopener noreferrer",
            class: "inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-label-md text-white border border-primary/50 hover:bg-primary-container hover:border-transparent transition-colors",
          },
          "Zomato",
          icon("arrow_outward", "text-[16px]"),
        )
      : null,
  );

  return h(
    "article",
    {
      class: "fade-in glass rounded-lg p-space-md md:p-space-lg flex flex-col gap-space-md hover:-translate-y-1 hover:border-primary/30 hover:shadow-[0_10px_40px_rgba(255,76,133,0.15)] transition-all duration-300",
      style: { animationDelay: `${Math.min(index, 8) * 60}ms` },
    },
    art,
    header,
    item.address ? h("p", { class: "text-body-sm text-on-surface-variant/70 line-clamp-1", title: item.address, text: item.address }) : null,
    chips,
    why,
    footer,
  );
}
