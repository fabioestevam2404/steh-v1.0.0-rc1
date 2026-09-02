from datetime import UTC, datetime
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.models.contracts import AgentResult
from app.models.specification import (
    AcceptanceScenario,
    RequirementKind,
    SoftwareSpecification,
    SpecificationRequirement,
)


class SpecificationAgent:
    def __init__(self, mode: str, model: str, api_key: str | None) -> None:
        self.mode = mode
        self.model = model
        self.api_key = api_key

    def run(self, requirements: dict[str, Any]) -> AgentResult:
        if self.mode == "openai":
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY required")
            llm = ChatOpenAI(
                model=self.model,
                temperature=0,
                api_key=SecretStr(self.api_key),
            ).with_structured_output(SoftwareSpecification)
            specification = SoftwareSpecification.model_validate(
                llm.invoke(
                    "Create an implementation-ready software specification. "
                    "Assign stable FR-### and NFR-### identifiers and express "
                    "acceptance scenarios with explicit Given, When and Then.\n\n"
                    f"REQUIREMENTS:\n{requirements}"
                )
            )
        else:
            specification = SoftwareSpecification(
                title="Customer management API specification",
                summary="Versioned API for secure customer management.",
                requirements=[
                    SpecificationRequirement(
                        id="FR-001",
                        kind=RequirementKind.FUNCTIONAL,
                        statement="The API shall manage customer records.",
                        source="functional_requirements[0]",
                    ),
                    SpecificationRequirement(
                        id="NFR-001",
                        kind=RequirementKind.NON_FUNCTIONAL,
                        statement="The API shall protect customer data.",
                        source="non_functional_requirements[0]",
                    ),
                ],
                acceptance_scenarios=[
                    AcceptanceScenario(
                        id="AC-001",
                        requirement_ids=["FR-001"],
                        given="an authenticated API client",
                        when="a valid customer request is submitted",
                        then="the customer record is persisted",
                    ),
                    AcceptanceScenario(
                        id="AC-002",
                        requirement_ids=["NFR-001"],
                        given="an unauthenticated API client",
                        when="protected customer data is requested",
                        then="access is denied without exposing data",
                    ),
                ],
                assumptions=requirements.get("assumptions", []),
                open_questions=requirements.get("open_questions", []),
            )

        return AgentResult(
            agent="specification_agent",
            status="SUCCESS",
            result=specification.model_dump(mode="json"),
            evidence=[
                {
                    "type": "software_specification",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "requirement_count": len(specification.requirements),
                    "scenario_count": len(specification.acceptance_scenarios),
                }
            ],
            confidence=0.82 if self.mode == "stub" else 0.9,
        )
