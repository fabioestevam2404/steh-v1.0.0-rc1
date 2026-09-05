import hashlib
import json
from typing import NoReturn

from sqlalchemy.orm import Session

from app.agents.pull_request_review import PullRequestReviewAgent
from app.core.config import settings
from app.db.models import TaskRecord
from app.models.context import ContextKind, ContextSourceInput
from app.models.contracts import TaskStatus, ids, utc_now
from app.models.github_pull_request import (
    FetchedGitHubPullRequest,
    GitHubPullRequestReceipt,
    GitHubPullRequestReference,
    GitHubPullRequestSnapshot,
    PullRequestFileSnapshot,
    PullRequestReviewArtifact,
)
from app.orchestration.lifecycle import AgentLifecycle
from app.services.audit import record_event
from app.services.context import ContextEngine, context_receipt, sanitize_context_text
from app.services.github_pull_requests import GitHubPullRequestReader


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sanitize_github_pull_request(
    pull_request: FetchedGitHubPullRequest,
    max_patch_characters: int = 100000,
) -> GitHubPullRequestSnapshot:
    if max_patch_characters < 1:
        raise ValueError("GitHub pull request patch limit must be positive.")

    title = sanitize_context_text(pull_request.title)
    body = sanitize_context_text(pull_request.body)
    author = sanitize_context_text(pull_request.author)
    base_ref = sanitize_context_text(pull_request.base_ref)
    head_ref = sanitize_context_text(pull_request.head_ref)
    if not title.content or not author.content:
        raise ValueError("GitHub pull request identity is empty after normalization.")
    if not base_ref.content or not head_ref.content:
        raise ValueError("GitHub pull request refs are empty after normalization.")

    remaining = max_patch_characters
    files: list[PullRequestFileSnapshot] = []
    any_redacted = title.redacted or body.redacted or author.redacted
    any_suspicious = (
        title.suspicious_instruction
        or body.suspicious_instruction
        or author.suspicious_instruction
    )
    any_truncated = pull_request.files_truncated

    for item in pull_request.files:
        filename = sanitize_context_text(item.filename)
        previous = (
            sanitize_context_text(item.previous_filename)
            if item.previous_filename is not None
            else None
        )
        patch = sanitize_context_text(item.patch)
        if not filename.content:
            raise ValueError("GitHub pull request filename is empty after normalization.")
        safe_patch = patch.content[:remaining]
        patch_missing = not patch.content and item.changes > 0
        patch_truncated = len(patch.content) > remaining or patch_missing
        remaining -= len(safe_patch)
        file_redacted = (
            filename.redacted
            or patch.redacted
            or (previous.redacted if previous is not None else False)
        )
        file_suspicious = (
            filename.suspicious_instruction
            or patch.suspicious_instruction
            or (previous.suspicious_instruction if previous is not None else False)
        )
        files.append(
            PullRequestFileSnapshot(
                filename=filename.content,
                status=item.status,
                additions=item.additions,
                deletions=item.deletions,
                changes=item.changes,
                patch=safe_patch,
                previous_filename=(
                    previous.content if previous is not None else None
                ),
                patch_sha256=_sha256(safe_patch),
                redacted=file_redacted,
                suspicious_instruction=file_suspicious,
                truncated=patch_truncated,
            )
        )
        any_redacted = any_redacted or file_redacted
        any_suspicious = any_suspicious or file_suspicious
        any_truncated = any_truncated or patch_truncated

    canonical_content = json.dumps(
        {
            "repository": pull_request.repository,
            "pull_number": pull_request.pull_number,
            "title": title.content,
            "body": body.content,
            "author": author.content,
            "base_ref": base_ref.content,
            "base_sha": pull_request.base_sha,
            "head_ref": head_ref.content,
            "head_sha": pull_request.head_sha,
            "files": [item.model_dump(mode="json") for item in files],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return GitHubPullRequestSnapshot(
        repository=pull_request.repository,
        pull_number=pull_request.pull_number,
        title=title.content,
        body=body.content,
        state=pull_request.state,
        author=author.content,
        pull_request_url=pull_request.pull_request_url,
        updated_at=pull_request.updated_at,
        base_ref=base_ref.content,
        base_sha=pull_request.base_sha,
        head_ref=head_ref.content,
        head_sha=pull_request.head_sha,
        draft=pull_request.draft,
        merged=pull_request.merged,
        changed_files=pull_request.changed_files,
        additions=pull_request.additions,
        deletions=pull_request.deletions,
        files=files,
        content_sha256=_sha256(canonical_content),
        redacted=any_redacted,
        suspicious_instruction=any_suspicious,
        truncated=any_truncated,
    )


def github_pull_request_receipt(
    pull_request: GitHubPullRequestSnapshot,
) -> GitHubPullRequestReceipt:
    return GitHubPullRequestReceipt(
        repository=pull_request.repository,
        pull_number=pull_request.pull_number,
        state=pull_request.state,
        pull_request_url=pull_request.pull_request_url,
        updated_at=pull_request.updated_at,
        base_ref=pull_request.base_ref,
        base_sha=pull_request.base_sha,
        head_ref=pull_request.head_ref,
        head_sha=pull_request.head_sha,
        draft=pull_request.draft,
        merged=pull_request.merged,
        changed_files=pull_request.changed_files,
        fetched_files=len(pull_request.files),
        additions=pull_request.additions,
        deletions=pull_request.deletions,
        content_sha256=pull_request.content_sha256,
        redacted=pull_request.redacted,
        suspicious_instruction=pull_request.suspicious_instruction,
        truncated=pull_request.truncated,
    )


def _context_source(
    pull_request: GitHubPullRequestSnapshot,
) -> ContextSourceInput:
    repository_id = _sha256(pull_request.repository.casefold())[:16]
    return ContextSourceInput(
        source_id=(
            f"github/pulls/{repository_id}/{pull_request.pull_number}"
        ),
        kind=ContextKind.REPOSITORY,
        version=pull_request.head_sha,
        content=pull_request.model_dump_json(),
        priority=100,
        metadata={
            "repository": pull_request.repository,
            "pull_number": str(pull_request.pull_number),
            "base_ref": pull_request.base_ref,
            "head_ref": pull_request.head_ref,
        },
    )


def _fail_task(
    db: Session,
    record: TaskRecord,
    error: Exception,
) -> NoReturn:
    db.rollback()
    record.status = TaskStatus.FAILED
    record.updated_at = utc_now()
    db.commit()
    record_event(
        db,
        record.task_id,
        record.trace_id,
        "TASK_FAILED",
        "pull_request_review",
        {"error_type": type(error).__name__},
    )
    raise error


def create_pull_request_review(
    db: Session,
    reference: GitHubPullRequestReference,
    reader: GitHubPullRequestReader,
) -> TaskRecord:
    fetched = reader.fetch(reference)
    pull_request = sanitize_github_pull_request(
        fetched,
        max_patch_characters=settings.github_pr_max_patch_chars,
    )
    task_id, trace_id = ids()
    record = TaskRecord(
        task_id=task_id,
        trace_id=trace_id,
        request=(
            f"Review GitHub pull request {pull_request.repository}"
            f"#{pull_request.pull_number}: {pull_request.title}"
        )[:10000],
        status=TaskStatus.ANALYZING_PULL_REQUEST,
        source_pull_request=pull_request.model_dump(mode="json"),
    )
    db.add(record)
    db.commit()
    record_event(
        db,
        task_id,
        trace_id,
        "TASK_CREATED",
        "github_pull_request_api",
        {"source": "github_pull_request"},
    )
    record_event(
        db,
        task_id,
        trace_id,
        "GITHUB_PULL_REQUEST_INGESTED",
        "github_pull_request_client",
        github_pull_request_receipt(pull_request).model_dump(mode="json"),
    )

    try:
        context = ContextEngine(
            max_sources=settings.context_max_sources,
            max_tokens=settings.context_max_tokens,
            max_source_tokens=settings.context_max_source_tokens,
        ).build(record.request, [_context_source(pull_request)])
        record.context_bundle = context.model_dump(mode="json")
        db.commit()
        record_event(
            db,
            task_id,
            trace_id,
            "CONTEXT_BUNDLE_CREATED",
            "context_engine",
            context_receipt(context).model_dump(mode="json"),
        )

        agent = PullRequestReviewAgent(
            settings.llm_mode,
            settings.llm_model,
            settings.openai_api_key,
        )
        result = AgentLifecycle(db, task_id, trace_id).execute(
            PullRequestReviewAgent.name,
            lambda: agent.run(pull_request, context),
        )
        review = PullRequestReviewArtifact.model_validate(result.result)
        record.pull_request_review = review.model_dump(mode="json")
        record.status = TaskStatus.COMPLETED
        record.updated_at = utc_now()
        db.commit()
        record_event(
            db,
            task_id,
            trace_id,
            "GITHUB_PULL_REQUEST_REVIEWED",
            PullRequestReviewAgent.name,
            {
                "risk_level": review.risk_level,
                "recommendation": review.recommendation,
                "finding_count": len(review.findings),
                "source_content_sha256": review.source_content_sha256,
                "context_bundle_sha256": review.context_bundle_sha256,
                "requires_human_review": review.requires_human_review,
            },
        )
        record_event(
            db,
            task_id,
            trace_id,
            "TASK_COMPLETED",
            "pull_request_review",
            {"status": record.status},
        )
        db.refresh(record)
        return record
    except Exception as exc:
        _fail_task(db, record, exc)
