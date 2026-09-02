from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RequirementKind(StrEnum):
    FUNCTIONAL = "FUNCTIONAL"
    NON_FUNCTIONAL = "NON_FUNCTIONAL"


class SpecificationRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^(FR|NFR)-\d{3}$")
    kind: RequirementKind
    statement: str = Field(min_length=1)
    source: str = Field(min_length=1)


class AcceptanceScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^AC-\d{3}$")
    requirement_ids: list[str] = Field(min_length=1)
    given: str = Field(min_length=1)
    when: str = Field(min_length=1)
    then: str = Field(min_length=1)


class SoftwareSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    requirements: list[SpecificationRequirement] = Field(min_length=1)
    acceptance_scenarios: list[AcceptanceScenario] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
