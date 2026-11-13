import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { EvaluationApiResult, Requirement } from "../types";
import {
  displayStatusFor,
  formatDuration,
  isEvaluationApiResult,
  mapLiveResult,
  mapReviewResult,
  mapSampleResult,
  methodLabel,
  sourceLabel,
  summarizeFindings,
} from "./assessment.ts";
import type { ReviewApiResult } from "../types.ts";

const livePayload: EvaluationApiResult = {
  id: "eval-1",
  policy_version: "v1",
  source_document: "security_policy_v1.txt",
  evaluation_mode: "rag",
  requested_mode: "auto",
  fallback_used: false,
  retrieval_ready: true,
  model: "gpt-4o-mini",
  duration_ms: 125000,
  findings: [
    {
      requirement_id: "AC-03",
      requirement_title: "Termination access revocation",
      requirement_text: "AC-03 must revoke access within 24 hours.",
      category: "access_control",
      classification: "contradicted",
      explanation: "Policy allows 30 days.",
      supporting_quote: "IT will disable the person’s accounts within thirty (30) days",
      source_document: "security_policy_v1.txt",
      evidence_verified: true,
      evidence_verification: "verified",
      needs_review: false,
      evaluation_state: "completed",
      uncertainty_note: null,
    },
    {
      requirement_id: "AUTH-05",
      requirement_title: "Password history",
      requirement_text: "AUTH-05 password history.",
      category: "authentication",
      classification: "satisfied",
      explanation: "Invented quote.",
      supporting_quote: "This quote is not in the policy.",
      source_document: "security_policy_v1.txt",
      evidence_verified: false,
      evidence_verification: "unverified",
      needs_review: true,
      evaluation_state: "needs_review",
      uncertainty_note: "Supporting quote was not found in the original policy text.",
    },
    {
      requirement_id: "DP-03",
      requirement_title: "Database logging",
      requirement_text: "DP-03 logging.",
      category: "data_protection",
      classification: null,
      explanation: "The model did not return a usable classification.",
      supporting_quote: null,
      source_document: "security_policy_v1.txt",
      evidence_verified: false,
      evidence_verification: "missing",
      needs_review: true,
      evaluation_state: "failed",
      uncertainty_note: "timeout",
    },
  ],
};

describe("live result mapping", () => {
  it("keeps sample and live runs as separate kinds", () => {
    const live = mapLiveResult(livePayload);
    assert.equal(live.kind, "live");
    assert.equal(live.evaluationId, "eval-1");
    assert.equal(live.findings[0].displayStatus, "contradicted");
    assert.equal(live.evaluationMode, "rag");
    assert.equal(live.requestedMode, "auto");
    assert.equal(live.fallbackUsed, false);
    assert.equal(live.durationMs, 125000);
    assert.equal(sourceLabel(live.kind), "Document assessment");
    assert.equal(methodLabel(live.evaluationMode), "Retrieved source passages");
    assert.equal(formatDuration(live.durationMs), "2m 5s");
  });

  it("does not treat unverified quotes as verified evidence", () => {
    const live = mapLiveResult(livePayload);
    const unverified = live.findings.find((item) => item.id === "AUTH-05");
    assert.equal(unverified?.evidenceVerified, false);
    assert.equal(unverified?.evidenceVerification, "unverified");
    assert.equal(unverified?.displayStatus, "needs_review");
    assert.equal(unverified?.classification, "satisfied");
  });

  it("maps failed evaluations to Evaluation failed, not Missing", () => {
    const live = mapLiveResult(livePayload);
    const failed = live.findings.find((item) => item.id === "DP-03");
    assert.equal(failed?.displayStatus, "failed");
    assert.equal(failed?.classification, null);
    assert.notEqual(failed?.displayStatus, "missing");
  });
});

describe("summary counts", () => {
  it("excludes needs-review and failed rows from the four status totals", () => {
    const summary = mapLiveResult(livePayload).summary;
    assert.equal(summary.total, 3);
    assert.equal(summary.statusCounts.contradicted, 1);
    assert.equal(summary.statusCounts.satisfied, 0);
    assert.equal(summary.statusCounts.missing, 0);
    assert.equal(summary.needsReview, 2);
    assert.equal(summary.failed, 1);
    assert.equal(summary.verifiedQuotes, 1);
  });

  it("counts all sample rows as completed classifications", () => {
    const requirements: Requirement[] = [
      {
        id: "AC-01",
        title: "Privileged MFA",
        category: "access_control",
        categoryLabel: "Access Control",
        sourceFile: "access_control_standard.txt",
        fullText: "AC-01",
        findings: {
          v1: { status: "satisfied", reason: "ok", evidence: "quote" },
          v2: { status: "satisfied", reason: "ok", evidence: "quote" },
        },
      },
      {
        id: "AUTH-05",
        title: "History",
        category: "authentication",
        categoryLabel: "Authentication",
        sourceFile: "authentication_standard.txt",
        fullText: "AUTH-05",
        findings: {
          v1: { status: "missing", reason: "silent", evidence: null },
          v2: { status: "satisfied", reason: "ok", evidence: "quote" },
        },
      },
    ];
    const sample = mapSampleResult(requirements, "v1");
    assert.equal(sample.kind, "sample");
    assert.equal(sample.evaluationId, null);
    assert.equal(sample.summary.statusCounts.satisfied, 1);
    assert.equal(sample.summary.statusCounts.missing, 1);
    assert.equal(sample.summary.needsReview, 0);
    assert.equal(sourceLabel(sample.kind), "Sample results");
  });
});

describe("display status", () => {
  it("prefers failed over a missing classification", () => {
    assert.equal(
      displayStatusFor({
        classification: null,
        evaluationState: "failed",
        needsReview: true,
      }),
      "failed",
    );
  });
});

describe("API payload guard", () => {
  it("rejects malformed payloads", () => {
    assert.equal(isEvaluationApiResult({ findings: [] }), false);
    assert.equal(isEvaluationApiResult(livePayload), true);
  });
});

describe("summarizeFindings isolation", () => {
  it("does not mix a previous sample run into live totals", () => {
    const live = mapLiveResult(livePayload);
    const sampleLike = summarizeFindings([
      {
        ...live.findings[0],
        id: "AC-01",
        classification: "satisfied",
        displayStatus: "satisfied",
        evaluationState: "completed",
        needsReview: false,
        evidenceVerified: true,
        evidenceVerification: "verified",
      },
    ]);
    assert.equal(live.summary.statusCounts.satisfied, 0);
    assert.equal(sampleLike.statusCounts.satisfied, 1);
  });
});

describe("deterministic review mapping", () => {
  it("keeps review findings separate from live AI runs", () => {
    const payload: ReviewApiResult = {
      id: "rev-1",
      workspace: "sox",
      evaluation_mode: "deterministic",
      disclaimer: "Not a SOX opinion.",
      source_document: "controls.json",
      findings: [
        {
          id: "ITGC-01-O",
          title: "Provisioning",
          category: "access",
          dimension: "operating_effectiveness",
          full_text: "Approve joiners.",
          classification: "contradicted",
          explanation: "IAM-2240 missing approval.",
          evidence: "iam_approval is null",
          source_document: "joiners.json",
          evidence_verified: true,
          evaluation_state: "completed",
          needs_review: false,
        },
      ],
    };
    const mapped = mapReviewResult(payload);
    assert.equal(mapped.kind, "deterministic");
    assert.equal(mapped.workspace, "sox");
    assert.equal(mapped.policyVersion, null);
    assert.equal(mapped.findings[0].dimension, "operating_effectiveness");
    assert.equal(mapped.findings[0].displayStatus, "contradicted");
  });
});
