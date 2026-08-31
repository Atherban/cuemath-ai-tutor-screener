import { useNavigate } from "react-router-dom";
import { Button } from "@/components/common/Button";
import { SiteHeader } from "@/components/navigation/SiteHeader";
import { SiteFooter } from "@/components/navigation/SiteFooter";

/**
 * Final thank-you screen shown after the results have been reviewed.
 * "We'll get back to you soon" — no scores are shown here (they live on the
 * evaluation screen).
 */
export function CompletionPage() {
  const navigate = useNavigate();

  const goHome = () => navigate("/");

  return (
    <>
      <SiteHeader />
      <main>
        <div className="completion container">
          <div className="completion__icon" aria-hidden="true">
            ✓
          </div>
          <h1 className="completion__title">Thank you</h1>
          <div className="completion__text">
            <p>
              Your screening conversation is complete and your results have been
              recorded.
            </p>
            <p style={{ marginTop: "var(--space-2)" }}>
              The Cuemath team will get back to you soon about the next steps.
            </p>
          </div>
          <div className="completion__actions">
            <Button size="lg" onClick={goHome}>
              Return Home
            </Button>
          </div>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
