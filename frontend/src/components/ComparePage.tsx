import { Fragment, useMemo, useState } from "react";
import type {
  AssessmentRun,
  ComplianceStatus,
  DatasetDocument,
  DisplayStatus,
  PolicyVersion,
  Requirement,
} from "../types";
import { compareChange, POLICY_LABELS } from "../lib/dataset";
import { Chevron } from "./Chevron";
import { FilterPopover } from "./FilterPopover";
import { PolicyPicker } from "./PolicyPicker";
import { StatusBadge } from "./StatusBadge";

type Change = "improved" | "unchanged" | "worsened";

type Props = {
  policies: DatasetDocument[];
  requirements: Requirement[];
  liveRuns: Partial<Record<PolicyVersion, AssessmentRun>>;
};

type Side = {
  status: ComplianceStatus | null;
  displayStatus: DisplayStatus;
  evidence: string | null;
  reason: string;
};

function sideFor(
  requirement: Requirement,
  version: PolicyVersion,
  liveRun: AssessmentRun | undefined,
): Side {
  const live =
    liveRun?.kind === "live"
      ? liveRun.findings.find((item) => item.id === requirement.id)
      : undefined;
  if (live) {
    return {
      status: live.classification,
      displayStatus: live.displayStatus,
      evidence: live.evidence,
      reason: live.explanation,
    };
  }
  const labeled = requirement.findings[version];
  return {
    status: labeled.status,
    displayStatus: labeled.status,
    evidence: labeled.evidence,
    reason: labeled.reason,
  };
}

function policyTitle(
  policies: DatasetDocument[],
  version: PolicyVersion,
): string {
  return (
    policies.find((doc) => doc.policyVersion === version)?.title ??
    POLICY_LABELS[version]
  );
}

export function ComparePage({ policies, requirements, liveRuns }: Props) {
  const versions = policies
    .map((doc) => doc.policyVersion)
    .filter((value): value is PolicyVersion => Boolean(value));
  const [baseline, setBaseline] = useState<PolicyVersion>(versions[0] ?? "v1");
  const [candidate, setCandidate] = useState<PolicyVersion>(
    versions.find((value) => value !== versions[0]) ?? versions[0] ?? "v2",
  );
  const [query, setQuery] = useState("");
  const [changes, setChanges] = useState<Change[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);

  const samePolicy = baseline === candidate;
  const baselineLabel = policyTitle(policies, baseline);
  const candidateLabel = policyTitle(policies, candidate);

  const compared = useMemo(() => {
    if (samePolicy) return [];
    return requirements.map((requirement) => {
      const from = sideFor(requirement, baseline, liveRuns[baseline]);
      const to = sideFor(requirement, candidate, liveRuns[candidate]);
      const change =
        from.status && to.status ? compareChange(from.status, to.status) : null;
      return { requirement, from, to, change };
    });
  }, [baseline, candidate, liveRuns, requirements, samePolicy]);

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return compared.filter((row) => {
      if (changes.length) {
        if (!row.change || !changes.includes(row.change)) return false;
      }
      if (!needle) return true;
      return (
        row.requirement.id.toLowerCase().includes(needle) ||
        row.requirement.title.toLowerCase().includes(needle)
      );
    });
  }, [changes, compared, query]);

  const improved = compared.filter((row) => row.change === "improved").length;
  const unchanged = compared.filter((row) => row.change === "unchanged").length;
  const worsened = compared.filter((row) => row.change === "worsened").length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Policy comparison</p>
          <h2>Compare policies</h2>
        </div>
      </div>

      <section className="card compact-card">
        <div className="compare-setup">
          <PolicyPicker
            compact
            heading="Baseline"
            labelledBy="Baseline policy"
            policies={policies}
            selected={baseline}
            onSelect={setBaseline}
          />
          <PolicyPicker
            compact
            heading="Compare to"
            labelledBy="Comparison policy"
            policies={policies}
            selected={candidate}
            onSelect={setCandidate}
          />
        </div>
        {samePolicy ? (
          <p className="muted">Select two different policies to compare.</p>
        ) : (
          <p className="meta-line">
            Comparing {baselineLabel} with {candidateLabel}.
            {liveRuns[baseline]?.kind === "live" || liveRuns[candidate]?.kind === "live"
              ? " Live assessments are used where available; other rows use sample results."
              : " Showing sample results (pre-labeled reference), not a live AI assessment."}
          </p>
        )}
      </section>

      {!samePolicy && (
        <>
          <div className="summary-grid compact-summary">
            <article className="summary-card">
              <p>Improved</p>
              <strong>{improved}</strong>
            </article>
            <article className="summary-card">
              <p>Unchanged</p>
              <strong>{unchanged}</strong>
            </article>
            <article className="summary-card">
              <p>Worsened</p>
              <strong>{worsened}</strong>
            </article>
          </div>

          <div className="toolbar">
            <input
              type="search"
              placeholder="Search by ID or title"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <FilterPopover
              groups={[
                {
                  id: "change",
                  label: "Change",
                  options: [
                    { id: "improved", label: "Improved" },
                    { id: "unchanged", label: "Unchanged" },
                    { id: "worsened", label: "Worsened" },
                  ],
                },
              ]}
              selected={{ change: changes }}
              activeCount={changes.length}
              onApply={(next) => setChanges((next.change ?? []) as Change[])}
              onClear={() => setChanges([])}
            />
          </div>

          <div className="table-wrap">
            {rows.length === 0 ? (
              <p className="empty">
                No requirements match the current search or filters.
              </p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th />
                    <th>ID</th>
                    <th>Requirement</th>
                    <th>{baseline.toUpperCase()}</th>
                    <th>{candidate.toUpperCase()}</th>
                    <th>Change</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const expanded = openId === row.requirement.id;
                    return (
                      <Fragment key={row.requirement.id}>
                        <tr
                          className={expanded ? "selected" : undefined}
                          tabIndex={0}
                          onClick={() =>
                            setOpenId(expanded ? null : row.requirement.id)
                          }
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              setOpenId(expanded ? null : row.requirement.id);
                            }
                          }}
                        >
                          <td className="expand-cell">
                            <Chevron open={expanded} />
                          </td>
                          <td>{row.requirement.id}</td>
                          <td>{row.requirement.title}</td>
                          <td>
                            <StatusBadge status={row.from.displayStatus} />
                          </td>
                          <td>
                            <StatusBadge status={row.to.displayStatus} />
                          </td>
                          <td
                            className={
                              row.change ? `change change-${row.change}` : "change"
                            }
                          >
                            {row.change ?? "—"}
                          </td>
                        </tr>
                        {expanded && (
                          <tr className="expand-row">
                            <td colSpan={6}>
                              <div className="compare-detail">
                                <VersionEvidence
                                  label={baselineLabel}
                                  evidence={row.from.evidence}
                                  reason={row.from.reason}
                                />
                                <VersionEvidence
                                  label={candidateLabel}
                                  evidence={row.to.evidence}
                                  reason={row.to.reason}
                                />
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function VersionEvidence({
  label,
  evidence,
  reason,
}: {
  label: string;
  evidence: string | null;
  reason: string;
}) {
  return (
    <div>
      <h4>{label}</h4>
      <p>{reason}</p>
      {evidence ? (
        <blockquote>{evidence}</blockquote>
      ) : (
        <p className="empty-evidence">No supporting evidence.</p>
      )}
    </div>
  );
}
