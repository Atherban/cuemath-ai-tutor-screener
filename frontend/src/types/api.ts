/**
 * Types matching the backend REST contracts exactly.
 *
 * Source of truth: backend `app/schemas/*.py` and `app/models/*.py`.
 */

/** Mirrors backend `SessionStatus`. */
export type SessionStatus =
  | "CREATED"
  | "READY"
  | "IN_PROGRESS"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

/** Mirrors backend `AssessmentStatus`. */
export type AssessmentStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED";

/** Body of `POST /sessions`. */
export interface SessionCreateRequest {
  candidate_id?: string;
}

/** Response of `POST /sessions` and `GET /sessions/{id}` (base fields). */
export interface SessionResponse {
  session_id: string;
  candidate_id: string;
  status: SessionStatus;
  started_at: string | null;
  ended_at: string | null;
  current_stage: string | null;
  turn_count: number;
  short_answer_count: number;
  long_answer_count: number;
  topics_covered: string[];
  assessment_status: AssessmentStatus;
}

/** Transcript entry from `GET /sessions/{id}`. */
export interface TranscriptEntry {
  role: string;
  text: string;
  stage: string | null;
  timestamp: string;
}

/** Response of `GET /sessions/{id}`. */
export interface SessionDetailResponse extends SessionResponse {
  conversation_history: TranscriptEntry[];
}

/** Response of `POST /sessions/{id}/complete`. */
export interface SessionCompleteResponse {
  session_id: string;
  status: SessionStatus;
  message: string;
}

/** Mirrors backend `Recommendation`. */
export type Recommendation =
  | "STRONG_PROCEED"
  | "PROCEED"
  | "BORDERLINE"
  | "DO_NOT_PROCEED";

/** Mirrors backend `EvidenceItem`. */
export interface EvidenceItem {
  quote: string;
  reason: string;
}

/** Mirrors backend `DimensionScore`. */
export interface DimensionScore {
  score: number;
  confidence: number;
  summary: string;
  strengths: string[];
  concerns: string[];
  evidence: EvidenceItem[];
  evidence_status: string;
}

/** Mirrors backend `AssessmentResult`. */
export interface AssessmentResult {
  overall_score: number;
  recommendation: Recommendation;
  summary: string;
  dimensions: Record<string, DimensionScore>;
  key_strengths: string[];
  key_concerns: string[];
  confidence: number;
  fairness_note: string | null;
}

/** Response of `GET /sessions/{id}/assessment`. */
export interface AssessmentResponse {
  session_id: string;
  assessment: AssessmentResult;
}

/** Standard error body returned by the backend for REST and WS. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}
