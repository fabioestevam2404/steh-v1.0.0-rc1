from app.agents.test_planning import TestPlanningAgent as PlanningAgent
from app.models.test_plan import TestPlan as PlanningContract
from app.models.test_plan import TestType as PlanningTestType


def test_stub_test_plan_covers_specification_and_security() -> None:
    specification = {"requirements": [{"id": "FR-001"}, {"id": "NFR-001"}]}
    result = PlanningAgent("stub", "test", None).run(
        specification,
        {"components": []},
        {"threat_model": {}},
    )
    plan = PlanningContract.model_validate(result.result)
    covered_ids = {
        requirement_id
        for test_case in plan.test_cases
        for requirement_id in test_case.requirement_ids
    }

    assert result.agent == "test_planning_agent"
    assert {"FR-001", "NFR-001"} <= covered_ids
    assert any(
        test_case.negative and test_case.test_type == PlanningTestType.SECURITY
        for test_case in plan.test_cases
    )
