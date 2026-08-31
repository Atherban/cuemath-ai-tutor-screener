import { useCallback, useEffect, useRef, useState } from "react";

export type MicState = "idle" | "requesting" | "granted" | "denied" | "unavailable";

/** Precise reason a microphone could not be obtained, for user-facing copy. */
export type MicErrorReason =
  | "no-device"
  | "in-use"
  | "insecure-context"
  | "overconstrained"
  | "unknown";

interface UseMicrophoneOptions {
  /** Called with the recorded audio blob (any format) once a turn ends. */
  onSpeechEnd?: (audio: ArrayBuffer) => void;
  /** Called with live RMS levels during capture (0–1). */
  onLevelChange?: (level: number) => void;
}

export interface UseMicrophoneReturn {
  micState: MicState;
  /** Precise failure reason when micState is "unavailable" (null otherwise). */
  micError: MicErrorReason | null;
  isRecording: boolean;
  /** Request microphone access. Must be called from a user gesture.
   *  Resolves to true when access was granted, false otherwise. */
  requestMic: () => Promise<boolean>;
  /** Release the microphone stream. */
  releaseMic: () => void;
  /** Start recording (must have mic granted). */
  startRecording: () => void;
  /** Stop recording without emitting a speech-end callback. */
  stopRecording: () => void;
  /** End the current turn and emit the recorded audio. */
  endTurn: () => void;
}

/**
 * Push-to-talk microphone capture.
 *
 * Recording starts only when the candidate clicks "Start speaking" and ends
 * only when they click "Done answering" (or call `endTurn`). There is NO
 * voice-activity detection: the interviewer is never listened to automatically,
 * and nothing depends on a running AudioContext (which Chrome/Brave keep
 * suspended under the autoplay policy).
 *
 * MediaRecorder captures directly from the MediaStream, so it works even when
 * the AudioContext is suspended. The AnalyserNode only drives the live level
 * meter and is best-effort.
 */
export function useMicrophone(options: UseMicrophoneOptions = {}): UseMicrophoneReturn {
  const { onSpeechEnd, onLevelChange } = options;

  const [micState, setMicState] = useState<MicState>("idle");
  const [micError, setMicError] = useState<MicErrorReason | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const ctxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const levelDataRef = useRef<Uint8Array | null>(null);
  const rafRef = useRef<number | null>(null);
  const recordingRef = useRef(false);
  const pendingEndRef = useRef(false);

  const onSpeechEndRef = useRef(onSpeechEnd);
  onSpeechEndRef.current = onSpeechEnd;

  // ── Mic permission lifecycle ─────────────────────────────────────────────

  const requestMic = useCallback(async (): Promise<boolean> => {
    if (streamRef.current) {
      setMicState("granted");
      setMicError(null);
      return true;
    }
    setMicState("requesting");
    try {
      // mediaDevices is unavailable in insecure (non-HTTPS / non-localhost)
      // contexts — calling getUserMedia then throws a TypeError. Detect it up
      // front so we can tell the candidate *why* it failed.
      if (typeof window !== "undefined" && !window.isSecureContext) {
        setMicState("unavailable");
        setMicError("insecure-context");
        return false;
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          autoGainControl: { ideal: true },
        },
      });
      streamRef.current = stream;
      // Best-effort level meter; never fatal.
      try {
        const ctx = new AudioContext();
        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 1024;
        analyser.smoothingTimeConstant = 0.6;
        source.connect(analyser);
        ctxRef.current = ctx;
        sourceRef.current = source;
        analyserRef.current = analyser;
        levelDataRef.current = new Uint8Array(analyser.frequencyBinCount);
        void ctx.resume().catch(() => {
          // Autoplay policy may keep it suspended; meter reads zero.
        });
      } catch {
        // No level meter; recording still works via MediaRecorder.
      }
      setMicState("granted");
      setMicError(null);
      return true;
    } catch (err: unknown) {
      const name = err instanceof DOMException ? err.name : "";
      switch (name) {
        case "NotAllowedError":
        case "SecurityError":
        case "PermissionDeniedError":
          setMicState("denied");
          setMicError(null);
          break;
        case "NotFoundError":
        case "DevicesNotFoundError":
          setMicState("unavailable");
          setMicError("no-device");
          break;
        case "NotReadableError":
        case "TrackStartError":
          setMicState("unavailable");
          setMicError("in-use");
          break;
        case "OverconstrainedError":
          setMicState("unavailable");
          setMicError("overconstrained");
          break;
        default:
          // Anything else (TypeError, AbortError, …).
          setMicState("unavailable");
          setMicError("unknown");
          break;
      }
      return false;
    }
  }, []);

  // ── Capture ──────────────────────────────────────────────────────────────

  const finalizeTurn = useCallback(() => {
    if (pendingEndRef.current) return;
    const recorder = recorderRef.current;
    if (!recorder) return;
    pendingEndRef.current = true;
    recordingRef.current = false;
    setIsRecording(false);
    recorder.onstop = () => {
      pendingEndRef.current = false;
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      chunksRef.current = [];
      if (blob.size > 0) {
        void blob.arrayBuffer().then((buf) => onSpeechEndRef.current?.(buf));
      }
    };
    if (recorder.state !== "inactive") {
      recorder.stop();
    } else {
      pendingEndRef.current = false;
    }
  }, []);

  // Level meter loop (visualizer only — no VAD).
  const pollLevel = useCallback(() => {
    const analyser = analyserRef.current;
    const data = levelDataRef.current;
    if (recordingRef.current && analyser && data) {
      try {
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const level = Math.min(1, Math.sqrt(sum / data.length) * 4);
        onLevelChange?.(level);
      } catch {
        // Analyser unavailable — ignore.
      }
    }
    rafRef.current = requestAnimationFrame(pollLevel);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs keep it fresh
  }, [onLevelChange]);

  // ── Recording controls ──────────────────────────────────────────────────

  const startRecording = useCallback(() => {
    if (!streamRef.current) return;
    if (recorderRef.current && recorderRef.current.state === "recording") return;
    chunksRef.current = [];
    recordingRef.current = true;
    pendingEndRef.current = false;
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/mp4")
        ? "audio/mp4"
        : "";
    const recorder = new MediaRecorder(streamRef.current, mimeType ? { mimeType } : undefined);
    recorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data);
    };
    recorderRef.current = recorder;
    recorder.start(250);
    setIsRecording(true);
    cancelAnimationFrame(rafRef.current ?? 0);
    rafRef.current = requestAnimationFrame(pollLevel);
  }, [micState, pollLevel]);

  const stopRecording = useCallback(() => {
    recordingRef.current = false;
    pendingEndRef.current = false;
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.onstop = null;
      try {
        recorder.stop();
      } catch {
        // Already stopped.
      }
    }
    recorderRef.current = null;
    chunksRef.current = [];
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    setIsRecording(false);
  }, []);

  const endTurn = useCallback(() => {
    finalizeTurn();
  }, [finalizeTurn]);

  const releaseMic = useCallback(() => {
    stopRecording();
    const stream = streamRef.current;
    if (stream) stream.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    const ctx = ctxRef.current;
    if (ctx && ctx.state !== "closed") void ctx.close();
    ctxRef.current = null;
    sourceRef.current = null;
    analyserRef.current = null;
    setMicState("idle");
  }, [stopRecording]);

  // Clean up on unmount.
  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (recorderRef.current && recorderRef.current.state !== "inactive") {
        try {
          recorderRef.current.stop();
        } catch {
          // Ignore.
        }
      }
      const ctx = ctxRef.current;
      if (ctx && ctx.state !== "closed") void ctx.close();
      const stream = streamRef.current;
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return {
    micState,
    micError,
    isRecording,
    requestMic,
    releaseMic,
    startRecording,
    stopRecording,
    endTurn,
  };
}
