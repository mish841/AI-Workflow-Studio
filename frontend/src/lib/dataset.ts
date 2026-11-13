import type {
  ComplianceStatus,
  PolicyVersion,
  Requirement,
  StatusCounts,
} from "../types";
import rawDataset from "../data/complianceDataset.json";

export const dataset = rawDataset as import("../types").ComplianceDataset;

export const STATUS_LABELS: Record<ComplianceStatus, string> = {
  satisfied: "Satisfied",
  partial: "Partial",
  missing: "Missing",
  contradicted: "Contradicted",
};

const STATUS_RANK: Record<ComplianceStatus, number> = {
  contradicted: 0,
  missing: 1,
  partial: 2,
  satisfied: 3,
};

export function countStatuses(
  requirements: Requirement[],
  version: PolicyVersion,
): StatusCounts {
  const counts: StatusCounts = {
    satisfied: 0,
    partial: 0,
    missing: 0,
    contradicted: 0,
  };
  for (const requirement of requirements) {
    counts[requirement.findings[version].status] += 1;
  }
  return counts;
}

export function compareChange(
  from: ComplianceStatus,
  to: ComplianceStatus,
): "improved" | "unchanged" | "worsened" {
  if (STATUS_RANK[to] > STATUS_RANK[from]) return "improved";
  if (STATUS_RANK[to] < STATUS_RANK[from]) return "worsened";
  return "unchanged";
}

export const POLICY_LABELS: Record<PolicyVersion, string> = {
  v1: "Security Policy V1",
  v2: "Security Policy V2",
};
