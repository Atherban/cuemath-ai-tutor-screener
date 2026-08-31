/**
 * TypeScript types matching the backend WebSocket protocol exactly.
 *
 * Source of truth: backend `app/schemas/websocket.py`.
 */

// ── Client-to-server events ───────────────────────────────────────────────

export type ClientEventType =
  | "session.start"
  | "audio.chunk"
  | "audio.end"
  | "candidate.text"
  | "session.end"
  | "ping";

export interface ClientEvent<T = unknown> {
  type: ClientEventType;
  data?: T;
}

export interface CandidateTextData {
  text: string;
}

// ── Server-to-client events ───────────────────────────────────────────────

export type InterviewerState = "speaking" | "listening" | "thinking";

export type ServerEventType =
  | "session.ready"
  | "interviewer.transcript"
  | "interviewer.state"
  | "candidate.transcript"
  | "interviewer.response"
  | "audio.chunk"
  | "audio.end"
  | "silence.prompt"
  | "assessment.started"
  | "assessment.completed"
  | "session.completed"
  | "error"
  | "pong";

export interface ServerEvent<T = Record<string, unknown>> {
  type: ServerEventType;
  data?: T;
}

// ── Typed event payloads ──────────────────────────────────────────────────

export interface SessionReadyData {
  session_id: string;
}

export interface InterviewerTranscriptData {
  text: string;
}

export interface InterviewerStateData {
  state: InterviewerState;
}

export interface CandidateTranscriptData {
  text: string;
}

export interface InterviewerResponseData {
  text: string;
  stage: string;
}

export interface SilencePromptData {
  message: string;
}

export interface SessionCompletedData {
  session_id: string;
}

export interface AssessmentCompletedData {
  session_id: string;
}

export interface ErrorData {
  code: string;
  message: string;
}

// ── Event type → payload mapping ──────────────────────────────────────────

export interface ServerEventMap {
  "session.ready": SessionReadyData;
  "interviewer.transcript": InterviewerTranscriptData;
  "interviewer.state": InterviewerStateData;
  "candidate.transcript": CandidateTranscriptData;
  "interviewer.response": InterviewerResponseData;
  "silence.prompt": SilencePromptData;
  "assessment.started": undefined;
  "assessment.completed": AssessmentCompletedData;
  "session.completed": SessionCompletedData;
  "error": ErrorData;
  "pong": undefined;
  "audio.chunk": undefined;
  "audio.end": undefined;
}

// ── Error codes ───────────────────────────────────────────────────────────

export type WsErrorCode =
  | "SESSION_NOT_FOUND"
  | "SESSION_ALREADY_CONNECTED"
  | "SESSION_ALREADY_COMPLETED"
  | "INVALID_MESSAGE"
  | "AUDIO_TOO_SHORT"
  | "TRANSCRIPTION_FAILED"
  | "TTS_FAILED"
  | "ASSESSMENT_FAILED"
  | "SESSION_NOT_READY";