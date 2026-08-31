interface InterviewProgressProps {
  turnCount: number;
}

const TOTAL_PIECES = 8;

export function InterviewProgress({ turnCount }: InterviewProgressProps) {
  const filled = Math.min(turnCount, TOTAL_PIECES);
  const active = filled < TOTAL_PIECES ? filled : -1;

  return (
    <div className="interview__progress" aria-label={`Interview progress: ${filled} of ${TOTAL_PIECES} pieces`}>
      <span className="interview__progress-label">Your conversation</span>
      <div className="interview__stage" aria-hidden="true">
        {Array.from({ length: TOTAL_PIECES }, (_, i) => (
          <div
            key={i}
            className={`progress-piece ${
              i < filled ? "progress-piece--filled" : i === active ? "progress-piece--active" : "progress-piece--empty"
            }`}
          />
        ))}
      </div>
    </div>
  );
}