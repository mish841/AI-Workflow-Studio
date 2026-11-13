from __future__ import annotations

import json
from pathlib import Path

from app.models.evaluation import PolicyVersion

POLICY_KEYS: dict[PolicyVersion, str] = {
    "v1": "security_policy_v1",
    "v2": "security_policy_v2",
}


def default_expected_findings_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "synthetic_data"
        / "evaluation"
        / "expected_findings.json"
    )


def load_expected_findings(
    path: Path | None = None,
) -> dict[str, dict[str, dict]]:
    findings_path = path or default_expected_findings_path()
    return json.loads(findings_path.read_text(encoding="utf-8"))


def expected_for_policy(
    version: PolicyVersion,
    path: Path | None = None,
) -> dict[str, dict]:
    return load_expected_findings(path)[POLICY_KEYS[version]]
