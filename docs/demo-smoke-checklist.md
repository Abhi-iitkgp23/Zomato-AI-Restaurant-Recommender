# Demo-day smoke checklist

Use before presenting. Assumes `prepare_dataset.py` has been run and `.env` is configured.

## Preflight

- [ ] `source .venv/bin/activate`
- [ ] `pytest -q` is green
- [ ] `.env` has `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`, and a valid `LLM_API_KEY`
- [ ] `.env` is **not** staged for git (`git status` should ignore it)

## Happy paths

- [ ] **CLI + Groq:**  
  `python scripts/recommend_cli.py --location Banashankari --cuisine Italian --budget medium --min-rating 4.0 --top-n 3`  
  Expect grounded restaurants + AI explanations, `Fallback` line absent.
- [ ] **CLI fallback:**  
  `python scripts/recommend_cli.py --location Banashankari --cuisine Italian --no-llm`  
  Expect template explanations and fallback notice.
- [ ] **Streamlit:**  
  `streamlit run src/zomato_rec/app/streamlit_app.py`  
  Submit Banashankari / Italian / medium / 4.0 → cards with name, cuisine, rating, cost, explanation.
- [ ] **API (optional):**  
  `python scripts/run_api.py` then open `http://127.0.0.1:8000/health` → `"status":"ok"`.

## Edge paths (from edge-case.md)

- [ ] Impossible filter (obscure cuisine + tiny area + min 5.0) → empty or relaxed notice; **no invented venues**
- [ ] Limited matches → limited-options notice
- [ ] Free-text injection (“ignore previous instructions…”) → only candidate IDs returned
- [ ] Invalid/missing key → UI/CLI still returns popularity-based results with a clear notice

## Security quick check

- [ ] No API keys in chat logs, screenshots, or committed files
- [ ] Sidebar/API health may show provider/model but never the raw key
