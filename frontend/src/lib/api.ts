import type {
  DatasetDocument,
  EvaluationApiResult,
  PolicyVersion,
  ReviewApiResult,
  WorkspaceId,
} from "../types";
import { isEvaluationApiResult, isReviewApiResult } from "./assessment";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export const LIVE_EVALUATION_TIMEOUT_MS = 12 * 60 * 1000;

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

function detailMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item),
        )
        .join("; ");
    }
  }
  if (status === 404) return "The evaluation was not found on the server.";
  if (status === 429) return "The model rate limit was reached. Try again shortly.";
  if (status >= 500) return "The compliance API failed.";
  return `The compliance API returned HTTP ${status}.`;
}

export async function createLiveEvaluation(
  policyVersion: PolicyVersion,
  signal?: AbortSignal,
): Promise<EvaluationApiResult> {
  let response: Response;
  try {
    response = await fetch(apiUrl("/compliance/evaluations"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        policy_version: policyVersion,
        evaluation_mode: "auto",
      }),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "The assessment timed out or was cancelled.",
      );
    }
    throw new ApiError(
      "Could not reach the assessment service. Confirm it is running, then try again.",
    );
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError(detailMessage(payload, response.status), response.status);
  }
  if (!isEvaluationApiResult(payload)) {
    throw new ApiError(
      "The API returned a response that did not match the evaluation schema.",
    );
  }
  return payload;
}

export async function fetchWorkspaceDocuments(
  workspace: Exclude<WorkspaceId, "security">,
): Promise<DatasetDocument[]> {
  let response: Response;
  try {
    response = await fetch(apiUrl(`/workspaces/${workspace}/documents`));
  } catch {
    throw new ApiError(
      "Could not reach the FastAPI backend to load workspace documents.",
    );
  }
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    throw new ApiError(detailMessage(payload, response.status), response.status);
  }
  if (!payload || typeof payload !== "object" || !("documents" in payload)) {
    throw new ApiError("The API returned an unexpected documents payload.");
  }
  return (payload as { documents: DatasetDocument[] }).documents;
}

export async function createWorkspaceReview(
  workspace: Exclude<WorkspaceId, "security">,
  signal?: AbortSignal,
): Promise<ReviewApiResult> {
  let response: Response;
  try {
    response = await fetch(apiUrl(`/workspaces/${workspace}/reviews`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The review timed out or was cancelled.");
    }
    throw new ApiError(
      "Could not reach the FastAPI backend. Confirm it is running, then retry.",
    );
  }
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    throw new ApiError(detailMessage(payload, response.status), response.status);
  }
  if (!isReviewApiResult(payload)) {
    throw new ApiError("The API returned a response that did not match the review schema.");
  }
  return payload;
}
