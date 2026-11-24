# Resume Studio API
**The Django REST Framework backend for Resume Studio. It reads a resume file and asks Gemini for honest, job-specific rewrites of lines the resume already has. It never invents experience.**

🔗 **[Live API docs (Swagger)](https://resume-studio-api-vfuy.onrender.com/api/docs/)** (hosted on Render's free tier; the first request can take about a minute while the server wakes up)
🔗 **[Live Demo](https://abdulkarimmziya.github.io/resume-studio-web/)** (the React frontend, calling this API)
📄 **[Frontend (React + TypeScript)](https://github.com/AbdulkarimMziya/resume-studio-web)**

<!-- Drop a screenshot of the Swagger docs into docs/media/ and add: ![Swagger docs](docs/media/swagger.png) -->

---

## 🎯 Problem & Motivation
A generic resume gets filtered out, but rewriting it by hand for every posting is slow, and AI tools that rewrite everything tend to exaggerate. Resume Studio compares your resume with one job description and suggests specific rewrites of lines you already have, each with the reason it fits the role.

The backend does the work the browser can't do safely:
* it keeps the Gemini API key off the client;
* it checks every AI answer before returning it;
* it reads `.docx` and `.pdf` files;
* it limits how much any one visitor can spend.

## ✨ Key Features & Engineering Highlights
* **Grounded suggestions:** Each suggestion's `original` text must actually appear in the resume, compared with whitespace normalised. If the model invents or paraphrases a line, the API returns `502` rather than passing it on (`analysis/services.py`).
* **Structured AI output, validated twice:** Gemini is called with a JSON response schema, and a DRF serializer checks the shape again. The call has a 30 s timeout and a 2,048-token output cap (`analysis/gemini.py`).
* **Prompt-injection guard:** The prompt (`analysis/prompt.txt`) puts the resume and job text inside tags and treats them as data, not instructions. It forbids new facts, tools, numbers or results.
* **Safe file parsing (.txt, .docx, .pdf):**
  * Files are limited to 2 MB.
  * The first bytes must match the claimed type, so a renamed file is rejected.
  * PDFs are capped at 20 pages, and password-protected or image-only PDFs get a clear message.
  * Text in `.docx` tables is included, since many templates put skills there.
  * Nothing is written to disk or saved (`analysis/documents.py`).
* **Clear error contract:** `400` bad input · `415` the body isn't multipart · `429` rate-limited (with a `Retry-After` header) · `502` unusable AI output · `503` AI unreachable. Each error comes with a human-readable `detail` the frontend shows as-is (`analysis/exceptions.py`).
* **Layered rate limits:**
  * Per IP: 5 analyses a minute and 50 a day.
  * Everyone together: 500 analyses a day, a hard cap on Gemini spend.
  * Uploads: 20 a minute per IP.
  * All of these can be changed with env vars. A throttled request never reaches Gemini. `NUM_PROXIES` makes the client IP correct behind Render's proxy (`analysis/throttles.py`).
* **Locked-down CORS:** Only exact origins from an env var are allowed, and `Retry-After` is exposed so the UI can say how long to wait.
* **OpenAPI docs:** drf-spectacular generates the schema, with Swagger UI at `/api/docs/` (including a file picker for uploads).
* **Tested:** 44 pytest-django tests cover the views, text extraction and throttling. Gemini is monkeypatched, so tests never call the paid API.

## 🛠 Tech Stack
* **Backend:** Python 3.14, Django 6.1, Django REST Framework 3.18, Google Gemini (`google-genai`)
* **File parsing:** pypdf, python-docx
* **API & config:** drf-spectacular, django-cors-headers, django-environ, gunicorn
* **Frontend (separate repo):** React 19, TypeScript, Vite
* **Tooling:** pytest, pytest-django
* **Hosting:** Render (API), GitHub Pages (frontend)

## 🏗 Architecture & Technical Decisions
```
React ──POST /api/extract-text/──▶ serializer (type, 2 MB) ──▶ documents.py ──▶ {"text": "..."}
      ──POST /api/analyze/───────▶ throttles ──▶ serializer ──▶ services.py ──▶ gemini.py ──▶ Gemini
                                                                    │
                                                     grounding check: every "original" is in the resume
                                                                    ▼
                                                    {"suggestions": [{original, replacement, reason}]}
```

| Method | Path | Body | Success |
|---|---|---|---|
| `POST` | `/api/analyze/` | JSON: `resume_text` (≤ 30,000 chars), `job_description` (≤ 20,000 chars) | `200` `{"suggestions": [...]}` (usually 3–5) |
| `POST` | `/api/extract-text/` | multipart: `file` (.txt / .docx / .pdf, ≤ 2 MB) | `200` `{"text": "..."}` |
| `GET` | `/api/docs/` · `/api/schema/` | none | Swagger UI · OpenAPI schema |

```bash
curl -X POST https://resume-studio-api-vfuy.onrender.com/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "Trained new staff on opening procedures.", "job_description": "Mentor junior developers."}'
```
```json
{
  "suggestions": [
    {
      "original": "Trained new staff on opening procedures.",
      "replacement": "Mentored and trained new team members on standard procedures.",
      "reason": "The role asks for mentoring; this shows the same skill in the job's language."
    }
  ]
}
```

* **Stateless by design:** There are no accounts and no database models. Uploaded files are read for their text and then discarded. The frontend keeps the resume in the browser tab.
* **Thin views, a service layer, one AI module:** Views validate input and call `analyze_resume()`. The grounding check lives in the service, and only `gemini.py` knows about the SDK. Tests patch one function, and switching AI providers touches one file.
* **Model ID in the environment:** `AI_MODEL` is configuration, so changing the model needs no code change.
* **Trade-offs & future improvements:**
  * Throttle counts live in Django's in-memory cache. They reset on each redeploy and aren't shared across instances, which is fine for one Render instance; scaling out would need Redis.
  * Scanned PDFs would need OCR.
  * On the free tier, the server sleeps when idle, so the first request after a while is slow.

## 🚀 Local Setup
```bash
# 1. Clone the repository
git clone https://github.com/AbdulkarimMziya/resume-studio-api.git
cd resume-studio-api

# 2. Create a virtual environment & install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure, then run
cp .env.example .env      # fill in SECRET_KEY, AI_API_KEY and AI_MODEL
python manage.py runserver    # http://localhost:8000/api/docs/
```
`pytest` runs the tests.

To use it from the frontend, run [resume-studio-web](https://github.com/AbdulkarimMziya/resume-studio-web) with `VITE_USE_MOCK=false` and `VITE_API_BASE_URL=http://localhost:8000` in its `.env.local`.

### Environment variables
| Name | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | yes | Django secret key |
| `AI_API_KEY` | yes | Google Gemini API key |
| `AI_MODEL` | yes | Gemini model ID |
| `DEBUG` | no (default `False`) | `True` locally only |
| `ALLOWED_HOSTS` | no | Comma-separated hosts, e.g. `127.0.0.1,localhost` |
| `CORS_ALLOWED_ORIGINS` | no | Comma-separated frontend origins, e.g. `http://localhost:5173` |
| `THROTTLE_ANALYZE_BURST` / `_DAILY` / `_GLOBAL`, `THROTTLE_EXTRACT` | no | Override the rate limits (defaults `5/min`, `50/day`, `500/day`, `20/min`) |
| `NUM_PROXIES` | no | Leave unset locally; `1` on Render |

### Deploying to Render
Create a Web Service from this repo:
* **Build command:** `pip install -r requirements.txt`
* **Start command:** `gunicorn config.wsgi`
* **Environment variables:** `SECRET_KEY`, `AI_API_KEY`, `AI_MODEL`, `DEBUG=False`, `NUM_PROXIES=1`, and `CORS_ALLOWED_ORIGINS=https://abdulkarimmziya.github.io`. Use the origin only, with no path and no trailing slash.

Render's hostname is added to `ALLOWED_HOSTS` automatically through `RENDER_EXTERNAL_HOSTNAME`. Each push to `main` redeploys.

## 📄 License
MIT. See [LICENSE](LICENSE).

## 📬 Contact
**Abdulkarim Mziya** – [LinkedIn](https://linkedin.com/in/abdulkarim-mziya) | [GitHub](https://github.com/AbdulkarimMziya)
