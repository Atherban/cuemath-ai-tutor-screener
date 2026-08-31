# AI Tutor Screener — Frontend

The candidate-facing web app for Cuemath's AI tutor voice-interview screening.
Built with **React + TypeScript + Vite + React Router**, using the **Web Audio
API** and **MediaRecorder-adjacent capture** (ScriptProcessorNode) for
microphone input, the native **WebSocket** API for the live interview, and no
UI framework.

It is a real remote first-round interview, not a chatbot demo: every UI state
is driven by real WebSocket events from the backend, and nothing is faked
(timers, AI responses, audio levels, progress, or completion).

---

## Prerequisites

- Node.js 18+
- The FastAPI backend running locally on `http://localhost:8000`
  (see `../backend`).

## Run commands

```bash
npm install          # install dependencies
npm run dev          # start the Vite dev server (http://localhost:5173)
npm run typecheck    # tsc -b --noEmit
npm run build        # tsc -b && vite build (production build → dist/)
npm run preview      # serve the production build locally
```

### Full local flow

1. Start the backend: `uvicorn app.main:app --port 8000` (in `../backend`).
2. `npm run dev` in this directory.
3. Open `http://localhost:5173`.

In development, Vite proxies `/api` → `http://localhost:8000`. The interview
**WebSocket connects directly** to `ws://localhost:8000` (set via
`VITE_WS_BASE_URL` in `.env.example`) — Vite's `http-proxy` mishandles
upstream WebSocket disconnects and floods the dev log with `EPIPE`/`ECONNRESET`,
so it is deliberately not proxied. Browsers allow cross-origin WebSockets; the
backend does not validate the `Origin` header.

## Environment variables

Only **public** configuration lives here. Never place backend secrets
(LLM/STT/TTS API keys, database credentials) in any `VITE_*` variable — anything
prefixed `VITE_` is exposed to the browser at build time.

| Variable              | Required | Default | Purpose                                   |
| --------------------- | -------- | ------- | ----------------------------------------- |
| `VITE_API_BASE_URL`   | No       | *(empty)* | Origin of the FastAPI REST API. Empty = same origin (Vite proxy). |
| `VITE_WS_BASE_URL`    | No       | *(empty)* | Origin of the WebSocket endpoint. Empty = derived from `window.location`. |

The default `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` in the committed
`.env.example` are empty to use the dev proxy. For a
deployed backend on another host, set them to e.g. `https://api.example.com`.

## Backend contract (relied upon, not modified)

The frontend was built against the **existing** FastAPI backend and makes the
**smallest compatible assumptions**. No backend changes were made.

### REST (`/api/v1`)

- `POST /sessions` — create an anonymous session
  (`{ "candidate_id": "anonymous" }` → `{ "session_id": "…" }`).
- `GET /sessions/{id}` — session detail including `status` and
  `conversation_history`. Used to restore interview state after a reconnect or
  page reload, because **the backend does not replay the conversation on
  reconnect**.

### WebSocket (`/ws/interview/{session_id}`)

- Client → server text events: `session.start`, `audio.end`, `candidate.text`
  (typed answers — no microphone needed), `session.end`, `ping`; plus **raw
  binary frames** for candidate audio.
- Server → client: `session.ready`, `interviewer.state`
  (`speaking`/`listening`/`thinking`), `interviewer.transcript`,
  `candidate.transcript`, `interviewer.response`, `audio.end` (text terminator
  for the interviewer audio stream), `silence.prompt`, `assessment.started`,
  `assessment.completed`, `session.completed`, `error`, `pong`.
- Server rejection pattern: accept → send `error` → close with `1008`.

### Key protocol facts the frontend depends on

1. **Candidates can type or speak (push-to-talk).** A text box and a "Start
   speaking" button are shown whenever the interviewer is listening. The
   candidate must click "Start speaking" to begin recording (this is a user
   gesture, so it works reliably in Brave/Chrome even when the AudioContext is
   suspended), then click "Done answering" to end their turn and send the audio.
   There is **no automatic listening**: the interviewer never overhears the
   candidate, and voice-activity detection is not used. Typing submits
   `candidate.text` and stops any in-progress recording. While recording, the
   browser's SpeechRecognition API shows the candidate's words live
   (best-effort display); the official transcript still comes from the backend
   STT after the audio is processed.
2. **Candidate audio is captured with `MediaRecorder`** (WebM/Opus, or MP4/AAC
   in Safari). The backend auto-detects the container (faster-whisper via
   PyAV), so any format works. MediaRecorder is used instead of a Web Audio
   `ScriptProcessorNode` so recording works even when the browser's autoplay
   policy keeps the AudioContext "suspended" (this previously froze the
   interview after the interviewer spoke).
3. **The client ends candidate turns.** The backend does *not* auto-detect the
   end of speech — the client streams audio as binary frames and then sends
   `audio.end`. VAD (best-effort, via an AnalyserNode) can auto-end a turn
   after ~2.5 s of silence; the "Done answering" button always works
   regardless of AudioContext state.
4. **Interviewer audio arrives as binary chunks (WAV) terminated by an
   `audio.end` text event.** The frontend buffers a burst, then decodes and
   plays it once per burst with no overlapping playback (a FIFO queue ensures
   the next utterance never starts before the current one ends).
5. **Assessment results are intentionally NOT exposed to the candidate.** The
   client types and UI never surface scores, recommendations, or rubric data.
6. **Errors are never shown raw.** Backend error codes are mapped to friendly,
   non-technical messages (e.g. `TRANSCRIPTION_FAILED` → "We couldn't hear that
   clearly").

### Connection recovery

Reconnect policy lives in the `useInterview` hook (the transport hook is
transport-only). On reconnect the frontend re-fetches the session detail to
restore the transcript and does **not** re-send `session.start` for an
`IN_PROGRESS` session. Reconnects are bounded (3 attempts with backoff), and
`SESSION_ALREADY_CONNECTED` during a reconnect is treated as a retryable race
rather than a fatal error.

## Project structure

```
src/
  app/            Router + App shell
  components/     Button, navigation, interview UI pieces
  hooks/          useInterview (state machine), useInterviewSocket,
                  useMicrophone (VAD + WAV), useAudioPlayback
  lib/            config (env-driven base URLs)
  pages/          Landing, Setup, Interview, Completion
  services/       api client, websocket transport, audio utils
  styles/         design tokens + global styles
  types/          API + WebSocket + interview types
```

## Security notes

- No `VITE_*` secret can exist (they're public). Only base URLs are configured.
- The bundle is scanned in CI for common secret patterns; nothing is embedded.
- Assessment data is never requested, transmitted, or rendered to the candidate.
