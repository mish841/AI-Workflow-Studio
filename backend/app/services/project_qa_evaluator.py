from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.models.review import ReviewFinding, ReviewResult
from app.services.review_common import finding

ROOT = Path(__file__).resolve().parents[3] / "synthetic_data" / "project_qa"
AS_OF = datetime(2026, 11, 13)
REQUIRED_STATUS_SECTIONS = ("Purpose", "Schedule", "Risks", "Budget", "Contact")
DISCLAIMER = (
    "Deterministic checks on synthetic Northstar project artifacts. "
    "Excel, Microsoft Project, and critical-path analysis are not implemented."
)


def _load(name: str):
    path = ROOT / name
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return path.read_text(encoding="utf-8")


def evaluate_project_qa() -> ReviewResult:
    charter = _load("charter.json")
    plan = _load("plan.json")
    raid = _load("raid.json")
    decisions = _load("decisions.json")
    status = _load("status_report.md")
    findings: list[ReviewFinding] = [
        _risks_missing_owners(raid),
        _overdue_issues(raid),
        _decisions_missing_approvers(decisions),
        _milestones_missing_dates(plan),
        _status_sections(status),
        _metadata_consistency(charter, plan, status),
    ]
    return ReviewResult(
        id=str(uuid4()),
        workspace="project_qa",
        disclaimer=DISCLAIMER,
        source_document="charter.json",
        findings=findings,
    )


def _risks_missing_owners(raid: dict) -> ReviewFinding:
    missing = [
        item
        for item in raid["items"]
        if item["type"] == "risk" and not item.get("owner")
    ]
    if missing:
        ids = ", ".join(item["id"] for item in missing)
        return finding(
            finding_id="PQA-01",
            title="Risks missing owners",
            category="raid",
            dimension="artifact_quality",
            full_text="Every open risk must have a named owner.",
            classification="missing",
            explanation=f"Open risk(s) have no owner: {ids}.",
            evidence=missing[0]["title"],
            source_document="raid.json",
        )
    return finding(
        finding_id="PQA-01",
        title="Risks missing owners",
        category="raid",
        dimension="artifact_quality",
        full_text="Every open risk must have a named owner.",
        classification="satisfied",
        explanation="All risks in the RAID log have owners.",
        evidence=None,
        source_document="raid.json",
    )


def _overdue_issues(raid: dict) -> ReviewFinding:
    overdue = []
    for item in raid["items"]:
        if item["type"] != "issue" or item.get("status") != "open":
            continue
        due = datetime.strptime(item["due"], "%Y-%m-%d")
        if due < AS_OF:
            overdue.append(item)
    if overdue:
        ids = ", ".join(item["id"] for item in overdue)
        return finding(
            finding_id="PQA-02",
            title="Overdue unresolved issues",
            category="raid",
            dimension="artifact_quality",
            full_text="Open issues must not remain past their due date.",
            classification="contradicted",
            explanation=f"Open issue(s) are past due as of {AS_OF.date().isoformat()}: {ids}.",
            evidence=f"{overdue[0]['id']} due {overdue[0]['due']} status={overdue[0]['status']}.",
            source_document="raid.json",
        )
    return finding(
        finding_id="PQA-02",
        title="Overdue unresolved issues",
        category="raid",
        dimension="artifact_quality",
        full_text="Open issues must not remain past their due date.",
        classification="satisfied",
        explanation="No open issues are past due.",
        evidence=None,
        source_document="raid.json",
    )


def _decisions_missing_approvers(decisions: dict) -> ReviewFinding:
    missing = [row for row in decisions["decisions"] if not row.get("approver")]
    if missing:
        return finding(
            finding_id="PQA-03",
            title="Decisions missing approvers",
            category="decisions",
            dimension="artifact_quality",
            full_text="Each recorded decision must name an approver.",
            classification="missing",
            explanation=f"{missing[0]['id']} has no approver.",
            evidence=missing[0]["title"],
            source_document="decisions.json",
        )
    return finding(
        finding_id="PQA-03",
        title="Decisions missing approvers",
        category="decisions",
        dimension="artifact_quality",
        full_text="Each recorded decision must name an approver.",
        classification="satisfied",
        explanation="All decisions list an approver.",
        evidence=None,
        source_document="decisions.json",
    )


def _milestones_missing_dates(plan: dict) -> ReviewFinding:
    missing = [row for row in plan["milestones"] if not row.get("date")]
    if missing:
        return finding(
            finding_id="PQA-04",
            title="Milestones missing dates",
            category="plan",
            dimension="artifact_quality",
            full_text="Each milestone must have a date.",
            classification="missing",
            explanation=f"{missing[0]['id']} ({missing[0]['title']}) has no date.",
            evidence=f"{missing[0]['id']}: date=null",
            source_document="plan.json",
        )
    return finding(
        finding_id="PQA-04",
        title="Milestones missing dates",
        category="plan",
        dimension="artifact_quality",
        full_text="Each milestone must have a date.",
        classification="satisfied",
        explanation="All plan milestones include dates.",
        evidence=None,
        source_document="plan.json",
    )


def _status_sections(status: str) -> ReviewFinding:
    found = set(re.findall(r"^##\s+(.+)$", status, re.MULTILINE))
    missing = [name for name in REQUIRED_STATUS_SECTIONS if name not in found]
    if missing:
        return finding(
            finding_id="PQA-05",
            title="Status report missing required sections",
            category="status",
            dimension="artifact_quality",
            full_text="Status reports must include Purpose, Schedule, Risks, Budget, and Contact.",
            classification="partial",
            explanation="Missing section(s): " + ", ".join(missing) + ".",
            evidence="Headings present: " + ", ".join(sorted(found)) + ".",
            source_document="status_report.md",
        )
    return finding(
        finding_id="PQA-05",
        title="Status report missing required sections",
        category="status",
        dimension="artifact_quality",
        full_text="Status reports must include Purpose, Schedule, Risks, Budget, and Contact.",
        classification="satisfied",
        explanation="All required status-report sections are present.",
        evidence=None,
        source_document="status_report.md",
    )


def _metadata_consistency(charter: dict, plan: dict, status: str) -> ReviewFinding:
    issues = []
    if charter["project_id"] != plan["project_id"]:
        issues.append(
            f"charter project_id {charter['project_id']} vs plan {plan['project_id']}"
        )
    if charter["name"] != plan["name"]:
        issues.append("project name differs between charter and plan")
    if charter["sponsor"] != plan["sponsor"]:
        issues.append("sponsor differs between charter and plan")
    report_id = re.search(r"Project ID:\s*(\S+)", status)
    report_sponsor = re.search(r"Sponsor:\s*(.+)", status)
    if report_id and report_id.group(1) != charter["project_id"]:
        issues.append(
            f"status report project id {report_id.group(1)} vs charter {charter['project_id']}"
        )
    if report_sponsor and report_sponsor.group(1).strip() != charter["sponsor"]:
        issues.append(
            f"status report sponsor {report_sponsor.group(1).strip()} vs charter {charter['sponsor']}"
        )
    if issues:
        return finding(
            finding_id="PQA-06",
            title="Inconsistent project metadata",
            category="metadata",
            dimension="artifact_quality",
            full_text="Charter, plan, and status report must share project id, name, and sponsor.",
            classification="contradicted",
            explanation="; ".join(issues) + ".",
            evidence=f"Charter {charter['project_id']} / {charter['sponsor']}.",
            source_document="status_report.md",
        )
    return finding(
        finding_id="PQA-06",
        title="Inconsistent project metadata",
        category="metadata",
        dimension="artifact_quality",
        full_text="Charter, plan, and status report must share project id, name, and sponsor.",
        classification="satisfied",
        explanation="Project id, name, and sponsor match across artifacts.",
        evidence=charter["project_id"],
        source_document="charter.json",
    )
