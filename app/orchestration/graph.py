from langgraph.graph import END, START, StateGraph

from app.agents.architecture import ArchitectureAgent
from app.agents.implementation import ImplementationAgent
from app.agents.requirements import RequirementsAgent
from app.agents.security import SecurityAgent
from app.agents.test_engineer import TestAgent
from app.core.config import settings
from app.models.state import EngineeringState
from app.orchestration.checkpoint import get_checkpointer
from app.policies.engine import PolicyEngine
from app.policies.loader import load_policy_config


def build_graph(lifecycle=None):
    requirements_agent = RequirementsAgent(
        settings.llm_mode,
        settings.llm_model,
        settings.openai_api_key,
    )

    architecture_agent = ArchitectureAgent(
        settings.llm_mode,
        settings.llm_model,
        settings.openai_api_key,
    )

    security_agent = SecurityAgent(
        settings.llm_mode,
        settings.llm_model,
        settings.openai_api_key,
    )

    implementation_agent = ImplementationAgent(
        settings.llm_mode,
        settings.llm_model,
        settings.openai_api_key,
    )

    test_agent = TestAgent()

    policy_engine = PolicyEngine(
        load_policy_config(settings.policy_file)
    )

    def requirements(state: EngineeringState) -> dict:
        def call():
            return requirements_agent.run(
                state["user_request"]
            )

        result = (
            lifecycle.execute(
                "requirements_agent",
                call,
            )
            if lifecycle
            else call()
        )

        return {
            "requirements": result.result,
            "requirements_run": result.model_dump(),
            "evidence": result.evidence,
            "status": "ANALYZING",
        }

    def requirements_gate(
        state: EngineeringState,
    ) -> dict:
        decisions = [
            policy_engine.evaluate(
                "REQ-001",
                state,
            ),
            policy_engine.evaluate(
                "AUDIT-001",
                state,
            ),
        ]

        blocked = any(
            not decision.passed
            and decision.action == "BLOCK"
            for decision in decisions
        )

        return {
            "policy_results": [
                decision.__dict__
                for decision in decisions
            ],
            "blocked": blocked,
        }

    def architecture(
        state: EngineeringState,
    ) -> dict:
        def call():
            return architecture_agent.run(
                state["requirements"]
            )

        result = (
            lifecycle.execute(
                "architecture_agent",
                call,
            )
            if lifecycle
            else call()
        )

        return {
            "architecture": result.result,
            "architecture_run": result.model_dump(),
            "evidence": [
                *state.get("evidence", []),
                *result.evidence,
            ],
            "status": "ARCHITECTING",
        }

    def architecture_gate(
        state: EngineeringState,
    ) -> dict:
        decision = policy_engine.evaluate(
            "ARCH-001",
            state,
        )

        return {
            "policy_results": [
                *state.get(
                    "policy_results",
                    [],
                ),
                decision.__dict__,
            ],
            "blocked": not decision.passed,
        }

    def security(
        state: EngineeringState,
    ) -> dict:
        def call():
            return security_agent.run(
                state["requirements"],
                state["architecture"],
            )

        result = (
            lifecycle.execute(
                "security_agent",
                call,
            )
            if lifecycle
            else call()
        )

        review = result.result

        return {
            "security_review": review,
            "security_run": result.model_dump(),
            "risk_level": review["overall_risk"],
            "evidence": [
                *state.get("evidence", []),
                *result.evidence,
            ],
            "status": "SECURITY_REVIEW",
        }

    def security_gate(
        state: EngineeringState,
    ) -> dict:
        decisions = [
            policy_engine.evaluate(
                "SEC-001",
                state,
            ),
            policy_engine.evaluate(
                "SEC-002",
                state,
            ),
            policy_engine.evaluate(
                "SEC-003",
                state,
            ),
            policy_engine.evaluate(
                "SEC-004",
                state,
            ),
        ]

        hard_block = any(
            not decision.passed
            and decision.action == "BLOCK"
            for decision in decisions
        )

        human_review = any(
            not decision.passed
            and decision.action == "HUMAN_REVIEW"
            for decision in decisions
        )

        if hard_block:
            status = "BLOCKED"
        elif human_review:
            status = "HUMAN_REVIEW"
        else:
            status = "READY_FOR_IMPLEMENTATION"

        return {
            "policy_results": [
                *state.get(
                    "policy_results",
                    [],
                ),
                *[
                    decision.__dict__
                    for decision in decisions
                ],
            ],
            "blocked": hard_block,
            "status": status,
        }

    def route_after_security(
        state: EngineeringState,
    ) -> str:
        status = state.get("status")

        if status == "READY_FOR_IMPLEMENTATION":
            return "implementation"

        return "end"

    def implementation(
        state: EngineeringState,
    ) -> dict:
        def call():
            return implementation_agent.run(
                state["task_id"],
                state["requirements"],
                state["architecture"],
                state["security_review"],
            )

        result = (
            lifecycle.execute(
                "implementation_agent",
                call,
            )
            if lifecycle
            else call()
        )

        return {
            "implementation": result.result,
            "implementation_run": result.model_dump(),
            "evidence": [
                *state.get("evidence", []),
                *result.evidence,
            ],
            "status": "IMPLEMENTING",
        }

    def implementation_gate(
        state: EngineeringState,
    ) -> dict:
        decision = policy_engine.evaluate(
            "IMPL-001",
            state,
        )

        return {
            "policy_results": [
                *state.get(
                    "policy_results",
                    [],
                ),
                decision.__dict__,
            ],
            "blocked": not decision.passed,
            "status": (
                "BLOCKED"
                if not decision.passed
                else "COMPLETED"
            ),
        }

    def validation(
        state: EngineeringState,
    ) -> dict:
        def call():
            return test_agent.run(
                state["task_id"],
                state["implementation"],
            )

        result = (
            lifecycle.execute(
                "test_agent",
                call,
            )
            if lifecycle
            else call()
        )

        return {
            "validation": result.result,
            "test_run": result.model_dump(),
            "evidence": [
                *state.get("evidence", []),
                *result.evidence,
            ],
            "status": "VALIDATING",
        }

    def validation_gate(
        state: EngineeringState,
    ) -> dict:
        decisions = [
            policy_engine.evaluate(
                "TEST-001",
                state,
            ),
            policy_engine.evaluate(
                "SCAN-001",
                state,
            ),
        ]

        requires_rework = any(
            not decision.passed
            for decision in decisions
        )

        return {
            "policy_results": [
                *state.get(
                    "policy_results",
                    [],
                ),
                *[
                    decision.__dict__
                    for decision in decisions
                ],
            ],
            "status": (
                "REWORK_REQUIRED"
                if requires_rework
                else "COMPLETED"
            ),
            "rework_count": state.get(
                "rework_count",
                0,
            ),
        }

    def route_after_requirements(
        state: EngineeringState,
    ) -> str:
        return (
            "blocked"
            if state.get("blocked")
            else "architecture"
        )

    def route_after_architecture(
        state: EngineeringState,
    ) -> str:
        return (
            "blocked"
            if state.get("blocked")
            else "security"
        )

    def blocked(_: EngineeringState) -> dict:
        return {
            "status": "BLOCKED",
        }

    builder = StateGraph(EngineeringState)

    builder.add_node(
        "requirements",
        requirements,
    )

    builder.add_node(
        "requirements_gate",
        requirements_gate,
    )

    builder.add_node(
        "architecture",
        architecture,
    )

    builder.add_node(
        "architecture_gate",
        architecture_gate,
    )

    builder.add_node(
        "security",
        security,
    )

    builder.add_node(
        "security_gate",
        security_gate,
    )

    builder.add_node(
        "implementation",
        implementation,
    )

    builder.add_node(
        "implementation_gate",
        implementation_gate,
    )

    builder.add_node(
        "validation",
        validation,
    )

    builder.add_node(
        "validation_gate",
        validation_gate,
    )

    builder.add_node(
        "blocked",
        blocked,
    )

    builder.add_edge(
        START,
        "requirements",
    )

    builder.add_edge(
        "requirements",
        "requirements_gate",
    )

    builder.add_conditional_edges(
        "requirements_gate",
        route_after_requirements,
        {
            "architecture": "architecture",
            "blocked": "blocked",
        },
    )

    builder.add_edge(
        "architecture",
        "architecture_gate",
    )

    builder.add_conditional_edges(
        "architecture_gate",
        route_after_architecture,
        {
            "security": "security",
            "blocked": "blocked",
        },
    )

    builder.add_edge(
        "security",
        "security_gate",
    )

    builder.add_conditional_edges(
        "security_gate",
        route_after_security,
        {
            "implementation": "implementation",
            "end": END,
        },
    )

    builder.add_edge(
        "implementation",
        "implementation_gate",
    )

    builder.add_edge(
        "implementation_gate",
        "validation",
    )

    builder.add_edge(
        "validation",
        "validation_gate",
    )

    builder.add_edge(
        "validation_gate",
        END,
    )

    builder.add_edge(
        "blocked",
        END,
    )

    return builder.compile(
        checkpointer=get_checkpointer()
    )