import { useState, type ReactNode } from "react";
import type { AssessmentKind, FindingView, PolicyVersion } from "../types";
import { POLICY_LABELS } from "../lib/dataset";
import { Chevron } from "./Chevron";
import { StatusBadge } from "./StatusBadge";

type Props = {
  finding: FindingView | null;
  kind: AssessmentKind;
  version: PolicyVersion | null;
  pinned: boolean;
  onTogglePin: () => void;
};

export function FindingDetail({
  finding,
  kind,
  version,
  pinned,
  onTogglePin,
}: Props) {
  if (!finding) {
    return (
      <aside className={pinned ? "panel detail-panel pinned" : "panel detail-panel"}>
        <div className="detail-toolbar">
          <h2>Finding</h2>
          <PinButton pinned={pinned} onToggle={onTogglePin} />
        </div>
        <div className="detail-scroll">
          <p className="muted">Select a row to inspect evidence.</p>
        </div>
      </aside>
    );
  }

  const live = kind === "live";
  const deterministic = kind === "deterministic";
  const subjectTitle = deterministic
    ? finding.dimensionLabel ?? "Review check"
    : "Security requirement";
  const evidenceTitle = deterministic ? "Evidence" : "Supporting policy evidence";
  const explanationTitle = live
    ? "Assessment rationale"
    : deterministic
      ? "Review notes"
      : "Reference explanation";

  return (
    <aside className={pinned ? "panel detail-panel pinned" : "panel detail-panel"}>
      <div className="detail-toolbar">
        <div>
          <p className="eyebrow req-id">{finding.id}</p>
          <h2>{finding.title}</h2>
          <p className="meta-row">
            <StatusBadge status={finding.displayStatus} />
            {finding.classification && finding.displayStatus !== finding.classification ? (
              <span className="muted">Predicted: {finding.classification}</span>
            ) : null}
            <span>{finding.categoryLabel}</span>
            {finding.dimensionLabel ? <span>{finding.dimensionLabel}</span> : null}
          </p>
        </div>
        <PinButton pinned={pinned} onToggle={onTogglePin} />
      </div>
      <div className="detail-scroll">
        <DetailSection title={subjectTitle} defaultOpen>
          <pre className="requirement-text">{finding.fullText}</pre>
        </DetailSection>
        <DetailSection title={evidenceTitle} defaultOpen>
          <EvidenceBlock finding={finding} />
        </DetailSection>
        <DetailSection title={explanationTitle} defaultOpen>
          <p>{finding.explanation}</p>
          {finding.uncertaintyNote ? (
            <p className="muted">{finding.uncertaintyNote}</p>
          ) : null}
        </DetailSection>
        {finding.retrievedPassages.length > 0 ? (
          <DetailSection title="Relevant source passages">
            <ul className="passage-list">
              {finding.retrievedPassages.map((passage) => (
                <li key={passage.chunk_id}>
                  <p className="meta-line">
                    {passage.section_number}. {passage.section_title}
                    {passage.used_in_finding ? " · used in finding" : ""}
                  </p>
                  <pre className="requirement-text">{passage.text}</pre>
                </li>
              ))}
            </ul>
          </DetailSection>
        ) : null}
        <DetailSection title="Source">
          <p className="muted">
            {finding.sourceDocument}
            {version ? ` · ${POLICY_LABELS[version]}` : ""}
          </p>
          {live || deterministic ? (
            <p className="muted">
              Source verified: {verificationLabel(finding.evidenceVerification)}
            </p>
          ) : (
            <p className="muted">
              Sample results — pre-labeled reference, not an AI assessment.
            </p>
          )}
        </DetailSection>
      </div>
    </aside>
  );
}

function PinButton({ pinned, onToggle }: { pinned: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      className={pinned ? "icon-btn pin-btn active" : "icon-btn pin-btn"}
      aria-pressed={pinned}
      aria-label={pinned ? "Unpin finding panel" : "Pin finding panel"}
      title={pinned ? "Unpin" : "Pin to the right"}
      onClick={onToggle}
    >
      <PinIcon pinned={pinned} />
    </button>
  );
}

function PinIcon({ pinned }: { pinned: boolean }) {
  return (
    <svg
      className={pinned ? "pin-icon is-pinned" : "pin-icon"}
      width="22"
      height="22"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <ellipse cx="12" cy="7.2" rx="5.6" ry="5.4" fill="#1d4e89" />
      <ellipse cx="10.2" cy="5.6" rx="2.1" ry="1.6" fill="#7aa0c9" opacity="0.7" />
      <path d="M8.2 11.6h7.6l-1.5 2.4H9.7z" fill="#152033" />
      <path
        d="M12 14v7.2"
        fill="none"
        stroke="#152033"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function EvidenceBlock({ finding }: { finding: FindingView }) {
  if (finding.evidenceVerified && finding.evidence) {
    return <blockquote>{finding.evidence}</blockquote>;
  }
  if (finding.evidenceVerification === "unverified" && finding.evidence) {
    return (
      <div>
        <p className="empty-evidence">
          This quote was not found in the original document, so it is not verified evidence.
        </p>
        <blockquote className="unverified-quote">{finding.evidence}</blockquote>
      </div>
    );
  }
  return <p className="empty-evidence">No supporting quote in the document.</p>;
}

function verificationLabel(value: FindingView["evidenceVerification"]): string {
  if (value === "verified") return "Yes — exact quote in source";
  if (value === "unverified") return "No — quote not found in source";
  return "No quote provided";
}

function DetailSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="detail-section">
      <button
        type="button"
        className="group-toggle"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <Chevron open={open} />
        {title}
      </button>
      {open && <div className="detail-body">{children}</div>}
    </section>
  );
}
