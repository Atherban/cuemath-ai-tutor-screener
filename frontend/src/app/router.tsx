import { Routes, Route, Navigate } from "react-router-dom";
import { LandingPage } from "@/pages/LandingPage";
import { InterviewSetupPage } from "@/pages/InterviewSetupPage";
import { InterviewPage } from "@/pages/InterviewPage";
import { EvaluationPage } from "@/pages/EvaluationPage";
import { CompletionPage } from "@/pages/CompletionPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/interview" element={<InterviewSetupPage />} />
      <Route path="/interview/:sessionId" element={<InterviewPage />} />
      <Route path="/interview/:sessionId/evaluation" element={<EvaluationPage />} />
      <Route path="/interview/:sessionId/complete" element={<CompletionPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}