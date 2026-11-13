from __future__ import annotations

from pathlib import Path

from app.models.evaluation import PolicySummary, PolicyVersion

POLICY_FILES: dict[PolicyVersion, str] = {
    "v1": "security_policy_v1.txt",
    "v2": "security_policy_v2.txt",
}

POLICY_TITLES: dict[PolicyVersion, str] = {
    "v1": "Northstar Information Security Policy V1",
    "v2": "Northstar Information Security Policy V2",
}


def default_policy_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "synthetic_data" / "policies"


def policy_path(version: PolicyVersion, policy_dir: Path | None = None) -> Path:
    directory = policy_dir or default_policy_dir()
    return directory / POLICY_FILES[version]


def load_policy_text(
    version: PolicyVersion,
    policy_dir: Path | None = None,
) -> str:
    path = policy_path(version, policy_dir)
    if not path.is_file():
        raise FileNotFoundError(f"Policy file not found: {path}")
    return path.read_text(encoding="utf-8")


def list_policies(policy_dir: Path | None = None) -> list[PolicySummary]:
    return [
        PolicySummary(
            id=version,
            filename=POLICY_FILES[version],
            title=POLICY_TITLES[version],
        )
        for version in ("v1", "v2")
        if policy_path(version, policy_dir).is_file()
    ]
