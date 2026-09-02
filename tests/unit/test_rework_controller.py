from app.orchestration.rework import ReworkController


def test_rework_is_bounded() -> None:
    controller=ReworkController()
    first=controller.decide(1,["high finding"])
    last=controller.decide(2,["high finding"])
    assert first.required is True
    assert first.exhausted is False
    assert last.exhausted is True

def test_clean_validation_needs_no_rework() -> None:
    decision=ReworkController().decide(1,[])
    assert decision.required is False
