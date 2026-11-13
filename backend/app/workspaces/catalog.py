from __future__ import annotations

import json
from pathlib import Path

from app.models.review import WorkspaceDocument, WorkspaceId, WorkspaceSummary

ROOT = Path(__file__).resolve().parents[3] / "synthetic_data"


def list_workspaces() -> list[WorkspaceSummary]:
    return [
        WorkspaceSummary(
            id="security",
            title="Security & Compliance",
            status="available",
            summary="Assess Northstar security policies against 18 reference requirements.",
            disclaimer="Live AI evaluation uses the selected policy. Sample labels are not sent to the model.",
            compare_enabled=True,
        ),
        WorkspaceSummary(
            id="sox",
            title="SOX / IT Controls",
            status="available",
            summary="Review synthetic IT general controls and period evidence.",
            disclaimer=(
                "Deterministic checks on fictional Northstar ITGC evidence. "
                "This is not a SOX audit opinion."
            ),
        ),
        WorkspaceSummary(
            id="project_qa",
            title="Project Quality Assurance",
            status="available",
            summary="Check portal-program artifacts for missing owners, dates, and consistency.",
            disclaimer="Deterministic PMO checks on synthetic project files. Excel/Gantt review is not implemented.",
        ),
        WorkspaceSummary(
            id="content",
            title="Content Quality & Standards",
            status="available",
            summary="Check one internal announcement against a short style guide.",
            disclaimer="A limited rule review, not a content-management system.",
        ),
    ]


def _read(path: Path) -> str:
    if path.suffix.lower() == ".json":
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(parsed, indent=2)
    return path.read_text(encoding="utf-8")


def load_workspace_documents(workspace: WorkspaceId) -> list[WorkspaceDocument]:
    if workspace == "security":
        raise ValueError("Security documents are served by the compliance dataset.")
    if workspace == "sox":
        docs = [
            WorkspaceDocument(
                id="sox-controls",
                kind="control",
                title="ITGC control catalog",
                file="controls.json",
                content=_read(ROOT / "sox" / "controls.json"),
            )
        ]
        evidence_dir = ROOT / "sox" / "evidence"
        for path in sorted(evidence_dir.glob("*.json")):
            docs.append(
                WorkspaceDocument(
                    id=f"sox-{path.stem}",
                    kind="evidence",
                    title=path.stem.replace("_", " ").title(),
                    file=path.name,
                    content=_read(path),
                )
            )
        return docs
    if workspace == "project_qa":
        mapping = [
            ("charter.json", "Project charter", "artifact"),
            ("plan.json", "Project plan", "artifact"),
            ("raid.json", "RAID log", "artifact"),
            ("decisions.json", "Decision log", "artifact"),
            ("status_report.md", "Status report", "artifact"),
        ]
        return [
            WorkspaceDocument(
                id=f"pqa-{Path(name).stem}",
                kind=kind,
                title=title,
                file=name,
                content=_read(ROOT / "project_qa" / name),
            )
            for name, title, kind in mapping
        ]
    mapping = [
        ("style_guide.txt", "Internal writing standard", "guide"),
        ("announcement.md", "Portal login announcement", "sample"),
    ]
    return [
        WorkspaceDocument(
            id=f"content-{Path(name).stem}",
            kind=kind,
            title=title,
            file=name,
            content=_read(ROOT / "content" / name),
        )
        for name, title, kind in mapping
    ]
