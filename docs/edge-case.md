# Edge Cases & Corner Scenarios

Catalog of edge cases and corner scenarios for the AI-powered restaurant recommendation system, aligned with [`implementation-plan.md`](./implementation-plan.md) and [`architecture.md`](./architecture.md).

Use this list for unit tests, manual QA, and demo-day smoke checks. Each case includes **expected behavior** so implementers and testers share the same contract.

**Severity legend**

| Tag | Meaning |
| --- | --- |
| `P0` | Must handle for MVP correctness / safety |
| `P1` | Should handle for polished demo |
| `P2` | Nice-to-have / post-MVP |

---

## 1. Project Scaffold & Configuration (Phase 0)

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| CFG-01 | `.env` missing entirely | App starts; LLM path uses heuristic fallback; clear warning in logs/UI | `P0` |
| CFG-02 | `LLM_API_KEY` empty or whitespace | Same as CFG-01; do not call provider | `P0` |
| CFG-03 | `LLM_API_KEY` invalid / revoked | Provider error → retry once → fallback rankings + notice | `P0` |
| CFG-04 | Unknown `LLM_PROVIDER` value | Fail fast at startup/config load with a clear error, or default to fallback mode | `P0` |
| CFG-05 | `DATA_PATH` points to missing file | Fail with actionable message: run `prepare_dataset.py` | `P0` |
| CFG-06 | `CANDIDATE_K` = 0 or negative | Clamp to a safe minimum (e.g. 1) or reject via config validation | `P1` |
| CFG-07 | `CANDIDATE_K` > 20 (or very large) | Cap at configured max (≤ 20) to protect cost/latency | `P1` |
| CFG-08 | `DEFAULT_TOP_N` > `CANDIDATE_K` | Return at most available candidates; do not invent rows | `P0` |
| CFG-09 | Budget threshold env vars inverted (`LOW_MAX` > `MED_MAX`) | Validate at load; refuse or correct with warning | `P1` |
| CFG-10 | Secrets accidentally printed in debug logs | Never log API keys or full prompts containing keys | `P0` |
| CFG-11 | Python &lt; 3.11 | Document unsupported; install may fail — README states 3.11+ | `P2` |
| CFG-12 | `data/processed/` empty but gitignored | Repo clones cleanly; docs tell user to generate Parquet | `P1` |

---

## 2. Data Ingestion & Parsing (Phase 1)

### 2.1 Rating parser

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| RATE-01 | `rate` = `"4.1/5"` | Parse to `4.1` | `P0` |
| RATE-02 | `rate` = `"NEW"` | `rating` = null / NaN; restaurant excluded when `min_rating` applied (unless rating filter relaxed) | `P0` |
| RATE-03 | `rate` = `"-"` | Same as RATE-02 | `P0` |
| RATE-04 | `rate` missing / null | Same as RATE-02 | `P0` |
| RATE-05 | `rate` = `"0/5"` or unexpectedly low | Keep numeric value; let filters decide | `P1` |
| RATE-06 | Malformed string e.g. `"4.1"` without `/5`, or `"Good"` | Best-effort parse or null; never crash ingest | `P0` |
| RATE-07 | Extra whitespace / mixed case | Strip and parse robustly | `P1` |

### 2.2 Cost parser & budget banding

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| COST-01 | `"1,200"` (comma thousands) | `cost_for_two` = 1200 → `budget_band` = `high` | `P0` |
| COST-02 | Missing / null cost | `cost_for_two` null; exclude from budget_band filter or treat as unknown (document choice) | `P0` |
| COST-03 | Cost = `0` or negative | Treat as invalid/null; do not assign a misleading band | `P1` |
| COST-04 | Exact boundary `400` | `low` (≤ 400) | `P0` |
| COST-05 | Exact boundary `401` | `medium` | `P0` |
| COST-06 | Exact boundary `800` | `medium` (401–800) | `P0` |
| COST-07 | Exact boundary `801` | `high` | `P0` |
| COST-08 | Cost as float string `"600.0"` | Parse to 600 → `medium` | `P1` |
| COST-09 | Non-numeric junk in cost field | null; ingest continues | `P0` |

### 2.3 Cuisines, locations, dedup

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| CUI-01 | Empty / null `cuisines` | Keep row; cuisine filter will not match unless relaxed | `P0` |
| CUI-02 | Multi-cuisine `"Pizza, Cafe, Italian"` | Searchable; substring match works for any listed cuisine | `P0` |
| CUI-03 | Inconsistent casing `"italian"` vs `"Italian"` | Normalize to lowercase for matching/vocab | `P0` |
| CUI-04 | Extra spaces `"Pizza,  Cafe"` | Normalize whitespace | `P1` |
| LOC-01 | Location casing / typo variants | Case-insensitive match; exact dropdown values preferred in UI | `P0` |
| LOC-02 | Same name, different addresses | Treat as distinct rows after dedup key | `P0` |
| LOC-03 | Duplicate `name` + `address` | Collapse to one row during ingest | `P0` |
| LOC-04 | `location` vs `listed_in(city)` mismatch | Prefer documented filter field (`location`); metadata may expose both | `P1` |
| DEDUP-01 | Near-duplicates (same name, slightly different address) | MVP: keep both; optional fuzzy dedup later | `P2` |

### 2.4 Dataset / cache lifecycle

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| DATA-01 | First run, no Parquet, HF download succeeds | Write Parquet + `metadata.json` | `P0` |
| DATA-02 | Parquet already exists | Skip HF download; load cache | `P0` |
| DATA-03 | HF unreachable / network error, no cache | Fail with clear error; do not hang forever | `P0` |
| DATA-04 | HF unreachable, cache exists | Use cache; optional warning that data may be stale | `P0` |
| DATA-05 | Corrupt / unreadable Parquet | Fail loudly; suggest re-running prepare script | `P0` |
| DATA-06 | Schema drift (old Parquet missing new columns) | Detect via metadata/schema version; prompt re-ingest | `P1` |
| DATA-07 | Empty dataset after cleaning (all rows dropped) | Fail ingest; do not write empty “success” cache silently | `P0` |
| DATA-08 | Extremely large `reviews_list` / `menu_item` | Excluded from MVP Parquet/prompts by design | `P0` |
| DATA-09 | Disk full while writing Parquet | Surface IO error; leave previous good cache intact if possible | `P1` |
| DATA-10 | Metadata with empty location/cuisine lists | Treat as ingest bug; UI cannot offer meaningful dropdowns | `P0` |

---

## 3. User Preferences & Validation (Phase 2.1 / Phase 3)

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| PREF-01 | Both location and cuisine empty | Validation error: require at least one | `P0` |
| PREF-02 | Only location set | Valid; filter on location (+ other set fields) | `P0` |
| PREF-03 | Only cuisine set | Valid; filter on cuisine across areas | `P0` |
| PREF-04 | All fields filled | Happy path | `P0` |
| PREF-05 | `min_rating` &lt; 0 or &gt; 5 | Reject or clamp to slider range (3.0–5.0 in UI) | `P0` |
| PREF-06 | `min_rating` = 5.0 (very strict) | May yield few/zero matches → relaxation path | `P0` |
| PREF-07 | `budget` not in `{low, medium, high}` | Validation error | `P0` |
| PREF-08 | `top_n` = 0 or negative | Reject or clamp to ≥ 1 | `P0` |
| PREF-09 | `top_n` very large (e.g. 1000) | Cap to `CANDIDATE_K` / available candidates | `P0` |
| PREF-10 | `additional_preferences` empty | Allowed; skip soft heuristics / still rank | `P0` |
| PREF-11 | `additional_preferences` &gt; 300 chars | Truncate before prompt; optional UI hint | `P0` |
| PREF-12 | Location not in metadata vocabulary (free-typed) | Case-insensitive contains; may return 0 → relax/empty | `P1` |
| PREF-13 | Cuisine not in vocabulary | Substring miss → 0 matches → relax/empty | `P1` |
| PREF-14 | Multi-select cuisines (if enabled) | Match if restaurant has **any** selected cuisine (document OR vs AND) | `P1` |
| PREF-15 | Conflicting prefs (e.g. “fine dining” + budget `low`) | Still run pipeline; LLM/explanation may note tension | `P1` |
| PREF-16 | Unicode / emoji / non-English free text | Accept; truncate; do not crash encoding | `P1` |
| PREF-17 | Prompt injection in free text (“ignore instructions…”) | Truncation + system prompt; never execute user text as system rules | `P0` |
| PREF-18 | Whitespace-only location/cuisine | Treat as empty → PREF-01 if both blank | `P0` |

---

## 4. Filter Layer (Phase 2.2)

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| FIL-01 | Exact match yields many rows (&gt; K) | Sort by rating then votes; take top K | `P0` |
| FIL-02 | Exact match yields 0 rows | Relax budget first, then rating; set `relaxed` flag | `P0` |
| FIL-03 | Still 0 after full relaxation | Return empty result + clear UI/CLI message | `P0` |
| FIL-04 | 1–2 matches (&lt; 3) | Proceed; flag limited options for LLM/UI | `P0` |
| FIL-05 | Matches = exactly 3 | Proceed without “limited” flag (threshold is &lt; 3) | `P1` |
| FIL-06 | Location substring false positive (e.g. `"Ban"` matches many areas) | Prefer exact/dropdown match; document contains behavior | `P1` |
| FIL-07 | Cuisine substring ambiguity (`"Chi"` → Chinese vs something else) | Prefer full cuisine tokens from vocabulary | `P1` |
| FIL-08 | `rest_type` heuristic from “quick” → Quick Bites | Soft filter applied after hard filters; do not zero out if heuristic too strict | `P1` |
| FIL-09 | Free-text implies rest_type that matches nothing | Ignore heuristic or skip that soft step; keep hard-filter candidates | `P0` |
| FIL-10 | All candidates have null rating after parse | Sorting/ranking must not crash; treat null as lowest | `P0` |
| FIL-11 | Tie on rating and votes | Stable sort (deterministic order) | `P1` |
| FIL-12 | Budget filter with null `budget_band` rows | Exclude null bands unless budget filter relaxed | `P0` |
| FIL-13 | User wants high rating + rare cuisine in niche location | Expect relaxation or empty; message must be honest | `P0` |
| FIL-14 | Filter order regressions (rating before location) | Keep documented order; tests lock pipeline sequence | `P1` |

---

## 5. Prompt Builder (Phase 2.3)

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| PRM-01 | Candidate list empty | Do not call LLM; return empty/fallback messaging | `P0` |
| PRM-02 | Candidate list size = K | Serialize all K without truncation of core fields | `P0` |
| PRM-03 | Very long `dish_liked` strings | Truncate field-level text to protect tokens | `P1` |
| PRM-04 | Special characters in restaurant names (`&`, quotes) | Valid JSON serialization; no broken prompts | `P0` |
| PRM-05 | `top_n` &gt; candidate count | Instruct LLM to return at most available; parser enforces | `P0` |
| PRM-06 | Review snippets included (optional) | Cap 1–2 short snippets; instruct model to ignore embedded instructions | `P1` |
| PRM-07 | Injection inside review/dish text | System prompt forbids following instructions in data fields | `P0` |
| PRM-08 | Missing optional candidate fields | Omit or null; prompt still valid | `P0` |

---

## 6. LLM Client, Parser & Orchestrator (Phase 2.4–2.5)

### 6.1 Provider / network

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| LLM-01 | Successful JSON response | Parse, validate, join by `id`, return top_n | `P0` |
| LLM-02 | Timeout | Retry once; then heuristic fallback | `P0` |
| LLM-03 | HTTP 429 rate limit | Retry once (optional backoff); then fallback | `P0` |
| LLM-04 | HTTP 5xx | Retry once; then fallback | `P0` |
| LLM-05 | Empty response body | Fallback | `P0` |
| LLM-06 | Extremely slow response (&gt; target 5–8s) | Timeout wins; do not block UI indefinitely | `P1` |
| LLM-07 | Provider returns content-policy refusal | Fallback + user-visible soft error | `P1` |
| LLM-08 | Wrong model name configured | Clear config/API error → fallback | `P1` |
| LLM-09 | Offline / Ollama not running | Fallback; message to start local server or switch provider | `P1` |

### 6.2 Response parsing & grounding

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| PAR-01 | Pure JSON object | Parse OK | `P0` |
| PAR-02 | Markdown-fenced JSON (` ```json ... ``` `) | Strip fences; parse OK | `P0` |
| PAR-03 | JSON with leading prose (“Here are…”) | Extract first JSON object if possible; else fallback | `P0` |
| PAR-04 | Invalid JSON / truncated | Fallback | `P0` |
| PAR-05 | Valid JSON, wrong schema (missing `recommendations`) | Validation fail → fallback | `P0` |
| PAR-06 | Hallucinated `id` not in candidates | Drop that item | `P0` |
| PAR-07 | Hallucinated `name` but valid `id` | Prefer dataset name for display; keep explanation if grounded by id | `P0` |
| PAR-08 | Duplicate `id`s in LLM list | Keep highest rank / first; dedupe | `P1` |
| PAR-09 | Fewer items than `top_n` | Return what is valid; optionally pad via heuristic | `P0` |
| PAR-10 | More items than `top_n` | Truncate to `top_n` after sort by `rank` | `P0` |
| PAR-11 | Missing `rank` field | Infer order from array index | `P1` |
| PAR-12 | Missing / empty `explanation` | Use template explanation for that row | `P0` |
| PAR-13 | Missing `summary` | Generate short template summary or omit gracefully | `P1` |
| PAR-14 | `rank` ties or non-monotonic ranks | Sort stably; re-number for display | `P1` |
| PAR-15 | Non-integer `id` / type coercion | Coerce or drop; never crash | `P0` |
| PAR-16 | Extra unknown fields in JSON | Ignore extras; accept known fields | `P1` |
| PAR-17 | Nested/array root instead of object | Reject → fallback | `P0` |
| PAR-18 | Explanations invent costs/ratings not in data | Display **dataset** cost/rating on cards; explanation is advisory | `P0` |

### 6.3 Fallback ranking

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| FB-01 | No API key | Heuristic rank `(rating, votes)` + template text | `P0` |
| FB-02 | Parse failure after successful HTTP | Same as FB-01; flag `used_fallback` | `P0` |
| FB-03 | Candidates empty | Empty list; no fake restaurants | `P0` |
| FB-04 | All ratings null | Sort by votes only (or stable id); templates still render | `P0` |
| FB-05 | Template with missing cuisine/location | Use “N/A” / omit fragment; no crash | `P0` |

---

## 7. Streamlit UI (Phase 3)

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| UI-01 | First page load, no submit yet | Empty results area; no error | `P0` |
| UI-02 | Submit with valid prefs | Spinner → cards + summary | `P0` |
| UI-03 | Submit while previous request in flight | Avoid double-submit chaos (disable button or ignore second click) | `P1` |
| UI-04 | 0 results after relaxation | Friendly empty state; suggest loosening prefs | `P0` |
| UI-05 | Relaxed filters used | Banner/notice: which constraint was relaxed | `P0` |
| UI-06 | Limited candidates (&lt; 3) | Notice that options are limited | `P1` |
| UI-07 | LLM failed but fallback returned | Show results + “AI ranking unavailable; showing popularity-based results” | `P0` |
| UI-08 | Metadata load failure | Error page/message; do not show broken empty dropdowns silently | `P0` |
| UI-09 | Very long restaurant name / explanation | Wrap text; layout does not overflow badly | `P1` |
| UI-10 | Missing optional fields (address, url) | Hide extras; core fields still shown | `P0` |
| UI-11 | Rapid preference changes between submits | Results match **last submitted** prefs | `P1` |
| UI-12 | Browser refresh mid-request | Clean reload; no partial corrupt session state | `P1` |
| UI-13 | Dropdown lists huge (thousands of locations) | Still usable (searchable select if needed) | `P2` |
| UI-14 | Slider `min_rating` at extremes | Behaves per PREF-05/06 | `P0` |
| UI-15 | `top_n` input cleared / non-numeric | Streamlit/validation prevents invalid submit | `P0` |

---

## 8. Hardening, Security & Ops (Phase 4)

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| SEC-01 | API key in git / committed `.env` | Prevent via `.gitignore`; README warns | `P0` |
| SEC-02 | Log line includes full prompt + key header | Forbidden; redact secrets | `P0` |
| SEC-03 | XSS-like explanation string (`<script>…`) | Streamlit escapes by default; if custom HTML, escape explicitly | `P0` |
| SEC-04 | Preference hash logging | Hash only; do not store raw free-text in verbose prod logs if sensitive | `P2` |
| OBS-01 | Measure latency on success and fallback | Logged; useful for demo debugging | `P1` |
| OBS-02 | Parse success rate tracking | Boolean/metric per request | `P1` |
| API-01 | (Optional FastAPI) Invalid JSON body | 422 with validation errors | `P1` |
| API-02 | (Optional) `/recommend` with empty candidates | 200 + empty list + message, or 404-style domain response — document one | `P1` |
| API-03 | (Optional) `/health` when Parquet missing | Unhealthy / degraded status | `P1` |
| PROV-01 | Switch provider mid-deploy without code change | `LLM_PROVIDER` + model env swap works | `P2` |

---

## 9. Cross-Cutting Product Corner Cases

| ID | Scenario | Expected behavior | Sev |
| --- | --- | --- | --- |
| X-01 | User expects Delhi restaurants; dataset is Bangalore-centric | Honest empty/near-empty; do not invent out-of-dataset cities | `P0` |
| X-02 | Same restaurant listed under multiple cuisine tags | May appear once after dedup; cuisine string still multi-value | `P1` |
| X-03 | Popular restaurant with low rating (or vice versa) | Ranking uses rating then votes; LLM may override order within candidates only | `P1` |
| X-04 | Cost shown ≠ user’s mental “budget” (for two vs per person) | Label clearly as approx cost for two | `P1` |
| X-05 | Online order / book table = unexpected values | Display raw or normalize Yes/No; do not crash | `P1` |
| X-06 | Concurrent users on Streamlit | Acceptable MVP contention; no shared mutable global corruption | `P1` |
| X-07 | Reproducibility: same prefs twice | Same candidate set; LLM ranks may vary slightly unless temperature 0 | `P2` |

---

## 10. Recommended Test Mapping

| Area | Priority test cases (IDs) |
| --- | --- |
| Ingestion parsers | RATE-02, RATE-03, RATE-06, COST-01, COST-04–07, CUI-03 |
| Filters | FIL-01, FIL-02, FIL-03, FIL-04, FIL-09, FIL-10 |
| Preferences | PREF-01, PREF-08, PREF-09, PREF-11, PREF-17, PREF-18 |
| Parser / grounding | PAR-02, PAR-03, PAR-06, PAR-07, PAR-09, PAR-12, PAR-18 |
| Fallback | LLM-02, FB-01, FB-02, FB-03 |
| UI smoke | UI-04, UI-05, UI-07, UI-08 |
| Config / safety | CFG-01, CFG-05, SEC-01, SEC-03 |

---

## 11. Demo-Day Checklist (Edge Paths)

Run these before presenting:

1. **Happy path** — Banashankari + medium + Italian + min 4.0 → cards with explanations  
2. **No API key** — confirm fallback templates still look acceptable  
3. **Impossible filter** — obscure cuisine + tiny area + min 5.0 → empty or relaxed notice  
4. **Limited matches** — prefs that yield 1–2 restaurants → limited-options notice  
5. **Injection free-text** — short “ignore previous instructions” string → still grounded IDs only  
6. **Missing Parquet** — rename cache temporarily → clear “run prepare_dataset” message  

---

## Traceability

| Implementation phase | Edge-case sections |
| --- | --- |
| Phase 0 | §1 |
| Phase 1 | §2 |
| Phase 2 | §3–§6 |
| Phase 3 | §7 |
| Phase 4 | §8 |
| All phases | §9–§11 |
