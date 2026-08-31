import { useCallback, useEffect, useRef, useState } from "react";
import { InterviewSocket, type CloseInfo } from "@/services/interviewSocket";
import { wsUrl } from "@/lib/config";
import type { ClientEvent, ClientEventType, ServerEvent } from "@/types/websocket";
import type { ConnectionState } from "@/types/interview";

interface UseInterviewSocketArgs {
  onEvent: (event: ServerEvent) => void;
  onAudio: (chunk: ArrayBuffer) => void;
  onOpen?: () => void;
  onClose?: (info: CloseInfo) => void;
}

export interface UseInterviewSocketReturn {
  connectionState: ConnectionState;
  connect: (sessionId: string) => void;
  disconnect: () => void;
  send: (event: ClientEvent) => boolean;
  sendType: (type: ClientEventType) => boolean;
  sendAudio: (bytes: ArrayBuffer | Uint8Array) => boolean;
  isOpen: boolean;
}

/**
 * Owns the interview WebSocket transport for a React component.
 *
 * Reconnect policy is intentionally left to `useInterview` (which re-syncs
 * interview state after reconnecting); this hook only wires the transport
 * lifecycle to React state.
 */
export function useInterviewSocket({
  onEvent,
  onAudio,
  onOpen,
  onClose,
}: UseInterviewSocketArgs): UseInterviewSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const socketRef = useRef<InterviewSocket | null>(null);

  // Keep callbacks fresh without recreating the socket.
  const handlersRef = useRef({ onEvent, onAudio, onOpen, onClose });
  useEffect(() => {
    handlersRef.current = { onEvent, onAudio, onOpen, onClose };
  }, [onEvent, onAudio, onOpen, onClose]);

  const connect = useCallback((sessionId: string) => {
    const socket = new InterviewSocket(wsUrl(sessionId));
    socketRef.current = socket;
    socket.setHandlers({
      onOpen: () => {
        setConnectionState("connected");
        handlersRef.current.onOpen?.();
      },
      onClose: (info) => {
        setConnectionState((prev) => (prev === "connected" ? "reconnecting" : "disconnected"));
        handlersRef.current.onClose?.(info);
      },
      onEvent: (event) => handlersRef.current.onEvent(event),
      onAudio: (chunk) => handlersRef.current.onAudio(chunk),
    });
    setConnectionState("connecting");
    socket.connect();
  }, []);

  const disconnect = useCallback(() => {
    socketRef.current?.disconnect();
    socketRef.current = null;
    setConnectionState("disconnected");
  }, []);

  const send = useCallback((event: ClientEvent) => {
    return socketRef.current?.send(event) ?? false;
  }, []);

  const sendType = useCallback((type: ClientEventType) => {
    return socketRef.current?.sendType(type) ?? false;
  }, []);

  const sendAudio = useCallback((bytes: ArrayBuffer | Uint8Array) => {
    return socketRef.current?.sendAudio(bytes) ?? false;
  }, []);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      socketRef.current?.disconnect();
      socketRef.current = null;
    };
  }, []);

  return {
    connectionState,
    connect,
    disconnect,
    send,
    sendType,
    sendAudio,
    isOpen: socketRef.current?.isOpen ?? false,
  };
}