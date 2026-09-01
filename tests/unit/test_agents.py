from app.agents.architecture import ArchitectureAgent
from app.agents.requirements import RequirementsAgent


def test_agents_stub():
    req = RequirementsAgent("stub","test").run("Crie uma API segura para clientes.")
    arch = ArchitectureAgent("stub","test").run(req.result)
    assert req.result["functional_requirements"]
    assert arch.result["architecture_style"]
    assert req.evidence and arch.evidence
