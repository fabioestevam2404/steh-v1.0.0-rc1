from app.policies.engine import requirements_gate, architecture_gate

def test_policy_blocks_missing():
    assert requirements_gate(None, []).action == "BLOCK"
    assert architecture_gate(None).action == "BLOCK"

def test_policy_allows_valid():
    assert requirements_gate({"x":1}, [{"type":"e"}]).passed
    assert architecture_gate({"style":"x"}).passed
