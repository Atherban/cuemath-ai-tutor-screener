/**
 * Thin WebSocket transport for the interview.
 *
 * This class owns the raw `WebSocket` connection and message framing only.
 * It does NOT manage reconnect policy or interview state — that lives in the
 * `useInterviewSocket` hook so that reconnection can re-sync interview state
 * safely (the backend does not replay the conversation on reconnect).
 *
 * Protocol (from the backend):
 *  - text frames: JSON events (client → server and server → client)
 *  - binary frames: audio chunks (candidate → server while speaking;
 *    server → client for interviewer speech, terminated by an `audio.end`
 *    text event)
 */

import type { ClientEvent, ClientEventType, ServerEvent, ServerEventType } from "@/types/websocket";

export interface CloseInfo {
  code: number;
  reason: string;
  wasClean: boolean;
}

export interface SocketHandlers {
  /** The underlying WebSocket transitioned to OPEN. */
  onOpen?: () => void;
  /** The underlying WebSocket closed. */
  onClose?: (info: CloseInfo) => void;
  /** A typed JSON server event arrived. */
  onEvent?: (event: ServerEvent) => void;
  /** A binary audio chunk arrived (interviewer speech). */
  onAudio?: (chunk: ArrayBuffer) => void;
  /** A low-level socket error occurred. */
  onSocketError?: (err: Event) => void;
}

const SOCKET_CLOSE_CODES: Record<number, string> = {
  1000: "Normal closure",
  1001: "Session ended",
  1006: "Connection lost",
  1008: "Policy violation",
};

export class InterviewSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: SocketHandlers = {};

  constructor(url: string) {
    this.url = url;
  }

  /** Set (or replace) the event handlers. */
  setHandlers(handlers: SocketHandlers): void {
    this.handlers = handlers;
  }

  /** Connect to the interview socket. Returns true if a connection attempt started. */
  connect(): boolean {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return false;
    }
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.binaryType = "arraybuffer";

    ws.onopen = () => this.handlers.onOpen?.();
    ws.onclose = (ev) => {
      this.handlers.onClose?.({
        code: ev.code,
        reason: ev.reason,
        wasClean: ev.wasClean,
      });
    };
    ws.onerror = (ev) => this.handlers.onSocketError?.(ev);
    ws.onmessage = (ev) => this.handleMessage(ev);
    return true;
  }

  /** True while a connection is open. */
  get isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  /** Close the connection (no reconnect). */
  disconnect(): void {
    if (this.ws) {
      const ws = this.ws;
      this.ws = null;
      ws.onopen = null;
      ws.onclose = null;
      ws.onerror = null;
      ws.onmessage = null;
      try {
        ws.close();
      } catch {
        // Already closing.
      }
    }
  }

  /** Send a text JSON client event. */
  send(event: ClientEvent): boolean {
    if (!this.isOpen) return false;
    this.ws!.send(JSON.stringify(event));
    return true;
  }

  /** Send a text JSON event without a typed payload. */
  sendType(type: ClientEventType): boolean {
    return this.send({ type });
  }

  /** Send raw binary audio bytes while the candidate is speaking. */
  sendAudio(bytes: ArrayBuffer | Uint8Array): boolean {
    if (!this.isOpen) return false;
    this.ws!.send(bytes);
    return true;
  }

  private handleMessage(ev: MessageEvent): void {
    if (typeof ev.data === "string") {
      let event: ServerEvent;
      try {
        event = JSON.parse(ev.data) as ServerEvent;
      } catch {
        // Ignore malformed frames; the backend only sends valid JSON.
        return;
      }
      this.handlers.onEvent?.(event);
      return;
    }
    if (ev.data instanceof ArrayBuffer) {
      this.handlers.onAudio?.(ev.data);
    }
  }

  /** Human-readable label for a socket close code (for logging/diagnostics). */
  static describeCode(code: number): string {
    return SOCKET_CLOSE_CODES[code] ?? `Unknown (${code})`;
  }
}

/** Re-exported for typing convenience in the hook. */
export type { ServerEventType };
