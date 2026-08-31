/**
 * Skeleton loading placeholders for the evaluation screen.
 * Shown while the assessment is being generated; replaced by the real
 * ResultsView once data arrives.
 */
export function ResultsSkeleton() {
  return (
    <div className="skeleton" aria-hidden="true">
      {/* Header card */}
      <div className="skeleton__header">
        <div className="skeleton__block skeleton__block--circle" />
        <div className="skeleton__lines">
          <div className="skeleton__block skeleton__block--tag" />
          <div className="skeleton__block skeleton__block--text" />
          <div className="skeleton__block skeleton__block--text skeleton__block--short" />
        </div>
      </div>

      {/* Chart placeholder */}
      <div className="skeleton__chart">
        <div className="skeleton__block skeleton__block--radar" />
        <div className="skeleton__lines">
          <div className="skeleton__block skeleton__block--text skeleton__block--short" />
          <div className="skeleton__block skeleton__block--text skeleton__block--short" />
        </div>
      </div>

      {/* Dimension cards */}
      <div className="skeleton__grid">
        {Array.from({ length: 5 }).map((_, i) => (
          <div className="skeleton__card" key={i}>
            <div className="skeleton__lines">
              <div className="skeleton__block skeleton__block--title" />
              <div className="skeleton__block skeleton__block--text" />
              <div className="skeleton__block skeleton__block--text skeleton__block--short" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
