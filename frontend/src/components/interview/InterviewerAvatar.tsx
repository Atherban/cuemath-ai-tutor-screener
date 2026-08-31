interface InterviewerAvatarProps {
  speaking: boolean;
}

const PIECE_PATH =
  "M 10,10 L 90,10 L 90,38 C 102,40 102,60 90,62 L 90,90 L 10,90 L 10,62 C -2,60 -2,40 10,38 L 10,10 Z";

export function InterviewerAvatar({ speaking }: InterviewerAvatarProps) {
  return (
    <div className="interviewer__avatar" role="img" aria-label="Interviewer">
      <div className={`avatar${speaking ? " avatar--speaking" : ""}`}>
        <div className="avatar__ring" aria-hidden="true" />
        <div className="avatar__piece" aria-hidden="true">
          <svg className="avatar__face" viewBox="0 0 40 30" aria-hidden="true">
            <rect x="2" y="3" width="36" height="24" rx="4" fill="#fbf6ec" stroke="#2b2417" strokeWidth="1.6" />
            <g className="avatar__brows">
              <path d="M8 9.5 l7 -3" stroke="#0e2b72" strokeWidth="2" strokeLinecap="round" />
              <path d="M25 9.5 l7 3" stroke="#0e2b72" strokeWidth="2" strokeLinecap="round" />
            </g>
            <g className="avatar__eyes">
              {speaking ? (
                <path d="M10 16 q3 -3 6 0 M24 16 q3 -3 6 0" stroke="#0e2b72" strokeWidth="2" fill="none" strokeLinecap="round" />
              ) : (
                <>
                  <circle cx="13" cy="17" r="2.4" fill="#0e2b72" />
                  <circle cx="27" cy="17" r="2.4" fill="#0e2b72" />
                </>
              )}
            </g>
            <path d="M12 23 c 4 3.5 12 3.5 16 0" stroke="#8a6d00" strokeWidth="2.2" fill="none" strokeLinecap="round" />
          </svg>
        </div>
        <span className="avatar__knob" aria-hidden="true" />
      </div>
    </div>
  );
}

export function MiniAvatar() {
  return (
    <svg className="chat__avatar" viewBox="0 0 100 100" aria-hidden="true">
      <path
        d={PIECE_PATH}
        fill="#1e4fd8" stroke="#2b2417" strokeWidth="3"
      />
      <rect x="30" y="30" width="40" height="40" rx="6" fill="#fbf6ec" stroke="#2b2417" strokeWidth="2.5" />
      <circle cx="42" cy="45" r="4" fill="#0e2b72" />
      <circle cx="58" cy="45" r="4" fill="#0e2b72" />
      <path d="M 38 62 q 12 8 24 0" stroke="#8a6d00" strokeWidth="3.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}