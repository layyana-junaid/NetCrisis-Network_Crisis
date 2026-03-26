"""
NETCRISIS - LangGraph Agent Orchestration
StateGraph orchestrating Attacker, Defender, Monitor, and Traffic agents.
Agents fire every 3-5 ticks (configurable), not every tick.
"""

import logging
import operator
from typing import TypedDict, Annotated, List, Dict, Any

from langgraph.graph import StateGraph, START, END

from agents import invoke_attacker, invoke_defender, invoke_monitor, invoke_traffic

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  State Definition
# ------------------------------------------------------------------ #

class AgentState(TypedDict):
    tick: int
    health: int
    network_summary: str
    active_attacks: List[Dict]
    # Agent outputs
    attacker_decision: Dict
    defender_decision: Dict
    monitor_report: Dict
    traffic_plan: Dict
    # Accumulated results
    actions_to_apply: Annotated[List[Dict], operator.add]
    agent_logs: Annotated[List[Dict], operator.add]

# ------------------------------------------------------------------ #
#  Agent Nodes
# ------------------------------------------------------------------ #

def attacker_node(state: AgentState) -> Dict:
    """RedStorm attacker agent — decides whether and how to attack."""
    logger.info(f"[LangGraph] Running attacker agent at tick {state['tick']}")
    decision = invoke_attacker(state["network_summary"])

    actions = []
    logs = []

    if decision.get("should_attack"):
        actions.append(decision)
        logs.append({
            "type": "attack",
            "tick": state["tick"],
            "message": f"REDSTORM: {decision.get('reasoning', 'Launching attack')}",
            "detail": f"Type: {decision.get('attack_type', '?')} | Target: {decision.get('target', '?')}",
        })
    else:
        logs.append({
            "type": "attack",
            "tick": state["tick"],
            "message": "REDSTORM: Holding position",
            "detail": decision.get("reasoning", "No viable targets this cycle"),
        })

    return {
        "attacker_decision": decision,
        "actions_to_apply": actions,
        "agent_logs": logs,
    }


def defender_node(state: AgentState) -> Dict:
    """Guardian defender agent — responds to threats and mitigates damage."""
    logger.info(f"[LangGraph] Running defender agent at tick {state['tick']}")
    decision = invoke_defender(state["network_summary"])

    actions = []
    logs = []

    if decision.get("should_act"):
        actions.append(decision)
        logs.append({
            "type": "defense",
            "tick": state["tick"],
            "message": f"GUARDIAN: {decision.get('reasoning', 'Taking action')}",
            "detail": f"Action: {decision.get('action', '?')} | Target: {decision.get('target', '?')}",
        })
    else:
        logs.append({
            "type": "defense",
            "tick": state["tick"],
            "message": "GUARDIAN: Monitoring — no action needed",
            "detail": decision.get("reasoning", "Network stable"),
        })

    return {
        "defender_decision": decision,
        "actions_to_apply": actions,
        "agent_logs": logs,
    }


def monitor_node(state: AgentState) -> Dict:
    """Overwatch monitor agent — observes and reports network status."""
    logger.info(f"[LangGraph] Running monitor agent at tick {state['tick']}")
    report = invoke_monitor(state["network_summary"])

    logs = []
    for alert in report.get("alerts", []):
        logs.append({
            "type": "monitor",
            "tick": state["tick"],
            "message": f"OVERWATCH [{report.get('severity', 'info').upper()}]: {alert}",
            "detail": report.get("summary", ""),
        })

    return {
        "monitor_report": report,
        "actions_to_apply": [],
        "agent_logs": logs,
    }


def traffic_node(state: AgentState) -> Dict:
    """FlowMaster traffic agent — generates realistic network traffic."""
    logger.info(f"[LangGraph] Running traffic agent at tick {state['tick']}")
    plan = invoke_traffic(state["network_summary"])

    actions = []
    logs = []

    if plan.get("flows"):
        actions.append({
            "agent": "traffic",
            "flows": plan["flows"],
        })
        flow_summary = ", ".join(f"{f['src']}->{f['dst']}" for f in plan["flows"][:5])
        logs.append({
            "type": "monitor",
            "tick": state["tick"],
            "message": f"FLOWMASTER: Generating {len(plan['flows'])} flows",
            "detail": flow_summary,
        })

    return {
        "traffic_plan": plan,
        "actions_to_apply": actions,
        "agent_logs": logs,
    }


# ------------------------------------------------------------------ #
#  Build the Graph
# ------------------------------------------------------------------ #

def create_agent_graph():
    """Build and compile the LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    # Add agent nodes
    workflow.add_node("attacker", attacker_node)
    workflow.add_node("defender", defender_node)
    workflow.add_node("monitor", monitor_node)
    workflow.add_node("traffic", traffic_node)

    # Sequential chain: attacker → defender → monitor → traffic
    # Defender needs attacker context, monitor observes all, traffic adapts
    workflow.add_edge(START, "attacker")
    workflow.add_edge("attacker", "defender")
    workflow.add_edge("defender", "monitor")
    workflow.add_edge("monitor", "traffic")
    workflow.add_edge("traffic", END)

    graph = workflow.compile()
    logger.info("[LangGraph] Agent graph compiled successfully")
    return graph


# ------------------------------------------------------------------ #
#  Execution Helper
# ------------------------------------------------------------------ #

AGENT_FREQUENCY = 4  # Run agents every N ticks

def should_run_agents(tick: int) -> bool:
    """Determine whether agents should fire this tick."""
    return tick > 0 and tick % AGENT_FREQUENCY == 0


def run_agents(graph, tick: int, health: int, network_summary: str,
               active_attacks: List[Dict]) -> Dict:
    """Execute the agent graph and return results."""
    initial_state: AgentState = {
        "tick": tick,
        "health": health,
        "network_summary": network_summary,
        "active_attacks": active_attacks,
        "attacker_decision": {},
        "defender_decision": {},
        "monitor_report": {},
        "traffic_plan": {},
        "actions_to_apply": [],
        "agent_logs": [],
    }

    try:
        result = graph.invoke(initial_state)
        logger.info(
            f"[LangGraph] Agents completed: "
            f"{len(result.get('actions_to_apply', []))} actions, "
            f"{len(result.get('agent_logs', []))} logs"
        )
        return result
    except Exception as e:
        logger.error(f"[LangGraph] Agent graph execution failed: {e}")
        return {
            "actions_to_apply": [],
            "agent_logs": [{
                "type": "monitor",
                "tick": tick,
                "message": "SYSTEM: Agent graph execution failed",
                "detail": str(e),
            }],
        }
