import type { ReactNode } from "react";

interface PuzzleSceneProps {
  /** How many pieces are placed (0–9). The rest render as empty slots. */
  placed: number;
  /** Board size scale factor, e.g. 1 = normal, 0.8 = smaller. */
  scale?: number;
  /** CSS max-width for the board (e.g. "320px"). */
  width?: string;
  className?: string;
}

const PIECES: { color: string; mark: ReactNode }[] = [
  {
    color: "var(--flat-sky)",
    mark: (
      <svg viewBox="0 0 40 40" width="60%" height="60%" aria-hidden="true">
        <circle cx="20" cy="20" r="7" fill="#fff" opacity="0.95" />
        <g stroke="#fff" strokeWidth="3" strokeLinecap="round">
          <line x1="20" y1="2" x2="20" y2="10" />
          <line x1="20" y1="30" x2="20" y2="38" />
          <line x1="2" y1="20" x2="10" y2="20" />
          <line x1="30" y1="20" x2="38" y2="20" />
        </g>
      </svg>
    ),
  },
  {
    color: "var(--flat-coral)",
    mark: (
      <svg viewBox="0 0 40 40" width="60%" height="60%" aria-hidden="true">
        <circle cx="20" cy="20" r="11" fill="#fff" opacity="0.95" />
        <path d="M13 20l5 5 9-10" stroke="var(--flat-coral)" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    color: "var(--flat-grass)",
    mark: (
      <svg viewBox="0 0 40 40" width="62%" height="62%" aria-hidden="true">
        <path d="M10 30V18c0-5 4-8 10-8s10 3 10 8v12" fill="#fff" opacity="0.95" />
        <path d="M14 26c3-2 6-2 8 0M22 26c2-2 5-2 7 0" stroke="var(--flat-grass)" strokeWidth="2" fill="none" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    color: "var(--flat-lilac)",
    mark: (
      <svg viewBox="0 0 40 40" width="60%" height="60%" aria-hidden="true">
        <text x="20" y="28" textAnchor="middle" fontSize="22" fontWeight="800" fill="#fff" fontFamily="Bricolage Grotesque, sans-serif">
          1+1
        </text>
      </svg>
    ),
  },
  {
    color: "var(--brand)",
    mark: (
      <svg viewBox="0 0 40 40" width="62%" height="62%" aria-hidden="true">
        <path d="M20 6l4 8.2 9 .9-6.8 6 2 9L20 26.6l-8.2 4.5 2-9-6.8-6 9-.9z" fill="var(--ink)" />
      </svg>
    ),
  },
  {
    color: "var(--flat-sky)",
    mark: (
      <svg viewBox="0 0 40 40" width="58%" height="58%" aria-hidden="true">
        <circle cx="20" cy="20" r="9" fill="#fff" opacity="0.95" />
        <circle cx="16.5" cy="19" r="1.6" fill="#2b2417" />
        <circle cx="23.5" cy="19" r="1.6" fill="#2b2417" />
        <path d="M14 23c2 3 10 3 12 0" stroke="#2b2417" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    color: "var(--flat-coral)",
    mark: (
      <svg viewBox="0 0 40 40" width="62%" height="62%" aria-hidden="true">
        <path d="M20 8c-3-3.5-9-2-9 2.5 0 6 9 11 9 11s9-5 9-11c0-4.5-6-6-9-2.5z" fill="#fff" />
      </svg>
    ),
  },
  {
    color: "var(--flat-grass)",
    mark: (
      <svg viewBox="0 0 40 40" width="60%" height="60%" aria-hidden="true">
        <rect x="10" y="18" width="20" height="13" rx="2" fill="#fff" opacity="0.95" transform="rotate(-8 20 24)" />
        <path d="M14 15l3-4M26 15l-3-4" stroke="#fff" strokeWidth="2.6" fill="none" strokeLinecap="round" />
        <path d="M17 24h6M17 27h6" stroke="var(--flat-grass)" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    color: "var(--flat-lilac)",
    mark: (
      <svg viewBox="0 0 40 40" width="62%" height="62%" aria-hidden="true">
        <circle cx="20" cy="20" r="10" fill="#fff" opacity="0.95" />
        <text x="20" y="25" textAnchor="middle" fontSize="15" fontWeight="800" fill="#ac8ce0" fontFamily="Bricolage Grotesque, sans-serif">
          =
        </text>
      </svg>
    ),
  },
];

/**
 * The puzzle scene: a framed 3×3 board of jigsaw pieces. Pieces place in
 * reading order; the rest render as dashed empty slots. When fully placed it
 * is "the conversation" — a warm little tableau of math's joys.
 */
export function PuzzleScene({ placed, scale = 1, width = "300px", className = "" }: PuzzleSceneProps) {
  const shown = Math.max(0, Math.min(placed, PIECES.length));

  return (
    <div
      className={`puzzle-board ${className}`}
      style={{ width, transform: `rotate(-1.5deg) scale(${scale})` }}
      role="img"
      aria-label="A jigsaw of math discoveries, being assembled one piece at a time"
    >
      <div className="puzzle-board__grid">
        {PIECES.map((piece, i) => (
          <div className="puzzle-board__tile" key={i}>
            <div className={`piece ${i < shown ? "" : "piece--slot"}`} style={i < shown ? { background: piece.color } : undefined}>
              {i < shown && piece.mark}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
