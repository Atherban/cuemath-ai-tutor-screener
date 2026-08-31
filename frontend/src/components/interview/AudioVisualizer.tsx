import { useEffect, useRef } from "react";

interface AudioVisualizerProps {
  level: number;
  /** Number of bars in the visualizer. */
  bars?: number;
  /** True when the mic is actively recording. */
  active: boolean;
}

/**
 * Simple live audio level indicator — a row of bars that react to the
 * microphone RMS level. Also serves as a floor indicator when idle.
 */
export function AudioVisualizer({ level, bars = 5, active }: AudioVisualizerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bars = containerRef.current?.querySelectorAll<HTMLElement>(".visualizer__bar");
    if (!bars) return;
    const heights = [0.08, 0.18, 0.35, 0.55, 0.75, 0.9, 1.0];
    const count = bars.length;
    for (let i = 0; i < count; i++) {
      // Each bar responds to a different portion of the level range.
      const threshold = heights[i] ?? 1;
      const s = level >= threshold ? Math.max(0.14, threshold * level * 1.9) : 0.12;
      bars[i].style.transform = `scaleY(${Math.round(s * 100) / 100})`;
    }
  }, [level]);

  return (
    <div className={`visualizer ${active ? "" : "visualizer--idle"}`} ref={containerRef} aria-hidden="true">
      {Array.from({ length: bars }, (_, i) => (
        <div key={i} className="visualizer__bar" />
      ))}
    </div>
  );
}