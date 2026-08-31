import type { InterviewPhase } from "@/types/interview";

interface InterviewStatusProps {
  phase: InterviewPhase;
  candidateSpeaking: boolean;
}

const LABELS: Record<InterviewPhase, string> = {
  connecting: "Connecting…",
  ready: "Ready",
  speaking: "Interviewer speaking",
  listening: "Your turn",
  processing: "Thinking…",
  completed: "Interview complete",
  error: "Something went wrong",
};

/**
 * Authoritative status indicator showing what the system expects from the
 * candidate at any moment. Never leaves the candidate wondering.
 */
export function InterviewStatus({ phase, candidateSpeaking }: InterviewStatusProps) {
  let label = LABELS[phase] ?? "";
  let cssClass = "status";

  if (phase === "listening") {
    cssClass = candidateSpeaking ? "status status--candidate" : "status status--listening";
    label = candidateSpeaking ? "You're speaking" : "Your turn";
  } else if (phase === "speaking") {
    cssClass = "status status--speaking";
  } else if (phase === "processing") {
    cssClass = "status status--processing";
  }

  return (
    <div className={cssClass} aria-live="polite">
      <span className="status__dot" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}