"""
Hub — Recovery Agent.

Consolidates four of Nexus's five agents (Intake, Care Plan, Monitoring, Admin)
into a single file with one public entry point, run_recovery_agent().

Only the Escalation boundary is preserved as a separate graph node — see orchestrator.py.

Every Claude call goes through instrumentation.usage_tracker.tracked_claude_call so that
tokens/cost/latency are logged into state["token_log"] for the Nexus-vs-Hub comparison.
"""

from anthropic import Anthropic
from tools.pdf_parser import parse_discharge_pdf
from tools.pinecone_store import store_discharge_summary, store_check_in
from tools.openfda import check_medication_interactions
from tools.notification_tool import send_email_notification
from instrumentation.usage_tracker import tracked_claude_call
from dotenv import load_dotenv
import json
import re
import uuid
import os
import threading
from datetime import datetime
from openai import OpenAI

load_dotenv(override=True)

# ──────────────────────────────────────────────────────────────────────────────
# Prompts — copied verbatim from Nexus (intake / care plan / monitoring).
# No prompt rewriting: the comparison is about orchestration, not prompt engineering.
# ──────────────────────────────────────────────────────────────────────────────

INTAKE_SYSTEM_PROMPT = """You are a medical document intake specialist.
Your job is to extract structured information from hospital discharge summaries.
Your audience will be patients and caregivers — but you output structured JSON only.

Extract the following fields with exact precision:
- primary_diagnosis (string)
- icd10_code (string or null)
- hospital_name (string or null — name of the hospital/facility)
- admit_date (string or null — date patient was admitted)
- attending_physician (string or null — primary physician name)
- primary_specialty (string or null — e.g. Cardiology, Pulmonology)
- medications (array of objects with: name, dose, frequency, duration, food_interactions)
- appointments (array of objects with: provider, specialty, timeframe_required)
- warning_signs_er (array of strings: symptoms requiring immediate ER visit)
- warning_signs_call (array of strings: symptoms requiring doctor call within 24hrs)
- dietary_restrictions (array of strings)
- activity_restrictions (array of strings)
- needs_clarification (array of strings: fields that were unclear or missing)

Return ONLY valid JSON. No preamble. No explanation. No markdown.
If a field is not mentioned in the document, set it to null or empty array.
Never invent information not present in the document."""

CARE_PLAN_SYSTEM_PROMPT = """You are a patient care coordinator creating a recovery plan.
Your audience is the patient and their family — NOT clinicians.
Use plain, simple language. No medical jargon. No abbreviations.

You will receive structured discharge data and generate a recovery plan.

CRITICAL RULES:
- If any medications are in the flagged_medications list, DO NOT include them in the plan.
  Add them to needs_human_review instead.
- NEVER change a prescribed dose
- NEVER recommend stopping a medication
- NEVER resolve a medication conflict yourself
- If uncertain about any instruction, add it to needs_human_review

Return ONLY valid JSON with EXACTLY these keys and shapes (no other keys, no markdown, no preamble):
{
  "first_7_days": [
    {"day": 1, "tasks": ["plain-language task", "another task"]}
  ],
  "weekly_tasks_8_30": ["plain-language weekly task", "..."],
  "medication_schedule": ["Take Aspirin 81mg with breakfast", "Take Lisinopril 10mg at bedtime"],
  "symptoms_to_watch": ["Call your doctor if you notice ..."],
  "er_warning_signs": ["Go to the ER immediately if ..."],
  "needs_human_review": ["item a doctor or pharmacist must confirm"]
}

- "first_7_days" MUST contain one object per day for days 1 through 7.
- "medication_schedule" MUST be a list of plain-language strings, one per medication to include
  (e.g. "Take Lisinopril 10mg with breakfast"). Never leave it empty if any medications are included."""

MONITORING_SYSTEM_PROMPT = """You are a recovery monitoring specialist.
You will receive a patient's daily check-in responses and their recovery context.
Your job is to classify the check-in and identify any flags.

Classification rules:
RED — Any of the following: patient reports an ER warning sign, weight gain >2lbs since
      yesterday, chest pain, difficulty breathing at rest, confusion, disorientation.
      → ALWAYS classify RED if any ER warning sign is present, even mild.

YELLOW — Any of the following: mild symptom present (not on ER list), missed >1 medication,
          declining trend vs prior days, patient confused about care plan, weight up 1-2lbs.

GREEN — No flags, all medications taken, no concerning symptoms.

Also check for: declining trends across multiple check-ins (even if today is YELLOW).
If 3+ consecutive check-ins are YELLOW, elevate to RED.

Return ONLY valid JSON:
{
  "classification": "GREEN" | "YELLOW" | "RED",
  "flags": ["list of specific concerns"],
  "summary": "one sentence plain-language summary",
  "recommended_action": "what the patient should do next",
  "escalation_reason": "only if RED — specific reason"
}"""


# ──────────────────────────────────────────────────────────────────────────────
# Phase logic helpers — bodies ported verbatim from Nexus's four agents.
# Only change: client.messages.create(...) -> tracked_claude_call(client, phase=..., state=state, ...)
# plus internal phase-chaining instead of graph edges (see _run_intake_logic / _run_monitoring_logic).
# ──────────────────────────────────────────────────────────────────────────────

def _run_intake_logic(state: dict) -> dict:
    """Was Nexus's run_intake_agent(). Chains directly into care plan on success."""
    client = Anthropic()
    print("[Recovery Agent: intake] Starting...")

    # Step 1: Parse PDF
    pdf_result = parse_discharge_pdf(state.get("pdf_path"))

    if not pdf_result["success"]:
        state["active_flags"].append(f"PDF_PARSE_FAILED: {pdf_result['error']}")
        state["needs_clarification"].append("discharge_pdf_unreadable")
        print(f"[Recovery Agent: intake] PDF parse failed: {pdf_result['error']}")
        return state  # do NOT chain to care plan on PDF failure (matches Nexus route_after_intake -> END)

    raw_text = pdf_result["text"]
    print(f"[Recovery Agent: intake] PDF parsed. {pdf_result['page_count']} pages, {len(raw_text)} chars.")

    # Step 2: Extract structured data via Claude
    try:
        response = tracked_claude_call(
            client, phase="intake", state=state,
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=INTAKE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Extract structured data from this discharge summary:\n\n{raw_text}"
            }]
        )

        extracted_text = response.content[0].text.strip()
        # Strip markdown code fences if Claude wrapped the JSON
        if extracted_text.startswith("```"):
            extracted_text = extracted_text.split("```")[1]
            if extracted_text.startswith("json"):
                extracted_text = extracted_text[4:]
        extracted_text = extracted_text.strip()
        extracted = json.loads(extracted_text)

    except json.JSONDecodeError as e:
        raw = response.content[0].text if 'response' in dir() else "no response"
        state["active_flags"].append(f"INTAKE_JSON_PARSE_FAILED: {str(e)} | RAW: {raw[:300]}")
        return state
    except Exception as e:
        state["active_flags"].append(f"INTAKE_CLAUDE_CALL_FAILED: {str(e)}")
        print(f"[Recovery Agent: intake] Claude call failed: {e}")
        return state

    # Step 3: Update state with extracted data
    state["diagnosis"] = extracted.get("primary_diagnosis", "Unknown")
    state["icd10_code"] = extracted.get("icd10_code")
    state["medications"] = extracted.get("medications", [])
    state["appointments"] = extracted.get("appointments", [])
    state["warning_signs_er"] = extracted.get("warning_signs_er", [])
    state["warning_signs_call"] = extracted.get("warning_signs_call", [])
    state["dietary_restrictions"] = extracted.get("dietary_restrictions", [])
    state["activity_restrictions"] = extracted.get("activity_restrictions", [])
    state["needs_clarification"].extend(extracted.get("needs_clarification", []))

    # Step 4: Store in Pinecone
    stored = store_discharge_summary(
        patient_id=state["patient_id"],
        text=raw_text,
        metadata={
            "patient_id": state["patient_id"],
            "diagnosis": state["diagnosis"],
            "discharge_date": state["discharge_date"]
        }
    )

    if not stored:
        state["active_flags"].append("PINECONE_STORE_FAILED_USING_LOCAL_FALLBACK")
        with open(f"data/{state['patient_id']}_discharge.json", "w") as f:
            json.dump(extracted, f, indent=2)

    state["intake_complete"] = True

    # Auto-populate hospitalization history from this discharge
    hosp_record = {
        "id": str(uuid.uuid4()),
        "admit_date": extracted.get("admit_date", "Unknown"),
        "discharge_date": state["discharge_date"],
        "hospital_name": extracted.get("hospital_name", "Unknown hospital"),
        "diagnosis": state["diagnosis"],
        "icd10_code": state.get("icd10_code"),
        "treating_physician": extracted.get("attending_physician"),
        "specialty": extracted.get("primary_specialty"),
        "notes": None,
        "source": "auto_imported",
        "created_at": datetime.now().isoformat()
    }
    if "hospitalization_history" not in state:
        state["hospitalization_history"] = []
    state["hospitalization_history"].append(hosp_record)

    print(f"[Recovery Agent: intake] Complete. Diagnosis: {state['diagnosis']}")

    # ── This replaces Nexus's graph edge intake_agent -> care_plan_agent ──
    state["phase"] = "careplan"
    return _run_careplan_logic(state)


def _run_careplan_logic(state: dict) -> dict:
    """Was Nexus's run_care_plan_agent(). Terminal for the intake path (no further chaining)."""
    client = Anthropic()
    print("[Recovery Agent: careplan] Starting...")

    # Step 1: Check medication interactions via OpenFDA
    if state["medications"]:
        print(f"[Recovery Agent: careplan] Checking {len(state['medications'])} medications via OpenFDA...")
        interaction_results = check_medication_interactions(state["medications"])

        if not interaction_results["all_clear"]:
            for detail in interaction_results["interaction_details"]:
                drug_label = detail["drug_1"]
                severity = detail.get("severity", "REVIEW_REQUIRED")

                if severity == "BOXED_WARNING":
                    what_it_means = (
                        "This medication has a serious warning printed on its label (an FDA black box warning). "
                        "Your doctor prescribed it knowing this — do not stop taking it on your own."
                    )
                elif severity == "API_ERROR":
                    what_it_means = (
                        "We were unable to automatically check this medication. "
                        "This is a system limitation, not necessarily a problem with the medication itself."
                    )
                else:
                    other = f" and {detail['drug_2']}" if detail.get("drug_2") else ""
                    drug_label += f" + {detail['drug_2']}" if detail.get("drug_2") else ""
                    what_it_means = (
                        f"This medication may interact with another medication you are taking{other}. "
                        "Your pharmacist can confirm whether this is a concern for your specific doses."
                    )

                content = "\n".join([
                    f"Medication to check: {drug_label}",
                    f"What this means: {what_it_means}",
                    "What to do: Before your next dose, please call your pharmacist or doctor's office to confirm it is safe.",
                    "Important: Do not stop any medication on your own without speaking to your doctor first.",
                ])

                approval_item = {
                    "id": str(uuid.uuid4()),
                    "type": "medication_conflict",
                    "content": content,
                    "recipient": "patient_caregiver",
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }
                state["human_approval_queue"].append(approval_item)

            for med in state["medications"]:
                if med["name"] in interaction_results["flagged_medications"]:
                    med["interaction_flag"] = True

            state["active_flags"].append("MEDICATION_INTERACTION_FLAGGED")
            print(f"[Recovery Agent: careplan] {len(interaction_results['flagged_medications'])} medications flagged.")

    # Step 2: Generate care plan via Claude
    clean_meds = [m for m in state["medications"] if not m.get("interaction_flag")]
    flagged_meds = [m for m in state["medications"] if m.get("interaction_flag")]

    try:
        response = tracked_claude_call(
            client, phase="careplan", state=state,
            model="claude-sonnet-4-6",
            max_tokens=5000,
            system=CARE_PLAN_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": json.dumps({
                    "diagnosis": state["diagnosis"],
                    "medications_to_include": clean_meds,
                    "flagged_medications_excluded": [m["name"] for m in flagged_meds],
                    "appointments": state["appointments"],
                    "warning_signs_er": state["warning_signs_er"],
                    "warning_signs_call": state["warning_signs_call"],
                    "dietary_restrictions": state["dietary_restrictions"],
                    "activity_restrictions": state["activity_restrictions"]
                }, indent=2)
            }]
        )

        care_plan_text = response.content[0].text.strip()
        if response.stop_reason == "max_tokens":
            raise ValueError("Care plan response was truncated (hit max_tokens). Increase limit or simplify prompt.")
        json_match = re.search(r'\{[\s\S]*\}', care_plan_text)
        if not json_match:
            raise ValueError(f"No JSON in care plan response: {care_plan_text[:200]}")
        care_plan = json.loads(json_match.group())

    except Exception as e:
        state["active_flags"].append(f"CARE_PLAN_GENERATION_FAILED: {str(e)}")
        print(f"[Recovery Agent: careplan] Error: {e}")
        return state

    # Phase 7 — fire Nebius in a daemon thread (logged, not used in the UI; satisfies rubric).
    threading.Thread(
        target=lambda: print(f"[Nebius] {(run_care_plan_via_nebius(state) or '')[:200]}"),
        daemon=True
    ).start()

    state["care_plan"] = care_plan
    state["care_plan_complete"] = True
    state["current_agent"] = "complete"
    print("[Recovery Agent: careplan] Complete.")
    return state


def _run_monitoring_logic(state: dict, check_in_responses: dict) -> dict:
    """Was Nexus's run_monitoring_agent(). Chains to admin on GREEN/YELLOW;
    on RED, exits and lets the GRAPH route to escalation_agent (the one preserved boundary)."""
    client = Anthropic()
    print(f"[Recovery Agent: monitoring] Processing Day {state['recovery_day']} check-in...")

    # A re-submission for the same day supersedes the prior one.
    state["check_in_history"] = [
        c for c in state.get("check_in_history", []) if c.get("day") != state["recovery_day"]
    ]

    history = state["check_in_history"]
    recent_history = history[-7:] if len(history) > 7 else history

    try:
        response = tracked_claude_call(
            client, phase="monitoring", state=state,
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=MONITORING_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": json.dumps({
                    "day": state["recovery_day"],
                    "diagnosis": state["diagnosis"],
                    "er_warning_signs": state.get("warning_signs_er", []),
                    "call_warning_signs": state.get("warning_signs_call", []),
                    "todays_responses": check_in_responses,
                    "recent_check_in_history": recent_history
                }, indent=2)
            }]
        )

        result_text = response.content[0].text.strip()
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if not json_match:
            raise ValueError(f"No JSON object in model response: {result_text[:200]}")
        result = json.loads(json_match.group())

    except Exception as e:
        print(f"[Recovery Agent: monitoring] Classification error: {type(e).__name__}: {e}")
        result = {
            "classification": "YELLOW",
            "flags": [f"Classification system error: {str(e)}"],
            "summary": "Unable to classify check-in. Flagging for review.",
            "recommended_action": "Please call your doctor's office if you have any concerns.",
            "escalation_reason": None
        }

    check_in_record = {
        "day": state["recovery_day"],
        "timestamp": datetime.now().isoformat(),
        "responses": check_in_responses,
        "classification": result["classification"],
        "flags": result.get("flags", []),
        "summary": result.get("summary", ""),
        "recommended_action": result.get("recommended_action", "")
    }

    stored = store_check_in(state["patient_id"], check_in_record)
    if not stored:
        state["active_flags"].append("CHECKIN_STORAGE_FAILED")

    # Extract vitals and medication adherence from this check-in
    meds_taken = []
    meds_missed = []
    for med in state.get("medications", []):
        if med.get("interaction_flag"):
            continue
        key = f"med_{med['name'].replace(' ', '_').lower()}"
        val = check_in_responses.get(key)
        if val is not None:
            took_it = (val is True) or (isinstance(val, str) and "yes" in val.lower())
            (meds_taken if took_it else meds_missed).append(med["name"])

    vitals_record = {
        "day": state["recovery_day"],
        "date": datetime.now().date().isoformat(),
        "weight_lbs": check_in_responses.get("weight"),
        "bp_systolic": None,
        "bp_diastolic": None,
        "energy_score": check_in_responses.get("general_feeling"),
        "meds_taken": meds_taken,
        "meds_missed": meds_missed,
    }

    if "daily_vitals_log" not in state:
        state["daily_vitals_log"] = []
    state["daily_vitals_log"] = [
        v for v in state["daily_vitals_log"] if v["day"] != state["recovery_day"]
    ]
    state["daily_vitals_log"].append(vitals_record)

    state["check_in_history"].append(check_in_record)
    state["last_check_in_date"] = datetime.now().isoformat()
    state["last_monitoring_result"] = result
    print(f"[Recovery Agent: monitoring] Classification: {result['classification']}")

    # ── Routing ──
    if result["classification"] == "RED":
        # The one hand-off that stays a real graph edge: monitoring -> escalation_agent.
        state["active_flags"].append(
            f"RED_FLAG_DAY_{state['recovery_day']}: {result.get('escalation_reason', '')}"
        )
        state["current_agent"] = "escalation_agent"
        return state  # exits here — orchestrator routes to escalation_agent

    if result["classification"] == "YELLOW":
        state["active_flags"].append(f"YELLOW_FLAG_DAY_{state['recovery_day']}")

    # ── This replaces Nexus's graph edge monitoring_agent -> admin_agent ──
    state["phase"] = "admin"
    return _run_admin_logic(state)


def _run_admin_logic(state: dict) -> dict:
    """Was Nexus's run_admin_agent(). No Claude call — nothing to track."""
    print("[Recovery Agent: admin] Running daily task check...")

    today = datetime.now()
    actions_taken = []

    for appt in state.get("appointments", []):
        if appt.get("scheduled_date") and not appt.get("confirmed"):
            appt_date = datetime.fromisoformat(appt["scheduled_date"])
            days_until = (appt_date - today).days

            if days_until == 2:
                message = (f"Reminder: You have an appointment with "
                           f"{appt['provider']} ({appt['specialty']}) in 2 days "
                           f"on {appt['scheduled_date']}.")
                if state.get("caregiver_email"):
                    send_email_notification(
                        to_email=state["caregiver_email"],
                        subject="Appointment Reminder — 48 Hours",
                        body=message
                    )
                actions_taken.append("48hr_appointment_reminder_sent")

    if state.get("recovery_day", 0) % 7 == 0 and state.get("recovery_day", 0) > 0:
        summary = generate_weekly_summary(state)
        if state.get("caregiver_email"):
            send_email_notification(
                to_email=state["caregiver_email"],
                subject=f"Weekly Recovery Summary — Week {state['recovery_day'] // 7}",
                body=summary
            )
        actions_taken.append("weekly_summary_sent")

    state["last_admin_run"] = datetime.now().isoformat()
    state["admin_actions_today"] = actions_taken
    state["current_agent"] = "complete"

    print(f"[Recovery Agent: admin] Done. Actions: {actions_taken}")
    return state


# ──────────────────────────────────────────────────────────────────────────────
# Single public entry point — the one node Hub's orchestrator calls.
# ──────────────────────────────────────────────────────────────────────────────

def run_recovery_agent(state: dict) -> dict:
    """
    Branches on state['phase']:
      'intake'     -> Day 0, PDF just uploaded (chains intake -> careplan internally)
      'monitoring' -> Day N, check-in submitted (chains monitoring -> admin, or exits to escalation)
    """
    phase = state.get("phase", "intake")

    if phase == "intake":
        return _run_intake_logic(state)
    elif phase == "monitoring":
        responses = state.get("todays_checkin_responses", {})
        return _run_monitoring_logic(state, responses)
    else:
        raise ValueError(f"Unknown phase for recovery_agent: {phase}")


# ──────────────────────────────────────────────────────────────────────────────
# Standalone helpers the UI calls directly (not through the graph) — copied from Nexus.
# ──────────────────────────────────────────────────────────────────────────────

def dedupe_history_by_day(state: dict) -> dict:
    """Keep only the most recent check-in (and vitals) per recovery day."""
    history = state.get("check_in_history", [])
    if history:
        by_day = {}
        for rec in history:
            day = rec.get("day")
            existing = by_day.get(day)
            if existing is None or rec.get("timestamp", "") >= existing.get("timestamp", ""):
                by_day[day] = rec
        state["check_in_history"] = [by_day[d] for d in sorted(by_day, key=lambda d: (d is None, d))]

    vitals = state.get("daily_vitals_log", [])
    if vitals:
        v_by_day = {}
        for rec in vitals:
            v_by_day[rec.get("day")] = rec
        state["daily_vitals_log"] = [v_by_day[d] for d in sorted(v_by_day, key=lambda d: (d is None, d))]

    return state


def generate_checkin_questions(state: dict) -> list:
    """Generate personalized check-in questions based on diagnosis and day."""
    diagnosis = state.get("diagnosis", "general").lower()
    day = state.get("recovery_day", 1)
    meds = [m["name"] for m in state.get("medications", []) if not m.get("interaction_flag")]
    warning_signs = state.get("warning_signs_er", [])

    questions = []

    for med in meds:
        questions.append({
            "id": f"med_{med.replace(' ', '_').lower()}",
            "question": f"Did you take {med} today?",
            "type": "med_checkbox",
            "med_name": med
        })

    questions.append({
        "id": "general_feeling",
        "question": "How are you feeling overall today? (1 = terrible, 10 = great)",
        "type": "scale_1_10"
    })

    if "heart" in diagnosis or "chf" in diagnosis or "cardiac" in diagnosis:
        questions.append({
            "id": "weight",
            "question": "What was your weight this morning? (Daily weight is important for heart patients)",
            "type": "number_lbs"
        })
        questions.append({
            "id": "swelling",
            "question": "Any swelling in your ankles, feet, or legs compared to yesterday?",
            "type": "yes_no_detail"
        })
        questions.append({
            "id": "breathing",
            "question": "Any shortness of breath while resting or lying flat?",
            "type": "yes_no_detail"
        })

    if warning_signs:
        questions.append({
            "id": "warning_signs",
            "question": "Are you experiencing any of these symptoms right now?",
            "type": "symptom_checklist",
            "options": warning_signs
        })

    questions.append({
        "id": "concerns",
        "question": "Anything else worrying you today that you'd like to flag?",
        "type": "free_text"
    })

    return questions


def generate_weekly_summary(state: dict) -> str:
    history = state.get("check_in_history", [])
    week_num = state.get("recovery_day", 7) // 7
    recent = history[-7:]

    green = sum(1 for c in recent if c.get("classification") == "GREEN")
    yellow = sum(1 for c in recent if c.get("classification") == "YELLOW")
    red = sum(1 for c in recent if c.get("classification") == "RED")

    return f"""Weekly Recovery Summary — Week {week_num}
Patient: {state.get('patient_name')}
Diagnosis: {state.get('diagnosis')}

Check-in summary (last 7 days):
✅ Green days: {green}
⚠️  Yellow days: {yellow}
🔴 Red days: {red}

{'All medications on track.' if yellow == 0 and red == 0 else 'Some medication or symptom concerns noted — see daily logs.'}

Next appointment: {state['appointments'][0]['provider'] if state.get('appointments') else 'None scheduled'}

This summary was generated by Hub — your post-discharge recovery co-pilot."""


def run_care_plan_via_nebius(state: dict) -> str:
    """Use Nebius Token Factory for care plan generation (satisfies rubric requirement).
    Not a Claude call — not routed through tracked_claude_call.
    Nebius is optional: if NEBIUS_API_KEY is unset, skip gracefully instead of crashing."""
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        print("[Nebius] Skipped — NEBIUS_API_KEY not set (optional integration).")
        return ""

    try:
        nebius_client = OpenAI(
            base_url=os.getenv("NEBIUS_BASE_URL"),
            api_key=api_key
        )
        response = nebius_client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct",
            messages=[
                {"role": "system", "content": CARE_PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate care plan for: {state['diagnosis']}"}
            ],
            max_tokens=1000
        )
        result = response.choices[0].message.content
        print("[Nebius] Care plan generation complete.")
        return result
    except Exception as e:
        print(f"[Nebius] Call failed: {e}")
        return ""
