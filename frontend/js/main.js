import { api } from "./api.js";
import { h } from "./dom.js";
import { createStore } from "./state.js";
import { Banner } from "./components/feedback.js";
import { Footer, Header, Hero } from "./components/header.js";
import { PreferencesPanel } from "./components/preferences.js";
import { ResultsView } from "./components/results.js";

const store = createStore({ health: null, meta: null, lastPrefs: null });

const header = Header();
const hero = Hero();
const results = ResultsView();
const statusSlot = h("div", { class: "empty:hidden mb-space-lg" });
const panel = PreferencesPanel({ onSubmit: runRecommend });

let inflight = null;

async function runRecommend(prefs) {
  inflight?.abort();
  const controller = new AbortController();
  inflight = controller;
  store.set({ lastPrefs: prefs });

  panel.setLoading(true);
  results.loading(prefs.top_n, prefs.use_llm);
  if (window.matchMedia("(max-width: 1023px)").matches) {
    results.el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  try {
    const resp = await api.recommend(prefs, controller.signal);
    results.show(resp, store.get().health);
  } catch (err) {
    if (err.name === "AbortError") return;
    if (err.status === 422) {
      panel.setError(err.message);
      results.idle();
    } else {
      results.error(err.message, () => runRecommend(store.get().lastPrefs));
    }
  } finally {
    if (inflight === controller) {
      inflight = null;
      panel.setLoading(false);
    }
  }
}

function showStatus(health) {
  if (!health) {
    statusSlot.replaceChildren(
      Banner({ tone: "error", title: "API unreachable", body: "Start the server with: python scripts/run_api.py" }),
    );
  } else if (!health.data_ready) {
    statusSlot.replaceChildren(
      Banner({ tone: "error", title: "Dataset not prepared", body: "Run: python scripts/prepare_dataset.py, then refresh this page." }),
    );
  } else if (!health.has_llm_credentials) {
    statusSlot.replaceChildren(
      Banner({
        tone: "warn",
        title: "Running without AI",
        body: "No LLM key is configured, so picks are ranked by rating and popularity. Add LLM_API_KEY to .env to unlock the AI take.",
      }),
    );
  } else {
    statusSlot.replaceChildren();
  }
}

async function boot() {
  const root = document.getElementById("app");
  root.append(
    header.el,
    h(
      "main",
      { class: "max-w-7xl mx-auto px-margin md:px-margin-desktop" },
      hero.el,
      statusSlot,
      h(
        "div",
        { class: "grid grid-cols-1 lg:grid-cols-12 gap-space-xl items-start" },
        h("aside", { class: "lg:col-span-5 xl:col-span-4 lg:sticky lg:top-24" }, panel.el),
        h("div", { class: "lg:col-span-7 xl:col-span-8 min-w-0" }, results.el),
      ),
    ),
    Footer(),
  );
  results.idle();

  const health = await api.health().catch(() => null);
  store.set({ health });
  header.setHealth(health ?? { unreachable: true });
  showStatus(health);
  if (!health?.data_ready) return;

  const [locations, cuisines, meta] = await Promise.all([
    api.locations().catch(() => []),
    api.cuisines().catch(() => []),
    api.meta().catch(() => null),
  ]);
  store.set({ meta });
  hero.setMeta(meta);
  panel.setData({ locations, cuisines, meta });
}

boot();
