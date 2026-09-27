import { h, icon } from "../dom.js";

function statusFor(health) {
  if (!health) return { tone: "idle", text: "Connecting…" };
  if (health.unreachable) return { tone: "error", text: "API offline" };
  if (!health.data_ready) return { tone: "error", text: "Data not ready" };
  if (!health.has_llm_credentials) return { tone: "warn", text: "Offline picks" };
  const provider = health.provider ? health.provider[0].toUpperCase() + health.provider.slice(1) : "AI";
  return { tone: "ok", text: `${provider} live` };
}

const TONES = {
  idle: "bg-surface-container-high text-on-surface-variant border-white/10",
  ok: "bg-tertiary/10 text-tertiary-fixed border-tertiary/40",
  warn: "bg-amber/10 text-amber border-amber/40",
  error: "bg-error-container/40 text-error border-error/40",
};

const DOTS = {
  idle: "bg-on-surface-variant",
  ok: "bg-tertiary-fixed shadow-[0_0_8px_#bdf532] animate-pulse",
  warn: "bg-amber",
  error: "bg-error",
};

export function Header() {
  const badge = h("span", { class: "inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-label-md" });

  function setHealth(health) {
    const { tone, text } = statusFor(health);
    badge.className = `inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-label-md ${TONES[tone]}`;
    badge.title = health?.model ? `Model: ${health.model}` : "";
    badge.replaceChildren(h("span", { class: `h-2 w-2 rounded-full ${DOTS[tone]}` }), text);
  }
  setHealth(null);

  const el = h(
    "header",
    { class: "sticky top-0 z-40 glass border-x-0 border-t-0" },
    h(
      "div",
      { class: "max-w-7xl mx-auto flex items-center justify-between gap-space-md px-margin md:px-margin-desktop h-16" },
      h(
        "a",
        { href: "/", class: "flex items-center gap-space-sm group", "aria-label": "Crave home" },
        h("img", { src: "assets/logo.svg", alt: "", class: "h-9 w-9 group-hover:rotate-6 transition-transform" }),
        h("span", { class: "font-display text-headline-md font-bold tracking-tight text-white", text: "crave" }),
        icon("auto_awesome", "icon-fill text-primary-container text-[18px] -ml-1 -mt-3"),
      ),
      h(
        "div",
        { class: "flex items-center gap-space-sm" },
        h(
          "span",
          { class: "hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-surface-container-high/70 border border-white/10 text-label-md text-on-surface-variant" },
          icon("location_on", "text-[16px] text-primary"),
          "Bangalore",
        ),
        badge,
        h(
          "a",
          {
            href: "/docs",
            target: "_blank",
            rel: "noopener",
            class: "hidden md:inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-label-md text-on-surface-variant hover:text-on-surface hover:bg-white/5 transition-colors",
          },
          icon("code", "text-[16px]"),
          "API",
        ),
      ),
    ),
  );
  return { el, setHealth };
}

export function Hero() {
  const stats = h("p", { class: "mt-space-md text-body-lg text-on-surface-variant max-w-xl" });

  function setMeta(meta) {
    if (!meta?.row_count) {
      stats.textContent = "Tell us your craving, budget and mood. AI shortlists the spots worth your evening.";
      return;
    }
    stats.textContent = `Tell us your craving, budget and mood. AI digs through ${meta.row_count.toLocaleString("en-IN")} Bangalore spots and hands you the few worth your evening.`;
  }
  setMeta(null);

  const el = h(
    "section",
    { class: "pt-space-xl md:pt-16 pb-space-xl" },
    h(
      "span",
      { class: "inline-flex items-center gap-1 px-3 py-1 rounded-full bg-secondary-container/40 border border-secondary/30 text-label-sm uppercase tracking-widest text-secondary" },
      icon("bolt", "icon-fill text-[14px]"),
      "AI restaurant finder",
    ),
    h(
      "h1",
      { class: "mt-space-md font-display text-headline-xl-mobile md:text-headline-xl text-white max-w-3xl" },
      "Stop scrolling. ",
      h("span", { class: "bg-gradient-to-r from-primary-container via-secondary to-tertiary-fixed bg-clip-text text-transparent", text: "Start eating." }),
    ),
    stats,
  );
  return { el, setMeta };
}

export function Footer() {
  return h(
    "footer",
    { class: "mt-16 border-t border-white/5" },
    h(
      "div",
      { class: "max-w-7xl mx-auto px-margin md:px-margin-desktop py-space-xl flex flex-col sm:flex-row gap-space-sm justify-between text-body-sm text-on-surface-variant/70" },
      h("p", { text: "Crave · Built on the Zomato Bangalore dataset (Hugging Face)." }),
      h("p", { text: "Picks are grounded in real listings. AI never invents restaurants." }),
    ),
  );
}
