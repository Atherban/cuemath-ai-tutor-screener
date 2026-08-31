import type { DimensionScore } from "@/types/api";

const DIMENSION_ORDER = ["clarity", "simplicity", "patience", "warmth", "fluency"];

const DIMENSION_LABEL: Record<string, string> = {
  clarity: "Clarity",
  simplicity: "Simplicity",
  patience: "Patience",
  warmth: "Warmth",
  fluency: "Fluency",
};

interface RadarChartProps {
  dimensions: Record<string, DimensionScore>;
  /** Height of the SVG in px. */
  size?: number;
}

/**
 * Dependency-free SVG radar chart for the five soft-skill dimensions.
 * Each axis runs 0–10 (the assessment score scale).
 */
export function RadarChart({ dimensions, size = 340 }: RadarChartProps) {
  const scores = DIMENSION_ORDER.map((key) => {
    const dim = dimensions[key];
    return dim ? Math.max(0, Math.min(10, dim.score)) : 0;
  });

  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 52;

  const point = (i: number, value: number) => {
    const angle = (Math.PI * 2 * i) / DIMENSION_ORDER.length - Math.PI / 2;
    const r = (value / 10) * radius;
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)] as const;
  };

  const ringPoints = (level: number) =>
    DIMENSION_ORDER.map((_, i) => point(i, (10 * level) / 4).join(",")).join(" ");

  const labelPoints = DIMENSION_ORDER.map((key, i) => {
    const [x, y] = point(i, 10);
    return { key, x, y };
  });

  const fill = scores
    .map((s, i) => `${point(i, s)[0]},${point(i, s)[1]}`)
    .join(" ");

  return (
    <div className="radar-chart" role="img" aria-label="Soft-skill dimension scores">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background rings */}
        {[1, 2, 3, 4].map((level) => (
          <polygon
            key={level}
            points={ringPoints(level)}
            fill="none"
            stroke="var(--line)"
            strokeWidth="1"
          />
        ))}
        {/* Axes */}
        {labelPoints.map(({ key, x, y }) => (
          <line
            key={key}
            x1={cx}
            y1={cy}
            x2={x}
            y2={y}
            stroke="var(--line)"
            strokeWidth="1"
          />
        ))}
        {/* Data shape */}
        <polygon points={fill} fill="var(--brand-soft)" stroke="var(--brand)" strokeWidth="2" />
        {/* Data points */}
        {scores.map((s, i) => {
          const [x, y] = point(i, s);
          return <circle key={i} cx={x} cy={y} r="3.5" fill="var(--brand)" />;
        })}
        {/* Labels */}
        {labelPoints.map(({ key, x, y }) => (
          <text
            key={key}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="radar-chart__label"
          >
            {DIMENSION_LABEL[key] ?? key}
          </text>
        ))}
      </svg>
    </div>
  );
}
