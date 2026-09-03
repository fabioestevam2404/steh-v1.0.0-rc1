from datetime import UTC, datetime, timedelta

from app.models.human_review import (
    HumanReviewArtifact,
    HumanReviewDecision,
    HumanReviewStatus,
)
from app.services.tasks import resolve_review_outcome


def pending_review(now: datetime) -> HumanReviewArtifact:
    return HumanReviewArtifact(
        status=HumanReviewStatus.PENDING,
        requested_at=now,
        expires_at=now + timedelta(minutes=30),
        policy_result_count=6,
    )


def test_approval_is_accepted_before_expiration() -> None:
    now = datetime.now(UTC)
    outcome, justification = resolve_review_outcome(
        pending_review(now),
        HumanReviewDecision(
            decision="APPROVE",
            justification="Risk accepted with compensating controls.",
        ),
        now + timedelta(minutes=5),
    )

    assert outcome == HumanReviewStatus.APPROVED
    assert justification == "Risk accepted with compensating controls."


def test_approval_becomes_expired_after_deadline() -> None:
    now = datetime.now(UTC)
    outcome, justification = resolve_review_outcome(
        pending_review(now),
        HumanReviewDecision(
            decision="APPROVE",
            justification="Risk accepted after reviewing the evidence.",
        ),
        now + timedelta(minutes=31),
    )

    assert outcome == HumanReviewStatus.EXPIRED
    assert "expired" in justification
