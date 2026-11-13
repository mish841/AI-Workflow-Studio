import type { WorkspaceId } from "../types";

type Props = {
  workspace: Exclude<WorkspaceId, "security">;
  onOpenSecurity: () => void;
};

export function WorkspacePreview({ workspace, onOpenSecurity }: Props) {
  const isProject = workspace === "project_qa";

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">{isProject ? "Upcoming" : "Planned"}</p>
          <h2>
            {isProject
              ? "Project Quality Assurance"
              : "Content Quality & Standards"}
          </h2>
        </div>
        <p className="banner">
          This workspace is not evaluating documents yet. No sample scores or
          AI results are shown here.
        </p>
      </div>

      <section className="card">
        {isProject ? (
          <>
            <h3>Intended workflow</h3>
            <p>
              A delivery team would attach project artifacts and run checks
              against documented PMO standards. Example artifacts: project
              plan, RAID log, AAD log, solution status report, budget tracker.
            </p>
            <h3>First implementation (not built)</h3>
            <ul>
              <li>Readable text/CSV artifacts for a fictional portal program</li>
              <li>
                Deterministic rules such as “every high-priority risk has an
                owner”
              </li>
              <li>Reuse the same findings layout as Security &amp; Compliance</li>
            </ul>
            <h3>Still planned</h3>
            <p>Excel workbooks, Gantt/predecessor graphs, and LLM narrative review.</p>
          </>
        ) : (
          <>
            <h3>Intended workflow</h3>
            <p>
              Communications would be checked against writing standards,
              readability, and a Northstar style guide.
            </p>
            <h3>Why it is preview-only</h3>
            <p>
              There is no style-guide dataset or evaluator in the repository.
              Showing invented scores would overstate the product.
            </p>
          </>
        )}
        <button type="button" className="primary-btn" onClick={onOpenSecurity}>
          Go to Security &amp; Compliance
        </button>
      </section>
    </div>
  );
}
