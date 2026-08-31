import { useEffect, useRef } from "react";
import { AudioVisualizer } from "./AudioVisualizer";
import { InterviewerAvatar, MiniAvatar } from "./InterviewerAvatar";
import type { TranscriptItem } from "@/hooks/useInterview";
import type { InterviewPhase } from "@/types/interview";

interface TranscriptProps {
  items: TranscriptItem[];
  phase: InterviewPhase;
  interviewerSpeaking: boolean;
  isRecording: boolean;
  liveTranscript: string;
  audioLevel: number;
}

function LiveWords({ text }: { text: string }) {
  // Render each word separately with a tiny staggered fade-in so words appear
  // one by one as the speech recognizer streams them in.
  const words = text.trim() ? text.trim().split(/\s+/) : [];
  return (
    <>
      {words.map((word, i) => (
        <span key={`${word}-${i}`} className="chat__word" style={{ animationDelay: `${i * 30}ms` }}>
          {word}{" "}
        </span>
      ))}
    </>
  );
}

export function Transcript({ items, phase, interviewerSpeaking, isRecording, liveTranscript, audioLevel }: TranscriptProps) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [items.length, liveTranscript, isRecording, phase]);

  const connecting = phase === "connecting";
  const thinking = phase === "processing";

  let lastInterviewerIndex = -1;
  for (let i = items.length - 1; i >= 0; i--) {
    if (items[i].role === "interviewer") {
      lastInterviewerIndex = i;
      break;
    }
  }

  return (
    <div className="chat" role="log" aria-label="Conversation transcript" ref={listRef}>
      {connecting && (
        <div className="chat__connecting">
          <InterviewerAvatar speaking={false} />
          <p className="chat__connecting-label">Connecting to your interviewer…</p>
        </div>
      )}

      {!connecting && items.map((item, i) => {
        const isInterviewer = item.role === "interviewer";
        const isSpeaking = isInterviewer && i === lastInterviewerIndex && interviewerSpeaking;

        return (
          <div
            key={i}
            className={`chat__msg${isInterviewer ? " chat__msg--interviewer" : " chat__msg--candidate"}`}
          >
            {isInterviewer && <MiniAvatar />}
            <div className={`chat__bubble${isSpeaking ? " chat__bubble--live" : ""}`}>
              {item.text}
            </div>
          </div>
        );
      })}

      {isRecording && (
        <div className="chat__msg chat__msg--candidate chat__msg--recording">
          <div className="chat__bubble chat__bubble--recording">
            <AudioVisualizer level={audioLevel} active bars={7} />
            <p className="chat__bubble-live" aria-live="polite">
              {liveTranscript ? <LiveWords text={liveTranscript} /> : "Listening…"}
            </p>
          </div>
        </div>
      )}

      {thinking && (
        <div className="chat__msg chat__msg--interviewer">
          <MiniAvatar />
          <div className="chat__bubble chat__bubble--thinking">
            <span className="chat__dot" />
            <span className="chat__dot" />
            <span className="chat__dot" />
          </div>
        </div>
      )}
    </div>
  );
}