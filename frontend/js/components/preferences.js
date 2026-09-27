import { h, icon, titleCase } from "../dom.js";
import { BudgetRange, ChipRow, RatingSlider, SearchSelect, Stepper, Switch, VibeInput } from "./controls.js";
import { Banner } from "./feedback.js";

const HOT_LOCATIONS = ["Indiranagar", "Koramangala 5th Block", "HSR", "BTM", "Whitefield", "Jayanagar"];
const HOT_CUISINES = ["north indian", "chinese", "south indian", "italian", "cafe", "biryani", "desserts"];
const VIBES = ["Quick bite", "Cafe vibes", "Date night", "Family-friendly", "Fine dining", "Craft beer", "Desserts"];
const BUDGET_MAX = 3000;

function budgetPresets(lowMax = 400, medMax = 800) {
  const inr = (n) => `₹${n.toLocaleString("en-IN")}`;
  return [
    { label: "Any", range: [0, BUDGET_MAX] },
    { label: `Under ${inr(lowMax)}`, range: [0, lowMax] },
    { label: `${inr(lowMax)} – ${inr(medMax)}`, range: [lowMax, medMax] },
    { label: `${inr(medMax)} – ${inr(1500)}`, range: [medMax, 1500] },
    { label: `${inr(1500)}+`, range: [1500, BUDGET_MAX] },
  ];
}

function Section(...children) {
  return h("div", { class: "space-y-space-sm" }, ...children);
}

export function PreferencesPanel({ onSubmit }) {
  const location = SearchSelect({
    label: "Where",
    iconName: "location_on",
    placeholder: "Search a neighbourhood…",
    onChange: () => {
      locationChips.refresh();
      clearError();
    },
  });
  const locationChips = ChipRow({
    items: [],
    isActive: (v) => location.getValue().toLowerCase() === v.toLowerCase(),
    onPick: (v) => location.setValue(location.getValue().toLowerCase() === v.toLowerCase() ? "" : v),
  });
  const cuisineMatches = (chip) => cuisine.getValue().toLowerCase() === chip.value;

  const cuisine = SearchSelect({
    label: "Craving",
    iconName: "restaurant",
    placeholder: "Search a cuisine…",
    format: titleCase,
    onChange: () => {
      cuisineChips.refresh();
      clearError();
    },
  });
  const cuisineChips = ChipRow({
    items: [],
    isActive: cuisineMatches,
    onPick: (chip) => cuisine.setValue(cuisineMatches(chip) ? "" : chip.value),
  });

  const budget = BudgetRange({
    label: "Budget",
    max: BUDGET_MAX,
    step: 50,
    value: [0, 1000],
    presets: budgetPresets(),
  });
  const rating = RatingSlider({ label: "Min rating", min: 3, max: 5, step: 0.1, value: 4 });
  const topN = Stepper({ label: "How many picks", min: 1, max: 20, value: 5 });
  const vibe = VibeInput({
    label: "The vibe",
    max: 300,
    placeholder: "rooftop, chill music, good for a group of 6…",
    chips: VIBES,
  });
  const useLlm = Switch({ label: "AI ranking", description: "Turn off for instant popularity picks", checked: true });

  const errorSlot = h("div", { class: "empty:hidden" });
  function clearError() {
    errorSlot.replaceChildren();
  }

  const labelSpan = h("span", { text: "Find my spot" });
  const btnIcon = icon("auto_awesome", "icon-fill text-[22px]");
  const submitBtn = h(
    "button",
    {
      type: "submit",
      class:
        "w-full h-14 rounded-full flex items-center justify-center gap-space-sm font-display text-headline-sm text-white bg-gradient-to-r from-primary-container to-secondary-container shadow-[0_0_24px_rgba(255,76,133,0.45)] hover:shadow-[0_0_36px_rgba(255,76,133,0.65)] hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-60 disabled:cursor-wait",
    },
    btnIcon,
    labelSpan,
  );

  const form = h(
    "form",
    {
      class: "gradient-rim glass rounded-lg p-space-lg md:p-space-xl space-y-space-lg",
      novalidate: true,
      "aria-label": "Your preferences",
      onSubmit: (e) => {
        e.preventDefault();
        const prefs = {
          location: location.getValue() || null,
          cuisine: cuisine.getValue() || null,
          ...budget.getValue(),
          min_rating: rating.getValue(),
          additional_preferences: vibe.getValue() || null,
          top_n: topN.getValue(),
          use_llm: useLlm.getValue(),
        };
        if (!prefs.location && !prefs.cuisine) {
          setError("Pick a neighbourhood or a cuisine so we know where to start.");
          location.focus();
          return;
        }
        clearError();
        onSubmit(prefs);
      },
    },
    h(
      "div",
      { class: "flex items-center gap-space-sm" },
      icon("tune", "text-primary"),
      h("h2", { class: "font-display text-headline-md text-white", text: "Your cravings" }),
    ),
    Section(location.el, locationChips.el),
    Section(cuisine.el, cuisineChips.el),
    budget.el,
    rating.el,
    vibe.el,
    h("div", { class: "space-y-space-md pt-space-sm border-t border-white/5" }, topN.el, useLlm.el),
    errorSlot,
    submitBtn,
  );

  function setError(message) {
    errorSlot.replaceChildren(Banner({ tone: "error", title: "Almost there", body: message }));
  }

  return {
    el: form,
    setData({ locations = [], cuisines = [], meta }) {
      location.setOptions(locations);
      cuisine.setOptions(cuisines);
      const locSet = new Set(locations.map((l) => l.toLowerCase()));
      const cuiSet = new Set(cuisines);
      locationChips.setItems(HOT_LOCATIONS.filter((l) => locSet.has(l.toLowerCase())));
      cuisineChips.setItems(
        HOT_CUISINES.filter((c) => cuiSet.has(c)).map((c) => ({ label: titleCase(c), value: c })),
      );
      if (meta?.budget_low_max && meta?.budget_med_max) {
        budget.setPresets(budgetPresets(meta.budget_low_max, meta.budget_med_max));
      }
    },
    setLoading(loading) {
      submitBtn.disabled = loading;
      labelSpan.textContent = loading ? "Finding your spot…" : "Find my spot";
      btnIcon.classList.toggle("animate-spin", loading);
      btnIcon.textContent = loading ? "progress_activity" : "auto_awesome";
    },
    setError,
  };
}
