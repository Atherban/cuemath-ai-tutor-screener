/**
 * Typed HTTP API client for the FastAPI backend.
 *
 * Only exposes the endpoints the candidate experience actually needs.
 * Assessment data is intentionally NOT surfaced to the candidate.
 */

import { apiUrl } from "@/lib/config";
import type {
  AssessmentResponse,
  SessionCreateRequest,
  SessionDetailResponse,
  SessionResponse,
} from "@/types/api";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      "We couldn't reach the interview service. Please try again.",
      "NETWORK_ERROR",
      0,
    );
  }

  if (!res.ok) {
    let code = "HTTP_ERROR";
    let message = "Something went wrong. Please try again.";
    try {
      const body = (await res.json()) as { error?: { code?: string; message?: string } };
      if (body.error?.code) code = body.error.code;
      if (body.error?.message) message = body.error.message;
    } catch {
      // Non-JSON error body; fall through to defaults.
    }
    throw new ApiError(message, code, res.status);
  }

  return (await res.json()) as T;
}

/** Create an anonymous interview session. */
export async function createInterviewSession(
  candidateId?: string,
): Promise<SessionResponse> {
  const body: SessionCreateRequest = { candidate_id: candidateId || "anonymous" };
  return request<SessionResponse>("/sessions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Fetch session details + full transcript. */
export async function getInterviewSession(sessionId: string): Promise<SessionDetailResponse> {
  return request<SessionDetailResponse>(`/sessions/${encodeURIComponent(sessionId)}`);
}

/** Fetch the evidence-backed assessment for a completed session. */
export async function getAssessment(sessionId: string): Promise<AssessmentResponse> {
  return request<AssessmentResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/assessment`,
  );
}
