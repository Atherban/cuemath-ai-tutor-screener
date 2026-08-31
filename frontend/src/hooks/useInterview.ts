import { useCallback, useEffect, useRef, useState } from "react";
import { getInterviewSession } from "@/services/api";
import { ANSWER_TIME_LIMIT_SEC } from "@/lib/config";
import { useInterviewSocket } from "./useInterviewSocket";
import { useAudioPlayback } from "./useAudioPlayback";
import { useLiveTranscription } from "./useLiveTranscription";
import { useMicrophone } from "./useMicrophone";
import type { ConnectionState, InterviewError, InterviewPhase } from "@/types/interview";
import type { ServerEvent, ServerEventType } from "@/types/websocket";
import type { TranscriptEntry } from "@/types/api";

export interface TranscriptItem {
  role: "interviewer" | "candidate";
  text: string;
}

interface UseInterviewArgs {
  sessionId: string;
  onCompleted?: (sessionId: string) => void;
}

const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_BACKOFF_MS = [1500, 3000, 6000];

function fromHistory(history: TranscriptEntry[]): TranscriptItem[] {
  return history
    .filter((e) => e.role === "interviewer" || e.role === "candidate")
    .map((e) => ({ role: e.role as TranscriptItem["role"], text: e.text }));
}

export interface UseInterviewReturn {
  /** Authoritative interview phase, driven by WebSocket events. */
  phase: InterviewPhase;
  connectionState: ConnectionState;
  /** The interviewer's current/last spoken text. */
  interviewerText: string;
  /** Full conversation shown subtly. */
  transcript: TranscriptItem[];
  /** Live microphone level (0–1). */
  audioLevel: number;
  /** True while the candidate is actually speaking (VAD). */
  candidateSpeaking: boolean;
  /** Non-blocking notice (e.g. "couldn't understand that"). */
  notice: string | null;
  /** Blocking error that ended the interview. */
  error: InterviewError | null;
  /** Prompt shown when the candidate goes quiet. */
  silencePrompt: string | null;
  /** Seconds left to answer the current question (null when no timer). */
  countdown: number | null;
  /** Live transcript of the candidate's current speech (best-effort display). */
  liveTranscript: string;
  /** Clear the live transcript. */
  resetLiveTranscript: () => void;
  /** True while interviewer audio is playing. */
  interviewerPlaying: boolean;
  micState: ReturnType<typeof useMicrophone>["micState"];
  /** Begin the interview (sends session.start). */
  start: () => void;
  /** Send a typed answer (bypasses the microphone). */
  sendText: (text: string) => boolean;
  /** Begin recording the candidate's answer (push-to-talk). */
  startSpeaking: () => Promise<void>;
  /** Skip the thinking timer so the candidate can start speaking now. */
  skipTimer: () => void;
  /** True while the candidate is actively recording. */
  isRecording: boolean;
  /** Manually finish the current answer now. */
  finishAnswer: () => void;
  /** End the interview via the candidate's own action. */
  endInterview: () => void;
  /** Manually retry the connection after a failure. */
  reconnect: () => void;
  /** Request microphone access. */
  requestMic: () => Promise<void>;
  /** Unlock audio playback (call from a user gesture for autoplay policy). */
  unlockAudio: () => void;
}

export function useInterview({ sessionId, onCompleted }: UseInterviewArgs): UseInterviewReturn {
  const [phase, setPhase] = useState<InterviewPhase>("connecting");
  const [interviewerText, setInterviewerText] = useState("");
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [audioLevel, setAudioLevel] = useState(0);
  const [candidateSpeaking, setCandidateSpeaking] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<InterviewError | null>(null);
  const [silencePrompt, setSilencePrompt] = useState<string | null>(null);
  // Seconds left for the candidate to answer the current question. Null when
  // there is no active timer.
  const [countdown, setCountdown] = useState<number | null>(null);

  // Stable refs for values used inside socket handlers.
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const onCompletedRef = useRef(onCompleted);
  onCompletedRef.current = onCompleted;
  const phaseRef = useRef(phase);
  phaseRef.current = phase;
  const hasStartedRef = useRef(false);
  const hasConnectedRef = useRef(false);
  const completedRef = useRef(false);
  const intentionalCloseRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const initialStatusRef = useRef<string | null>(null);

  // ── Audio playback ───────────────────────────────────────────────────────
  const {
    isPlaying: interviewerPlaying,
    addChunk,
    endBurst,
    stop: stopPlayback,
    unlock: unlockAudio,
  } = useAudioPlayback();

  // ── Microphone ───────────────────────────────────────────────────────────
  const mic = useMicrophone({
    onLevelChange: (level) => setAudioLevel(level),
    onSpeechEnd: (wav) => handleSpeechEnd(wav),
  });

  // Live transcription of the candidate's speech — active only while the
  // candidate is actually recording (push-to-talk), never while listening.
  const { liveTranscript, resetLiveTranscript } = useLiveTranscription({
    active: mic.isRecording,
  });

  // ── Core handlers ────────────────────────────────────────────────────────
  //
  // These are deliberately plain functions (not useCallback): the socket hook
  // stores them in a ref that is refreshed on every render, so they never need
  // to be referentially stable. Being hoisted also lets `socket` be declared
  // below while still being referenced here.

  function clearNotice() {
    if (notice) setNotice(null);
  }

  function complete() {
    if (completedRef.current) return;
    completedRef.current = true;
    intentionalCloseRef.current = true;
    mic.stopRecording();
    setPhase("completed");
    // NOTE: we deliberately do NOT stopPlayback() here — the interviewer's
    // closing speech should finish playing first. Navigation to the results
    // screen happens in an effect once `interviewerPlaying` becomes false.
  }

  // Navigate to the evaluation screen once the interview is complete AND the
  // interviewer's closing audio has finished playing. Guarded so it fires once.
  const navigatedToResultsRef = useRef(false);
  useEffect(() => {
    if (completedRef.current && !interviewerPlaying && !navigatedToResultsRef.current) {
      navigatedToResultsRef.current = true;
      onCompletedRef.current?.(sessionIdRef.current);
    }
  }, [interviewerPlaying, phase]);

  function restoreTranscript() {
    void getInterviewSession(sessionIdRef.current)
      .then((detail) => {
        if (detail.status === "COMPLETED") {
          complete();
          return;
        }
        setTranscript(fromHistory(detail.conversation_history));
        const last = detail.conversation_history.filter((e) => e.role === "interviewer").pop();
        if (last) setInterviewerText(last.text);
      })
      .catch(() => {
        // Ignore — the conversation still resumes with what we have locally.
      });
  }

  function scheduleReconnect() {
    if (completedRef.current || intentionalCloseRef.current) return;
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      setError({
        code: "CONNECTION_LOST",
        message: "We lost the connection to your interview. Your interview hasn't been submitted.",
        recoverable: true,
      });
      setPhase("error");
      return;
    }
    const delay = RECONNECT_BACKOFF_MS[reconnectAttemptsRef.current] ?? 6000;
    reconnectAttemptsRef.current += 1;
    if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = window.setTimeout(() => {
      reconnectTimerRef.current = null;
      socket.connect(sessionIdRef.current);
    }, delay);
  }
  const scheduleReconnectRef = useRef(scheduleReconnect);
  scheduleReconnectRef.current = scheduleReconnect;

  function handleServerError({ code, message }: { code?: string; message?: string }) {
    const msg = message ?? "Something went wrong.";
    switch (code) {
      case "SESSION_ALREADY_COMPLETED":
        complete();
        break;
      case "SESSION_NOT_FOUND":
        intentionalCloseRef.current = true;
        socket.disconnect();
        setError({ code, message: msg, recoverable: false });
        setPhase("error");
        break;
      case "SESSION_ALREADY_CONNECTED":
        if (hasConnectedRef.current) {
          // Reconnect raced the old server-side connection cleaning up.
          scheduleReconnect();
        } else {
          intentionalCloseRef.current = true;
          socket.disconnect();
          setError({ code, message: msg, recoverable: false });
          setPhase("error");
        }
        break;
      case "TRANSCRIPTION_FAILED":
      case "AUDIO_TOO_SHORT":
        setNotice("We couldn't hear that clearly. Please try again.");
        break;
      case "TTS_FAILED":
        setNotice("We couldn't play that message. Please try again.");
        break;
      case "INVALID_MESSAGE":
      case "SESSION_NOT_READY":
        setNotice("Something went wrong. Please try again.");
        break;
      default:
        // Unexpected but non-fatal: keep the interview going.
        setNotice(msg);
        break;
    }
  }

  function handleServerEvent(event: ServerEvent) {
    switch (event.type as ServerEventType) {
      case "session.ready":
        handleReady();
        break;
      case "interviewer.state": {
        const state = (event.data as { state?: string })?.state;
        clearNotice();
        if (state === "speaking") {
          setPhase("speaking");
          setSilencePrompt(null);
        } else if (state === "thinking") {
          setPhase("processing");
          setSilencePrompt(null);
        } else if (state === "listening") {
          setPhase("listening");
          setSilencePrompt(null);
        }
        break;
      }
      case "interviewer.transcript": {
        const text = (event.data as { text?: string })?.text ?? "";
        if (text) {
          setInterviewerText(text);
          setTranscript((prev) => [...prev, { role: "interviewer", text }]);
        }
        break;
      }
      case "candidate.transcript": {
        const text = (event.data as { text?: string })?.text ?? "";
        if (text) {
          setTranscript((prev) => [...prev, { role: "candidate", text }]);
        }
        break;
      }
      case "silence.prompt": {
        const message = (event.data as { message?: string })?.message ?? "";
        if (message && phaseRef.current === "listening") {
          setSilencePrompt(message);
        }
        break;
      }
      case "audio.end":
        endBurst();
        break;
      case "session.completed":
        complete();
        break;
      case "assessment.started":
      case "assessment.completed":
        break;
      case "error":
        handleServerError((event.data as { code?: string; message?: string }) ?? {});
        break;
      case "pong":
        break;
      default:
        break;
    }
  }

  function handleReady() {
    // Fresh connection: decide start vs resume.
    if (hasConnectedRef.current) {
      // Reconnect after an established session.
      resumeAfterReconnect();
      return;
    }
    hasConnectedRef.current = true;
    reconnectAttemptsRef.current = 0;

    if (initialStatusRef.current === "IN_PROGRESS") {
      // A session that was already mid-interview (e.g. page reload).
      hasStartedRef.current = true;
      restoreTranscript();
      setPhase("listening");
      return;
    }
    if (initialStatusRef.current === "COMPLETED") {
      complete();
      return;
    }
    // Fresh session — kick off the interview.
    hasStartedRef.current = true;
    socket.sendType("session.start");
  }

  function resumeAfterReconnect() {
    restoreTranscript();
    setPhase("listening");
  }

  function handleSocketClose() {
    if (completedRef.current || intentionalCloseRef.current) return;
    scheduleReconnect();
  }

  function handleSpeechEnd(wav: ArrayBuffer) {
    if (phaseRef.current !== "listening") return;
    // Stop capturing and hand the audio to the backend.
    mic.stopRecording();
    resetLiveTranscript();
    socket.sendAudio(wav);
    socket.sendType("audio.end");
    setSilencePrompt(null);
    // We've finished our turn; the backend will confirm with "thinking".
    setPhase("processing");
  }

  // ── Socket ───────────────────────────────────────────────────────────────
  const socket = useInterviewSocket({
    onEvent: handleServerEvent,
    onAudio: (chunk) => addChunk(chunk),
    onClose: handleSocketClose,
  });

  // ── Public actions ───────────────────────────────────────────────────────

  const start = useCallback(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;
    // Unlock audio playback from a user gesture (autoplay policy in
    // Chrome/Brave requires this before the interviewer can be heard).
    unlockAudio();
    socket.sendType("session.start");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- socket methods are stable
  }, [socket.sendType, unlockAudio]);

  const sendText = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || phaseRef.current !== "listening") return false;
      // A typed answer supersedes any in-progress recording.
      mic.stopRecording();
      resetLiveTranscript();
      setSilencePrompt(null);
      setPhase("processing");
      return socket.send({ type: "candidate.text", data: { text: trimmed } });
    },
    [mic, resetLiveTranscript, socket.send]
  );

  const finishAnswer = useCallback(() => {
    mic.endTurn();
  }, [mic]);

  /**
   * Push-to-talk: begin recording the candidate's answer.
   * Only valid while the interviewer is listening. Requests mic permission
   * first if not yet granted (a user gesture makes this reliable in Brave).
   */
  const startSpeaking = useCallback(async () => {
    if (phaseRef.current !== "listening") return;
    // Request the mic first if not yet granted (the click is a user gesture,
    // which makes this reliable in Brave/Chrome). startRecording no-ops unless
    // the stream exists.
    if (mic.micState !== "granted") {
      await mic.requestMic();
    }
    mic.startRecording();
  }, [mic]);

  const endInterview = useCallback(() => {
    socket.sendType("session.end");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- socket methods are stable
  }, [socket.sendType]);

  const reconnect = useCallback(() => {
    intentionalCloseRef.current = false;
    reconnectAttemptsRef.current = 0;
    setError(null);
    setPhase("connecting");
    socket.connect(sessionIdRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- socket methods are stable
  }, [socket.connect]);

  const requestMic = useCallback(async () => {
    await mic.requestMic();
  }, [mic]);

  // ── Effects ──────────────────────────────────────────────────────────────

  // Fetch the session's initial status once on mount.
  useEffect(() => {
    let cancelled = false;
    getInterviewSession(sessionId)
      .then((detail) => {
        if (cancelled) return;
        initialStatusRef.current = detail.status;
        if (detail.status === "COMPLETED") {
          complete();
        }
        // Otherwise wait for the socket to connect.
      })
      .catch(() => {
        // Defaults to a fresh start on connect.
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Connect once on mount.
  useEffect(() => {
    socket.connect(sessionId);
    return () => {
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      socket.disconnect();
      stopPlayback();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Push-to-talk: never auto-start recording. Only ensure recording stops
  // whenever the interviewer is speaking/processing (not listening).
  const micState = mic.micState;
  const micStopRecording = mic.stopRecording;
  useEffect(() => {
    if (phase !== "listening" && micStopRecording) {
      micStopRecording();
    }
  }, [phase, micStopRecording]);

  // Reflect candidate recording (push-to-talk) in the UI.
  useEffect(() => {
    setCandidateSpeaking(mic.isRecording);
  }, [mic.isRecording]);

  // Thinking-time countdown: starts only AFTER the interviewer's question
  // audio has finished playing (phase "listening" AND not playing). The
  // candidate gets ANSWER_TIME_LIMIT_SEC seconds to think, then can speak.
  // It does NOT submit anything — it simply counts down. The candidate ends
  // their turn manually with "Done answering".
  const micIsRecording = mic.isRecording;
  useEffect(() => {
    if (phase !== "listening" || interviewerPlaying || completedRef.current || micIsRecording) {
      setCountdown(null);
      return;
    }
    // Restart only if not already finished.
    setCountdown((prev) => (prev === null || prev === 0 ? ANSWER_TIME_LIMIT_SEC : prev));
    const timer = window.setInterval(() => {
      setCountdown((prev) => {
        if (prev === null) return prev;
        if (prev <= 1) {
          window.clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, interviewerPlaying, micIsRecording]);

  // Skip the thinking timer so the candidate can start speaking immediately.
  const skipTimer = useCallback(() => {
    setCountdown(0);
  }, []);

  // Reconnect when the tab becomes visible again if the socket was dropped.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") {
        if (
          !completedRef.current &&
          !intentionalCloseRef.current &&
          socket.connectionState !== "connected"
        ) {
          scheduleReconnectRef.current();
        }
      }
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [socket.connectionState]);

  // When the mic is not granted, prompt for permission on first listening.
  const micRequestMic = mic.requestMic;
  useEffect(() => {
    if (phase === "listening" && micState === "idle") {
      void micRequestMic();
    }
  }, [phase, micState, micRequestMic]);

  return {
    phase,
    connectionState: socket.connectionState,
    interviewerText,
    transcript,
    audioLevel,
    candidateSpeaking,
    notice,
    error,
    silencePrompt,
    countdown,
    liveTranscript,
    resetLiveTranscript,
    interviewerPlaying,
    micState: mic.micState,
    start,
    sendText,
    startSpeaking,
    skipTimer,
    isRecording: mic.isRecording,
    finishAnswer,
    endInterview,
    reconnect,
    requestMic,
    unlockAudio,
  };
}