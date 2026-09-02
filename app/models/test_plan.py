from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TestType(StrEnum):
    UNIT = "UNIT"
    INTEGRATION = "INTEGRATION"
    E2E = "E2E"
    SECURITY = "SECURITY"


class PlannedTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^TC-\d{3}$")
    name: str = Field(min_length=1)
    requirement_ids: list[str] = Field(min_length=1)
    test_type: TestType
    scenario: str = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    negative: bool = False


class TestPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str = Field(min_length=1)
    test_cases: list[PlannedTestCase] = Field(min_length=1)
    definition_of_done: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
