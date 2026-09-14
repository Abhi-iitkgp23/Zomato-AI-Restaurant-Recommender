# AI-Powered Restaurant Recommendation (Zomato-M7)

Hybrid **filter + LLM** restaurant recommendations over the Hugging Face
[`ManikaSaini/zomato-restaurant-recommendation`](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
dataset.

Docs: [`architecture.md`](docs/architecture.md) · [`implementation-plan.md`](docs/implementation-plan.md) ·
[`edge-case.md`](docs/edge-case.md) · [`eval.md`](docs/eval.md) ·
[`demo-smoke-checklist.md`](docs/demo-smoke-checklist.md)

## Requirements

- Python **3.11+** (3.12 recommended)
- A **Groq** API key (default), or run in heuristic-fallback mode without a key

## Setup

```bash
cd Zomato-M7
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set LLM_API_KEY to your Groq key (https://console.groq.com)
# Defaults: LLM_PROVIDER=groq, LLM_MODEL=openai/gpt-oss-120b
```

Verify:

```bash
python -c "from zomato_rec.config import get_settings; print(get_settings(validate=False))"
pytest -q
```

## Prepare data

```bash
python scripts/prepare_dataset.py          # download + cache (skips if cache exists)
python scripts/prepare_dataset.py --force  # rebuild
```

Writes gitignored `data/processed/restaurants.parquet` and `metadata.json`.

## Recommend CLI

```bash
python scripts/recommend_cli.py \
  --location Banashankari --cuisine Italian --budget medium --min-rating 4.0

# Force heuristic fallback (no LLM call)
python scripts/recommend_cli.py --location Koramangala --cuisine Chinese --no-llm
```

## Streamlit UI (Groq)

```bash
streamlit run src/zomato_rec/app/streamlit_app.py
```

Ensure `.env` has:

```bash
LLM_PROVIDER=groq
LLM_API_KEY=gsk_...
LLM_MODEL=openai/gpt-oss-120b
```

Without a key, the UI still returns popularity-based rankings with a clear notice.

## FastAPI (optional)

```bash
python scripts/run_api.py
# or: uvicorn zomato_rec.app.api:app --reload --port 8000
```

| Endpoint | Description |
| --- | --- |
| `GET /health` | Data + provider status |
| `GET /meta/locations` | Location dropdown values |
| `GET /meta/cuisines` | Cuisine vocabulary |
| `POST /recommend` | Preferences JSON → ranked recommendations |

Example:

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"location":"Banashankari","cuisine":"Italian","budget":"medium","min_rating":4.0,"top_n":3}'
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `LLM_PROVIDER` | `groq` (default) \| `openai` \| `gemini` \| `ollama` |
| `LLM_API_KEY` | Provider API key (never commit) |
| `LLM_MODEL` | e.g. `openai/gpt-oss-120b` |
| `DATA_PATH` | Processed Parquet path |
| `METADATA_PATH` | Metadata JSON path |
| `CANDIDATE_K` | Max candidates sent to the LLM (1–20) |
| `DEFAULT_TOP_N` | Recommendations shown |
| `BUDGET_LOW_MAX` / `BUDGET_MED_MAX` | Cost band thresholds |
| `HF_DATASET_ID` / `HF_DATASET_REVISION` | Hugging Face source pin |

## Security

- Keep secrets only in `.env` (gitignored). Use `.env.example` as the template.
- Never commit API keys or paste them into tickets/chat logs.
- Free-text preferences are truncated (300 chars). LLM output is treated as untrusted: JSON is schema-validated, unknown restaurant IDs are dropped, and API responses HTML-escape explanations.
- Logs record a preference hash, candidate counts, latency, and parse/fallback flags — not API keys or full prompts.

## Troubleshooting

| Symptom | What to try |
| --- | --- |
| `Processed data not found` | Run `python scripts/prepare_dataset.py` |
| UI/CLI always uses fallback | Confirm `.env` is **saved**, `LLM_API_KEY` is non-empty, provider is `groq` |
| `Unknown LLM_PROVIDER` | Use `groq`, `openai`, `gemini`, or `ollama` |
| Groq 4xx/model errors | Confirm `LLM_MODEL=openai/gpt-oss-120b` is still available on Groq |
| Import / package errors | Re-run `pip install -r requirements.txt` inside the 3.11+ venv |
| Empty results | Loosen budget or min rating; try a broader location/cuisine |

## Demo checklist

See [`docs/demo-smoke-checklist.md`](docs/demo-smoke-checklist.md).

## Project layout

```text
src/zomato_rec/     # package (data, filtering, llm, services, app)
data/processed/     # Parquet cache (generated, gitignored)
scripts/            # prepare_dataset, recommend_cli, run_api
tests/              # pytest
docs/               # architecture, plan, edge cases, eval, smoke checklist
```

## Status

**Phases 0–4 complete** — scaffold, data, recommend core, Streamlit + Groq UI, hardening + FastAPI.
