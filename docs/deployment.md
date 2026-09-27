# Deployment Guide — Railway (backend) + Vercel (frontend)

This guide deploys the whole project:

| Part | What it is | Where it runs |
| --- | --- | --- |
| **Backend** | FastAPI app (`zomato_rec.app.api:app`) — `/health`, `/meta`, `/meta/locations`, `/meta/cuisines`, `POST /recommend`, `/docs` | **Railway** |
| **Frontend** | Crave web UI in `frontend/` (plain HTML + ES modules + Tailwind CDN, no build step) | **Vercel** |
| **LLM** | Groq (`openai/gpt-oss-120b`) via OpenAI-compatible API | Groq cloud (called only by the backend) |

## 1. Architecture

```text
 Browser ──► Vercel (crave.vercel.app)
               │  static files: index.html, js/, css/, assets/
               │
               │  rewrites (same-origin proxy)
               │  /health, /meta, /meta/*, /recommend, /docs, /openapi.json
               ▼
            Railway (your-app.up.railway.app)
               │  FastAPI + uvicorn
               │  data/processed/restaurants.parquet + metadata.json
               ▼
            Groq API (LLM_API_KEY lives only here)
```

Why this shape:

- The frontend calls relative paths (`/recommend`, `/health`, …) — see `frontend/js/api.js`. Vercel **rewrites** those paths to Railway, so the browser only ever talks to one origin. **No CORS setup and no frontend code changes are needed.**
- The Groq key is stored only in Railway. Vercel holds no secrets.
- Railway also serves the frontend at `/` (FastAPI mounts `frontend/`). That gives you a free fallback URL and a way to test the backend before Vercel is set up.

> **Simplest option:** if you don't need Vercel, deploy only Railway (sections 2–4) and use `https://<your-app>.up.railway.app/` as the app URL. Everything works from one service.

---

## 2. Prerequisites

- A GitHub account with the project pushed to a repository (both Railway and Vercel deploy from GitHub).
- A [Railway](https://railway.com) account and a [Vercel](https://vercel.com) account (both can sign in with GitHub).
- A Groq API key from [console.groq.com](https://console.groq.com).
- Local project working: `python scripts/run_api.py` → http://127.0.0.1:8000/ shows Crave and returns recommendations.

---

## 3. Prepare the repository (one-time)

The repo already contains everything below. This section explains each piece, so you know what to edit.

| File | Purpose |
| --- | --- |
| `.gitignore` | Allows `data/processed/restaurants.parquet` + `metadata.json` to be committed; raw data and `.env` stay ignored |
| `.python-version` | Pins Python 3.12 for Railway |
| `railway.json` | Railway start command (`0.0.0.0:$PORT`), health check, restart policy |
| `frontend/vercel.json` | Vercel rewrites to Railway (**edit the domain placeholder**) + security headers |
| `scripts/run_api.py` | Honors `HOST` / `PORT` env vars (defaults `127.0.0.1:8000` locally) |
| `tests/test_deploy_config.py` | Fails if a new API route lacks a Vercel rewrite, or Railway config drifts |

### 3.1 Ship the processed dataset

The API reads `data/processed/restaurants.parquet` (~2.8 MB) and `data/processed/metadata.json` (~5 KB). Without them the deployed API reports `data_ready: false` and `/recommend` returns 503.

`.gitignore` excludes everything in `data/processed/` **except** these two files, so they're committed like normal files (small, deterministic, fast deploys):

```bash
python scripts/prepare_dataset.py          # skip if data/processed/ already exists
git add data/processed/restaurants.parquet data/processed/metadata.json
```

**Alternative — build the data on Railway:** set the build command to `pip install -r requirements.txt && python scripts/prepare_dataset.py`. This downloads the full Hugging Face dataset on every build, so builds are slower and depend on Hugging Face being reachable. Only use this if you can't commit the Parquet file.

### 3.2 Pin the Python version

The project needs Python 3.11+. `.python-version` in the repo root contains:

```text
3.12
```

Railway's builders read this file.

### 3.3 Add the Railway config

`railway.json` in the repo root:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "deploy": {
    "startCommand": "uvicorn zomato_rec.app.api:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 120,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

Notes:

- Railway injects `PORT`; the app must bind `0.0.0.0`. (`HOST=0.0.0.0 python scripts/run_api.py` also works, since the script reads `HOST`/`PORT`.)
- `requirements.txt` already installs the package with the API extras (`-e ".[dev,api]"`), so Railway auto-detects a Python app and installs FastAPI + uvicorn.

### 3.4 Add the Vercel config

`frontend/vercel.json` ships with a `YOUR-APP.up.railway.app` placeholder. Replace it with your Railway domain once you have it (step 4.4 → step 5.1):

```json
{
  "rewrites": [
    { "source": "/health", "destination": "https://YOUR-APP.up.railway.app/health" },
    { "source": "/meta", "destination": "https://YOUR-APP.up.railway.app/meta" },
    { "source": "/meta/:path*", "destination": "https://YOUR-APP.up.railway.app/meta/:path*" },
    { "source": "/recommend", "destination": "https://YOUR-APP.up.railway.app/recommend" },
    { "source": "/docs", "destination": "https://YOUR-APP.up.railway.app/docs" },
    { "source": "/openapi.json", "destination": "https://YOUR-APP.up.railway.app/openapi.json" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

Static files (`index.html`, `js/…`, `css/…`, `assets/…`) are served by Vercel directly; only the API paths listed above are proxied.

### 3.5 Push to GitHub

This repo has no remote yet. Create an empty GitHub repo (no README), then:

```bash
git add .gitignore .python-version railway.json frontend/ docs/ scripts/ src/ tests/ README.md
git add data/processed/restaurants.parquet data/processed/metadata.json
git commit -m "Add Crave frontend and Railway/Vercel deployment config"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin master
```

Before pushing, double-check that secrets are not staged:

```bash
git status            # .env must NOT appear
git check-ignore .env # should print ".env"
```

> Optional: `stitch_ui/stitch_crave_ai_restaurant_finder.zip` is only design source material. You can leave it out of the repo to keep it small.

---

## 4. Deploy the backend on Railway

### 4.1 Create the service

1. Railway dashboard → **New Project** → **Deploy from GitHub repo** → pick your repo.
2. Railway detects Python (from `requirements.txt` / `pyproject.toml`) and uses `railway.json` for the start command and health check.

### 4.2 Set environment variables

Service → **Variables** → add:

| Variable | Value | Required |
| --- | --- | --- |
| `LLM_PROVIDER` | `groq` | yes |
| `LLM_API_KEY` | your Groq key (`gsk_…`) | yes (without it the app runs in heuristic fallback mode) |
| `LLM_MODEL` | `openai/gpt-oss-120b` | yes |
| `CANDIDATE_K` | `15` | no |
| `DEFAULT_TOP_N` | `5` | no |
| `BUDGET_LOW_MAX` | `400` | no |
| `BUDGET_MED_MAX` | `800` | no |
| `DATA_PATH` / `METADATA_PATH` | leave unset (defaults to `data/processed/…`) | no |

Never put the key in code, `railway.json`, or `vercel.json`.

### 4.3 Deploy

Railway builds and deploys automatically after the variables are saved (or click **Deploy**). Watch **Deployments → Logs**; a healthy start shows:

```text
Uvicorn running on http://0.0.0.0:<PORT>
Application startup complete.
```

### 4.4 Generate a public domain

Service → **Settings → Networking → Generate Domain**. You'll get something like `https://crave-api-production.up.railway.app`.

### 4.5 Verify the backend

```bash
export API=https://<your-app>.up.railway.app

curl -s $API/health
# expect: "status":"ok", "data_ready":true, "has_llm_credentials":true

curl -s $API/meta
# expect: row_count ≈ 12499, budget_low_max, budget_med_max

curl -s -X POST $API/recommend \
  -H 'Content-Type: application/json' \
  -d '{"location":"Indiranagar","cuisine":"Italian","budget_min":800,"budget_max":1500,"top_n":3}'
# expect: used_fallback:false, 3 recommendations with cost_for_two in range
```

Also open `$API/` in a browser — Railway serves the Crave UI too.

---

## 5. Deploy the frontend on Vercel

### 5.1 Point rewrites at Railway

Edit `frontend/vercel.json` and replace every `YOUR-APP.up.railway.app` with your real Railway domain from step 4.4. Commit and push.

### 5.2 Create the project

1. Vercel dashboard → **Add New… → Project** → import the same GitHub repo.
2. Configure:

| Setting | Value |
| --- | --- |
| **Root Directory** | `frontend` |
| **Framework Preset** | `Other` |
| **Build Command** | *(leave empty / override to empty)* |
| **Output Directory** | `.` *(default when no build)* |
| **Install Command** | *(leave empty)* |
| **Environment Variables** | none needed |

3. Click **Deploy**. You'll get a URL like `https://crave.vercel.app`.

### 5.3 Verify the frontend

1. Open the Vercel URL. The header badge should say **Groq live** and the hero should show the "12,499 Bangalore spots" line (that proves `/health` and `/meta` are proxied).
2. Pick **Indiranagar** + **Italian**, set a budget range, press **Find my spot** → cards appear with the AI summary.
3. DevTools → Network: requests go to `https://crave.vercel.app/recommend` (same origin) and return 200.

---

## 6. Alternative: call Railway directly (no Vercel rewrites)

Use this only if you prefer the browser to hit Railway directly (for example, to avoid proxying through Vercel).

1. **Frontend:** set the API base before `main.js` loads. In `frontend/index.html`, add above the module script:

   ```html
   <script>window.CRAVE_API_BASE = "https://<your-app>.up.railway.app";</script>
   ```

   `frontend/js/api.js` already prefixes every request with `window.CRAVE_API_BASE`.

2. **Backend:** enable CORS for your Vercel domain in `src/zomato_rec/app/api.py`:

   ```python
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://crave.vercel.app"],
       allow_methods=["GET", "POST"],
       allow_headers=["Content-Type"],
   )
   ```

   Keep `allow_origins` to your real domains — don't use `"*"` for a key-backed LLM endpoint.

3. Remove the `rewrites` block from `frontend/vercel.json`.

---

## 7. Custom domains (optional)

- **Vercel:** Project → Settings → Domains → add `crave.yourdomain.com`, then create the DNS record Vercel shows.
- **Railway:** Service → Settings → Networking → Custom Domain → add `api.yourdomain.com`, then create the CNAME it shows. Update `frontend/vercel.json` rewrites (or `CRAVE_API_BASE` / CORS origins) to the new API domain and redeploy.

---

## 8. Updating and rolling back

| Action | How |
| --- | --- |
| Deploy a change | `git push` to the connected branch — Railway and Vercel both redeploy automatically |
| Change an env var | Railway → Variables → edit → service redeploys |
| Rotate the Groq key | Create a new key in Groq → update `LLM_API_KEY` on Railway → revoke the old key |
| Refresh the dataset | Run `python scripts/prepare_dataset.py --force` locally → `git add data/processed/restaurants.parquet data/processed/metadata.json` → commit → push |
| Roll back | Railway: Deployments → pick a previous one → **Redeploy**. Vercel: Deployments → previous → **Promote to Production** |

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Railway health check fails / "Application failed to respond" | App bound to `127.0.0.1` or wrong port | Start command must be `uvicorn … --host 0.0.0.0 --port $PORT` |
| `/health` shows `data_ready: false`; `/recommend` returns 503 | Parquet/metadata not in the deployed image | Commit both `data/processed/` files (step 3.1) |
| Header badge says **Offline picks**; `used_fallback: true` | `LLM_API_KEY` missing/empty on Railway | Add the key in Railway Variables and redeploy |
| `used_fallback: true` with a key set | Groq error (bad key, model retired, rate limit) | Check Railway logs; verify `LLM_MODEL=openai/gpt-oss-120b` is still listed in Groq's models |
| Vercel page loads but badge says **API offline** | Rewrites not pointing at Railway | Fix the domain in `frontend/vercel.json`, push, redeploy |
| Vercel shows 404 for `/` | Root Directory not set | Vercel → Settings → General → Root Directory = `frontend` |
| Browser console shows CORS errors | Using direct mode (section 6) without CORS | Add `CORSMiddleware` with your Vercel origin, or switch back to rewrites |
| Build fails on Python version | Python < 3.11 selected | Ensure `.python-version` contains `3.12` |
| Slow first request after idle | Service woke from sleep / cold start | Expected on free tiers; keep the service always-on if needed |
| Pushes don't redeploy Railway; no Railway tick on GitHub commits; repo missing from Railway's repo picker | Railway GitHub App lacks access to the repo | [github.com/settings/installations](https://github.com/settings/installations) → Railway → Configure → grant the repo → Save. Only commits pushed afterwards get a Railway status |

---

## 10. Security and cost checklist

- [ ] `.env` is not in the repo (`git check-ignore .env` prints `.env`).
- [ ] `LLM_API_KEY` exists only in Railway Variables.
- [ ] Vercel has no secrets configured.
- [ ] If using direct mode, CORS `allow_origins` lists only your domains.
- [ ] `/recommend` is public and each call spends Groq tokens. Set usage limits in the Groq console, and consider adding rate limiting to the API before sharing the link widely.
- [ ] API responses HTML-escape free text and the frontend renders everything via `textContent`; keep it that way when editing components.

---

## 11. Post-deploy smoke test

Run through [`docs/demo-smoke-checklist.md`](demo-smoke-checklist.md) against the production URL, plus:

- [ ] `GET /health` → `status: ok`, `data_ready: true`, `has_llm_credentials: true`
- [ ] Vercel URL loads, badge shows **Groq live**
- [ ] Location + cuisine + budget range search returns AI-ranked cards
- [ ] Empty form shows the "Almost there" validation message
- [ ] Budget min > max is prevented in the UI; the API returns 422 if forced
- [ ] "AI ranking" switch off → instant popularity picks with the "Crowd favourites" label
- [ ] `/docs` opens the API docs (via the Vercel rewrite or the Railway URL)
