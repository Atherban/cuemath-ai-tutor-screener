/**
 * Runtime configuration.
 *
 * Values are read from Vite environment variables. In development the Vite
 * dev-server proxy routes `/api` and `/ws` to the FastAPI backend, so the base
 * URLs can be empty. In production, set `VITE_API_BASE_URL` and
 * `VITE_WS_BASE_URL` to the deployed backend.
 *
 * Only public configuration lives here — never secrets.
 */
function trimTrailingSlash(value: string | undefined): string {
  return value?.replace(/\/+$/, "") ?? "";
}

const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_API_BASE_URL);

/** Base URL for REST calls. Empty means "same origin" (Vite proxy). */
export const API_BASE_URL = apiBaseUrl;

/** Base URL for WebSocket calls. Empty means derive from window location. */
export const WS_BASE_URL = trimTrailingSlash(import.meta.env.VITE_WS_BASE_URL);

/** REST prefix used by the backend. */
export const API_V1_PREFIX = "/api/v1";

/** WebSocket path prefix used by the backend. */
export const WS_PATH_PREFIX = "/ws/interview";

/** Seconds a candidate gets to answer each question before auto-submit. */
export const ANSWER_TIME_LIMIT_SEC = Number(import.meta.env.VITE_ANSWER_TIME_LIMIT_SEC ?? 10);

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${API_V1_PREFIX}${path}`;
}

export function wsUrl(sessionId: string): string {
  const base = WS_BASE_URL || (window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host;
  return `${base}${WS_PATH_PREFIX}/${sessionId}`;
}
