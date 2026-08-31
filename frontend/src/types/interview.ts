/**
 * Frontend interview state types.
 */

/** The authoritative interview phase, driven by WebSocket events. */
export type InterviewPhase =
  | "connecting"
  | "ready"
  | "speaking"
  | "listening"
  | "processing"
  | "completed"
  | "error";

/** Connection state of the WebSocket. */
export type ConnectionState = "disconnected" | "connecting" | "connected" | "reconnecting";

/** Error info for display. */
export interface InterviewError {
  code: string;
  message: string;
  recoverable: boolean;
}