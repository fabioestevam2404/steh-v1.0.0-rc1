from app.agents.specification import SpecificationAgent
from app.models.specification import SoftwareSpecification


def test_stub_specification_is_structured_and_traceable() -> None:
    result = SpecificationAgent("stub", "test", None).run(
        {
            "functional_requirements": ["Manage customers"],
            "non_functional_requirements": ["Protect customer data"],
            "assumptions": [],
            "open_questions": [],
        }
    )
    specification = SoftwareSpecification.model_validate(result.result)
    requirement_ids = {item.id for item in specification.requirements}
    traced_ids = {
        requirement_id
        for scenario in specification.acceptance_scenarios
        for requirement_id in scenario.requirement_ids
    }

    assert result.agent == "specification_agent"
    assert requirement_ids <= traced_ids
