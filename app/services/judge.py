import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml

from app.models.judge import (
    JudgeArtifactName,
    JudgeCriterionEvaluation,
    JudgeDimension,
    JudgeEvaluationArtifact,
    JudgeEvaluationStatus,
    JudgeInputSnapshot,
    JudgeProposal,
    JudgeRubric,
    JudgeVerdict,
)
from app.services.context import sanitize_context_text

JUDGE_ARTIFACT_NAMES: tuple[JudgeArtifactName, ...] = (
    "requirements",
    "specification",
    "architecture",
    "security_review",
    "test_plan",
    "implementation",
    "validation",
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_judge_rubric(path: str) -> JudgeRubric:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return JudgeRubric.model_validate(raw)


def judge_rubric_sha256(rubric: JudgeRubric) -> str:
    canonical = json.dumps(
        rubric.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256(canonical)


def judge_artifacts(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        name: state[name]
        for name in JUDGE_ARTIFACT_NAMES
        if state.get(name) is not None
    }


def build_judge_input(
    state: Mapping[str, Any],
    max_characters: int,
) -> JudgeInputSnapshot:
    if max_characters < 1:
        raise ValueError("Judge input limit must be positive.")
    artifacts = judge_artifacts(state)
    serialized = json.dumps(
        artifacts,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    sanitized = sanitize_context_text(serialized)
    content = sanitized.content[:max_characters]
    return JudgeInputSnapshot(
        content=content,
        input_sha256=_sha256(content),
        artifact_names=cast(list[JudgeArtifactName], list(artifacts)),
        truncated=len(sanitized.content) > max_characters,
        redacted=sanitized.redacted,
        suspicious_instruction=sanitized.suspicious_instruction,
    )


def _sanitize_output(value: str, fallback: str) -> tuple[str, bool, bool]:
    sanitized = sanitize_context_text(value)
    return (
        sanitized.content or fallback,
        sanitized.redacted,
        sanitized.suspicious_instruction,
    )


def compile_judge_evaluation(
    rubric: JudgeRubric,
    proposal: JudgeProposal,
    judge_input: JudgeInputSnapshot,
    provider: str,
    model: str,
    evaluated_at: datetime,
) -> JudgeEvaluationArtifact:
    proposed_ids = [item.criterion_id for item in proposal.criteria]
    expected_ids = [item.id for item in rubric.criteria]
    if len(proposed_ids) != len(set(proposed_ids)):
        raise ValueError("Judge proposal contains duplicate criterion identifiers.")
    if set(proposed_ids) != set(expected_ids):
        raise ValueError("Judge proposal must evaluate every rubric criterion exactly once.")

    proposal_by_id = {item.criterion_id: item for item in proposal.criteria}
    evaluations: list[JudgeCriterionEvaluation] = []
    output_redacted = False
    output_suspicious = False
    for criterion in rubric.criteria:
        proposed = proposal_by_id[criterion.id]
        rationale, redacted, suspicious = _sanitize_output(
            proposed.rationale,
            "No rationale was retained after sanitization.",
        )
        evidence_refs: list[str] = []
        for reference in proposed.evidence_refs:
            safe_reference, ref_redacted, ref_suspicious = _sanitize_output(
                reference,
                "[SANITIZED_EVIDENCE_REFERENCE]",
            )
            evidence_refs.append(safe_reference[:500])
            output_redacted = output_redacted or ref_redacted
            output_suspicious = output_suspicious or ref_suspicious
        output_redacted = output_redacted or redacted
        output_suspicious = output_suspicious or suspicious
        evaluations.append(
            JudgeCriterionEvaluation(
                criterion_id=criterion.id,
                dimension=criterion.dimension,
                description=criterion.description,
                score=proposed.score,
                weight=criterion.weight,
                weighted_score=round(proposed.score * criterion.weight, 4),
                rationale=rationale,
                evidence_refs=evidence_refs,
            )
        )

    overall_score = round(sum(item.weighted_score for item in evaluations))
    if overall_score >= rubric.pass_score:
        verdict = JudgeVerdict.PASS
    elif overall_score >= rubric.concern_score:
        verdict = JudgeVerdict.CONCERNS
    else:
        verdict = JudgeVerdict.FAIL

    dimension_scores: dict[JudgeDimension, int] = {}
    for dimension in JudgeDimension:
        dimension_items = [
            item for item in evaluations if item.dimension == dimension
        ]
        if dimension_items:
            total_weight = sum(item.weight for item in dimension_items)
            dimension_scores[dimension] = round(
                sum(item.score * item.weight for item in dimension_items)
                / total_weight
            )

    summary, summary_redacted, summary_suspicious = _sanitize_output(
        proposal.summary,
        "Judge summary was removed during sanitization.",
    )
    output_redacted = output_redacted or summary_redacted
    output_suspicious = output_suspicious or summary_suspicious
    limitations: list[str] = []
    for limitation in proposal.limitations:
        safe_limitation, redacted, suspicious = _sanitize_output(
            limitation,
            "Judge limitation was removed during sanitization.",
        )
        limitations.append(safe_limitation[:1000])
        output_redacted = output_redacted or redacted
        output_suspicious = output_suspicious or suspicious
    if judge_input.truncated:
        limitations.append("Judge input was truncated by the configured size limit.")
    if judge_input.suspicious_instruction:
        limitations.append("Judge input contained instruction-like untrusted data.")
    if output_suspicious:
        limitations.append("Judge output contained instruction-like content.")

    return JudgeEvaluationArtifact(
        rubric_version=rubric.version,
        rubric_sha256=judge_rubric_sha256(rubric),
        status=JudgeEvaluationStatus.COMPLETED,
        verdict=verdict,
        overall_score=overall_score,
        dimension_scores=dimension_scores,
        criteria=evaluations,
        summary=summary,
        limitations=list(dict.fromkeys(limitations))[:20],
        provider=provider,
        model=model,
        input_sha256=judge_input.input_sha256,
        input_truncated=judge_input.truncated,
        input_redacted=judge_input.redacted,
        output_redacted=output_redacted,
        suspicious_instruction=(
            judge_input.suspicious_instruction or output_suspicious
        ),
        authoritative=False,
        evaluated_at=evaluated_at,
    )


def non_authoritative_judge_result(
    status: JudgeEvaluationStatus,
    judge_input: JudgeInputSnapshot,
    provider: str,
    model: str,
    evaluated_at: datetime,
    error_type: str | None = None,
    rubric: JudgeRubric | None = None,
) -> JudgeEvaluationArtifact:
    rubric_version = rubric.version if rubric is not None else "unavailable"
    rubric_hash = judge_rubric_sha256(rubric) if rubric is not None else _sha256("")
    summary = (
        "Auxiliary judge evaluation is disabled."
        if status == JudgeEvaluationStatus.SKIPPED
        else "Auxiliary judge evaluation was unavailable; deterministic gates are unchanged."
    )
    return JudgeEvaluationArtifact(
        rubric_version=rubric_version,
        rubric_sha256=rubric_hash,
        status=status,
        verdict=JudgeVerdict.NOT_EVALUATED,
        summary=summary,
        limitations=[
            "This artifact never overrides tests, policies, scanners, or human review."
        ],
        provider=provider,
        model=model,
        input_sha256=judge_input.input_sha256,
        input_truncated=judge_input.truncated,
        input_redacted=judge_input.redacted,
        output_redacted=False,
        suspicious_instruction=judge_input.suspicious_instruction,
        authoritative=False,
        evaluated_at=evaluated_at,
        error_type=error_type,
    )


def judge_evaluation_receipt(
    evaluation: JudgeEvaluationArtifact,
) -> dict[str, Any]:
    return {
        "schema_version": evaluation.schema_version,
        "rubric_version": evaluation.rubric_version,
        "rubric_sha256": evaluation.rubric_sha256,
        "status": evaluation.status,
        "verdict": evaluation.verdict,
        "overall_score": evaluation.overall_score,
        "input_sha256": evaluation.input_sha256,
        "authoritative": False,
        "evaluated_at": evaluation.evaluated_at.isoformat(),
        "error_type": evaluation.error_type,
    }
