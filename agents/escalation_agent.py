from anthropic import Anthropic
from tools.notification_tool import send_email_notification, send_sms_notification
from instrumentation.usage_tracker import tracked_claude_call
import json
import os
import re
import uuid
from datetime import datetime

client = Anthropic()

# ── v2 improvement (Week 4): semantic escalation tier ────────────────────────
# Gated behind HUB_V2 so the shipped app keeps the original keyword behavior by
# default. Fixes the dominant baseline failure mode: paraphrased emergencies
# (e.g. "I feel like I'm suffocating", "an elephant on my chest") that the literal
# keyword list under-tiers from TIER_3 to TIER_2.
V2_TIER_SYSTEM = """You are a clinical triage specialist assigning the ESCALATION TIER for a
post-discharge patient who has ALREADY been flagged RED (needs escalation). Pick the tier:

TIER_3  (CALL 911 NOW — actively life-threatening): air hunger / severe breathing trouble at rest,
  "suffocating", crushing or pressure-like chest pain (incl. "elephant on my chest", pain radiating
  to the arm with sweating), suspected heart attack or stroke, blue/gray lips or gray appearance,
  fainting/unresponsive, coughing pink frothy mucus.
TIER_2  (URGENT — notify contact / go to ER soon / same-day): serious but not immediately
  life-threatening — moderate breathing trouble only partly relieved by rescue inhaler, a sustained
  multi-day worsening trend, significant fluid gain with new swelling.
TIER_1 (call provider within 24h): urgent but currently stable.

Judge by MEANING, including lay paraphrases — not just exact keywords. Return ONLY JSON:
{"tier": "TIER_3" | "TIER_2" | "TIER_1", "reason": "one sentence"}"""


def _consecutive_yellow(state: dict) -> int:
    """Count the run of YELLOW check-ins immediately preceding today's RED (the trend that
    triggered escalation). Today's just-appended RED record is skipped, not counted."""
    cnt = 0
    for rec in reversed(state.get("check_in_history", [])):
        cls = rec.get("classification")
        if cls == "RED":
            continue          # skip today's RED, keep looking back at the trend
        if cls == "YELLOW":
            cnt += 1
        else:
            break
    return cnt


def _keyword_tier(flags: list, responses: dict) -> str:
    """Original v1 logic — pure keyword/substring matching (kept as the v2 fallback)."""
    flag_text = " ".join(flags).lower()
    responses_text = json.dumps(responses).lower()

    tier_3_keywords = ["can't breathe", "cannot breathe", "chest pain", "unconscious",
                       "not breathing", "stroke", "seizure", "911"]
    tier_2_keywords = ["difficulty breathing", "severe pain", "confusion", "disoriented",
                       "won't wake", "unresponsive", "er warning"]

    for keyword in tier_3_keywords:
        if keyword in flag_text or keyword in responses_text:
            return "TIER_3"
    for keyword in tier_2_keywords:
        if keyword in flag_text or keyword in responses_text:
            return "TIER_2"
    return "TIER_1"


_TIER_RANK = {"TIER_1": 1, "TIER_2": 2, "TIER_3": 3}


def _more_urgent(a: str, b: str) -> str:
    """Return whichever tier is MORE urgent. Never let either layer downgrade the other."""
    return a if _TIER_RANK.get(a, 1) >= _TIER_RANK.get(b, 1) else b


def _ai_judged_tier(flags: list, responses: dict, state: dict):
    """Layer 2 — an LLM urgency judgment that reads MEANING, not keywords. Works identically
    on typed text or voice-transcribed text (both arrive here as a block of text). Returns a
    tier string, or None if the call fails (so the caller falls back to the keyword layer)."""
    try:
        ctx = {
            "er_warning_signs": state.get("warning_signs_er", []),
            "active_flags": flags,
            "todays_checkin": responses,
            "consecutive_yellow_days_before_today": _consecutive_yellow(state),
        }
        resp = tracked_claude_call(
            client, phase="escalation_tier", state=state,
            model="claude-sonnet-4-6", max_tokens=300,
            system=V2_TIER_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(ctx, indent=2)}],
        )
        m = re.search(r"\{[\s\S]*\}", resp.content[0].text)
        tier = json.loads(m.group())["tier"] if m else None
        return tier if tier in _TIER_RANK else None
    except Exception as e:  # noqa: BLE001 — never let triage crash
        print(f"[Escalation v2] AI tier judgment failed ({e}); using keyword layer only.")
        return None


def _two_layer_tier(flags: list, responses: dict, state: dict) -> str:
    """v2 escalation tier — two safety layers, biased toward over-caution:

      Layer 1: the original keyword/substring check (fast, free, catches obvious phrasings).
      Layer 2: an LLM urgency judgment that understands paraphrases & metaphors.
      Combine: take the MORE urgent of the two — neither layer can downgrade the other,
               so an LLM hiccup can never silently lower a real emergency below the keyword
               floor, and the LLM can RAISE a tier the keywords missed (e.g. "suffocating").
      Plus a trend floor: a RED driven by a sustained YELLOW decline is at least TIER_2.
    """
    keyword_tier = _keyword_tier(flags, responses)          # Layer 1 (deterministic backstop)
    ai_tier = _ai_judged_tier(flags, responses, state)       # Layer 2 (semantic)
    tier = _more_urgent(keyword_tier, ai_tier) if ai_tier else keyword_tier

    if _consecutive_yellow(state) >= 2 and _TIER_RANK.get(tier, 1) < 2:
        tier = "TIER_2"
    return tier


def determine_escalation_tier(flags: list, responses: dict, state: dict) -> str:
    """
    TIER_1: Urgent but not life-threatening — draft message for human approval
    TIER_2: Potentially life-threatening — auto-notify emergency contact (with consent)
    TIER_3: Actively life-threatening — display 911 immediately

    v2 (HUB_V2): two-layer max-urgency tiering (keyword backstop + LLM judgment, take the more
    urgent) with a trend floor. v1 default: keyword matching only.
    """
    if os.getenv("HUB_V2"):
        return _two_layer_tier(flags, responses, state)
    return _keyword_tier(flags, responses)

def run_escalation_agent(state: dict) -> dict:
    """
    Escalation Agent: Handle RED flags. Tier-based response.
    """
    print("[Escalation Agent] RED flag detected. Determining tier...")

    recent_checkin = state["check_in_history"][-1] if state["check_in_history"] else {}
    flags = state.get("active_flags", [])
    responses = recent_checkin.get("responses", {})

    tier = determine_escalation_tier(flags, responses, state)
    print(f"[Escalation Agent] Tier: {tier}")

    state["escalation_tier"] = tier
    state["escalation_timestamp"] = datetime.now().isoformat()

    if tier == "TIER_3":
        # Immediate 911 display — no agent actions, just surface to UI
        state["show_911_screen"] = True
        state["911_message"] = "CALL 911 NOW. Do not wait."

        # Auto-notify emergency contact if consented
        if state.get("emergency_contact_consented") and state.get("emergency_contact_phone"):
            send_sms_notification(
                to_phone=state["emergency_contact_phone"],
                message=f"URGENT: {state['patient_name']} may need emergency help. "
                        f"Please check on them immediately or call 911."
            )
        state["current_agent"] = "complete"

    elif tier == "TIER_2":
        # Auto-notify emergency contact (with consent) + draft ER handoff summary
        if state.get("emergency_contact_consented") and state.get("emergency_contact_phone"):
            send_sms_notification(
                to_phone=state["emergency_contact_phone"],
                message=f"URGENT: {state['patient_name']} has reported concerning symptoms "
                        f"(Day {state['recovery_day']} of recovery from {state['diagnosis']}). "
                        f"Please check on them."
            )

        # Draft ER handoff summary patient can show on arrival
        er_summary = generate_er_summary(state)
        state["er_handoff_summary"] = er_summary
        state["show_er_guidance"] = True
        state["current_agent"] = "admin_agent"

    elif tier == "TIER_1":
        # Draft provider message for human approval
        draft = generate_provider_message_draft(state, recent_checkin)

        approval_item = {
            "id": str(uuid.uuid4()),
            "type": "escalation_message",
            "content": draft,
            "recipient": "primary_care_physician",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        state["human_approval_queue"].append(approval_item)
        state["show_yellow_guidance"] = True
        state["current_agent"] = "admin_agent"

    return state

def generate_er_summary(state: dict) -> str:
    """Generate a plain-language ER handoff summary."""
    meds = [f"{m['name']} {m['dose']} {m['frequency']}"
            for m in state.get("medications", [])
            if not m.get("interaction_flag")]

    return f"""PATIENT INFORMATION FOR ER STAFF
Name: {state.get('patient_name', 'Unknown')}
Recent discharge: {state.get('discharge_date', 'Unknown')}
Diagnosis: {state.get('diagnosis', 'Unknown')}

Current medications:
{chr(10).join(f'- {m}' for m in meds)}

Allergies: Please ask patient

Recovery day: {state.get('recovery_day', 'Unknown')}
Flagged symptoms today: {', '.join(state.get('active_flags', [])[:3])}"""

def generate_provider_message_draft(state: dict, recent_checkin: dict) -> str:
    """Draft a provider message for human approval."""
    return f"""Draft message to your care team (please review before sending):

Subject: Recovery update — Day {state.get('recovery_day')} concern

I was discharged on {state.get('discharge_date')} following treatment for {state.get('diagnosis')}.
During my Day {state.get('recovery_day')} check-in, I noticed the following:

{recent_checkin.get('summary', 'See flags below')}

Specific concerns: {', '.join(recent_checkin.get('flags', []))}

Could you please advise on next steps?

[REVIEW AND APPROVE BEFORE SENDING]"""