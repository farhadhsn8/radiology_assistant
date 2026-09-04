# Radiology Assistant

An AI-powered service that turns voice-transcribed (or raw text) radiologist dictations into well-structured, template-aligned radiology reports.

It transcribes audio with Whisper (`openai/whisper-base`), detects the study type with an LLM, and rewrites the dictation into a clean, findings-faithful report following a study-specific template.

## Features

- **Voice → Report**: upload an MP3/audio recording or use the browser recorder; audio is chunked and transcribed, the study type is auto-detected, and a formatted report is generated.
- **Text → Report**: pass raw dictation text together with a study type.
- **Template-driven output**: report structure follows per-study templates under `assets/templates/`.
- **Clinical safety constraints**: prompts enforce editing only (grammar/terminology) — never adding/removing findings, measurements, or locations.
- **API-key protected endpoints** with an OpenAPI (FastAPI) frontend.

## Architecture

```
Browser (index.html)
   │  HTTPS
   ▼
Nginx (deploy/reportexx_nginx.conf)
   │  proxy /api
   ▼
FastAPI (main.py)
   └─ /api/v1 routes (src/apis/v1/route.py)
       └─ Report_orchestrator (src/orchestrators)
           ├─ Reporter_from_voice: Whisper STT + chunking
           ├─ TypeDetector:          LLM study-type detection
           └─ Reporter:              LLM template rewrite + post-processing
               └─ LLM client (langchain + OpenAI-compatible API)
```

Runtime config is loaded through `src/config.py`, which resolves all paths relative to the project root so the app can be launched from any working directory.

## Project layout

```
.
├── main.py                     # FastAPI app, mounts /api, serves index.html
├── env_sample.json             # Template for env.json (copy + fill in)
├── configs/
│   └── voice.json              # voice dir + audio format config
├── src/
│   ├── config.py               # central config/path helpers
│   ├── apis/v1/route.py        # API routes + key verification
│   ├── orchestrators/          # report pipeline orchestration
│   ├── services/
│   │   ├── llm/                # LLM client wrapper
│   │   └── reporters/          # text/voice reporters + type detector
│   └── utils/                  # file/text helpers
├── assets/
│   ├── prompts/                # system prompts
│   ├── templates/              # study templates (modality/contrast/study.txt)
│   └── voices/                 # runtime audio storage (git-ignored)
├── deploy/
│   └── reportexx_nginx.conf    # production nginx site config
├── logs/                       # runtime logs (git-ignored)
└── requirements.txt
```

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) (required by `pydub` for audio conversion)
- ~2 GB RAM minimum for the Whisper model plus PyTorch

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the environment file from the sample and fill in your values:

```bash
cp env_sample.json env.json
```

`env.json` structure:

```json
{
  "models": {
    "llm": {
      "base_url": "https://api.openai.com/v1",
      "api_key": "<your-key>",
      "model_name": "gpt-4o-mini-2024-07-18",
      "temperature": 0.1
    }
  },
  "API": {
    "name": "radio",
    "key": "<shared-secret-header-value>"
  }
}
```

- `models.llm` — any OpenAI-compatible chat model (works with OpenAI or compatible gateways by changing `base_url`).
- `API.name` — HTTP header that clients must send; `API.key` — its expected value. Requests missing or mismatching this header get `403`.

> `env.json` is git-ignored and must never be committed.

## Run locally

```bash
uvicorn main:app --host 127.0.0.1 --port 5682 --timeout-keep-alive 300 --workers 1
```

The frontend (`index.html`) is served at `http://127.0.0.1:5682/`. The OpenAPI docs are at `http://127.0.0.1:5682/docs`.

Keep `--workers 1`: the Whisper model is loaded in memory at startup and is not fork-safe across multiple workers.

## API

Both endpoints require the API header (default name `radio`):

```bash
API_KEY="<API.key from env.json>"
```

### Voice → report

```bash
curl -X POST http://127.0.0.1:5682/api/voice/gen_report \
  -H "radio: $API_KEY" \
  -F "input_voice=@recording.mp3"
```

### Text → report

```bash
curl -X POST "http://127.0.0.1:5682/api/text/gen_report" \
  -H "radio: $API_KEY" \
  --data-urlencode "input_text=liver normal size. no focal lesion." \
  --data-urlencode "report_type=CT:no_contrast:Brain"
```

`report_type` uses the `modality:contrast:study` convention that maps to `assets/templates/<modality>/<contrast>/<study>.txt` (for example `CT:no_contrast:HRCT_chest` → `assets/templates/CT/no_contrast/HRCT_chest.txt`).

### Response

```json
{
  "status": 200,
  "generated_report": "The liver is normal in size ...",
  "message": "Report generated from voice"
}
```

## Adding a study type

1. Add a template file `assets/templates/<modality>/<contrast>/<Study>.txt`.
2. Register the canonical study id (`modality:contrast:Study`) in the prompt at `assets/prompts/type_detector.txt` so voice auto-detection can find it.
3. Optionally add a matching `<Study>` entry to the study selector in `index.html`.

## Production deployment

### 1. Run the backend behind a process manager

Example systemd unit (`/etc/systemd/system/radiology-assistant.service`):

```ini
[Unit]
Description=Radiology Assistant API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/radiology_assistant
EnvironmentFile=/opt/radiology_assistant/env.json
ExecStart=/opt/radiology_assistant/.venv/bin/uvicorn main:app \
    --host 127.0.0.1 --port 5682 --timeout-keep-alive 300 --workers 1
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable --now radiology-assistant
```

### 2. Serve the frontend and proxy `/api` with Nginx

Install the site config (edit the domain, SSL certificate paths, and frontend root first):

```bash
sudo cp deploy/reportexx_nginx.conf /etc/nginx/sites-available/reportexx
sudo ln -s /etc/nginx/sites-available/reportexx /etc/nginx/sites-enabled/
sudo nginx -t && sudo nginx -s reload
```

Copy the built/frontend page to the Nginx web root (or keep serving `index.html` directly from FastAPI):

```bash
sudo cp index.html /var/www/html/
```

The `index.html` client calls `/api/...` with a relative URL, so it works locally and behind the proxy without changes.

### 3. TLS

Use certbot for Let's Encrypt certificates and point the paths in `deploy/reportexx_nginx.conf` at them.

## Production readiness checklist

Before go-live:

- [ ] **Secrets** — `env.json` is git-ignored. Never commit `API.key` or LLM API keys. If a key was ever committed, rotate it and scrub history. The header key shown in `index.html` is visible to any browser; treat it as a gate for casual access only and rely on Nginx/TLS for real protection, or restrict `/api` by client IP/allowlist in Nginx.
- [ ] **TLS** — HTTPS with a valid certificate and HTTP→HTTPS redirect (see `deploy/`).
- [ ] **Workers** — run with `--workers 1` because of the in-memory Whisper model; scale by adding hosts, not workers.
- [ ] **Timeouts** — voice transcription + LLM calls are slow; keep generous proxy timeouts (the sample config uses 300s) and increase them if long recordings are expected.
- [ ] **Audio storage** — uploaded and generated audio lands in `assets/voices/` (git-ignored). Add a cleanup/retention job and ensure the directory has enough disk space.
- [ ] **Dependencies** — pin exact versions in production (`pip freeze > requirements.lock`) and rebuild images from a frozen environment.
- [ ] **Resource sizing** — the server must hold the Whisper model in memory while also running other services. Monitor RAM and disk.
- [ ] **Logs** — capture stdout/stderr of the service to `logs/` and set up rotation (`logrotate`).
- [ ] **Monitoring/backups** — add health checks against `/` and `/docs`, plus backups of the template/prompt assets (they are your report-quality source of truth).
- [ ] **CORS** — if the API is ever called from a separate frontend origin, tighten `allow_origins` in `main.py` from `*` to the real origin.
- [ ] **Rate limiting** — add Nginx `limit_req` or an API gateway layer to protect expensive LLM/STT endpoints.

## Notes

- The heavy ML/audio dependencies (`torch`, `transformers`, `scipy`) load at startup; first response will be slow until the model is warm.
- Reports are formatted as plain text inside a JSON envelope. Findings are marked bold in the report text by the LLM per the prompt in `assets/prompts/general_prompt.txt`.
