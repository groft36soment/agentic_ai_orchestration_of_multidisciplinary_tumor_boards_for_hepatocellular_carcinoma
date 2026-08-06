from hera_mdt.rulebook import DECISION_RULES, find_rule, validate_rulebook
from hera_mdt.schema import Treatment


def test_complete_rule_matrix() -> None:
    validate_rulebook()
    assert len(DECISION_RULES) == 384


def test_terminal_rule() -> None:
    rule = find_rule("D", "preserved", "none", "absent", "absent")
    assert rule.treatment == Treatment.SUPPORTIVE
