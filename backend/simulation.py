"""
NETCRISIS - Network Simulation Engine
NetworkX topology with OSPF/Dijkstra routing, BGP route tables, ACL engine.
"""

import networkx as nx
import random
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class NetworkSimulation:
    """Core network simulation with full topology, routing, and attack processing."""

    def __init__(self):
        self.G: nx.Graph = nx.Graph()
        self.tick_count: int = 0
        self.state: str = "paused"
        self.speed: float = 1.0
        self.active_attacks: List[Dict] = []
        self.pending_logs: List[Dict] = []
        self.pending_packets: List[Dict] = []
        self.bgp_tables: Dict[str, Dict] = {}
        self._attack_id_counter: int = 0
        self._init_topology()
        self._init_bgp_tables()

    # ------------------------------------------------------------------ #
    #  TOPOLOGY INITIALIZATION
    # ------------------------------------------------------------------ #

    def _init_topology(self):
        nodes = [
            ("CR1", {"label": "Core-1", "type": "core", "ip": "10.0.0.1",
                     "services": ["BGP", "OSPF"], "health": 100.0, "status": "normal", "acl": []}),
            ("CR2", {"label": "Core-2", "type": "core", "ip": "10.0.0.2",
                     "services": ["BGP", "OSPF"], "health": 100.0, "status": "normal", "acl": []}),
            ("CR3", {"label": "Core-3", "type": "core", "ip": "10.0.0.3",
                     "services": ["BGP", "OSPF"], "health": 100.0, "status": "normal", "acl": []}),
            ("ER1", {"label": "Edge-1", "type": "edge", "ip": "10.1.0.1",
                     "services": ["NAT", "DHCP"], "health": 100.0, "status": "normal", "acl": []}),
            ("ER2", {"label": "Edge-2", "type": "edge", "ip": "10.2.0.1",
                     "services": ["NAT", "DHCP"], "health": 100.0, "status": "normal", "acl": []}),
            ("ER3", {"label": "Edge-3", "type": "edge", "ip": "10.3.0.1",
                     "services": ["NAT", "DHCP"], "health": 100.0, "status": "normal", "acl": []}),
            ("ER4", {"label": "Edge-4", "type": "edge", "ip": "10.4.0.1",
                     "services": ["NAT", "DHCP"], "health": 100.0, "status": "normal", "acl": []}),
            ("DNS", {"label": "DNS-Srv", "type": "server", "ip": "10.10.1.1",
                     "services": ["DNS"], "health": 100.0, "status": "normal", "acl": []}),
            ("WEB", {"label": "Web-Srv", "type": "server", "ip": "10.10.2.1",
                     "services": ["HTTP", "HTTPS"], "health": 100.0, "status": "normal", "acl": []}),
            ("DB",  {"label": "DB-Srv", "type": "server", "ip": "10.10.3.1",
                     "services": ["MySQL", "Redis"], "health": 100.0, "status": "normal", "acl": []}),
            ("H1",  {"label": "Host-1", "type": "host", "ip": "192.168.1.10",
                     "services": [], "health": 100.0, "status": "normal", "acl": []}),
            ("H2",  {"label": "Host-2", "type": "host", "ip": "192.168.1.20",
                     "services": [], "health": 100.0, "status": "normal", "acl": []}),
            ("H3",  {"label": "Host-3", "type": "host", "ip": "192.168.2.10",
                     "services": [], "health": 100.0, "status": "normal", "acl": []}),
            ("H4",  {"label": "Host-4", "type": "host", "ip": "192.168.2.20",
                     "services": [], "health": 100.0, "status": "normal", "acl": []}),
            ("H5",  {"label": "Host-5", "type": "host", "ip": "192.168.3.10",
                     "services": [], "health": 100.0, "status": "normal", "acl": []}),
            ("H6",  {"label": "Host-6", "type": "host", "ip": "192.168.4.10",
                     "services": [], "health": 100.0, "status": "normal", "acl": []}),
        ]
        edges = [
            ("CR1", "CR2", {"bandwidth": 10000, "utilization": 12.0, "status": "active", "id": "CR1-CR2"}),
            ("CR2", "CR3", {"bandwidth": 10000, "utilization": 10.0, "status": "active", "id": "CR2-CR3"}),
            ("CR1", "CR3", {"bandwidth": 10000, "utilization": 11.0, "status": "active", "id": "CR1-CR3"}),
            ("CR1", "ER1", {"bandwidth": 5000,  "utilization": 15.0, "status": "active", "id": "CR1-ER1"}),
            ("CR1", "ER2", {"bandwidth": 5000,  "utilization": 14.0, "status": "active", "id": "CR1-ER2"}),
            ("CR2", "ER3", {"bandwidth": 5000,  "utilization": 13.0, "status": "active", "id": "CR2-ER3"}),
            ("CR3", "ER4", {"bandwidth": 5000,  "utilization": 12.0, "status": "active", "id": "CR3-ER4"}),
            ("CR2", "ER1", {"bandwidth": 3000,  "utilization": 8.0,  "status": "active", "id": "CR2-ER1"}),
            ("CR3", "ER3", {"bandwidth": 3000,  "utilization": 9.0,  "status": "active", "id": "CR3-ER3"}),
            ("ER3", "DNS", {"bandwidth": 2000,  "utilization": 18.0, "status": "active", "id": "ER3-DNS"}),
            ("ER2", "WEB", {"bandwidth": 2000,  "utilization": 22.0, "status": "active", "id": "ER2-WEB"}),
            ("ER4", "DB",  {"bandwidth": 2000,  "utilization": 16.0, "status": "active", "id": "ER4-DB"}),
            ("ER1", "H1",  {"bandwidth": 1000,  "utilization": 10.0, "status": "active", "id": "ER1-H1"}),
            ("ER1", "H2",  {"bandwidth": 1000,  "utilization": 9.0,  "status": "active", "id": "ER1-H2"}),
            ("ER2", "H3",  {"bandwidth": 1000,  "utilization": 11.0, "status": "active", "id": "ER2-H3"}),
            ("ER2", "H4",  {"bandwidth": 1000,  "utilization": 8.0,  "status": "active", "id": "ER2-H4"}),
            ("ER3", "H5",  {"bandwidth": 1000,  "utilization": 7.0,  "status": "active", "id": "ER3-H5"}),
            ("ER4", "H6",  {"bandwidth": 1000,  "utilization": 10.0, "status": "active", "id": "ER4-H6"}),
        ]
        self.G.add_nodes_from(nodes)
        self.G.add_edges_from(edges)
        for _, _, d in self.G.edges(data=True):
            d["_base_util"] = d["utilization"]
            d["_attack_boost"] = False

    # ------------------------------------------------------------------ #
    #  BGP ROUTE TABLES
    # ------------------------------------------------------------------ #

    def _init_bgp_tables(self):
        for nid in self.G.nodes():
            ntype = self.G.nodes[nid].get("type")
            if ntype in ("core", "edge"):
                self.bgp_tables[nid] = self._compute_bgp_table(nid)

    def _compute_bgp_table(self, node_id: str) -> Dict:
        table: Dict[str, Dict] = {}
        for target in self.G.nodes():
            if target == node_id:
                continue
            try:
                path = nx.shortest_path(self.G, node_id, target, weight=self._edge_weight)
                if len(path) > 1:
                    tip = self.G.nodes[target]["ip"]
                    table[tip] = {
                        "next_hop": path[1],
                        "path": path,
                        "metric": len(path) - 1,
                        "origin": "igp",
                    }
            except nx.NetworkXNoPath:
                pass
        return table

    def _rebuild_bgp_tables(self):
        self._init_bgp_tables()

    @staticmethod
    def _edge_weight(u, v, d):
        if d.get("status") == "severed":
            return 9999
        return 1 + d.get("utilization", 0) / 100

    # ------------------------------------------------------------------ #
    #  OSPF ROUTING (Dijkstra via NetworkX)
    # ------------------------------------------------------------------ #

    def ospf_route(self, src: str, dst: str) -> Optional[List[str]]:
        subG = nx.Graph()
        for u, v, d in self.G.edges(data=True):
            if d["status"] == "severed":
                continue
            nu, nv = self.G.nodes[u], self.G.nodes[v]
            if nu["status"] == "isolated" or nv["status"] == "isolated":
                continue
            w = 1 + d["utilization"] / 100
            subG.add_edge(u, v, weight=w)
        try:
            return nx.dijkstra_path(subG, src, dst, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    # ------------------------------------------------------------------ #
    #  ACL ENGINE
    # ------------------------------------------------------------------ #

    def check_acl(self, node_id: str, src_ip: str) -> bool:
        node = self.G.nodes.get(node_id)
        if not node:
            return True
        for rule in node.get("acl", []):
            if rule["action"] == "deny":
                if rule.get("src") in (src_ip, "any"):
                    return False
        return True

    def add_acl_rule(self, node_id: str, rule: Dict):
        if node_id in self.G.nodes:
            self.G.nodes[node_id]["acl"].append(rule)
            self.pending_logs.append({
                "type": "defense", "tick": self.tick_count,
                "message": f"ACL UPDATED on {self.G.nodes[node_id]['label']}",
                "detail": f"Rule: {rule['action']} src={rule.get('src','any')}",
            })

    def clear_acl(self, node_id: str):
        if node_id in self.G.nodes:
            self.G.nodes[node_id]["acl"] = []

    # ------------------------------------------------------------------ #
    #  TICK ENGINE
    # ------------------------------------------------------------------ #

    def tick(self) -> Dict:
        self.tick_count += 1
        self.pending_logs = []
        self.pending_packets = []

        self._update_baseline_traffic()
        self._process_attacks()
        self._auto_recovery()
        self._generate_traffic()

        health = self.get_health()
        if health < 30 and self.state != "crisis":
            self.state = "crisis"
            self.pending_logs.append({
                "type": "monitor", "tick": self.tick_count,
                "message": "CRITICAL: Network health below 30%",
                "detail": f"Health: {health}% — Multiple systems failing",
            })
        elif health >= 30 and self.state == "crisis":
            self.state = "running"

        if self.tick_count % 10 == 0:
            self._rebuild_bgp_tables()

        return self.get_state()

    # ------------------------------------------------------------------ #
    #  BASELINE TRAFFIC
    # ------------------------------------------------------------------ #

    def _update_baseline_traffic(self):
        for u, v, d in self.G.edges(data=True):
            if d["status"] == "severed":
                continue
            if not d["_attack_boost"]:
                delta = (random.random() - 0.5) * 6
                d["_base_util"] = max(5, min(35, d["_base_util"] + delta))
                d["utilization"] = d["_base_util"]

    _TRAFFIC_PATTERNS = [
        ("H1", "WEB", 0.7), ("H2", "DNS", 0.8), ("H3", "WEB", 0.6),
        ("H4", "DB", 0.4),  ("H5", "DNS", 0.5), ("H6", "WEB", 0.5),
        ("H1", "DB", 0.3),  ("H3", "DNS", 0.6),
    ]

    def _generate_traffic(self):
        for src, dst, freq in self._TRAFFIC_PATTERNS:
            if random.random() < freq:
                route = self.ospf_route(src, dst)
                if route:
                    self.pending_packets.append({"path": route, "type": "legitimate"})

    # ------------------------------------------------------------------ #
    #  ATTACK PROCESSING
    # ------------------------------------------------------------------ #

    def launch_attack(self, attack_type: str, target_id: str) -> Optional[Dict]:
        node = self.G.nodes.get(target_id)
        if not node or node["status"] == "isolated":
            return None

        if attack_type == "bgp_hijack" and node["type"] not in ("core", "edge"):
            self.pending_logs.append({
                "type": "attack", "tick": self.tick_count,
                "message": "BGP HIJACK FAILED — Invalid target",
                "detail": "Only routers can be targeted",
            })
            return None

        self._attack_id_counter += 1
        durations = {"ddos": random.randint(15, 25), "bgp_hijack": 20, "mitm": 18, "port_scan": 8}
        attack = {
            "id": f"{attack_type}-{self._attack_id_counter}",
            "type": attack_type,
            "target": target_id,
            "start_tick": self.tick_count,
            "duration": durations.get(attack_type, 15),
            "active": True,
            "intensity": 0,
            "max_intensity": 80 + random.random() * 20,
            "packets_intercepted": 0,
            "ports_scanned": 0,
            "routes_hijacked": 0,
        }
        self.active_attacks.append(attack)
        if attack_type != "port_scan":
            node["status"] = "under_attack"

        labels = {"ddos": "DDoS", "bgp_hijack": "BGP HIJACK", "mitm": "MITM", "port_scan": "PORT SCAN"}
        self.pending_logs.append({
            "type": "attack", "tick": self.tick_count,
            "message": f"INITIATING {labels[attack_type]} --> {node['label']}",
            "detail": f"Target: {node['ip']}",
        })
        return attack

    def _process_attacks(self):
        for attack in self.active_attacks:
            if not attack["active"]:
                continue
            elapsed = self.tick_count - attack["start_tick"]
            if elapsed >= attack["duration"]:
                self._end_attack(attack)
                continue
            handler = {
                "ddos": self._tick_ddos,
                "bgp_hijack": self._tick_bgp,
                "mitm": self._tick_mitm,
                "port_scan": self._tick_scan,
            }.get(attack["type"])
            if handler:
                handler(attack, elapsed)
        self.active_attacks = [a for a in self.active_attacks if a["active"]]

    def _tick_ddos(self, atk, elapsed):
        tid = atk["target"]
        t = self.G.nodes.get(tid)
        if not t or t["status"] == "isolated":
            self._end_attack(atk)
            return
        ramp = min(1.0, elapsed / 5.0)
        atk["intensity"] = atk["max_intensity"] * ramp
        self._damage_node(tid, 3 + atk["intensity"] / 20)
        for nb in self.G.neighbors(tid):
            ed = self.G.edges[tid, nb]
            if ed["status"] == "active":
                ed["_attack_boost"] = True
                ed["utilization"] = min(100, 40 + atk["intensity"] * 0.6)
        if random.random() > 0.3:
            hosts = [n for n in self.G.nodes() if self.G.nodes[n]["type"] == "host"]
            if hosts:
                src = random.choice(hosts)
                route = self.ospf_route(src, tid)
                if route:
                    self.pending_packets.append({"path": route, "type": "malicious"})
        if elapsed % 4 == 0 and elapsed > 0:
            self.pending_logs.append({
                "type": "attack", "tick": self.tick_count,
                "message": f"DDoS on {t['label']} — Flood active",
                "detail": f"Intensity: {int(atk['intensity'])}% | Health: {int(t['health'])}%",
            })

    def _tick_bgp(self, atk, elapsed):
        tid = atk["target"]
        t = self.G.nodes.get(tid)
        if not t or t["status"] == "isolated":
            self._end_attack(atk)
            return
        self._damage_node(tid, 2)
        for nb in self.G.neighbors(tid):
            self._damage_node(nb, 0.8)
        atk["routes_hijacked"] = min(12, int(elapsed * 0.8))
        if random.random() > 0.5:
            nbs = list(self.G.neighbors(tid))
            if nbs:
                dst = random.choice(nbs)
                self.pending_packets.append({"path": [tid, dst], "type": "malicious"})
        if elapsed % 5 == 0 and elapsed > 0:
            self.pending_logs.append({
                "type": "attack", "tick": self.tick_count,
                "message": f"BGP HIJACK active on {t['label']}",
                "detail": f"Routes hijacked: {atk['routes_hijacked']}",
            })

    def _tick_mitm(self, atk, elapsed):
        tid = atk["target"]
        t = self.G.nodes.get(tid)
        if not t or t["status"] == "isolated":
            self._end_attack(atk)
            return
        self._damage_node(tid, 1.5)
        atk["packets_intercepted"] += random.randint(5, 15)
        if elapsed % 4 == 0 and elapsed > 0:
            self.pending_logs.append({
                "type": "attack", "tick": self.tick_count,
                "message": f"MITM on {t['label']} — Intercepting",
                "detail": f"Packets captured: {atk['packets_intercepted']}",
            })

    def _tick_scan(self, atk, elapsed):
        tid = atk["target"]
        t = self.G.nodes.get(tid)
        if not t:
            self._end_attack(atk)
            return
        atk["ports_scanned"] = min(1024, int((elapsed / atk["duration"]) * 1024))
        self._damage_node(tid, 0.5)
        if random.random() > 0.4:
            hosts = [n for n in self.G.nodes() if self.G.nodes[n]["type"] == "host"]
            if hosts:
                src = random.choice(hosts)
                route = self.ospf_route(src, tid)
                if route:
                    self.pending_packets.append({"path": route, "type": "malicious"})
        if elapsed % 3 == 0 and elapsed > 0:
            self.pending_logs.append({
                "type": "attack", "tick": self.tick_count,
                "message": f"SCANNING {t['label']} — {int(atk['ports_scanned']/1024*100)}%",
                "detail": f"Ports: {atk['ports_scanned']}/1024",
            })

    def _end_attack(self, atk):
        atk["active"] = False
        tid = atk["target"]
        t = self.G.nodes.get(tid)
        if atk["type"] == "ddos":
            for nb in self.G.neighbors(tid):
                ed = self.G.edges[tid, nb]
                ed["_attack_boost"] = False
                ed["utilization"] = ed["_base_util"]
        if t:
            if t["health"] <= 20:
                t["status"] = "compromised"
            elif t["status"] == "under_attack":
                t["status"] = "recovering"
        labels = {"ddos": "DDoS", "bgp_hijack": "BGP HIJACK", "mitm": "MITM", "port_scan": "PORT SCAN"}
        self.pending_logs.append({
            "type": "monitor", "tick": self.tick_count,
            "message": f"{labels.get(atk['type'], atk['type'])} on {t['label'] if t else '?'} ended",
            "detail": f"Final health: {int(t['health']) if t else '?'}% | Status: {t['status'] if t else '?'}",
        })

    # ------------------------------------------------------------------ #
    #  AUTO RECOVERY
    # ------------------------------------------------------------------ #

    def _auto_recovery(self):
        for nid in self.G.nodes():
            n = self.G.nodes[nid]
            if n["status"] == "compromised" and not self._is_under_attack(nid):
                self._heal_node(nid, 1.5)
                if self.tick_count % 8 == 0:
                    self.pending_logs.append({
                        "type": "defense", "tick": self.tick_count,
                        "message": f"AUTO-RECOVERY: {n['label']}",
                        "detail": f"Health: {int(n['health'])}%",
                    })
            elif n["status"] == "recovering":
                self._heal_node(nid, 2)
            elif n["status"] == "normal" and n["health"] < 100:
                self._heal_node(nid, 0.5)

    # ------------------------------------------------------------------ #
    #  NODE HELPERS
    # ------------------------------------------------------------------ #

    def _damage_node(self, nid: str, amount: float):
        n = self.G.nodes.get(nid)
        if not n:
            return
        n["health"] = max(0, n["health"] - amount)
        if n["health"] <= 0 and n["status"] != "isolated":
            n["status"] = "compromised"

    def _heal_node(self, nid: str, amount: float):
        n = self.G.nodes.get(nid)
        if not n:
            return
        n["health"] = min(100, n["health"] + amount)
        if n["health"] > 50 and n["status"] == "compromised":
            n["status"] = "recovering"
        if n["health"] >= 90 and n["status"] == "recovering":
            n["status"] = "normal"

    def _is_under_attack(self, nid: str) -> bool:
        return any(a["target"] == nid and a["active"] for a in self.active_attacks)

    # ------------------------------------------------------------------ #
    #  LINK CONTROLS
    # ------------------------------------------------------------------ #

    def sever_link(self, a: str, b: str) -> bool:
        if self.G.has_edge(a, b):
            self.G.edges[a, b]["status"] = "severed"
            self.G.edges[a, b]["utilization"] = 0
            self._rebuild_bgp_tables()
            self.pending_logs.append({
                "type": "monitor", "tick": self.tick_count,
                "message": f"LINK SEVERED: {a} <-> {b}",
                "detail": "Manual intervention",
            })
            return True
        return False

    def restore_link(self, a: str, b: str) -> bool:
        if self.G.has_edge(a, b):
            d = self.G.edges[a, b]
            d["status"] = "active"
            d["utilization"] = random.uniform(5, 20)
            d["_base_util"] = d["utilization"]
            d["_attack_boost"] = False
            self._rebuild_bgp_tables()
            self.pending_logs.append({
                "type": "monitor", "tick": self.tick_count,
                "message": f"LINK RESTORED: {a} <-> {b}",
                "detail": "Manual intervention",
            })
            return True
        return False

    # ------------------------------------------------------------------ #
    #  HEALTH
    # ------------------------------------------------------------------ #

    _WEIGHTS = {"core": 3, "edge": 2, "server": 2.5, "host": 1}

    def get_health(self) -> int:
        tw = wh = 0
        for nid in self.G.nodes():
            n = self.G.nodes[nid]
            w = self._WEIGHTS.get(n["type"], 1)
            tw += w
            wh += n["health"] * w
        return round(wh / tw) if tw else 0

    # ------------------------------------------------------------------ #
    #  STATE SERIALIZATION
    # ------------------------------------------------------------------ #

    def get_state(self) -> Dict:
        nodes = []
        for nid in self.G.nodes():
            n = self.G.nodes[nid]
            nodes.append({
                "id": nid, "label": n["label"], "type": n["type"], "ip": n["ip"],
                "health": round(n["health"], 1), "status": n["status"],
                "services": n["services"], "acl": [{"action": r["action"], "src": r.get("src", "any")} for r in n.get("acl", [])],
            })
        links = []
        for u, v, d in self.G.edges(data=True):
            links.append({
                "id": d.get("id", f"{u}-{v}"), "source": u, "target": v,
                "bandwidth": d["bandwidth"], "utilization": round(d["utilization"], 1),
                "status": d["status"],
            })
        return {
            "type": "tick",
            "tick": self.tick_count,
            "health": self.get_health(),
            "state": self.state,
            "nodes": nodes,
            "links": links,
            "packets": list(self.pending_packets),
            "logs": list(self.pending_logs),
            "active_attacks": [
                {"id": a["id"], "type": a["type"], "target": a["target"],
                 "intensity": round(a.get("intensity", 0), 1), "active": a["active"]}
                for a in self.active_attacks if a["active"]
            ],
        }

    def get_summary(self) -> str:
        """Condensed network summary for LLM agent context."""
        health = self.get_health()
        lines = [f"Tick: {self.tick_count} | Overall Health: {health}% | State: {self.state}"]

        critical = [n for n in self.G.nodes() if self.G.nodes[n]["health"] < 60]
        if critical:
            lines.append("Low-health nodes: " + ", ".join(
                f"{nid}({int(self.G.nodes[nid]['health'])}%,{self.G.nodes[nid]['status']})" for nid in critical
            ))

        hot = [(u, v) for u, v, d in self.G.edges(data=True) if d["utilization"] > 60 and d["status"] == "active"]
        if hot:
            lines.append("High-util links: " + ", ".join(f"{u}<->{v}" for u, v in hot))

        severed = [(u, v) for u, v, d in self.G.edges(data=True) if d["status"] == "severed"]
        if severed:
            lines.append("Severed links: " + ", ".join(f"{u}<->{v}" for u, v in severed))

        if self.active_attacks:
            lines.append("Active attacks: " + ", ".join(
                f"{a['type']} on {a['target']}" for a in self.active_attacks if a["active"]
            ))

        node_summary = []
        for nid in self.G.nodes():
            n = self.G.nodes[nid]
            node_summary.append(f"{nid}({n['type']},{n['ip']},hp={int(n['health'])},{n['status']},svc={n['services']})")
        lines.append("All nodes: " + " | ".join(node_summary))
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  APPLY AGENT ACTIONS
    # ------------------------------------------------------------------ #

    def apply_agent_actions(self, actions: List[Dict]):
        for act in actions:
            try:
                agent = act.get("agent", "")
                if agent == "attacker" and act.get("should_attack"):
                    self.launch_attack(act["attack_type"], act["target"])
                elif agent == "defender":
                    cmd = act.get("action", "")
                    target = act.get("target", "")
                    if cmd == "rate_limit":
                        for a in self.active_attacks:
                            if a["target"] == target and a["active"]:
                                a["max_intensity"] *= 0.7
                        self.pending_logs.append({
                            "type": "defense", "tick": self.tick_count,
                            "message": f"RATE LIMITING on {target}",
                            "detail": "Reducing attack throughput by 30%",
                        })
                    elif cmd == "isolate":
                        n = self.G.nodes.get(target)
                        if n:
                            n["status"] = "isolated"
                            self.pending_logs.append({
                                "type": "defense", "tick": self.tick_count,
                                "message": f"ISOLATED {n['label']}",
                                "detail": "Node quarantined from network",
                            })
                    elif cmd == "add_acl":
                        self.add_acl_rule(target, act.get("rule", {"action": "deny", "src": "any"}))
                    elif cmd == "heal":
                        self._heal_node(target, 15)
                        n = self.G.nodes.get(target)
                        if n:
                            self.pending_logs.append({
                                "type": "defense", "tick": self.tick_count,
                                "message": f"EMERGENCY PATCH on {n['label']}",
                                "detail": f"Restored to {int(n['health'])}%",
                            })
                    elif cmd == "restore_link":
                        self.restore_link(act.get("source", ""), target)
                elif agent == "traffic":
                    for flow in act.get("flows", []):
                        route = self.ospf_route(flow["src"], flow["dst"])
                        if route:
                            self.pending_packets.append({"path": route, "type": "legitimate"})
            except Exception as e:
                logger.warning(f"Failed to apply agent action: {e}")

    # ------------------------------------------------------------------ #
    #  RESET
    # ------------------------------------------------------------------ #

    def reset(self):
        for nid in self.G.nodes():
            n = self.G.nodes[nid]
            n["health"] = 100.0
            n["status"] = "normal"
            n["acl"] = []
        for u, v, d in self.G.edges(data=True):
            d["status"] = "active"
            d["utilization"] = random.uniform(5, 20)
            d["_base_util"] = d["utilization"]
            d["_attack_boost"] = False
        self.active_attacks = []
        self.tick_count = 0
        self.state = "paused"
        self._rebuild_bgp_tables()
        self.pending_logs = [{"type": "monitor", "tick": 0, "message": "SIMULATION RESET", "detail": "All systems nominal"}]
        self.pending_packets = []
