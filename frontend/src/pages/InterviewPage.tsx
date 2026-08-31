import { useNavigate, useParams } from "react-router-dom";
import { useState, useRef, useCallback, useEffect } from "react";
import { SiteHeader } from "@/components/navigation/SiteHeader";
import { InterviewStatus } from "@/components/interview/InterviewStatus";
import { Transcript } from "@/components/interview/Transcript";
import { InterviewProgress } from "@/components/interview/InterviewProgress";
import { EndInterviewButton } from "@/components/interview/EndInterviewButton";
import { Button } from "@/components/common/Button";
import { useInterview } from "@/hooks/useInterview";

function MicIcon({ recording }: { recording: boolean }) {
  if (recording) {
    return (
      <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
        <rect x="6" y="6" width="12" height="12" rx="2" />
      </svg>
    );
  }
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="17" x2="12" y2="22" />
    </svg>
  );
}

export function InterviewPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();

  const exitFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      void document.exitFullscreen().catch(() => {});
    }
  }, []);

  const interview = useInterview({
    sessionId,
    onCompleted: (id) => {
      exitFullscreen();
      navigate(`/interview/${id}/evaluation`, { replace: true });
    },
  });

  // Leave fullscreen if the user unmounts mid-interview (e.g. error → home).
  useEffect(() => {
    return () => exitFullscreen();
  }, [exitFullscreen]);

  const {
    phase,
    transcript,
    audioLevel,
    notice,
    error,
    silencePrompt,
    countdown,
    liveTranscript,
    interviewerPlaying,
    micState,
    sendText,
    startSpeaking,
    skipTimer,
    isRecording,
    finishAnswer,
    endInterview,
    reconnect,
  } = interview;

  const [textInput, setTextInput] = useState("");
  const textInputRef = useRef<HTMLInputElement>(null);

  // Unlock audio on the first user interaction anywhere on the page. Browsers
  // (Chrome/Brave) block AudioContext playback until a user gesture.
  // Also request fullscreen on that first interaction.
  const unlockOnceRef = useRef(false);
  const unlockAudioOnce = useCallback(() => {
    if (unlockOnceRef.current) return;
    unlockOnceRef.current = true;
    interview.unlockAudio();
    if (document.fullscreenEnabled && !document.fullscreenElement) {
      void document.documentElement.requestFullscreen().catch(() => {});
    }
  }, [interview]);

  const handleSendText = useCallback(() => {
    const sent = sendText(textInput);
    if (sent) setTextInput("");
  }, [textInput, sendText]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendText();
      }
    },
    [handleSendText]
  );

  // Communicate the current status to assistive tech.
  const statusLabel =
    phase === "listening"
      ? isRecording
        ? "Recording — press Done answering when you're finished"
        : countdown !== null && countdown > 0
          ? "Thinking time — press Skip timer or wait"
          : "Listening — press Start speaking, or type your answer"
      : phase;

  const micBlocked = micState === "denied" || micState === "unavailable";
  const endDisabled =
    phase === "connecting" || phase === "processing" || phase === "completed" || phase === "error";

  const thinking = countdown !== null && countdown > 0;
  // Answer controls stay disabled until the agent has finished speaking and
  // is listening for the candidate.
  const agentBusy = interviewerPlaying || phase === "speaking" || phase === "processing" || phase === "connecting";
  const canAnswer = phase === "listening" && !agentBusy;

  return (
    <>
      <SiteHeader />
      <main onClick={unlockAudioOnce} className="convo-main">
        <div className="convo">
          {/* Top rail — progress, status, end */}
          <header className="convo__top">
            <InterviewProgress turnCount={transcript.filter((t) => t.role === "candidate").length} />
            <div className="convo__top-right">
              <InterviewStatus phase={phase} candidateSpeaking={isRecording} />
              <EndInterviewButton onClick={endInterview} disabled={endDisabled} />
            </div>
          </header>

          {/* Conversation body — the transcript fills the screen */}
          <div className="convo__body">
            {error ? (
              <div className="error-panel" role="alert">
                <div className="error-panel__title">We lost the connection</div>
                <p className="error-panel__text">
                  {error.message}. {error.recoverable ? "Your interview hasn't been submitted." : ""}
                </p>
                <div className="error-panel__actions">
                  {error.recoverable && <Button onClick={reconnect}>Reconnect</Button>}
                  <Button variant="ghost" onClick={() => navigate("/")}>
                    Return Home
                  </Button>
                </div>
              </div>
            ) : (
              <Transcript
                items={transcript}
                phase={phase}
                interviewerSpeaking={interviewerPlaying}
                isRecording={isRecording}
                liveTranscript={liveTranscript}
                audioLevel={audioLevel}
              />
            )}
          </div>

          {/* Bottom dock — the control bar */}
          {!error && (
            <footer className="convo__dock">
              {thinking && (
                <div className="countdown" aria-live="polite">
                  <span className="countdown__value">{countdown}</span>
                  <span className="countdown__label">s to think — then you can answer</span>
                  <button className="countdown__skip" onClick={skipTimer}>
                    Skip
                  </button>
                </div>
              )}

              {silencePrompt && (
                <div className="silence-prompt" aria-live="polite">
                  {silencePrompt}
                </div>
              )}

              {notice && (
                <div className="notice" role="status">
                  {notice}
                </div>
              )}

              {micBlocked && (
                <div className="notice" role="alert">
                  Microphone access is required to speak. You can also type your answers.
                </div>
              )}

              <div className="convo__controls">
                <button
                  type="button"
                  className={`mic-btn${isRecording ? " mic-btn--recording" : ""}`}
                  onClick={() => {
                    if (isRecording) {
                      finishAnswer();
                    } else {
                      void startSpeaking();
                    }
                  }}
                  disabled={!isRecording && !canAnswer}
                  aria-label={isRecording ? "Done answering" : "Start speaking"}
                >
                  <MicIcon recording={isRecording} />
                </button>

                <input
                  ref={textInputRef}
                  type="text"
                  className="convo__input"
                  placeholder={canAnswer ? "Type your answer…" : "The interviewer is speaking…"}
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={!canAnswer}
                />
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleSendText}
                  disabled={!canAnswer || !textInput.trim()}
                >
                  Send
                </Button>
              </div>

              <p className="convo__hint">
                {canAnswer
                  ? "Tap the mic to answer by voice, or type your answer below"
                  : "The interviewer is speaking — sit back and listen"}
              </p>
            </footer>
          )}
        </div>

        <p className="hidden-visually" aria-live="polite">
          {statusLabel}
        </p>
      </main>
    </>
  );
}