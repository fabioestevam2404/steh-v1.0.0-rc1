from datetime import UTC, datetime
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.models.contracts import AgentResult
from app.models.test_plan import PlannedTestCase, TestPlan, TestType


class TestPlanningAgent:
    __test__ = False

    def __init__(self, mode: str, model: str, api_key: str | None) -> None:
        self.mode = mode
        self.model = model
        self.api_key = api_key

    def run(
        self,
        specification: dict[str, Any],
        architecture: dict[str, Any],
        security_review: dict[str, Any],
    ) -> AgentResult:
        if self.mode == "openai":
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY required")
            llm = ChatOpenAI(
                model=self.model,
                temperature=0,
                api_key=SecretStr(self.api_key),
            ).with_structured_output(TestPlan)
            plan = TestPlan.model_validate(
                llm.invoke(
                    "Create a test plan before implementation. Cover every "
                    "requirement identifier and include negative security tests.\n\n"
                    f"SPECIFICATION:\n{specification}\n\n"
                    f"ARCHITECTURE:\n{architecture}\n\n"
                    f"SECURITY REVIEW:\n{security_review}"
                )
            )
        else:
            requirement_ids = [item["id"] for item in specification.get("requirements", [])]
            plan = TestPlan(
                strategy="Validate behavior, integration boundaries and security.",
                test_cases=[
                    PlannedTestCase(
                        id="TC-001",
                        name="Specification happy path",
                        requirement_ids=requirement_ids,
                        test_type=TestType.INTEGRATION,
                        scenario="Exercise all specified customer API behavior.",
                        expected_result="All specified outcomes are observed.",
                    ),
                    PlannedTestCase(
                        id="TC-002",
                        name="Reject unauthorized access",
                        requirement_ids=requirement_ids,
                        test_type=TestType.SECURITY,
                        scenario="Request protected resources without credentials.",
                        expected_result="The request is rejected without data leakage.",
                        negative=True,
                    ),
                ],
                definition_of_done=[
                    "Every requirement is covered by a planned test.",
                    "Negative security behavior is verified.",
                ],
                risks=["Generated implementation may require environment fixtures."],
            )

        return AgentResult(
            agent="test_planning_agent",
            status="SUCCESS",
            result=plan.model_dump(mode="json"),
            evidence=[
                {
                    "type": "test_plan",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "test_case_count": len(plan.test_cases),
                }
            ],
            confidence=0.82 if self.mode == "stub" else 0.9,
        )
