"""v2 guardrail: non-negated shortness-of-breath language floors a GREEN check-in at YELLOW."""
import pytest

from agents.recovery_agent import _dyspnea_present


@pytest.mark.parametrize("text", [
    "a little short of breath when I carried the laundry",
    "I get winded climbing the stairs",
    "I feel like I'm suffocating",
    "it's hard to breathe lying down",
])
def test_detects_breathlessness(text):
    assert _dyspnea_present({"answer": text})


@pytest.mark.parametrize("text", [
    "no shortness of breath today",
    "I'm not winded at all",
    "she isn't short of breath",
    "denies trouble breathing",
    "feeling great, walked to the mailbox",
])
def test_ignores_negated_or_absent_breathlessness(text):
    assert not _dyspnea_present({"answer": text})
