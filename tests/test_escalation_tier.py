"""Escalation tiering: the v1 keyword limitation and the v2 two-layer fix.

The LLM layer is replaced with a fixed answer, so these tests check the safety
logic around it — not the model.
"""
import pytest

from agents import escalation_agent as esc


def responses(text: str) -> dict:
    return {"how_are_you_feeling": text}


def history(*classifications: str) -> dict:
    return {"check_in_history": [{"classification": c} for c in classifications]}


@pytest.fixture
def v2(monkeypatch):
    monkeypatch.setenv("HUB_V2", "1")


@pytest.fixture
def llm_says(monkeypatch):
    def _set(tier):
        monkeypatch.setattr(esc, "_ai_judged_tier", lambda flags, resp, state: tier)
    return _set


# ── v1: keyword matching only (the default) ─────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("I have chest pain and I'm sweating", "TIER_3"),
    ("I can't breathe", "TIER_3"),
    ("having difficulty breathing since this morning", "TIER_2"),
    ("I feel a bit tired", "TIER_1"),
])
def test_v1_keyword_tiers(monkeypatch, text, expected):
    monkeypatch.delenv("HUB_V2", raising=False)
    assert esc.determine_escalation_tier([], responses(text), {}) == expected


@pytest.mark.parametrize("paraphrase", [
    "I feel like I'm suffocating",
    "it feels like an elephant is sitting on my chest",
])
def test_v1_misses_paraphrased_emergencies(monkeypatch, paraphrase):
    """The documented v1 failure: real emergencies without a literal keyword are under-tiered."""
    monkeypatch.delenv("HUB_V2", raising=False)
    assert esc.determine_escalation_tier([], responses(paraphrase), {}) != "TIER_3"


# ── v2: keyword floor + LLM judgment, take the more urgent ──────────────────

@pytest.mark.parametrize("paraphrase", [
    "I feel like I'm suffocating",
    "it feels like an elephant is sitting on my chest",
])
def test_v2_llm_raises_paraphrased_emergency(v2, llm_says, paraphrase):
    llm_says("TIER_3")
    assert esc.determine_escalation_tier([], responses(paraphrase), {}) == "TIER_3"


def test_v2_llm_cannot_downgrade_keyword_emergency(v2, llm_says):
    llm_says("TIER_1")
    assert esc.determine_escalation_tier([], responses("crushing chest pain"), {}) == "TIER_3"


def test_v2_falls_back_to_keywords_when_llm_fails(v2, llm_says):
    llm_says(None)  # timeout / unparseable response
    assert esc.determine_escalation_tier([], responses("I can't breathe"), {}) == "TIER_3"


def test_v2_trend_floor_lifts_sustained_decline(v2, llm_says):
    """Two YELLOW days before today's RED means at least TIER_2, even if both layers say TIER_1."""
    llm_says("TIER_1")
    state = history("GREEN", "YELLOW", "YELLOW", "RED")
    assert esc.determine_escalation_tier([], responses("feeling worse"), state) == "TIER_2"


def test_v2_single_yellow_day_does_not_trigger_trend_floor(v2, llm_says):
    llm_says("TIER_1")
    state = history("GREEN", "YELLOW", "RED")
    assert esc.determine_escalation_tier([], responses("feeling worse"), state) == "TIER_1"


@pytest.mark.parametrize("classifications, expected", [
    (("YELLOW", "YELLOW", "RED"), 2),         # today's RED is skipped, the trend is counted
    (("YELLOW", "GREEN", "YELLOW", "RED"), 1),  # a GREEN day breaks the run
    (("GREEN", "RED"), 0),
    ((), 0),
])
def test_consecutive_yellow_count(classifications, expected):
    assert esc._consecutive_yellow(history(*classifications)) == expected


@pytest.mark.parametrize("a, b, expected", [
    ("TIER_1", "TIER_3", "TIER_3"),
    ("TIER_3", "TIER_1", "TIER_3"),
    ("TIER_2", "TIER_2", "TIER_2"),
])
def test_more_urgent_never_downgrades(a, b, expected):
    assert esc._more_urgent(a, b) == expected
