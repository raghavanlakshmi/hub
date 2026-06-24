"""
Hub — Orchestrator.

One compiled LangGraph graph, three nodes:
  - recovery_agent        : the consolidated Intake/CarePlan/Monitoring/Admin agent
  - escalation_agent      : the ONE preserved boundary (copied verbatim from Nexus)
  - recovery_agent_admin  : thin wrapper to re-enter admin logic after a TIER_1/TIER_2 escalation

Compare to Nexus: two compiled graphs (intake + monitoring), five nodes, three+ edges.
"""

from langgraph.graph import StateGraph, END
from agents.recovery_agent import run_recovery_agent, _run_admin_logic
from agents.escalation_agent import run_escalation_agent


def route_after_recovery(state: dict) -> str:
    # The only hand-off that goes through the graph: monitoring -> escalation.
    if state.get("current_agent") == "escalation_agent":
        return "escalation_agent"
    return END


def _admin_followup_wrapper(state: dict) -> dict:
    """Re-enters recovery_agent's admin logic after an escalation (any tier),
    mirroring Nexus's unconditional escalation_agent -> admin_agent edge."""
    state["phase"] = "admin"
    return _run_admin_logic(state)


def build_hub_graph():
    workflow = StateGraph(dict)

    workflow.add_node("recovery_agent", run_recovery_agent)
    workflow.add_node("escalation_agent", run_escalation_agent)
    workflow.add_node("recovery_agent_admin", _admin_followup_wrapper)

    workflow.set_entry_point("recovery_agent")

    workflow.add_conditional_edges(
        "recovery_agent", route_after_recovery,
        {"escalation_agent": "escalation_agent", END: END}
    )
    # Unconditional, exactly like Nexus's add_edge("escalation_agent", "admin_agent"):
    # admin follow-up runs after EVERY escalation tier (TIER_1/2/3), not just some.
    workflow.add_edge("escalation_agent", "recovery_agent_admin")
    workflow.add_edge("recovery_agent_admin", END)

    return workflow.compile()


hub_graph = build_hub_graph()


def run_intake(state: dict) -> dict:
    state["phase"] = "intake"
    return hub_graph.invoke(state)


def run_daily_checkin(state: dict, checkin_responses: dict) -> dict:
    state["phase"] = "monitoring"
    state["todays_checkin_responses"] = checkin_responses
    return hub_graph.invoke(state)
