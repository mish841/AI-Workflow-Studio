from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.models.review import ReviewFinding, ReviewResult
from app.services.review_common import finding, parse_dt

ROOT = Path(__file__).resolve().parents[3] / "synthetic_data" / "sox"
DISCLAIMER = (
    "Deterministic ITGC review of synthetic Northstar evidence. "
    "This is not a SOX audit opinion."
)


def _load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def evaluate_sox() -> ReviewResult:
    catalog = _load_json("controls.json")
    evidence_dir = ROOT / "evidence"
    present = {path.name for path in evidence_dir.glob("*.json")}
    joiners = _load_json("evidence/joiners.json")
    terminations = _load_json("evidence/terminations.json")
    reviews = _load_json("evidence/access_reviews.json")
    privileged = _load_json("evidence/privileged_access.json")
    changes = _load_json("evidence/changes.json")
    deployments = _load_json("evidence/deployments.json")
    incidents = _load_json("evidence/incidents.json")

    findings: list[ReviewFinding] = []
    for control in catalog["controls"]:
        findings.extend(
            _design_and_completeness(control, present)
        )

    findings.append(_provisioning(joiners))
    findings.append(_termination(terminations))
    findings.append(_access_reviews(reviews))
    findings.append(_privileged(privileged))
    findings.append(_change_approvals(changes))
    findings.append(_deployments(deployments))
    findings.append(_change_docs(changes))
    findings.append(_sod(changes))
    findings.append(_incidents(incidents))
    findings.append(_package_completeness(catalog, present))
    findings.append(_emergency(changes))

    return ReviewResult(
        id=str(uuid4()),
        workspace="sox",
        disclaimer=DISCLAIMER,
        source_document="controls.json",
        findings=findings,
    )


def _design_and_completeness(control: dict, present: set[str]) -> list[ReviewFinding]:
    required = ["objective", "frequency", "owner", "evidence_expected"]
    missing_fields = [field for field in required if not control.get(field)]
    if missing_fields:
        design = finding(
            finding_id=f"{control['id']}-D",
            title=f"{control['title']} — control design",
            category=control["category"],
            dimension="design",
            full_text=control.get("objective") or control["title"],
            classification="partial",
            explanation=(
                f"Control {control['id']} is missing catalog field(s): "
                + ", ".join(missing_fields)
                + "."
            ),
            evidence=None,
            source_document="controls.json",
        )
    else:
        design = finding(
            finding_id=f"{control['id']}-D",
            title=f"{control['title']} — control design",
            category=control["category"],
            dimension="design",
            full_text=control["objective"],
            classification="satisfied",
            explanation="Objective, frequency, owner, and expected evidence are documented.",
            evidence=f"Owner: {control['owner']}. Frequency: {control['frequency']}.",
            source_document="controls.json",
        )

    expected_files = control.get("evidence_expected") or []
    missing_files = [name for name in expected_files if name not in present]
    if missing_files:
        completeness = finding(
            finding_id=f"{control['id']}-C",
            title=f"{control['title']} — evidence completeness",
            category=control["category"],
            dimension="completeness",
            full_text=control.get("objective") or control["title"],
            classification="missing",
            explanation="Expected evidence file(s) are not in the period package: "
            + ", ".join(missing_files)
            + ".",
            evidence=None,
            source_document="controls.json",
        )
    else:
        completeness = finding(
            finding_id=f"{control['id']}-C",
            title=f"{control['title']} — evidence completeness",
            category=control["category"],
            dimension="completeness",
            full_text=control.get("objective") or control["title"],
            classification="satisfied",
            explanation="All expected evidence files for this control are present.",
            evidence=", ".join(expected_files),
            source_document=expected_files[0] if expected_files else "controls.json",
        )
    return [design, completeness]


def _provisioning(joiners: dict) -> ReviewFinding:
    bad = [
        row
        for row in joiners["records"]
        if row.get("access_granted") and not row.get("iam_approval")
    ]
    if bad:
        row = bad[0]
        return finding(
            finding_id="ITGC-01-O",
            title="User access provisioning — operating effectiveness",
            category="access",
            dimension="operating_effectiveness",
            full_text="New workforce access is granted only after manager and IAM approval.",
            classification="contradicted",
            explanation=(
                f"{row['ticket']} granted access to {row['user']} without IAM approval."
            ),
            evidence=f"{row['ticket']}: iam_approval is null and access_granted={row['access_granted']}.",
            source_document="joiners.json",
        )
    return finding(
        finding_id="ITGC-01-O",
        title="User access provisioning — operating effectiveness",
        category="access",
        dimension="operating_effectiveness",
        full_text="New workforce access is granted only after manager and IAM approval.",
        classification="satisfied",
        explanation="Sampled joiner tickets include manager and IAM approval before grant.",
        evidence=joiners["records"][0]["ticket"],
        source_document="joiners.json",
    )


def _termination(terminations: dict) -> ReviewFinding:
    late = []
    for row in terminations["records"]:
        start = parse_dt(row["hr_termination"])
        end = parse_dt(row["iam_disabled"])
        hours = (end - start).total_seconds() / 3600
        if hours > 24 or row.get("systems_still_active"):
            late.append((row, hours))
    if late:
        row, hours = late[0]
        return finding(
            finding_id="ITGC-02-O",
            title="User access termination — operating effectiveness",
            category="access",
            dimension="operating_effectiveness",
            full_text="Access is revoked within 24 hours of HR recording a termination.",
            classification="contradicted",
            explanation=(
                f"{row['user']} was disabled {hours:.0f} hours after HR termination "
                f"and still had access on {', '.join(row['systems_still_active']) or 'listed systems'}."
            ),
            evidence=(
                f"{row['ticket']}: hr_termination={row['hr_termination']}; "
                f"iam_disabled={row['iam_disabled']}."
            ),
            source_document="terminations.json",
        )
    return finding(
        finding_id="ITGC-02-O",
        title="User access termination — operating effectiveness",
        category="access",
        dimension="operating_effectiveness",
        full_text="Access is revoked within 24 hours of HR recording a termination.",
        classification="satisfied",
        explanation="Sampled terminations were disabled within 24 hours.",
        evidence=terminations["records"][0]["ticket"],
        source_document="terminations.json",
    )


def _access_reviews(reviews: dict) -> ReviewFinding:
    reviewed = {row["system"] for row in reviews["reviews"]}
    missing = [name for name in reviews["systems_in_scope"] if name not in reviewed]
    if missing:
        return finding(
            finding_id="ITGC-03-O",
            title="Periodic access reviews — operating effectiveness",
            category="access",
            dimension="operating_effectiveness",
            full_text="System owners review all active accounts at least quarterly and record sign-off.",
            classification="partial",
            explanation="Quarterly reviews omitted in-scope system(s): " + ", ".join(missing) + ".",
            evidence="systems_in_scope includes Harbor CI/CD; reviews cover Northstar Hub and Atlas IAM.",
            source_document="access_reviews.json",
        )
    return finding(
        finding_id="ITGC-03-O",
        title="Periodic access reviews — operating effectiveness",
        category="access",
        dimension="operating_effectiveness",
        full_text="System owners review all active accounts at least quarterly and record sign-off.",
        classification="satisfied",
        explanation="Every in-scope system has a signed quarterly review.",
        evidence=", ".join(sorted(reviewed)),
        source_document="access_reviews.json",
    )


def _privileged(privileged: dict) -> ReviewFinding:
    weak = [
        row
        for row in privileged["grants"]
        if not row.get("manager_approval")
        or not row.get("security_approval")
        or not row.get("mfa_enrolled")
    ]
    if weak:
        row = weak[0]
        return finding(
            finding_id="ITGC-04-O",
            title="Privileged access — operating effectiveness",
            category="access",
            dimension="operating_effectiveness",
            full_text="Privileged roles require dual approval and MFA enrollment before use.",
            classification="partial",
            explanation=f"{row['ticket']} is missing dual approval or MFA enrollment.",
            evidence=json.dumps(row),
            source_document="privileged_access.json",
        )
    row = privileged["grants"][0]
    return finding(
        finding_id="ITGC-04-O",
        title="Privileged access — operating effectiveness",
        category="access",
        dimension="operating_effectiveness",
        full_text="Privileged roles require dual approval and MFA enrollment before use.",
        classification="satisfied",
        explanation="Sampled privileged grants have manager approval, security approval, and MFA.",
        evidence=f"{row['ticket']}: MFA enrolled; dual approval dated {row['security_approval']}.",
        source_document="privileged_access.json",
    )


def _change_approvals(changes: dict) -> ReviewFinding:
    bad = [
        row
        for row in changes["changes"]
        if not row.get("emergency")
        and not row.get("cab_approved")
        and len(row.get("approvers") or []) < 2
    ]
    if bad:
        row = bad[0]
        return finding(
            finding_id="ITGC-05-O",
            title="Change approvals — operating effectiveness",
            category="change",
            dimension="operating_effectiveness",
            full_text="Production changes are approved by CAB or two independent approvers before implementation.",
            classification="contradicted",
            explanation=(
                f"{row['id']} was implemented without CAB approval and with "
                f"{len(row.get('approvers') or [])} approver(s)."
            ),
            evidence=f"{row['id']} cab_approved=false approvers={row.get('approvers')}.",
            source_document="changes.json",
        )
    return finding(
        finding_id="ITGC-05-O",
        title="Change approvals — operating effectiveness",
        category="change",
        dimension="operating_effectiveness",
        full_text="Production changes are approved by CAB or two independent approvers before implementation.",
        classification="satisfied",
        explanation="Non-emergency changes in the sample have CAB or dual approval.",
        evidence=changes["changes"][0]["id"],
        source_document="changes.json",
    )


def _deployments(deployments: dict) -> ReviewFinding:
    orphan = [
        row
        for row in deployments["deployments"]
        if row.get("environment") == "production" and not row.get("change_id")
    ]
    if orphan:
        row = orphan[0]
        return finding(
            finding_id="ITGC-06-O",
            title="Deployment authorization — operating effectiveness",
            category="change",
            dimension="operating_effectiveness",
            full_text="Production deployments reference an approved change ticket.",
            classification="missing",
            explanation=f"{row['id']} was deployed to production with no change ticket.",
            evidence=row.get("note") or row["id"],
            source_document="deployments.json",
        )
    return finding(
        finding_id="ITGC-06-O",
        title="Deployment authorization — operating effectiveness",
        category="change",
        dimension="operating_effectiveness",
        full_text="Production deployments reference an approved change ticket.",
        classification="satisfied",
        explanation="Production deployments in the sample cite a change id.",
        evidence=deployments["deployments"][0]["id"],
        source_document="deployments.json",
    )


def _change_docs(changes: dict) -> ReviewFinding:
    weak = [
        row
        for row in changes["changes"]
        if not row.get("implementation_steps")
        or not row.get("backout_plan")
        or not row.get("post_implement_evidence")
    ]
    if weak:
        row = weak[0]
        missing = [
            name
            for name, ok in (
                ("implementation steps", row.get("implementation_steps")),
                ("backout plan", row.get("backout_plan")),
                ("post-implement evidence", row.get("post_implement_evidence")),
            )
            if not ok
        ]
        return finding(
            finding_id="ITGC-07-O",
            title="Production change documentation — operating effectiveness",
            category="change",
            dimension="operating_effectiveness",
            full_text="Each production change records implementation steps, backout, and post-implement evidence.",
            classification="partial",
            explanation=f"{row['id']} is missing: {', '.join(missing)}.",
            evidence=f"{row['id']} backout_plan={row.get('backout_plan')}.",
            source_document="changes.json",
        )
    return finding(
        finding_id="ITGC-07-O",
        title="Production change documentation — operating effectiveness",
        category="change",
        dimension="operating_effectiveness",
        full_text="Each production change records implementation steps, backout, and post-implement evidence.",
        classification="satisfied",
        explanation="Sampled changes include implementation, backout, and evidence flags.",
        evidence=changes["changes"][0]["id"],
        source_document="changes.json",
    )


def _sod(changes: dict) -> ReviewFinding:
    conflicts = []
    for row in changes["changes"]:
        approvers = row.get("approvers") or []
        if row["developer"] in approvers and set(approvers) <= {row["developer"]}:
            conflicts.append(row)
    if conflicts:
        row = conflicts[0]
        return finding(
            finding_id="ITGC-08-O",
            title="Segregation of duties — operating effectiveness",
            category="sod",
            dimension="operating_effectiveness",
            full_text="The same person cannot develop a production change and approve it.",
            classification="contradicted",
            explanation=(
                f"{row['developer']} both developed and was the only approver of {row['id']}."
            ),
            evidence=f"{row['id']} developer={row['developer']} approvers={row['approvers']}.",
            source_document="changes.json",
        )
    return finding(
        finding_id="ITGC-08-O",
        title="Segregation of duties — operating effectiveness",
        category="sod",
        dimension="operating_effectiveness",
        full_text="The same person cannot develop a production change and approve it.",
        classification="satisfied",
        explanation="No sampled change is solely self-approved by its developer.",
        evidence=changes["changes"][0]["id"],
        source_document="changes.json",
    )


def _incidents(incidents: dict) -> ReviewFinding:
    weak = [
        row
        for row in incidents["incidents"]
        if row["severity"] in {"Sev 1", "Sev 2"} and not row.get("exception_ticket")
    ]
    if weak:
        row = weak[0]
        return finding(
            finding_id="ITGC-09-O",
            title="Incident and exception tracking — operating effectiveness",
            category="operations",
            dimension="operating_effectiveness",
            full_text="Sev 1 and Sev 2 incidents are logged, and control exceptions have tickets.",
            classification="partial",
            explanation=f"{row['id']} ({row['severity']}) has no exception ticket.",
            evidence=f"{row['id']} exception_ticket=null.",
            source_document="incidents.json",
        )
    return finding(
        finding_id="ITGC-09-O",
        title="Incident and exception tracking — operating effectiveness",
        category="operations",
        dimension="operating_effectiveness",
        full_text="Sev 1 and Sev 2 incidents are logged, and control exceptions have tickets.",
        classification="satisfied",
        explanation="Sampled Sev 1/2 incidents include exception tickets.",
        evidence=incidents["incidents"][0]["id"],
        source_document="incidents.json",
    )


def _package_completeness(catalog: dict, present: set[str]) -> ReviewFinding:
    required = catalog["required_evidence_files"]
    missing = [name for name in required if name not in present]
    if missing:
        return finding(
            finding_id="ITGC-10-O",
            title="Evidence completeness — operating effectiveness",
            category="evidence",
            dimension="operating_effectiveness",
            full_text="The period evidence package contains every artifact named in the control catalog.",
            classification="missing",
            explanation="Missing required files: " + ", ".join(missing) + ".",
            evidence=None,
            source_document="controls.json",
        )
    return finding(
        finding_id="ITGC-10-O",
        title="Evidence completeness — operating effectiveness",
        category="evidence",
        dimension="operating_effectiveness",
        full_text="The period evidence package contains every artifact named in the control catalog.",
        classification="satisfied",
        explanation="All eight required period evidence files are present.",
        evidence=", ".join(required),
        source_document="controls.json",
    )


def _emergency(changes: dict) -> ReviewFinding:
    weak = [
        row
        for row in changes["changes"]
        if row.get("emergency") and not row.get("post_approval")
    ]
    if weak:
        row = weak[0]
        return finding(
            finding_id="ITGC-11-O",
            title="Emergency change follow-up — operating effectiveness",
            category="change",
            dimension="operating_effectiveness",
            full_text="Emergency production changes receive documented post-implementation approval within two business days.",
            classification="missing",
            explanation=f"{row['id']} is an emergency change with no post-implementation approval.",
            evidence=f"{row['id']} emergency=true post_approval=null.",
            source_document="changes.json",
        )
    return finding(
        finding_id="ITGC-11-O",
        title="Emergency change follow-up — operating effectiveness",
        category="change",
        dimension="operating_effectiveness",
        full_text="Emergency production changes receive documented post-implementation approval within two business days.",
        classification="satisfied",
        explanation="Emergency changes in the sample have post-approval recorded.",
        evidence=None,
        source_document="changes.json",
    )
