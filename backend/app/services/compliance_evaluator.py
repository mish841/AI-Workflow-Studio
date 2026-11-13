from __future__ import annotations

import os
import uuid
from collections.abc import Callable

from dotenv import load_dotenv
from fastapi import HTTPException
from langchain_core.documents import Document
from openai import APIError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from app.ingestion.requirement_parser import parse_reference_requirements
from app.models.evaluation import (
    ComplianceFinding,
    EvaluationMode,
    EvaluationResult,
    ModelFinding,
    PolicyVersion,
    RetrievedPassage,
    RequirementSummary,
)
from app.services.evidence import verify_quote
from app.services.policy_loader import POLICY_FILES, load_policy_text
from app.services.retrieval import (
    format_passages_for_prompt,
    mark_used_passages,
    passages_for_requirement,
)

load_dotenv()

SYSTEM_PROMPT = """You are a security-policy compliance evaluator.

Classify how the company policy covers one security requirement.
Use only the policy text provided in the user message.

Allowed classifications:
- satisfied: the policy fully meets the requirement
- partial: the policy addresses the topic but is incomplete or weaker
- missing: the policy is silent on the requirement
- contradicted: the policy states something that conflicts with the requirement

Rules:
- If you cite supporting evidence, copy an exact substring from the policy. Do not paraphrase quotes.
- If there is no exact quote, set supporting_quote to null.
- Distinguish silence (missing) from an explicit conflicting statement (contradicted).
- If you cannot make a reliable determination, set needs_review to true and explain why in uncertainty_note. Do not guess "missing" when you are uncertain.
- Never use expected labels, scoring keys, or evaluation answer sheets. Those are not provided.
"""

RAG_SYSTEM_PROMPT = """You are a security-policy compliance evaluator.

Classify how the company policy covers one security requirement.
Use only the retrieved policy passages provided in the user message. Those passages are excerpts from one selected policy version.

Allowed classifications:
- satisfied: the passages fully meet the requirement
- partial: the passages address the topic but are incomplete or weaker
- missing: the passages are silent on the requirement
- contradicted: the passages state something that conflicts with the requirement

Rules:
- If you cite supporting evidence, copy an exact substring from a retrieved passage. Do not paraphrase quotes.
- If there is no exact quote, set supporting_quote to null.
- If no passages were retrieved, or the passages are too thin to judge, set needs_review to true. Do not guess "missing" solely because retrieval returned nothing.
- Distinguish silence (missing) from an explicit conflicting statement (contradicted) using only the passages you were given.
- Never use expected labels, scoring keys, or evaluation answer sheets. Those are not provided.
"""

Completer = Callable[..., ModelFinding]


def requirement_title(content: str, requirement_id: str) -> str:
    first_line = content.splitlines()[0].strip() if content.strip() else requirement_id
    prefix = requirement_id
    rest = first_line[len(prefix) :].strip(" :-") if first_line.startswith(prefix) else first_line
    return rest or requirement_id


def inventory_from_documents(documents: list[Document]) -> list[RequirementSummary]:
    return [
        RequirementSummary(
            requirement_id=doc.metadata["requirement_id"],
            title=requirement_title(doc.page_content, doc.metadata["requirement_id"]),
            category=doc.metadata["category"],
            source_file=doc.metadata["source_file"],
            text=doc.page_content,
        )
        for doc in documents
    ]


def load_requirement_inventory() -> list[RequirementSummary]:
    return inventory_from_documents(parse_reference_requirements())


def _openai_completer(
    requirement_id: str,
    requirement_text: str,
    policy_text: str,
    policy_filename: str,
    *,
    system_prompt: str = SYSTEM_PROMPT,
) -> ModelFinding:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="The language model is not configured on this server.",
        )

    client = OpenAI(api_key=api_key, timeout=90.0, max_retries=1)
    try:
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Policy filename: {policy_filename}\n\n"
                        f"Company policy:\n{policy_text}\n\n"
                        f"Security requirement {requirement_id}:\n{requirement_text}"
                    ),
                },
            ],
            text_format=ModelFinding,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Language-model authentication failed.",
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="OpenAI rate limit reached. Try again shortly.",
        ) from exc
    except APITimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="OpenAI request timed out.",
        ) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI request failed.",
        ) from exc

    parsed = response.output_parsed
    if parsed is None:
        raise HTTPException(
            status_code=502,
            detail="OpenAI returned an empty structured result.",
        )
    return parsed


def finalize_finding(
    requirement: RequirementSummary,
    model_finding: ModelFinding | None,
    policy_text: str,
    source_document: str,
    *,
    failed: bool = False,
    failure_note: str | None = None,
    retrieved_passages: list[RetrievedPassage] | None = None,
) -> ComplianceFinding:
    passages = mark_used_passages(
        retrieved_passages or [],
        None if model_finding is None else model_finding.supporting_quote,
    )
    if failed or model_finding is None:
        return ComplianceFinding(
            requirement_id=requirement.requirement_id,
            requirement_title=requirement.title,
            requirement_text=requirement.text,
            category=requirement.category,
            classification=None,
            explanation=failure_note or "The model did not return a usable classification.",
            supporting_quote=None,
            source_document=source_document,
            evidence_verified=False,
            evidence_verification="missing",
            needs_review=True,
            evaluation_state="failed",
            uncertainty_note=failure_note,
            retrieved_passages=passages,
        )

    verification = verify_quote(model_finding.supporting_quote, policy_text)
    evidence_verified = verification == "verified"
    needs_review = model_finding.needs_review
    uncertainty = model_finding.uncertainty_note

    if verification == "unverified":
        needs_review = True
        note = "Supporting quote was not found in the original policy text."
        uncertainty = f"{uncertainty} {note}".strip() if uncertainty else note
    elif (
        model_finding.classification in {"satisfied", "partial", "contradicted"}
        and verification == "missing"
    ):
        needs_review = True
        note = "Classification is not missing/contradiction-silent, but no verifiable quote was provided."
        uncertainty = f"{uncertainty} {note}".strip() if uncertainty else note
    elif (
        evidence_verified
        and passages
        and model_finding.supporting_quote
        and not any(passage.used_in_finding for passage in passages)
    ):
        needs_review = True
        note = "Quote exists in the source policy but was not present in retrieved passages."
        uncertainty = f"{uncertainty} {note}".strip() if uncertainty else note

    state = "needs_review" if needs_review else "completed"
    quote = model_finding.supporting_quote.strip() if model_finding.supporting_quote else None

    return ComplianceFinding(
        requirement_id=requirement.requirement_id,
        requirement_title=requirement.title,
        requirement_text=requirement.text,
        category=requirement.category,
        classification=model_finding.classification,
        explanation=model_finding.explanation,
        supporting_quote=quote,
        source_document=source_document,
        evidence_verified=evidence_verified,
        evidence_verification=verification,
        needs_review=needs_review,
        evaluation_state=state,
        uncertainty_note=uncertainty,
        retrieved_passages=passages,
    )


def _select_requirements(
    requirements: list[RequirementSummary],
    requirement_ids: list[str] | None,
) -> list[RequirementSummary]:
    if not requirement_ids:
        return requirements
    wanted = {item.strip() for item in requirement_ids if item and item.strip()}
    if not wanted:
        raise HTTPException(
            status_code=400,
            detail="requirement_ids was provided but empty.",
        )
    selected = [item for item in requirements if item.requirement_id in wanted]
    missing = sorted(wanted - {item.requirement_id for item in selected})
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown requirement IDs: {missing}",
        )
    return selected


def _call_completer(
    complete: Completer,
    requirement_id: str,
    requirement_text: str,
    policy_text: str,
    filename: str,
    system_prompt: str,
) -> ModelFinding:
    try:
        return complete(
            requirement_id,
            requirement_text,
            policy_text,
            filename,
            system_prompt=system_prompt,
        )
    except TypeError:
        return complete(
            requirement_id,
            requirement_text,
            policy_text,
            filename,
        )


def evaluate_policy(
    policy_version: PolicyVersion,
    *,
    completer: Completer | None = None,
    inventory: list[RequirementSummary] | None = None,
    policy_text: str | None = None,
    requirement_ids: list[str] | None = None,
    evaluation_mode: EvaluationMode = "direct",
    retrieval_k: int = 4,
    passage_loader: Callable[..., list[RetrievedPassage]] | None = None,
) -> EvaluationResult:
    requirements = _select_requirements(
        inventory or load_requirement_inventory(),
        requirement_ids,
    )
    source_text = (
        policy_text if policy_text is not None else load_policy_text(policy_version)
    )
    filename = POLICY_FILES[policy_version]
    complete = completer or _openai_completer
    system_prompt = RAG_SYSTEM_PROMPT if evaluation_mode == "rag" else SYSTEM_PROMPT
    load_passages = passage_loader or passages_for_requirement
    findings: list[ComplianceFinding] = []

    for requirement in requirements:
        retrieved: list[RetrievedPassage] = []
        model_context = source_text
        try:
            if evaluation_mode == "rag":
                try:
                    retrieved = load_passages(
                        requirement.text,
                        policy_version,
                        k=retrieval_k,
                    )
                except TypeError:
                    retrieved = load_passages(requirement.text, policy_version)
                except Exception as exc:  # noqa: BLE001 - retrieval isolation
                    findings.append(
                        finalize_finding(
                            requirement,
                            None,
                            source_text,
                            filename,
                            failed=True,
                            failure_note=(
                                f"Retrieval failed for {requirement.requirement_id}: {exc}"
                            ),
                            retrieved_passages=[],
                        )
                    )
                    continue
                model_context = format_passages_for_prompt(retrieved)

            model_finding = _call_completer(
                complete,
                requirement.requirement_id,
                requirement.text,
                model_context,
                filename,
                system_prompt,
            )
            if model_finding.requirement_id != requirement.requirement_id:
                model_finding = model_finding.model_copy(
                    update={"requirement_id": requirement.requirement_id}
                )
            finding = finalize_finding(
                requirement,
                model_finding,
                source_text,
                filename,
                retrieved_passages=retrieved,
            )
            if evaluation_mode == "rag" and not retrieved and finding.evaluation_state != "failed":
                finding = finding.model_copy(
                    update={
                        "needs_review": True,
                        "evaluation_state": "needs_review",
                        "uncertainty_note": (
                            (finding.uncertainty_note + " ")
                            if finding.uncertainty_note
                            else ""
                        )
                        + "No policy passages were retrieved for this requirement.",
                    }
                )
            findings.append(finding)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - per-requirement isolation
            findings.append(
                finalize_finding(
                    requirement,
                    None,
                    source_text,
                    filename,
                    failed=True,
                    failure_note=f"Evaluation failed for {requirement.requirement_id}: {exc}",
                    retrieved_passages=retrieved,
                )
            )

    return EvaluationResult(
        id=str(uuid.uuid4()),
        policy_version=policy_version,
        source_document=filename,
        evaluation_mode=evaluation_mode,
        findings=findings,
    )
