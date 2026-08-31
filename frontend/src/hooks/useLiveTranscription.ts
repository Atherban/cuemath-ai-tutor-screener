import { useCallback, useEffect, useRef, useState } from "react";

interface UseLiveTranscriptionOptions {
  /** True while the candidate is expected to be speaking. */
  active: boolean;
}

/**
 * Live speech-to-text for display only.
 *
 * Uses the browser's SpeechRecognition API (Chrome/Brave/Edge; `webkit*`
 * prefixed) to show the candidate's words as they speak. This is a display
 * convenience — the official transcript still comes from the backend's STT
 * after the audio is processed, so the two are independent.
 *
 * Falls back silently to empty text when the API is unavailable, unsupported,
 * or blocked by permissions.
 */
export function useLiveTranscription({
  active,
}: UseLiveTranscriptionOptions): {
  liveTranscript: string;
  resetLiveTranscript: () => void;
} {
  const [liveTranscript, setLiveTranscript] = useState("");
  const recognitionRef = useRef<any>(null);
  const activeRef = useRef(active);
  activeRef.current = active;
  const setLiveRef = useRef(setLiveTranscript);
  setLiveRef.current = setLiveTranscript;

  const resetLiveTranscript = useCallback(() => {
    setLiveTranscript("");
  }, []);

  useEffect(() => {
    if (!active) {
      (recognitionRef.current as any)?.stop();
      setLiveTranscript("");
      return;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    // Start (or restart) recognition.
    const startRecognition = () => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const rec: any = new SR();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = "en-US";
        rec.onresult = (ev: any) => {
          if (!activeRef.current) return;
          let interim = "";
          let final = "";
          for (let i = ev.resultIndex; i < ev.results.length; i++) {
            const res = ev.results[i];
            if (res.isFinal) final += res[0].transcript;
            else interim += res[0].transcript;
          }
          setLiveRef.current((interim || final).trim());
        };
        rec.onend = () => {
          // Restart if still active (recognition auto-stops on silence).
          if (activeRef.current) {
            try {
              rec.start();
            } catch {
              // Ignore.
            }
          }
        };
        rec.onerror = () => {
          // Non-fatal: live text is best-effort.
        };
        recognitionRef.current = rec;
        rec.start();
      } catch {
        // Best-effort.
      }
    };

    startRecognition();
    return () => {
      try {
(recognitionRef.current as any)?.stop();
      } catch {
        // Ignore.
      }
      recognitionRef.current = null;
    };
  }, [active]);

  return { liveTranscript, resetLiveTranscript };
}
