import { clear, decodeEntities, h, icon } from "../dom.js";
import { Banner, EmptyState, SkeletonCard } from "./feedback.js";
import { RestaurantCard } from "./restaurant-card.js";

const HANDLED_NOTICES = /relaxed (budget|minimum rating)/i;

function MetaStrip(resp, health) {
  const meta = resp.filter_meta || {};
  const n = resp.recommendations.length;
  const parts = [
    [icon("filter_alt", "text-[16px]"), `${meta.candidate_count ?? 0} candidates`],
    [icon("arrow_forward", "text-[16px]"), `top ${n}`],
  ];
  if (resp.latency_ms != null) parts.push([icon("timer", "text-[16px]"), `${(resp.latency_ms / 1000).toFixed(1)}s`]);
  if (!resp.used_fallback && health?.model) parts.push([icon("memory", "text-[16px]"), health.model]);

  return h(
    "div",
    { class: "flex flex-wrap gap-2" },
    parts.map((content) =>
      h("span", { class: "inline-flex items-center gap-1 px-3 py-1 rounded-full bg-surface-container-high/70 border border-white/10 text-label-md text-on-surface-variant" }, ...content),
    ),
  );
}

function SummaryCard(resp) {
  const ai = !resp.used_fallback;
  const summary = decodeEntities(resp.summary);
  return h(
    "div",
    { class: "fade-in gradient-rim glass rounded-lg p-space-lg" },
    h(
      "p",
      { class: `flex items-center gap-1 text-label-sm uppercase tracking-widest mb-space-sm ${ai ? "text-tertiary-fixed" : "text-amber"}` },
      icon(ai ? "auto_awesome" : "trending_up", "icon-fill text-[16px]"),
      ai ? "The AI take" : "Crowd favourites",
    ),
    h("p", { class: "font-display text-headline-sm md:text-headline-md text-white leading-snug", text: summary || "Here's what we found." }),
  );
}

function noticeBanners(resp) {
  const meta = resp.filter_meta || {};
  const out = [];
  if (resp.used_fallback) {
    out.push(
      Banner({
        tone: "warn",
        iconName: "bolt",
        title: "AI took a breather",
        body: "These picks are ranked by rating and popularity instead. Try again in a moment for the full AI take.",
      }),
    );
  }
  const relaxed = [];
  if (meta.relaxed_budget) relaxed.push("budget");
  if (meta.relaxed_rating) relaxed.push("minimum rating");
  if (relaxed.length) {
    out.push(
      Banner({
        tone: "info",
        iconName: "tune",
        title: `We loosened your ${relaxed.join(" and ")}`,
        body: "Nothing matched exactly, so we widened the net a little.",
      }),
    );
  }
  for (const notice of meta.notices || []) {
    if (!HANDLED_NOTICES.test(notice)) out.push(Banner({ tone: "info", body: notice }));
  }
  return out;
}

export function ResultsView() {
  const el = h("section", { class: "space-y-space-lg", "aria-live": "polite", "aria-busy": "false" });

  function heading(title, sub) {
    return h(
      "div",
      { class: "flex items-end justify-between gap-space-md" },
      h(
        "div",
        {},
        h("h2", { class: "font-display text-headline-md text-white", text: title }),
        sub ? h("p", { class: "text-body-md text-on-surface-variant", text: sub }) : null,
      ),
    );
  }

  const grid = (children) => h("div", { class: "grid grid-cols-1 md:grid-cols-2 gap-space-lg" }, children);

  return {
    el,
    idle() {
      el.setAttribute("aria-busy", "false");
      clear(el).append(
        EmptyState({
          iconName: "restaurant_menu",
          title: "Your picks land here",
          body: "Choose a neighbourhood or a cuisine, set the vibe, and hit Find my spot.",
        }),
      );
    },
    loading(topN, useLlm) {
      el.setAttribute("aria-busy", "true");
      clear(el).append(
        heading(useLlm ? "Asking the AI…" : "Crunching the list…", useLlm ? "Filtering real listings, then ranking the best fits." : "Sorting by rating and popularity."),
        grid(Array.from({ length: Math.min(Math.max(topN, 2), 4) }, SkeletonCard)),
      );
    },
    error(message, onRetry) {
      el.setAttribute("aria-busy", "false");
      clear(el).append(
        EmptyState({
          iconName: "cloud_off",
          title: "Something broke on our side",
          body: message,
          action: h(
            "button",
            {
              type: "button",
              class: "mt-space-lg inline-flex items-center gap-1 px-5 py-2.5 rounded-full border border-primary/50 text-label-lg text-white hover:bg-primary-container hover:border-transparent transition-colors",
              onClick: onRetry,
            },
            icon("refresh", "text-[18px]"),
            "Try again",
          ),
        }),
      );
    },
    show(resp, health) {
      el.setAttribute("aria-busy", "false");
      const items = resp.recommendations || [];
      clear(el);

      if (!items.length) {
        el.append(
          ...noticeBanners({ ...resp, used_fallback: false }),
          EmptyState({
            iconName: "search_off",
            title: "No spots match that combo",
            body: "Try another neighbourhood, a broader cuisine, or widen your budget range.",
          }),
        );
        return;
      }

      const meta = resp.filter_meta || {};
      const sub = meta.limited_options ? `Only ${items.length} ${items.length === 1 ? "spot fits" : "spots fit"} everything you asked for.` : null;
      el.append(
        heading("Your picks", sub),
        MetaStrip(resp, health),
        ...noticeBanners(resp),
        SummaryCard(resp),
        grid(items.map((item, i) => RestaurantCard(item, i))),
      );
    },
  };
}
