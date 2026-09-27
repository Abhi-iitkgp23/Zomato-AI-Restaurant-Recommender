import { clear, h, icon, uid } from "../dom.js";

const MAX_OPTIONS = 60;

function FieldLabel(forId, text, extra) {
  return h(
    "div",
    { class: "flex items-center justify-between mb-space-sm" },
    h("label", { for: forId, class: "font-display text-label-lg uppercase tracking-widest text-on-surface-variant", text }),
    extra || null,
  );
}

/** Searchable combobox. Free text is allowed; options are suggestions. */
export function SearchSelect({ label, iconName, placeholder, options = [], format = (v) => v, onChange }) {
  const inputId = uid("combo");
  const listId = uid("list");
  let items = options;
  let visible = [];
  let active = -1;

  const input = h("input", {
    id: inputId,
    type: "text",
    autocomplete: "off",
    spellcheck: "false",
    placeholder,
    role: "combobox",
    "aria-expanded": "false",
    "aria-controls": listId,
    "aria-autocomplete": "list",
    class: "flex-1 min-w-0 bg-transparent border-none outline-none focus:ring-0 p-0 text-body-lg text-on-surface placeholder:text-on-surface-variant/50",
  });

  const clearBtn = h(
    "button",
    {
      type: "button",
      class: "hidden text-on-surface-variant hover:text-primary transition-colors",
      "aria-label": `Clear ${label}`,
      onClick: () => {
        setValue("");
        input.focus();
      },
    },
    icon("close", "text-[20px]"),
  );

  const list = h("ul", {
    id: listId,
    role: "listbox",
    class: "listbox hidden absolute left-0 right-0 top-full mt-2 z-30 glass rounded p-space-xs shadow-2xl shadow-black/50",
  });

  const box = h(
    "div",
    { class: "focus-glow flex items-center gap-space-sm bg-surface-container-highest/60 border border-white/10 rounded-full px-space-md py-3 transition-shadow" },
    icon(iconName, "text-secondary text-[20px]"),
    input,
    clearBtn,
  );

  const wrapper = h("div", { class: "relative" }, FieldLabel(inputId, label), box, list);

  function syncClear() {
    clearBtn.classList.toggle("hidden", !input.value);
  }

  function open() {
    render();
    list.classList.toggle("hidden", visible.length === 0);
    input.setAttribute("aria-expanded", String(visible.length > 0));
  }

  function close() {
    list.classList.add("hidden");
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    active = -1;
  }

  function render() {
    const q = input.value.trim().toLowerCase();
    const starts = [];
    const contains = [];
    for (const item of items) {
      const text = format(item).toLowerCase();
      if (!q || text.startsWith(q)) starts.push(item);
      else if (text.includes(q)) contains.push(item);
    }
    visible = starts.concat(contains).slice(0, MAX_OPTIONS);
    clear(list);
    visible.forEach((item, i) => {
      list.append(
        h(
          "li",
          {
            id: `${listId}-${i}`,
            role: "option",
            "aria-selected": String(i === active),
            class: `px-space-md py-2 rounded-full cursor-pointer text-body-md transition-colors ${
              i === active ? "bg-secondary-container text-white" : "text-on-surface hover:bg-white/5"
            }`,
            onMousedown: (e) => {
              e.preventDefault();
              choose(item);
            },
          },
          format(item),
        ),
      );
    });
    if (active >= 0) {
      input.setAttribute("aria-activedescendant", `${listId}-${active}`);
      list.children[active]?.scrollIntoView({ block: "nearest" });
    }
  }

  function choose(item) {
    input.value = format(item);
    syncClear();
    close();
    onChange?.(input.value);
  }

  function setValue(value) {
    input.value = value ? format(value) : "";
    syncClear();
    close();
    onChange?.(input.value);
  }

  input.addEventListener("input", () => {
    active = -1;
    syncClear();
    open();
    onChange?.(input.value);
  });
  input.addEventListener("focus", open);
  input.addEventListener("blur", () => setTimeout(close, 100));
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (list.classList.contains("hidden")) open();
      active = Math.min(active + 1, visible.length - 1);
      render();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      active = Math.max(active - 1, 0);
      render();
    } else if (e.key === "Enter" && active >= 0 && !list.classList.contains("hidden")) {
      e.preventDefault();
      choose(visible[active]);
    } else if (e.key === "Escape") {
      close();
    }
  });

  return {
    el: wrapper,
    getValue: () => input.value.trim(),
    setValue,
    setOptions(next) {
      items = next;
    },
    focus: () => input.focus(),
  };
}

export function ChipRow({ items, onPick, isActive = () => false }) {
  const row = h("div", { class: "flex flex-wrap gap-space-sm mt-space-sm" });
  function render() {
    clear(row);
    for (const item of items) {
      const on = isActive(item);
      row.append(
        h(
          "button",
          {
            type: "button",
            "aria-pressed": String(on),
            class: `px-3 py-1.5 rounded-full text-label-md border transition-all active:scale-95 ${
              on
                ? "bg-primary-container text-white border-transparent shadow-[0_0_14px_rgba(255,76,133,0.45)]"
                : "bg-surface-container-high/70 text-on-surface-variant border-white/10 hover:border-primary/50 hover:text-on-surface"
            }`,
            onClick: () => {
              onPick(item);
              render();
            },
          },
          item.label ?? item,
        ),
      );
    }
  }
  render();
  return {
    el: row,
    refresh: render,
    setItems(next) {
      items = next;
      render();
    },
  };
}

export function SegmentedToggle({ label, options, value, onChange }) {
  let current = value;
  const groupId = uid("seg");
  const hint = h("p", { class: "mt-space-sm text-body-sm text-on-surface-variant min-h-[16px]", "aria-live": "polite" });
  const track = h("div", {
    role: "radiogroup",
    "aria-labelledby": groupId,
    class: "grid gap-1 p-1 rounded-full bg-surface-container-lowest border border-white/10",
    style: { gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` },
  });

  function render() {
    clear(track);
    for (const opt of options) {
      const on = opt.value === current;
      track.append(
        h(
          "button",
          {
            type: "button",
            role: "radio",
            "aria-checked": String(on),
            title: opt.hint || "",
            class: `py-2 rounded-full font-display text-label-lg transition-all ${
              on
                ? "bg-gradient-to-r from-primary-container to-secondary-container text-white shadow-[0_0_16px_rgba(255,76,133,0.35)]"
                : "text-on-surface-variant hover:text-on-surface hover:bg-white/5"
            }`,
            onClick: () => {
              current = opt.value;
              render();
              onChange?.(current);
            },
          },
          opt.label,
        ),
      );
    }
    const selected = options.find((o) => o.value === current);
    hint.textContent = selected?.hint || "";
  }
  render();

  const el = h(
    "div",
    {},
    h("p", { id: groupId, class: "font-display text-label-lg uppercase tracking-widest text-on-surface-variant mb-space-sm", text: label }),
    track,
    hint,
  );
  return {
    el,
    getValue: () => current,
    setOptions(next) {
      options = next;
      render();
    },
  };
}

/**
 * Two-handle cost-for-two range with typed inputs and presets.
 * The ends of the track mean "no limit", so they map to null in getValue().
 */
export function BudgetRange({ label, max = 3000, step = 50, value = [0, 1000], presets = [] }) {
  let [low, high] = value;
  const labelId = uid("budget");
  const fmt = (n) => `₹${Math.round(n).toLocaleString("en-IN")}`;

  const summary = h("span", { class: "font-display text-label-lg text-tertiary-fixed", "aria-live": "polite" });
  const fill = h("div", { class: "absolute top-1/2 -translate-y-1/2 h-2 rounded-full bg-gradient-to-r from-primary-container to-tertiary shadow-[0_0_12px_rgba(255,76,133,0.4)]" });

  const rangeInput = (ariaLabel) =>
    h("input", { type: "range", min: "0", max: String(max), step: String(step), "aria-label": ariaLabel, class: "dual-thumb" });
  const lowRange = rangeInput("Minimum cost for two");
  const highRange = rangeInput("Maximum cost for two");

  const numberBox = (ariaLabel, placeholder) => {
    const input = h("input", {
      type: "number",
      inputmode: "numeric",
      min: "0",
      step: String(step),
      placeholder,
      "aria-label": ariaLabel,
      class: "w-full min-w-0 bg-transparent border-none outline-none focus:ring-0 p-0 text-body-lg text-on-surface placeholder:text-on-surface-variant/50 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none",
    });
    const box = h(
      "label",
      { class: "focus-glow flex-1 flex items-center gap-1 bg-surface-container-highest/60 border border-white/10 rounded-full px-space-md py-2.5 transition-shadow cursor-text" },
      h("span", { class: "text-on-surface-variant", text: "₹" }),
      input,
    );
    return { input, box };
  };
  const lowBox = numberBox("Minimum cost for two in rupees", "0");
  const highBox = numberBox("Maximum cost for two in rupees", "No limit");

  const presetRow = ChipRow({
    items: presets,
    isActive: (p) => p.range[0] === low && p.range[1] === high,
    onPick: (p) => set(p.range[0], p.range[1]),
  });

  function set(nextLow, nextHigh, source) {
    low = Math.max(0, Math.min(nextLow, max));
    high = Math.max(0, Math.min(nextHigh, max));
    if (low > high) {
      if (source === "high") low = high;
      else high = low;
    }
    render(source);
  }

  function render(source) {
    lowRange.value = String(low);
    highRange.value = String(high);
    // Keep the low thumb grabbable when both thumbs sit at the top end.
    lowRange.style.zIndex = low >= max - step ? "4" : "3";
    fill.style.left = `${(low / max) * 100}%`;
    fill.style.right = `${100 - (high / max) * 100}%`;
    if (source !== "lowText") lowBox.input.value = low > 0 ? String(low) : "";
    if (source !== "highText") highBox.input.value = high < max ? String(high) : "";

    const anyLow = low <= 0;
    const anyHigh = high >= max;
    summary.textContent =
      anyLow && anyHigh ? "Any budget" : anyLow ? `Up to ${fmt(high)}` : anyHigh ? `${fmt(low)}+` : `${fmt(low)} – ${fmt(high)}`;
    presetRow.refresh();
  }

  lowRange.addEventListener("input", () => set(Number(lowRange.value), high, "low"));
  highRange.addEventListener("input", () => set(low, Number(highRange.value), "high"));
  lowBox.input.addEventListener("input", () => {
    const v = lowBox.input.value === "" ? 0 : Number(lowBox.input.value);
    if (!Number.isNaN(v)) set(v, Math.max(v, high), "lowText");
  });
  highBox.input.addEventListener("input", () => {
    const v = highBox.input.value === "" ? max : Number(highBox.input.value);
    if (!Number.isNaN(v) && v >= low) set(low, v, "highText");
  });
  lowBox.input.addEventListener("change", () => render());
  highBox.input.addEventListener("change", () => {
    const v = highBox.input.value === "" ? max : Number(highBox.input.value);
    set(low, Number.isNaN(v) ? high : v, "high");
  });

  render();

  const el = h(
    "div",
    { role: "group", "aria-labelledby": labelId },
    h(
      "div",
      { class: "flex items-center justify-between mb-space-sm" },
      h("p", { id: labelId, class: "font-display text-label-lg uppercase tracking-widest text-on-surface-variant", text: label }),
      summary,
    ),
    h(
      "div",
      { class: "relative h-6 mx-1" },
      h("div", { class: "absolute top-1/2 -translate-y-1/2 left-0 right-0 h-2 rounded-full bg-surface-container-highest" }),
      fill,
      lowRange,
      highRange,
    ),
    h(
      "div",
      { class: "flex justify-between mt-1 text-body-sm text-on-surface-variant/70" },
      h("span", { text: "₹0" }),
      h("span", { text: `${fmt(max)}+` }),
    ),
    h(
      "div",
      { class: "flex items-center gap-space-sm mt-space-md" },
      lowBox.box,
      h("span", { class: "text-on-surface-variant", text: "to" }),
      highBox.box,
    ),
    h("p", { class: "mt-1 text-body-sm text-on-surface-variant/70", text: "Approx. cost for two people" }),
    presetRow.el,
  );

  return {
    el,
    getValue: () => ({
      budget_min: low > 0 ? low : null,
      budget_max: high < max ? high : null,
    }),
    setPresets(next) {
      presetRow.setItems(next);
      presetRow.refresh();
    },
  };
}

export function RatingSlider({ label, min = 0, max = 5, step = 0.5, value = 4 }) {
  const inputId = uid("range");
  const readout = h("span", { class: "flex items-center gap-1 font-display text-headline-sm text-tertiary-fixed" });
  const input = h("input", {
    id: inputId,
    type: "range",
    min: String(min),
    max: String(max),
    step: String(step),
    value: String(value),
    class: "range-lime w-full",
  });

  function sync() {
    const v = Number(input.value);
    input.style.setProperty("--fill", `${((v - min) / (max - min)) * 100}%`);
    input.setAttribute("aria-valuetext", `${v.toFixed(1)} stars and up`);
    readout.replaceChildren(icon("star", "icon-fill text-[20px]"), `${v.toFixed(1)}+`);
  }
  input.addEventListener("input", sync);
  sync();

  const el = h(
    "div",
    {},
    FieldLabel(inputId, label, readout),
    input,
    h(
      "div",
      { class: "flex justify-between mt-1 text-body-sm text-on-surface-variant/70" },
      h("span", { text: `${min.toFixed(1)}` }),
      h("span", { text: `${max.toFixed(1)}` }),
    ),
  );
  return { el, getValue: () => Number(input.value) };
}

export function Stepper({ label, min = 1, max = 20, value = 5 }) {
  let current = value;
  const out = h("output", { class: "w-10 text-center font-display text-headline-sm text-on-surface", "aria-live": "polite" });
  const btnClass =
    "h-10 w-10 grid place-items-center rounded-full bg-surface-container-high border border-white/10 text-on-surface hover:border-primary/60 hover:text-primary active:scale-90 transition-all disabled:opacity-30 disabled:pointer-events-none";
  const minus = h("button", { type: "button", class: btnClass, "aria-label": "Fewer results", onClick: () => set(current - 1) }, icon("remove"));
  const plus = h("button", { type: "button", class: btnClass, "aria-label": "More results", onClick: () => set(current + 1) }, icon("add"));

  function set(v) {
    current = Math.max(min, Math.min(max, v));
    out.textContent = String(current);
    minus.disabled = current <= min;
    plus.disabled = current >= max;
  }
  set(current);

  const el = h(
    "div",
    { class: "flex items-center justify-between" },
    h("span", { class: "font-display text-label-lg uppercase tracking-widest text-on-surface-variant", text: label }),
    h("div", { class: "flex items-center gap-space-sm", role: "group", "aria-label": label }, minus, out, plus),
  );
  return { el, getValue: () => current };
}

export function Switch({ label, description, checked = true }) {
  let on = checked;
  const knob = h("span", { class: "absolute top-1 h-5 w-5 rounded-full bg-white transition-all shadow" });
  const btn = h("button", { type: "button", role: "switch", class: "relative h-7 w-12 shrink-0 rounded-full transition-colors" }, knob);

  function render() {
    btn.setAttribute("aria-checked", String(on));
    btn.className = `relative h-7 w-12 shrink-0 rounded-full transition-colors ${
      on ? "bg-tertiary shadow-[0_0_14px_rgba(162,216,1,0.45)]" : "bg-surface-container-highest"
    }`;
    knob.style.left = on ? "1.5rem" : "0.25rem";
  }
  btn.addEventListener("click", () => {
    on = !on;
    render();
  });
  render();

  const labelId = uid("sw");
  btn.setAttribute("aria-labelledby", labelId);
  const el = h(
    "div",
    { class: "flex items-center justify-between gap-space-md" },
    h(
      "div",
      {},
      h("p", { id: labelId, class: "text-label-lg text-on-surface", text: label }),
      description ? h("p", { class: "text-body-sm text-on-surface-variant", text: description }) : null,
    ),
    btn,
  );
  return { el, getValue: () => on };
}

export function VibeInput({ label, max = 300, placeholder, chips = [] }) {
  const inputId = uid("vibe");
  const counter = h("span", { class: "text-body-sm text-on-surface-variant/70" });
  const textarea = h("textarea", {
    id: inputId,
    rows: 3,
    maxlength: String(max),
    placeholder,
    class: "w-full resize-none bg-transparent border-none outline-none focus:ring-0 p-0 text-body-lg text-on-surface placeholder:text-on-surface-variant/50",
  });

  const phrases = () =>
    textarea.value
      .split(",")
      .map((p) => p.trim().toLowerCase())
      .filter(Boolean);

  function sync() {
    counter.textContent = `${textarea.value.length}/${max}`;
    counter.classList.toggle("text-amber", textarea.value.length > max * 0.9);
  }

  const chipRow = ChipRow({
    items: chips,
    isActive: (chip) => phrases().includes(chip.toLowerCase()),
    onPick: (chip) => {
      const current = textarea.value
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean);
      const idx = current.findIndex((p) => p.toLowerCase() === chip.toLowerCase());
      if (idx >= 0) current.splice(idx, 1);
      else current.push(chip);
      textarea.value = current.join(", ").slice(0, max);
      sync();
    },
  });

  textarea.addEventListener("input", () => {
    sync();
    chipRow.refresh();
  });
  sync();

  const el = h(
    "div",
    {},
    FieldLabel(inputId, label, counter),
    h(
      "div",
      { class: "focus-glow bg-surface-container-highest/60 border border-white/10 rounded p-space-md transition-shadow" },
      textarea,
    ),
    chipRow.el,
  );
  return { el, getValue: () => textarea.value.trim() };
}
