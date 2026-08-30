from pydantic import BaseModel, ConfigDict, Field


class FileChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    content: str
    reason: str


class ImplementationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    files: list[FileChange] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: str
    success: bool
    artifact: str | None = None
    message: str


class ImplementationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: ImplementationPlan
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    tool_results: list[ToolExecutionResult] = Field(default_factory=list)
