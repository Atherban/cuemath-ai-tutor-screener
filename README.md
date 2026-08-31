# AI Tutor Screener

A production-ready **AI-powered first-round tutor screening system** for Cuemath.

A candidate joins a live, voice-based interview with an AI interviewer over the
browser, answers a short set of tutoring questions, and the system produces an
**evidence-backed assessment** across five tutoring soft-skill dimensions with a
hiring recommendation — all without a human recruiter in the loop.

```
┌─────────────────────────────┐         ┌──────────────────────────────────────┐
│        React SPA            │  ws://   │            FastAPI backend             │
│  landing / setup / interview│◄────────►│  InterviewEngine (state machine)      │
│  results / completion       │  REST    │  AIProvider (nvidia·openai·gemini·mock)│
│  push-to-talk audio capture │ /api/v1  │  STT  = faster-whisper (local)         │
│  WebAudio playback          │          │  TTS  = edge-tts (natural voice)       │
└─────────────────────────────┘          │  AssessmentEvaluator (evidence-backed) │
                                         └──────────────────────────────────────┘
        one origin — the backend serves the built SPA (no CORS)
```

- **Backend** — Python 3.11, FastAPI, Pydantic v2, WebSocket voice protocol.
  See [`backend/README.md`](backend/README.md).
- **Frontend** — React 18, TypeScript, Vite, React Router, Web Audio API.
  See [`frontend/README.md`](frontend/README.md).
- **Deployment** — single Docker image, Render Blueprint, `docker-compose` for local.

---

## What I built

### The interview

A candidate opens the app, runs a quick device check, and is paired with an AI
interviewer over a persistent WebSocket. The interview is a **structured,
deterministic state machine** — `INTRO → SIMPLIFICATION → ROLEPLAY → METHODOLOGY
→ SCENARIO → CLOSING → ASSESSMENT` — where each stage probes one of the five
dimensions:

| Stage | Dimension probed |
| --- | --- |
| Simplification | Can they break a concept down for a young learner? |
| Roleplay | Do they stay patient when a student is stuck? |
| Methodology | Is their explanation logical, concrete, jargon-free? |
| Scenario | Do they respond with warmth and empathy? |
| *(throughout)* | English fluency — comprehensibility, not accent |

The AI generates **one personalized question per stage** from the candidate's
own answers, so each interview is unique yet every candidate covers the same
five dimensions — fair by construction. There is no follow-up drilling; the
interview moves forward deterministically and ends once coverage is met.

### The voice pipeline

- **Candidate → AI**: push-to-talk capture in the browser → binary audio frames
  over WebSocket → local `faster-whisper` transcription (off the event loop).
- **AI → candidate**: interviewer text → local `edge-tts` speech → binary PCM
  frames → browser playback. Reused `AudioContext`, FIFO queue, no overlapping
  utterances.
- Candidates can also **type** answers (a `candidate.text` event), which makes
  manual testing and accessibility much easier.

### The assessment

After the interview, the evaluator scores **Clarity, Simplicity, Patience,
Warmth, and Fluency** (0–10), each backed by **mandatory transcript evidence**
(`evidence_status`: `SUFFICIENT` / `PARTIAL` / `INSUFFICIENT`), plus a
rule-based recommendation: `STRONG_PROCEED` / `PROCEED` / `BORDERLINE` /
`DO_NOT_PROCEED`. The rules are deliberately conservative — low evidence
coverage or confidence caps the recommendation at `BORDERLINE`, and the
assessment **never considers accent, origin, gender, or appearance**.

### Abuse / non-cooperation handling

Aggressive, abusive, or disengaged answers trigger a polite early termination;
the session records a `fail_reason` and the assessment returns
`DO_NOT_PROCEED`. A unit test covers this path.

---

## Why these choices

### Single origin — one service serves the UI and the API

The FastAPI app mounts the built React SPA (`backend/app/main.py`), so the
frontend and API share one origin. This eliminates CORS entirely, lets
WebSockets share the host, and collapses the deployment to **one Docker image**
— dramatically simpler to run and host than a split SPA + API setup.

### WebSocket for the interview

A live voice conversation needs bidirectional, low-latency streaming: binary
audio in, binary audio + typed events out. REST could not deliver the interview
experience; WebSocket is the right tool and the protocol contract is small and
explicit (`backend/README.md` has the full event schema).

### Provider abstraction + a `mock` default

AI/STT/TTS are **`Protocol` interfaces with swappable implementations**:
- `AIProvider` — NVIDIA / OpenAI / Ollama (OpenAI-compatible), Google Gemini, or
  `mock`.
- `ModelRouter` — tries models in order and caches the first working one
  (no upfront probing, so no latency penalty before the first question), with
  automatic failover when a cached model dies mid-interview.
- STT/TTS default to **local, offline implementations**, so the whole system
  runs with **zero external services and zero cost** (`AI_PROVIDER=mock`), yet
  upgrades to a real provider by environment variables alone. A broken or
  missing API key degrades gracefully to the built-in question bank.

### Local STT/TTS

Local transcription and synthesis avoid per-call latency, vendor cost, and
privacy surface. `faster-whisper` (int8, tiny) and `edge-tts` are fast enough
for a 5–8 minute interview, and the Docker image pre-caches the model so there
is no cold-start download.

### Deterministic engine + personalized questions

A pure rule-based script feels robotic and leaks stage coverage; pure free-form
AI drifts and is unfair. The middle path — **deterministic stages, AI-written
questions** — gives structure, fairness, and naturalness. Each question is
logged with its `source` (`ai` vs. a bank fallback) for verification.

### Conservative, evidence-backed assessment

The recommendation rules (`backend/app/services/assessment/rubric.py`) refuse to
make strong calls on thin evidence, and every dimension score must cite
transcript quotes. This is the difference between a helpful screener and an
LLM confidently inventing a hiring verdict.

### Client ends turns; no ambient listening

The candidate clicks "Start speaking" and "Done answering". There is no
automatic voice-activity detection on the server — privacy-first, and a
click-gesture sidesteps browser autoplay restrictions reliably across Chrome,
Safari, and Brave.

### The frontend is honest

Every UI state is driven by **real WebSocket events** — nothing is faked. And
assessment scores/recommendations are **never exposed to the candidate**; the
candidate-facing types and UI surface only session status and the transcript.

---

## Quick start

**Local dev (two processes):**

```bash
# Backend (Python 3.11+, uv)
cd backend
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --reload-include '.env' --port 8000

# Frontend (Node 18+)
cd frontend
npm install
npm run dev        # http://localhost:5173  (Vite proxies /api → :8000)
```

**Everything in one container (recommended for testing the full app):**

```bash
docker compose up --build   # http://localhost:8080  (mock AI, runs offline)
```

**Deploy (Render):** connect this repo, choose Blueprint → Render reads
`render.yaml` and provisions a single Docker web service. Set
`AI_GEMINI_API_KEY` in the service settings (the blueprint defaults
`AI_PROVIDER` to `gemini`; for an offline deploy, set it to `mock`).

See `backend/README.md` and `frontend/README.md` for configuration reference,
the full WebSocket protocol, and the HTTP API.

---

## Testing

```bash
# Backend — 50+ unit/integration/websocket tests, no external services
cd backend && uv run pytest && uv run ruff check app tests

# Frontend — type safety only (test tooling was intentionally kept out of the
# committed project; see "What I'd improve")
cd frontend && npm run typecheck && npm run build
```

---

## Repository layout

```
.
├── backend/            FastAPI app: interview engine, AI/STT/TTS providers,
│                       assessment evaluator, WebSocket controller, tests
├── frontend/           React + TS + Vite SPA: pages, hooks, WebSocket client,
│                       audio capture/playback, styles
├── Dockerfile          Multi-stage build (frontend → Python deps → runtime)
├── docker-compose.yml  Single-service local run (port 8080, mock AI)
└── render.yaml         Render Blueprint for one-click deployment
```

---

## What I'd improve with more time

1. **Real persistence.** Sessions live in an in-memory repository today. Next:
   PostgreSQL (async, via SQLAlchemy) for sessions + transcripts + assessments,
   and Redis for pub/sub so the interview survives horizontally-scaled
   instances behind a load balancer.

2. **Auth and an admin review flow.** Today any candidate who knows a
   `session_id` can fetch their session state. Next: a recruiter-facing
   dashboard where a human reviews transcript evidence alongside scores,
   approves/rejects, and the candidate never touches assessment data.

3. **Streaming STT + better audio UX.** Currently transcription happens on a
   completed turn. I'd move to streaming partial transcripts, add WebRTC or
   server-side VAD for natural turn-taking, echo cancellation, and noise
   suppression to make the voice experience feel native.

4. **Calibration and fairness experiments.** The rubric and prompt templates
   are hand-tuned. I'd run an A/B/evals harness against human-graded interviews
   to calibrate scores, tune recommendation thresholds, and formally measure
   fairness (e.g., equalized odds across candidate groups).

5. **CI/CD.** Lint, typecheck, tests, and a Docker build on every push;
   automated E2E tests that exercise the full interview with a real backend and
   a browser (Playwright).

6. **Observability.** Structured audit logs already exist; next I'd add
   request/turn-level tracing (OpenTelemetry), interview duration/failure
   metrics, and alerting on provider failures and unusual assessment patterns.

7. **Hardening for scale.** Rate limiting, WebSocket backpressure, abuse
   detection beyond text (audio-level checks), session quotas, and a data
   retention / consent flow to meet privacy obligations (the interview records
   voice).

8. **More question depth.** A single question per dimension keeps interviews
   short and fair; with more turn budget I'd add calibrated follow-up probes
   per dimension without letting the AI wander.

---

## Fairness & privacy notes

- Assessment evaluates **tutoring behaviour and communication only** — never
  accent, origin, gender, ethnicity, appearance, or background.
- "Fluency" means comprehensibility and sentence construction, not
  native-speaker status.
- No candidate voice/transcript is sent to a third-party model provider by
  default; STT/TTS run locally. Scores require direct transcript evidence or a
  dimension is marked `INSUFFICIENT` — never hallucinated.
