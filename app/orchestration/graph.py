from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.architecture import ArchitectureAgent
from app.agents.implementation import ImplementationAgent
from app.agents.requirements import RequirementsAgent
from app.agents.security import SecurityAgent
from app.agents.specification import SpecificationAgent
from app.agents.test_engineer import TestAgent
from app.agents.test_planning import TestPlanningAgent
from app.core.config import settings
from app.models.contracts import AgentResult
from app.models.state import EngineeringState
from app.orchestration.checkpoint import get_checkpointer
from app.orchestration.lifecycle import AgentLifecycle
from app.orchestration.rework import ReworkController
from app.policies.engine import PolicyEngine
from app.policies.loader import load_policy_config

StateUpdate = EngineeringState
Workflow = CompiledStateGraph[
    EngineeringState,
    None,
    EngineeringState,
    EngineeringState,
]


def build_graph(
    lifecycle: AgentLifecycle | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Workflow:
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

    specification_agent = SpecificationAgent(
        settings.llm_mode, settings.llm_model, settings.openai_api_key
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
    test_planning_agent = TestPlanningAgent(
        settings.llm_mode, settings.llm_model, settings.openai_api_key
    )

    policy_engine = PolicyEngine(
        load_policy_config(settings.policy_file)
    )
    rework_controller = ReworkController()

    def requirements(state: EngineeringState) -> StateUpdate:
        def call() -> AgentResult:
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
    ) -> StateUpdate:
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

    def specification(state: EngineeringState) -> StateUpdate:
        def call() -> AgentResult:
            return specification_agent.run(state["requirements"])

        result = lifecycle.execute("specification_agent", call) if lifecycle else call()
        return {
            "specification": result.result,
            "specification_run": result.model_dump(),
            "evidence": [*state.get("evidence", []), *result.evidence],
            "status": "SPECIFYING",
        }

    def specification_gate(state: EngineeringState) -> StateUpdate:
        decisions = [
            policy_engine.evaluate(policy_id, state)
            for policy_id in ("SPEC-001", "SPEC-002", "SPEC-003", "TRACE-001")
        ]
        blocked = any(not decision.passed for decision in decisions)
        return {
            "policy_results": [
                *state.get("policy_results", []),
                *[decision.__dict__ for decision in decisions],
            ],
            "blocked": blocked,
        }

    def architecture(
        state: EngineeringState,
    ) -> StateUpdate:
        def call() -> AgentResult:
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
    ) -> StateUpdate:
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
    ) -> StateUpdate:
        def call() -> AgentResult:
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
    ) -> StateUpdate:
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
            return "test_planning"

        return "end"

    def test_planning(state: EngineeringState) -> StateUpdate:
        def call() -> AgentResult:
            return test_planning_agent.run(
                state["specification"],
                state["architecture"],
                state["security_review"],
            )

        result = lifecycle.execute("test_planning_agent", call) if lifecycle else call()
        return {
            "test_plan": result.result,
            "test_plan_run": result.model_dump(),
            "evidence": [*state.get("evidence", []), *result.evidence],
            "status": "TEST_PLANNING",
        }

    def test_plan_gate(state: EngineeringState) -> StateUpdate:
        decisions = [
            policy_engine.evaluate(policy_id, state)
            for policy_id in ("TESTPLAN-001", "TESTPLAN-002", "TESTPLAN-003")
        ]
        blocked = any(not decision.passed for decision in decisions)
        return {
            "policy_results": [
                *state.get("policy_results", []),
                *[decision.__dict__ for decision in decisions],
            ],
            "blocked": blocked,
        }

    def implementation(
        state: EngineeringState,
    ) -> StateUpdate:
        def call() -> AgentResult:
            return implementation_agent.run(
                state["task_id"],
                state["requirements"],
                state["architecture"],
                state["security_review"],
                state["test_plan"],
                state.get("rework_decision"),
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
    ) -> StateUpdate:
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
                else "IMPLEMENTING"
            ),
        }

    def route_after_implementation(state: EngineeringState) -> str:
        return "blocked" if state.get("blocked") else "validation"

    def validation(
        state: EngineeringState,
    ) -> StateUpdate:
        def call() -> AgentResult:
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
    ) -> StateUpdate:
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

        reasons = [decision.reason for decision in decisions if not decision.passed]
        current_attempt = state.get("rework_count", 0)
        decision = rework_controller.decide(
            current_attempt + 1 if reasons else current_attempt,
            reasons,
        )
        serialized_decision = decision.model_dump(mode="json")

        if not decision.required:
            next_status = "COMPLETED"
        elif decision.exhausted:
            next_status = "REWORK_EXHAUSTED"
        elif decision.automatic:
            next_status = "REWORK_REQUIRED"
        else:
            next_status = "HUMAN_REVIEW"

        rework_evidence = {
            "type": "rework_decision",
            "timestamp": datetime.now(UTC).isoformat(),
            **serialized_decision,
        }

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
            "status": next_status,
            "rework_count": decision.attempt,
            "rework_decision": serialized_decision,
            "rework_history": [
                *state.get("rework_history", []),
                serialized_decision,
            ],
            "evidence": [
                *state.get("evidence", []),
                rework_evidence,
            ],
        }

    def route_after_validation(state: EngineeringState) -> str:
        return (
            "implementation"
            if state.get("status") == "REWORK_REQUIRED"
            else "end"
        )

    def route_after_requirements(
        state: EngineeringState,
    ) -> str:
        return (
            "blocked"
            if state.get("blocked")
            else "specification"
        )

    def route_after_specification(state: EngineeringState) -> str:
        return "blocked" if state.get("blocked") else "architecture"

    def route_after_architecture(
        state: EngineeringState,
    ) -> str:
        return (
            "blocked"
            if state.get("blocked")
            else "security"
        )

    def route_after_test_plan(state: EngineeringState) -> str:
        return "blocked" if state.get("blocked") else "implementation"

    builder = StateGraph[
        EngineeringState,
        None,
        EngineeringState,
        EngineeringState,
    ](EngineeringState)

    builder.add_node(
        "requirements",
        requirements,
    )

    builder.add_node(
        "requirements_gate",
        requirements_gate,
    )

    builder.add_node("specification", specification)
    builder.add_node("specification_gate", specification_gate)

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

    builder.add_node("test_planning", test_planning)
    builder.add_node("test_plan_gate", test_plan_gate)

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
        lambda _: {"status": "BLOCKED"},
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
            "specification": "specification",
            "blocked": "blocked",
        },
    )

    builder.add_edge("specification", "specification_gate")
    builder.add_conditional_edges(
        "specification_gate",
        route_after_specification,
        {"architecture": "architecture", "blocked": "blocked"},
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
            "test_planning": "test_planning",
            "end": END,
        },
    )

    builder.add_edge("test_planning", "test_plan_gate")
    builder.add_conditional_edges(
        "test_plan_gate",
        route_after_test_plan,
        {"implementation": "implementation", "blocked": "blocked"},
    )

    builder.add_edge(
        "implementation",
        "implementation_gate",
    )

    builder.add_conditional_edges(
        "implementation_gate",
        route_after_implementation,
        {
            "validation": "validation",
            "blocked": "blocked",
        },
    )

    builder.add_edge(
        "validation",
        "validation_gate",
    )

    builder.add_conditional_edges(
        "validation_gate",
        route_after_validation,
        {
            "implementation": "implementation",
            "end": END,
        },
    )

    builder.add_edge(
        "blocked",
        END,
    )

    return builder.compile(
        checkpointer=checkpointer or get_checkpointer()
    )
