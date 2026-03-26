"""
NETCRISIS - FastAPI Backend
WebSocket /ws pushes simulation state every tick.
REST endpoints for manual control actions.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from simulation import NetworkSimulation
from graph import create_agent_graph, should_run_agents, run_agents

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  App Setup
# ------------------------------------------------------------------ #

app = FastAPI(title="NETCRISIS Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
#  Global State
# ------------------------------------------------------------------ #

sim = NetworkSimulation()
agent_graph = create_agent_graph()
connected_clients: Set[WebSocket] = set()
sim_task = None

# ------------------------------------------------------------------ #
#  Request Models
# ------------------------------------------------------------------ #

class AttackRequest(BaseModel):
    type: str    # ddos, bgp_hijack, mitm, port_scan
    target: str  # node ID

class LinkRequest(BaseModel):
    source: str
    target: str

# ------------------------------------------------------------------ #
#  WebSocket Connection Manager
# ------------------------------------------------------------------ #

async def broadcast(data: Dict):
    """Send data to all connected WebSocket clients."""
    if not connected_clients:
        return
    msg = json.dumps(data)
    disconnected = set()
    for ws in connected_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.add(ws)
    connected_clients.difference_update(disconnected)


# ------------------------------------------------------------------ #
#  Simulation Loop (Background Task)
# ------------------------------------------------------------------ #

async def simulation_loop():
    """Main tick loop — runs in background, pushes state via WebSocket."""
    logger.info("Simulation loop started")
    while True:
        try:
            if sim.state in ("running", "crisis"):
                # --- Execute one tick ---
                state = sim.tick()

                # --- Run AI agents every N ticks ---
                if should_run_agents(sim.tick_count):
                    summary = sim.get_summary()
                    health = sim.get_health()
                    active = [
                        {"id": a["id"], "type": a["type"], "target": a["target"]}
                        for a in sim.active_attacks if a["active"]
                    ]
                    # Run agents in thread pool to avoid blocking
                    result = await asyncio.to_thread(
                        run_agents, agent_graph,
                        sim.tick_count, health, summary, active
                    )
                    # Apply agent actions to simulation
                    actions = result.get("actions_to_apply", [])
                    if actions:
                        sim.apply_agent_actions(actions)

                    # Merge agent logs into state
                    agent_logs = result.get("agent_logs", [])
                    state["logs"].extend(agent_logs)

                    # Re-serialize state with updated data
                    state = sim.get_state()
                    state["logs"].extend(agent_logs)

                # --- Broadcast to all clients ---
                await broadcast(state)

            # Tick interval based on speed
            interval = 1.0 / sim.speed
            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
            break
        except Exception as e:
            logger.error(f"Simulation loop error: {e}", exc_info=True)
            await asyncio.sleep(1)


# ------------------------------------------------------------------ #
#  WebSocket Endpoint
# ------------------------------------------------------------------ #

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)
    logger.info(f"WebSocket client connected ({len(connected_clients)} total)")

    # Send initial state immediately
    try:
        initial = sim.get_state()
        initial["type"] = "init"
        await ws.send_text(json.dumps(initial))
    except Exception:
        pass

    try:
        while True:
            # Keep connection alive; listen for client messages
            data = await ws.receive_text()
            # Client can send control messages via WebSocket too
            try:
                msg = json.loads(data)
                if msg.get("action") == "start":
                    sim.state = "running"
                elif msg.get("action") == "pause":
                    sim.state = "paused"
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(ws)
        logger.info(f"WebSocket client disconnected ({len(connected_clients)} total)")


# ------------------------------------------------------------------ #
#  REST Endpoints
# ------------------------------------------------------------------ #

@app.get("/health")
async def health_endpoint():
    return {
        "tick": sim.tick_count,
        "health": sim.get_health(),
        "state": sim.state,
        "active_attacks": len([a for a in sim.active_attacks if a["active"]]),
        "nodes": len(sim.G.nodes()),
        "links": len(sim.G.edges()),
    }


@app.post("/control/attack")
async def attack_endpoint(req: AttackRequest):
    if sim.state not in ("running", "crisis"):
        return {"success": False, "error": "Simulation not running"}
    result = sim.launch_attack(req.type, req.target)
    if result:
        return {"success": True, "attack_id": result["id"]}
    return {"success": False, "error": "Invalid target or attack type"}


@app.post("/control/cut-link")
async def cut_link_endpoint(req: LinkRequest):
    ok = sim.sever_link(req.source, req.target)
    if not ok:
        # Try reversed
        ok = sim.sever_link(req.target, req.source)
    return {"success": ok}


@app.post("/control/restore-link")
async def restore_link_endpoint(req: LinkRequest):
    ok = sim.restore_link(req.source, req.target)
    if not ok:
        ok = sim.restore_link(req.target, req.source)
    return {"success": ok}


@app.post("/control/reset")
async def reset_endpoint():
    sim.reset()
    state = sim.get_state()
    state["type"] = "init"
    await broadcast(state)
    return {"success": True}


@app.post("/control/start")
async def start_endpoint():
    sim.state = "running"
    return {"success": True, "state": sim.state}


@app.post("/control/pause")
async def pause_endpoint():
    sim.state = "paused"
    return {"success": True, "state": sim.state}


@app.post("/control/speed")
async def speed_endpoint(speed: float = 1.0):
    sim.speed = max(0.5, min(2.0, speed))
    return {"success": True, "speed": sim.speed}


# ------------------------------------------------------------------ #
#  Startup / Shutdown
# ------------------------------------------------------------------ #

@app.on_event("startup")
async def startup():
    global sim_task
    sim_task = asyncio.create_task(simulation_loop())
    logger.info("NETCRISIS backend started")


@app.on_event("shutdown")
async def shutdown():
    global sim_task
    if sim_task:
        sim_task.cancel()
        try:
            await sim_task
        except asyncio.CancelledError:
            pass
    logger.info("NETCRISIS backend stopped")


# ------------------------------------------------------------------ #
#  Entry Point
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
