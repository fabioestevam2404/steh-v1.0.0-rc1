from datetime import datetime, timezone
from app.models.contracts import AgentResult, ArchitectureResult

class ArchitectureAgent:
    name = "architecture_agent"
    def __init__(self, mode: str, model_name: str, api_key: str | None = None):
        self.mode, self.model_name, self.api_key = mode, model_name, api_key

    def run(self, requirements: dict) -> AgentResult:
        if self.mode == "openai":
            from langchain_openai import ChatOpenAI
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY required")
            model = ChatOpenAI(model=self.model_name, api_key=self.api_key, temperature=0)
            structured = model.with_structured_output(ArchitectureResult)
            artifact = ArchitectureResult.model_validate(structured.invoke([
                ("system","You are STEH Architecture Agent. Prioritize security, observability, auditability, scalability, reliability and explicit tradeoffs. Return only structured architecture."),
                ("human",str(requirements)),
            ]))
            confidence = 0.88
        else:
            artifact = ArchitectureResult(
                architecture_style="modular_monolith",
                components=[
                    {"name":"API Layer","responsibility":"Validated HTTP boundary","technology_options":["FastAPI"]},
                    {"name":"Agent Orchestration","responsibility":"Coordinate specialized agents and workflow state","technology_options":["LangGraph"]},
                    {"name":"Persistence","responsibility":"Persist tasks, agent runs and audit events","technology_options":["PostgreSQL"]},
                ],
                data_flow=["API -> Requirements Agent -> Gate -> Architecture Agent -> Gate -> Persistence"],
                security_considerations=["Validate input","No secrets in logs","No shell/host access"],
                scalability_considerations=["Externalize state","Prepare asynchronous workers"],
                observability_considerations=["Propagate trace_id","Persist agent runs and audit events"],
                decisions=[{"title":"Modular monolith","decision":"Use one deployable unit initially","rationale":"Reduce distributed complexity","tradeoffs":["May require later extraction"]}],
                assumptions=["Requirements artifact is validated input."],
            )
            confidence = 0.55
        return AgentResult(
            agent=self.name, status="SUCCESS", result=artifact.model_dump(),
            evidence=[{"type":"architecture_artifact","timestamp":datetime.now(timezone.utc).isoformat()}],
            confidence=confidence,
        )
