import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/common/Button";
import { ResultsSkeleton } from "@/components/results/ResultsSkeleton";
import { ResultsView } from "@/components/results/ResultsView";
import { SiteHeader } from "@/components/navigation/SiteHeader";
import { SiteFooter } from "@/components/navigation/SiteFooter";
import { ApiError, getAssessment } from "@/services/api";
import type { AssessmentResult } from "@/types/api";

const POLL_INTERVAL_MS = 2000;
// NVIDIA's gpt-oss-20b assessment can take 30–90+ seconds, so we poll for
// up to 10 minutes (300 attempts × 2 s) to avoid giving up too early.
const MAX_POLL_ATTEMPTS = 300;

type LoadState = "loading" | "ready" | "unavailable";

/**
 * Evaluation screen: shows a loading animation while the backend generates the
 * assessment, then renders the results via the isolated `ResultsView`.
 */
export function EvaluationPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [assessment, setAssessment] = useState<AssessmentResult | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const cancelledRef = useRef(false);
  // Allow the user to reset the unavailable state and retry.
  const [retryKey, setRetryKey] = useState(0);

  const startPolling = useCallback(() => {
    cancelledRef.current = false;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      if (cancelledRef.current || !sessionId) return;
      try {
        const res = await getAssessment(sessionId);
        if (cancelledRef.current) return;
        setAssessment(res.assessment);
        setLoadState("ready");
      } catch (err) {
        if (cancelledRef.current) return;
        if (
          err instanceof ApiError &&
          err.code === "ASSESSMENT_NOT_READY" &&
          attempts < MAX_POLL_ATTEMPTS
        ) {
          attempts += 1;
          timer = setTimeout(() => void poll(), POLL_INTERVAL_MS);
          return;
        }
        setLoadState("unavailable");
      }
    };

    void poll();
    return () => {
      cancelledRef.current = true;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId]);

  useEffect(() => {
    const cleanup = startPolling();
    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, retryKey]);

  const retry = useCallback(() => {
    setLoadState("loading");
    setRetryKey((k) => k + 1);
  }, []);

  const goToThanks = () => navigate(`/interview/${sessionId}/complete`, { replace: true });

  return (
    <>
      <SiteHeader />
      <main>
        <div className="evaluation container">
          <h1 className="evaluation__title">Your screening results</h1>

          {loadState === "loading" && (
            <div className="evaluation__loading" role="status" aria-live="polite">
              <p className="evaluation__waiting-label">Your screening conversation is complete.</p>
              <p className="evaluation__waiting-sub">Please wait while we prepare your results…</p>
              <ResultsSkeleton />
            </div>
          )}

          {loadState === "ready" && assessment && (
            <>
              <ResultsView assessment={assessment} />
              <div className="evaluation__actions">
                <Button size="lg" onClick={goToThanks}>
                  Continue
                </Button>
              </div>
            </>
          )}

          {loadState === "unavailable" && (
            <div className="evaluation__loading">
              <p>
                We couldn’t load your results right now. The evaluation is still
                being generated — it can take a minute or two.
              </p>
              <div className="evaluation__actions">
                <Button size="lg" onClick={retry}>
                  Try again
                </Button>
                <Button variant="ghost" size="lg" onClick={goToThanks}>
                  Continue anyway
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
