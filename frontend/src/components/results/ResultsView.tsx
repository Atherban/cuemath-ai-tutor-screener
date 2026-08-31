import type { CSSProperties } from "react";
import type { AssessmentResult, DimensionScore, Recommendation } from "@/types/api";
import { RadarChart } from "./RadarChart";

/**
 * Independent, presentational results view.
 *
 * It receives an `AssessmentResult` and renders it — nothing else. It has no
 * knowledge of the interview flow, WebSocket, or routing, so it can be reused
 * or swapped without affecting anything else.
 */
interface ResultsViewProps {
  assessment: AssessmentResult;
}

const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  STRONG_PROCEED: "Strong proceed",
  PROCEED: "Proceed",
  BORDERLINE: "Borderline",
  DO_NOT_PROCEED: "Do not proceed",
};

const DIMENSION_LABEL: Record<string, string> = {
  clarity: "Communication clarity",
  simplicity: "Simplicity",
  patience: "Patience",
  warmth: "Warmth / Empathy",
  fluency: "English fluency",
};

function scoreTone(score: number): string {
  if (score >= 8) return "score--high";
  if (score >= 6) return "score--mid";
  return "score--low";
}

export function ResultsView({ assessment }: ResultsViewProps) {
  const dims = assessment.dimensions ?? {};

  return (
    <div className="results">
      <header className="results__header">
        <div className={`results__score ${scoreTone(assessment.overall_score)}`}>
          <span className="results__score-value">{assessment.overall_score.toFixed(1)}</span>
          <span className="results__score-max">/ 10</span>
        </div>
        <div className="results__headline">
          <span className={`results__recommendation results__recommendation--${assessment.recommendation.toLowerCase()}`}>
            {RECOMMENDATION_LABEL[assessment.recommendation] ?? assessment.recommendation}
          </span>
          <p className="results__summary">{assessment.summary}</p>
        </div>
      </header>

      {/* Visual overview of the five soft-skill dimensions */}
      <section className="results__chart-section">
        <h2 className="results__section-title">Soft-skill breakdown</h2>
        <div className="results__chart-layout">
          <RadarChart dimensions={dims} />
          <div className="results__chart-legend">
            {Object.entries(dims).map(([key, dim]) => (
              <div key={key} className="results__legend-row">
                <span className="results__legend-dot" style={{ "--c": "var(--brand)" } as CSSProperties} />
                <span className="results__legend-label">{DIMENSION_LABEL[key] ?? key}</span>
                <span className={`results__legend-score ${scoreTone(dim.score)}`}>
                  {dim.score.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="results__dimensions">
        {Object.entries(dims).map(([key, dim]) => (
          <DimensionCard key={key} label={DIMENSION_LABEL[key] ?? key} dim={dim} />
        ))}
      </div>

      {(assessment.key_strengths.length > 0 || assessment.key_concerns.length > 0) && (
        <footer className="results__footer">
          {assessment.key_strengths.length > 0 && (
            <div className="results__block results__block--strengths">
              <h3 className="results__block-title">Key strengths</h3>
              <ul>
                {assessment.key_strengths.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {assessment.key_concerns.length > 0 && (
            <div className="results__block results__block--concerns">
              <h3 className="results__block-title">Key concerns</h3>
              <ul>
                {assessment.key_concerns.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </footer>
      )}
    </div>
  );
}

function DimensionCard({ label, dim }: { label: string; dim: DimensionScore }) {
  const insufficient = dim.evidence_status === "INSUFFICIENT";
  return (
    <div className="results__dimension">
      <div className="results__dimension-head">
        <span className="results__dimension-label">{label}</span>
        <span className={`results__dimension-score ${scoreTone(dim.score)}`}>
          {dim.score.toFixed(1)}
        </span>
      </div>
      <p className="results__dimension-summary">{dim.summary}</p>

      {dim.strengths.length > 0 && (
        <ul className="results__dimension-tags results__dimension-tags--good">
          {dim.strengths.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}
      {dim.concerns.length > 0 && (
        <ul className="results__dimension-tags results__dimension-tags--bad">
          {dim.concerns.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}

      {insufficient ? (
        <p className="results__dimension-evidence results__dimension-evidence--insufficient">
          Insufficient evidence for this dimension.
        </p>
      ) : (
        dim.evidence.length > 0 && (
          <ul className="results__dimension-evidence">
            {dim.evidence.slice(0, 2).map((e, i) => (
              <li key={i}>
                <blockquote>“{e.quote}”</blockquote>
                <span className="results__dimension-reason">{e.reason}</span>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}
