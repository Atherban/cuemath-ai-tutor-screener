import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/common/Button";
import { SiteHeader } from "@/components/navigation/SiteHeader";
import { SiteFooter } from "@/components/navigation/SiteFooter";
import { AudioVisualizer } from "@/components/interview/AudioVisualizer";
import { useMicrophone } from "@/hooks/useMicrophone";
import { createInterviewSession } from "@/services/api";

type SetupError = "none" | "creating" | "failed";

const MIC_ERROR_MESSAGE: Record<string, string> = {
  "no-device": "We couldn't find a microphone on this device. Please connect one and refresh this page.",
  "in-use": "Your microphone is being used by another application. Close it and try again.",
  "insecure-context":
    "Your browser blocks microphone access on this connection. Open the app over https:// (or http://localhost) and try again.",
  overconstrained:
    "We couldn't start your microphone with the required settings. Please check your system sound input settings and try again.",
  unknown: "We couldn't access your microphone. Please check your system sound settings and try again.",
};

export function InterviewSetupPage() {
  const navigate = useNavigate();
  const [level, setLevel] = useState(0);
  const [setupError, setSetupError] = useState<SetupError>("none");
  const creatingRef = useRef(false);

  const mic = useMicrophone({
    onLevelChange: (l) => setLevel(l),
  });

  const handleTestMic = async () => {
    const granted = await mic.requestMic();
    if (granted) {
      mic.startRecording();
    }
  };

  const handleContinue = async () => {
    if (creatingRef.current) return;
    // Starting the screening is a user gesture — enter fullscreen now so the
    // interview opens in an immersive, distraction-free view.
    if (document.fullscreenEnabled && !document.fullscreenElement) {
      void document.documentElement.requestFullscreen().catch(() => {});
    }
    creatingRef.current = true;
    setSetupError("creating");
    try {
      const session = await createInterviewSession();
      creatingRef.current = false;
      navigate(`/interview/${session.session_id}`);
    } catch {
      creatingRef.current = false;
      setSetupError("failed");
    }
  };

  const micDenied = mic.micState === "denied";
  const micUnavailable = mic.micState === "unavailable";

  const micStatusClass =
    mic.micState === "granted" ? "mic-status--ready" : "mic-status--needed";
  const micStatusText =
    mic.micState === "granted" ? "Microphone Ready" : "Microphone permission required";

  return (
    <>
      <SiteHeader />
      <main>
        <div className="setup container">
          <h1 className="section-title" style={{ marginTop: "0.4em" }}>
            A quick setup for your interview
          </h1>
          <p className="setup__lead">
            A few quick checks before you meet your interviewer.
          </p>

          <ul className="checklist" aria-label="Pre-interview checklist">
            <li>
              <span className="checklist__mark" aria-hidden="true">
                ✓
              </span>
              Find a quiet place
            </li>
            <li>
              <span className="checklist__mark" aria-hidden="true">
                ✓
              </span>
              Make sure your microphone works
            </li>
            <li>
              <span className="checklist__mark" aria-hidden="true">
                ✓
              </span>
              Speak naturally
            </li>
            <li>
              <span className="checklist__mark" aria-hidden="true">
                ✓
              </span>
              Take your time answering
            </li>
          </ul>

          <p className="setup__note">
            The interview takes approximately 10 minutes.
          </p>

          <div style={{ marginTop: "var(--space-5)" }}>
            <div className={`mic-status ${micStatusClass}`} aria-live="polite">
              <span className="mic-status__dot" aria-hidden="true" />
              {micStatusText}
            </div>
          </div>

          <div style={{ marginTop: "var(--space-5)" }}>
            <Button size="lg" onClick={handleTestMic}>
              {mic.micState === "granted" ? "Retest Microphone" : "Test Microphone"}
            </Button>
          </div>

          {mic.micState === "requesting" && (
            <p style={{ marginTop: "var(--space-4)", color: "var(--ink-muted)" }} aria-live="polite">
              Requesting microphone access…
            </p>
          )}

          {micDenied && (
            <div className="notice" role="alert">
              Microphone access is required for the interview. Please allow microphone
              access in your browser and try again.
            </div>
          )}

          {micUnavailable && (
            <div className="notice" role="alert">
              {MIC_ERROR_MESSAGE[mic.micError ?? "unknown"]}
            </div>
          )}

          {mic.micState === "granted" && (
            <div className="mic-test">
              <div className="mic-test__heading">Microphone test</div>
              <div className="mic-test__status">
                {mic.isRecording
                  ? "Speak now — your microphone is working"
                  : "Your microphone is working"}
              </div>
              <div className="mic-test__visual">
                <AudioVisualizer level={level} active={mic.isRecording} bars={7} />
              </div>
              <div className="mic-test__actions">
                <Button
                  variant="secondary"
                  onClick={() => (mic.isRecording ? mic.stopRecording() : mic.startRecording())}
                >
                  {mic.isRecording ? "Stop test" : "Speak to test"}
                </Button>
                <Button size="lg" onClick={handleContinue} disabled={setupError === "creating"}>
                  {setupError === "creating" ? (
                    <>
                      <span className="spinner" aria-hidden="true" /> Starting…
                    </>
                  ) : (
                    "Continue →"
                  )}
                </Button>
              </div>
            </div>
          )}

          {setupError === "failed" && (
            <div className="notice" role="alert">
              Something went wrong while preparing your interview. Please try again.
            </div>
          )}

          {micDenied || micUnavailable ? (
            <div style={{ marginTop: "var(--space-5)", textAlign: "center" }}>
              <Button size="lg" onClick={handleContinue}>
                Continue anyway →
              </Button>
            </div>
          ) : null}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}