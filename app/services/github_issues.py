import hashlib
import json
from typing import NoReturn

from sqlalchemy.orm import Session

from app.agents.github_issue_analysis import GitHubIssueAnalysisAgent
from app.core.config import settings
from app.db.models import TaskRecord
from app.models.context import ContextKind, ContextSourceInput
from app.models.contracts import TaskCreate, TaskStatus, ids
from app.models.github_issue import (
    FetchedGitHubIssue,
    GitHubIssueReceipt,
    GitHubIssueReference,
    GitHubIssueSnapshot,
    IssueAnalysisArtifact,
)
from app.orchestration.lifecycle import AgentLifecycle
from app.services.audit import record_event
from app.services.context import sanitize_context_text
from app.services.github_client import GitHubIssueReader
from app.services.tasks import execute_task


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sanitize_github_issue(
    issue: FetchedGitHubIssue,
    max_body_characters: int = 20000,
) -> GitHubIssueSnapshot:
    if max_body_characters < 1:
        raise ValueError("GitHub issue body limit must be positive.")
    title = sanitize_context_text(issue.title)
    body = sanitize_context_text(issue.body)
    author = sanitize_context_text(issue.author)
    labels = [sanitize_context_text(label) for label in issue.labels]
    if not title.content:
        raise ValueError("GitHub issue title is empty after normalization.")
    if not author.content:
        raise ValueError("GitHub issue author is empty after normalization.")
    safe_labels = [label.content for label in labels if label.content]
    safe_body = body.content[:max_body_characters]
    truncated = len(body.content) > max_body_characters
    canonical_content = json.dumps(
        {
            "title": title.content,
            "body": safe_body,
            "labels": safe_labels,
            "author": author.content,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return GitHubIssueSnapshot.model_validate(
        issue.model_dump()
        | {
            "title": title.content,
            "body": safe_body,
            "labels": safe_labels,
            "author": author.content,
            "content_sha256": _sha256(canonical_content),
            "redacted": (
                title.redacted
                or body.redacted
                or author.redacted
                or any(label.redacted for label in labels)
            ),
            "suspicious_instruction": (
                title.suspicious_instruction
                or body.suspicious_instruction
                or author.suspicious_instruction
                or any(label.suspicious_instruction for label in labels)
            ),
            "truncated": truncated,
        }
    )


def github_issue_receipt(issue: GitHubIssueSnapshot) -> GitHubIssueReceipt:
    return GitHubIssueReceipt(
        repository=issue.repository,
        issue_number=issue.issue_number,
        state=issue.state,
        labels=issue.labels,
        issue_url=issue.issue_url,
        updated_at=issue.updated_at,
        content_sha256=issue.content_sha256,
        redacted=issue.redacted,
        suspicious_instruction=issue.suspicious_instruction,
        truncated=issue.truncated,
    )


def _task_request(analysis: IssueAnalysisArtifact) -> str:
    criteria = "\n".join(f"- {item}" for item in analysis.acceptance_criteria)
    return (
        f"Implement GitHub issue {analysis.repository}#{analysis.issue_number}: "
        f"{analysis.summary}\n\n"
        f"Problem statement:\n{analysis.problem_statement}\n\n"
        f"Acceptance criteria:\n{criteria}"
    )[:10000]


def _context_sources(
    issue: GitHubIssueSnapshot,
    analysis: IssueAnalysisArtifact,
) -> list[ContextSourceInput]:
    repository_id = _sha256(issue.repository.casefold())[:16]
    source_prefix = f"github/issues/{repository_id}/{issue.issue_number}"
    issue_content = json.dumps(
        {
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "labels": issue.labels,
            "author": issue.author,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return [
        ContextSourceInput(
            source_id=source_prefix,
            kind=ContextKind.REQUIREMENTS,
            version=issue.updated_at.isoformat(),
            content=issue_content,
            priority=100,
            metadata={
                "repository": issue.repository,
                "issue_number": str(issue.issue_number),
            },
        ),
        ContextSourceInput(
            source_id=f"{source_prefix}/analysis",
            kind=ContextKind.REQUIREMENTS,
            version=analysis.schema_version,
            content=analysis.model_dump_json(),
            priority=90,
            metadata={"agent": GitHubIssueAnalysisAgent.name},
        ),
    ]


def _fail_task(
    db: Session,
    record: TaskRecord,
    error: Exception,
) -> NoReturn:
    db.rollback()
    record.status = TaskStatus.FAILED
    db.commit()
    record_event(
        db,
        record.task_id,
        record.trace_id,
        "TASK_FAILED",
        "github_issue_analysis",
        {"error_type": type(error).__name__},
    )
    raise error


def create_task_from_github_issue(
    db: Session,
    reference: GitHubIssueReference,
    reader: GitHubIssueReader,
) -> TaskRecord:
    fetched = reader.fetch(reference)
    issue = sanitize_github_issue(
        fetched,
        max_body_characters=settings.github_issue_max_body_chars,
    )
    task_id, trace_id = ids()
    record = TaskRecord(
        task_id=task_id,
        trace_id=trace_id,
        request=issue.title,
        status=TaskStatus.ANALYZING_ISSUE,
        source_issue=issue.model_dump(mode="json"),
    )
    db.add(record)
    db.commit()
    record_event(
        db,
        task_id,
        trace_id,
        "TASK_CREATED",
        "github_issue_api",
        {"source": "github_issue"},
    )
    record_event(
        db,
        task_id,
        trace_id,
        "GITHUB_ISSUE_INGESTED",
        "github_issue_client",
        github_issue_receipt(issue).model_dump(mode="json"),
    )

    try:
        agent = GitHubIssueAnalysisAgent(
            settings.llm_mode,
            settings.llm_model,
            settings.openai_api_key,
        )
        analysis_result = AgentLifecycle(db, task_id, trace_id).execute(
            GitHubIssueAnalysisAgent.name,
            lambda: agent.run(issue),
        )
        analysis = IssueAnalysisArtifact.model_validate(analysis_result.result)
        record.issue_analysis = analysis.model_dump(mode="json")
        record.request = _task_request(analysis)
        db.commit()
        record_event(
            db,
            task_id,
            trace_id,
            "GITHUB_ISSUE_ANALYZED",
            GitHubIssueAnalysisAgent.name,
            {
                "issue_kind": analysis.issue_kind,
                "priority": analysis.priority,
                "recommendation": analysis.recommendation,
                "source_content_sha256": analysis.source_content_sha256,
            },
        )
        payload = TaskCreate(
            request=record.request,
            context_sources=_context_sources(issue, analysis),
        )
        return execute_task(db, task_id, trace_id, payload)
    except Exception as exc:
        _fail_task(db, record, exc)
