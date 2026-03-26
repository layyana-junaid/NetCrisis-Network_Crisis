"""
NETCRISIS - AI Agent System
Four LangChain chains using Groq (llama-3.3-70b-versatile):
  Attacker (RedStorm), Defender (Guardian), Monitor (Overwatch), Traffic (FlowMaster)
"""

import json
import logging
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

load_dotenv()
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  LLM Setup
# ------------------------------------------------------------------ #

def get_llm():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key.startswith("gsk_your"):
        logger.warning("GROQ_API_KEY not set — agents will use fallback logic")
        return None
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        api_key=api_key,
        max_retries=2,
    )

# ------------------------------------------------------------------ #
#  Output Schemas
# ------------------------------------------------------------------ #

class AttackDecision(BaseModel):
    should_attack: bool = Field(description="Whether to launch an attack this cycle")
    attack_type: str = Field(default="", description="ddos | bgp_hijack | mitm | port_scan")
    target: str = Field(default="", description="Target node ID, e.g. WEB, DNS, CR1")
    reasoning: str = Field(default="", description="Brief tactical reasoning")

class DefenseDecision(BaseModel):
    should_act: bool = Field(description="Whether to take defensive action")
    action: str = Field(default="", description="rate_limit | isolate | add_acl | heal | restore_link")
    target: str = Field(default="", description="Target node ID")
    source: str = Field(default="", description="Source node for restore_link")
    reasoning: str = Field(default="", description="Defense rationale")

class MonitorReport(BaseModel):
    alerts: List[str] = Field(default_factory=list, description="List of alert messages")
    severity: str = Field(default="normal", description="normal | elevated | critical")
    summary: str = Field(default="", description="Brief network status summary")

class TrafficPlan(BaseModel):
    flows: List[Dict] = Field(default_factory=list, description="List of {src, dst} traffic flows to generate")
    reasoning: str = Field(default="", description="Traffic generation logic")

# ------------------------------------------------------------------ #
#  System Prompts
# ------------------------------------------------------------------ #

ATTACKER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are REDSTORM, an elite network attack agent in a cybersecurity simulation.
Your mission: probe, exploit, and degrade the target network infrastructure.

PERSONALITY: Calculated, aggressive, methodical. You savor finding weak points.

ATTACK TYPES:
- ddos: Flood a target with traffic. Best against servers (WEB, DNS, DB). Devastating but obvious.
- bgp_hijack: Corrupt routing tables. Only works on routers (CR1-CR3, ER1-ER4). Subtle, widespread damage.
- mitm: Intercept traffic through a node. Works on any node with neighbors. Stealthy data theft.
- port_scan: Probe a target for vulnerabilities. Low damage but reveals services. Good recon.

STRATEGY GUIDELINES:
- Don't attack already-compromised or isolated nodes (waste of resources)
- Prefer high-value targets: WEB server, DNS server, Core routers
- If network health is high (>80%), be aggressive — launch attacks
- If defenses are active, try different targets or attack types
- Vary your attacks — don't always use DDoS
- If health is already low (<40%), you're winning — consider surgical strikes

TARGET NODE IDS: CR1, CR2, CR3, ER1, ER2, ER3, ER4, DNS, WEB, DB, H1-H6

You MUST respond with valid JSON matching this schema:
{{"should_attack": bool, "attack_type": "ddos|bgp_hijack|mitm|port_scan", "target": "NODE_ID", "reasoning": "brief reason"}}"""),
    ("human", "Current network state:\n{network_state}\n\nDecide your next attack move."),
])

DEFENDER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are GUARDIAN, the network defense agent in a cybersecurity simulation.
Your mission: protect infrastructure, mitigate attacks, and restore compromised systems.

PERSONALITY: Calm, strategic, protective. You think two steps ahead.

DEFENSE ACTIONS:
- rate_limit: Throttle malicious traffic to a node under DDoS. Reduces attack intensity by 30%.
- isolate: Quarantine a compromised node to prevent lateral movement. Last resort — disconnects the node.
- add_acl: Add firewall rule to block traffic. Good against targeted attacks.
- heal: Emergency patch — restores 15 health points to a damaged node. Use on critical infrastructure.
- restore_link: Restore a severed network link between two nodes.

STRATEGY GUIDELINES:
- Prioritize defending Core routers and servers (WEB, DNS, DB) — they're critical infrastructure
- Use rate_limit against active DDoS attacks first
- Only isolate if a node is severely compromised (<20% health) and actively spreading damage
- Use heal on nodes that are recovering or have moderate damage
- Don't waste actions if no threats are present (set should_act=false)
- If links are severed, consider restoring them to maintain connectivity

You MUST respond with valid JSON matching this schema:
{{"should_act": bool, "action": "rate_limit|isolate|add_acl|heal|restore_link", "target": "NODE_ID", "source": "NODE_ID_for_restore_link_only", "reasoning": "brief reason"}}"""),
    ("human", "Current network state:\n{network_state}\n\nDecide your defensive action."),
])

MONITOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are OVERWATCH, the network monitoring agent in a cybersecurity simulation.
Your mission: observe the network, detect anomalies, and generate actionable alerts.

PERSONALITY: Analytical, precise, vigilant. Nothing escapes your attention.

MONITORING FOCUS:
- Node health levels — flag anything below 70%
- Link utilization — flag anything above 60%
- Active attacks — report ongoing threats
- Severed links — report connectivity issues
- Compromised/isolated nodes — track recovery progress
- Overall network health trend — is it improving or degrading?

SEVERITY LEVELS:
- normal: Health >80%, no active attacks, all links stable
- elevated: Health 50-80%, minor attacks, some congestion
- critical: Health <50%, major attacks active, infrastructure at risk

Generate 1-3 concise alert messages. Each alert should be a single line.

You MUST respond with valid JSON matching this schema:
{{"alerts": ["alert message 1", "alert message 2"], "severity": "normal|elevated|critical", "summary": "one line overview"}}"""),
    ("human", "Current network state:\n{network_state}\n\nGenerate your monitoring report."),
])

TRAFFIC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are FLOWMASTER, the network traffic simulation agent.
Your mission: generate realistic user traffic patterns across the network.

PERSONALITY: Steady, adaptive, realistic. You simulate real user behavior.

AVAILABLE SOURCE NODES (hosts): H1, H2, H3, H4, H5, H6
AVAILABLE DESTINATION NODES (servers): WEB, DNS, DB

TRAFFIC GUIDELINES:
- Generate 2-5 traffic flows per cycle
- Most traffic should go to WEB (HTTP) and DNS (queries)
- DB traffic should be less frequent
- If some paths are congested or severed, route traffic elsewhere
- If a server is down/isolated, don't send traffic there
- During attacks, user traffic might decrease (users experience outages)
- Regular business hours pattern: more WEB traffic, steady DNS

You MUST respond with valid JSON matching this schema:
{{"flows": [{{"src": "H1", "dst": "WEB"}}, {{"src": "H3", "dst": "DNS"}}], "reasoning": "brief reason"}}"""),
    ("human", "Current network state:\n{network_state}\n\nGenerate traffic flows for this cycle."),
])

# ------------------------------------------------------------------ #
#  Chain Construction
# ------------------------------------------------------------------ #

_llm = None
_chains: Dict = {}

def _get_chains():
    global _llm, _chains
    if _chains:
        return _chains
    _llm = get_llm()
    if _llm is None:
        return {}
    _chains = {
        "attacker": ATTACKER_PROMPT | _llm | JsonOutputParser(),
        "defender": DEFENDER_PROMPT | _llm | JsonOutputParser(),
        "monitor":  MONITOR_PROMPT  | _llm | JsonOutputParser(),
        "traffic":  TRAFFIC_PROMPT  | _llm | JsonOutputParser(),
    }
    return _chains

# ------------------------------------------------------------------ #
#  Agent Invocation Functions
# ------------------------------------------------------------------ #

def invoke_attacker(network_state: str) -> Dict:
    chains = _get_chains()
    if "attacker" not in chains:
        return _fallback_attacker(network_state)
    try:
        result = chains["attacker"].invoke({"network_state": network_state})
        logger.info(f"[REDSTORM] {result}")
        return {
            "agent": "attacker",
            "should_attack": result.get("should_attack", False),
            "attack_type": result.get("attack_type", "ddos"),
            "target": result.get("target", "WEB"),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        logger.error(f"Attacker chain error: {e}")
        return _fallback_attacker(network_state)


def invoke_defender(network_state: str) -> Dict:
    chains = _get_chains()
    if "defender" not in chains:
        return _fallback_defender(network_state)
    try:
        result = chains["defender"].invoke({"network_state": network_state})
        logger.info(f"[GUARDIAN] {result}")
        return {
            "agent": "defender",
            "should_act": result.get("should_act", False),
            "action": result.get("action", ""),
            "target": result.get("target", ""),
            "source": result.get("source", ""),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        logger.error(f"Defender chain error: {e}")
        return _fallback_defender(network_state)


def invoke_monitor(network_state: str) -> Dict:
    chains = _get_chains()
    if "monitor" not in chains:
        return _fallback_monitor(network_state)
    try:
        result = chains["monitor"].invoke({"network_state": network_state})
        logger.info(f"[OVERWATCH] {result}")
        return {
            "agent": "monitor",
            "alerts": result.get("alerts", []),
            "severity": result.get("severity", "normal"),
            "summary": result.get("summary", ""),
        }
    except Exception as e:
        logger.error(f"Monitor chain error: {e}")
        return _fallback_monitor(network_state)


def invoke_traffic(network_state: str) -> Dict:
    chains = _get_chains()
    if "traffic" not in chains:
        return _fallback_traffic(network_state)
    try:
        result = chains["traffic"].invoke({"network_state": network_state})
        logger.info(f"[FLOWMASTER] {result}")
        return {
            "agent": "traffic",
            "flows": result.get("flows", []),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        logger.error(f"Traffic chain error: {e}")
        return _fallback_traffic(network_state)


# ------------------------------------------------------------------ #
#  Fallback Rule-Based Logic (used when Groq key not configured)
# ------------------------------------------------------------------ #

import random

def _fallback_attacker(state_text: str) -> Dict:
    """Rule-based attacker when LLM is unavailable."""
    targets = ["WEB", "DNS", "DB", "CR1", "CR2", "ER1", "ER2"]
    types = ["ddos", "bgp_hijack", "mitm", "port_scan"]
    should_attack = random.random() > 0.45
    target = random.choice(targets)
    atype = random.choice(types)
    # Don't BGP hijack servers
    if atype == "bgp_hijack" and target in ("WEB", "DNS", "DB"):
        atype = "ddos"
    return {
        "agent": "attacker",
        "should_attack": should_attack,
        "attack_type": atype,
        "target": target,
        "reasoning": "Fallback rule-based decision",
    }


def _fallback_defender(state_text: str) -> Dict:
    """Rule-based defender when LLM is unavailable."""
    should_act = "under_attack" in state_text or "compromised" in state_text
    action = "rate_limit"
    target = ""
    if "under_attack" in state_text:
        action = "rate_limit"
    elif "compromised" in state_text:
        action = "heal"

    # Try to extract a target
    for nid in ["WEB", "DNS", "DB", "CR1", "CR2", "CR3", "ER1", "ER2", "ER3", "ER4"]:
        if f"{nid}(" in state_text and ("under_attack" in state_text or "compromised" in state_text):
            # Check if this node is in trouble
            idx = state_text.find(f"{nid}(")
            snippet = state_text[idx:idx+80]
            if "under_attack" in snippet or "compromised" in snippet:
                target = nid
                break
    if not target:
        target = "WEB"
        should_act = False

    return {
        "agent": "defender",
        "should_act": should_act,
        "action": action,
        "target": target,
        "source": "",
        "reasoning": "Fallback rule-based defense",
    }


def _fallback_monitor(state_text: str) -> Dict:
    """Rule-based monitor when LLM is unavailable."""
    alerts = []
    severity = "normal"
    if "under_attack" in state_text:
        alerts.append("Active attack detected on network infrastructure")
        severity = "elevated"
    if "compromised" in state_text:
        alerts.append("Compromised nodes detected — containment advised")
        severity = "critical"
    if "severed" in state_text.lower():
        alerts.append("Severed links detected — routing impact possible")
        severity = "elevated" if severity == "normal" else severity
    if not alerts:
        alerts.append("All systems nominal — no anomalies detected")
    return {
        "agent": "monitor",
        "alerts": alerts,
        "severity": severity,
        "summary": f"Network status: {severity}",
    }


def _fallback_traffic(state_text: str) -> Dict:
    """Rule-based traffic when LLM is unavailable."""
    hosts = ["H1", "H2", "H3", "H4", "H5", "H6"]
    servers = ["WEB", "DNS", "DB"]
    n_flows = random.randint(2, 5)
    flows = []
    for _ in range(n_flows):
        flows.append({"src": random.choice(hosts), "dst": random.choice(servers)})
    return {
        "agent": "traffic",
        "flows": flows,
        "reasoning": "Fallback random traffic generation",
    }
