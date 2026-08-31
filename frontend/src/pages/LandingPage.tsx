import { useNavigate } from "react-router-dom";
import { Button } from "@/components/common/Button";
import { SiteHeader } from "@/components/navigation/SiteHeader";
import { SiteFooter } from "@/components/navigation/SiteFooter";
import { PuzzleScene } from "@/components/common/PuzzleScene";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <>
      <SiteHeader />
      <main>
        {/* ── Hero: the unfinished picture invites ───────────────────────── */}
        <section className="hero section">
          <div className="hero__inner container">
            <div>
              <h1 className="hero__title">
                Help children discover <em>the joy</em> of mathematics.
              </h1>
              <p className="hero__subtitle">
                A short, natural voice conversation to understand how you teach and connect
                with students. No preparation needed — just speak like you would in a classroom.
              </p>
              <div className="hero__cta">
                <Button size="lg" onClick={() => navigate("/interview")}>
                  Start Screening →
                </Button>
              </div>
              <div className="hero__meta">
                <span className="hero__meta-item">
                  <span className="hero__meta-dot" style={{ background: "var(--flat-sky)" }} aria-hidden="true" />
                  ~10 minute voice interview
                </span>
                <span className="hero__meta-item">
                  <span className="hero__meta-dot" style={{ background: "var(--flat-grass)" }} aria-hidden="true" />
                  Quiet place recommended
                </span>
                <span className="hero__meta-item">
                  <span className="hero__meta-dot" style={{ background: "var(--flat-coral)" }} aria-hidden="true" />
                  No preparation needed
                </span>
              </div>
            </div>

            <div className="hero__board-wrap">
              <div>
                <PuzzleScene placed={4} width="min(320px, 82vw)" />
                <p className="puzzle-board__caption">
                  Your interview, one piece at a time.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── What to expect — three interlocking pieces ─────────────────── */}
        <section className="section" style={{ background: "var(--surface-soft)" }}>
          <div className="container">
            <h2 className="section-title" style={{ maxWidth: "18ch" }}>
              A natural conversation about teaching
            </h2>

            <div className="tile-chain">
              <div className="tile">
                <div className="tile__icon" aria-hidden="true">💬</div>
                <div className="tile__title">Speak naturally</div>
                <div className="tile__text">
                  There are no wrong answers. The conversation helps us understand your
                  approach to tutoring — just talk the way you teach.
                </div>
              </div>
              <div className="tile">
                <div className="tile__icon" aria-hidden="true">🧮</div>
                <div className="tile__title">Think like a tutor</div>
                <div className="tile__text">
                  Share how you'd explain a concept, support a struggling student, and help
                  a child feel confident with numbers.
                </div>
              </div>
              <div className="tile">
                <div className="tile__icon" aria-hidden="true">🌟</div>
                <div className="tile__title">Be yourself</div>
                <div className="tile__text">
                  The best tutors connect authentically with students. We'd love to hear
                  your genuine voice — no script required.
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── How it works — a guided, stepped path ──────────────────────── */}
        <section className="section">
          <div className="container">
            <h2 className="section-title" style={{ maxWidth: "18ch" }}>
              A simple, guided experience
            </h2>

            <div className="steps">
              <div className="step">
                <div className="step__piece step__piece--1" aria-hidden="true">1</div>
                <div className="step__title">Meet your interviewer</div>
                <div className="step__text">
                  You'll be introduced to an AI interviewer who guides the conversation from
                  start to finish.
                </div>
              </div>
              <div className="step">
                <div className="step__piece step__piece--2" aria-hidden="true">2</div>
                <div className="step__title">Have a short conversation</div>
                <div className="step__text">
                  Answer a few questions about your teaching approach. Speak naturally —
                  treat it like a real conversation.
                </div>
              </div>
              <div className="step">
                <div className="step__piece step__piece--3" aria-hidden="true">3</div>
                <div className="step__title">Share how you teach</div>
                <div className="step__text">
                  You'll be asked to describe how you explain concepts and support students
                  who need extra help.
                </div>
              </div>
            </div>

            <div style={{ marginTop: "var(--space-7)", textAlign: "center" }}>
              <Button size="lg" onClick={() => navigate("/interview")}>
                Start Screening →
              </Button>
            </div>
          </div>
        </section>

        {/* ── Closing ────────────────────────────────────────────────────── */}
        <section className="section" style={{ paddingTop: 0 }}>
          <div className="container">
            <div className="closing">
              <h2 className="closing__title">Ready to begin?</h2>
              <p className="closing__text">
                You'll need a microphone and about 10 minutes in a quiet space.
                Take your time with each question.
              </p>
              <div style={{ marginTop: "var(--space-5)" }}>
                <Button size="lg" variant="primary" onClick={() => navigate("/interview")}>
                  Start Screening →
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
