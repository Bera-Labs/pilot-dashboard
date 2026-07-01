#!/usr/bin/env python3
"""Pilot Dashboard — FastAPI wrapper for Railway deployment.
Read-only browser. All POSTs from Hermes/cron only.
"""
import json, os, time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── STATE ──────────────────────────────────
def default_state():
    return {
        "mission_start": "2026-05-18T04:00:00",
        "metrics": {"wip": 0, "completed": 0, "ooda_last": None, "avg_latency": None},
        "decisions": [],
        "activity_log": [
            {"time": time.strftime("%H:%M:%S"), "type": "BOOT", "message": "Dashboard initialized"},
            {"time": time.strftime("%H:%M:%S"), "type": "LOAD", "message": "STEM Stack v2.0 active"},
            {"time": time.strftime("%H:%M:%S"), "type": "STATUS", "message": "Read-Only mode active"}
        ],
        "properties": {"tracked": 0, "viewings": 0, "offers": 0},
        "skills": [
            {"name": "probabilistic-thinking", "tags": "randomness, bias, causality"},
            {"name": "warp-speed-execution", "tags": "velocity, bottlenecks, compound"},
            {"name": "pilot-dashboard", "tags": "this dashboard itself"}
        ]
    }

def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        state = default_state()
        save_state(state)
        return state

def save_state(state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── GET (browser) ───────────────────────────
@app.get("/api/state")
def api_state():
    return load_state()

@app.get("/api/wiki-graph")
def api_wiki_graph():
    try:
        return json.loads((DATA_DIR / "wiki-graph.json").read_text())
    except FileNotFoundError:
        return JSONResponse({"error": "wiki-graph.json not found"}, status_code=404)

@app.get("/api/augmented-graph")
def api_augmented_graph():
    try:
        return json.loads((DATA_DIR / "augmented-graph.json").read_text())
    except FileNotFoundError:
        return JSONResponse({"error": "augmented-graph.json not found"}, status_code=404)

@app.get("/api/housing-graph")
def api_housing_graph():
    try:
        return json.loads((DATA_DIR / "housing-graph.json").read_text())
    except FileNotFoundError:
        return JSONResponse({"error": "housing-graph.json not found"}, status_code=404)

@app.get("/api/growth")
def api_growth():
    try:
        return json.loads((DATA_DIR / "growth.json").read_text())
    except FileNotFoundError:
        return JSONResponse({"error": "growth.json not found"}, status_code=404)

@app.post("/api/growth")
async def post_growth(req: Request):
    body = await req.json()
    growth_file = DATA_DIR / "growth.json"
    try:
        growth = json.loads(growth_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        growth = {"last_updated": "", "history": []}
    growth["last_updated"] = time.strftime("%Y-%m-%d")
    # Append new data point (or merge if same date)
    new_entry = {
        "date": body.get("date", time.strftime("%Y-%m-%d")),
        "cumulative_completions": body.get("cumulative_completions", 0),
        "wip": body.get("wip", 0),
        "velocity": body.get("velocity", 0),
        "completion_rate": body.get("completion_rate", 0)
    }
    # Replace existing entry for same date, otherwise append
    existing = [i for i, h in enumerate(growth["history"]) if h["date"] == new_entry["date"]]
    if existing:
        growth["history"][existing[0]] = new_entry
    else:
        growth["history"].append(new_entry)
    growth["history"].sort(key=lambda x: x["date"])
    growth_file.write_text(json.dumps(growth, indent=2))
    return {"status": "ok"}

# ── POST (Hermes/cron only) ────────────────
@app.post("/api/log-decision")
async def log_decision(req: Request):
    body = await req.json()
    state = load_state()
    state["decisions"].append({
        "title": body.get("title", ""),
        "confidence": body.get("confidence", 50),
        "rationale": body.get("rationale", ""),
        "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "resolved": False, "outcome": None
    })
    state["activity_log"].insert(0, {"time": time.strftime("%H:%M:%S"), "type": "DECISION",
        "message": f"\"{body.get('title','')}\" — {body.get('confidence',50)}% confidence"})
    state["activity_log"] = state["activity_log"][:100]
    save_state(state)
    return {"status": "ok"}

@app.post("/api/resolve-decision")
async def resolve_decision(req: Request):
    body = await req.json()
    state = load_state()
    pending = [d for d in state["decisions"] if not d["resolved"]]
    if pending:
        pending[-1]["resolved"] = True
        pending[-1]["outcome"] = body.get("outcome", False)
        pending[-1]["resolvedDate"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        resolved = [d for d in state["decisions"] if d["resolved"]]
        correct = sum(1 for d in resolved if d["outcome"] is True)
        total = len(resolved)
        avg_conf = sum(d["confidence"] for d in resolved) / total if total else 0
        state["activity_log"].insert(0, {"time": time.strftime("%H:%M:%S"), "type": "CALIBRATE",
            "message": f"{correct}/{total} correct ({round(correct/total*100)}%) vs avg {round(avg_conf)}% confidence"})
        state["activity_log"] = state["activity_log"][:100]
        save_state(state)
    return {"status": "ok"}

@app.post("/api/log-completion")
def log_completion():
    state = load_state()
    state["metrics"]["completed"] = state["metrics"].get("completed", 0) + 1
    state["metrics"]["wip"] = max(0, state["metrics"].get("wip", 0) - 1)
    state["activity_log"].insert(0, {"time": time.strftime("%H:%M:%S"), "type": "COMPLETE",
        "message": f"Task finished. WIP: {state['metrics']['wip']} | Total: {state['metrics']['completed']}"})
    state["activity_log"] = state["activity_log"][:100]
    save_state(state)
    return {"status": "ok"}

@app.post("/api/set-wip")
async def set_wip(req: Request):
    body = await req.json()
    state = load_state()
    state["metrics"]["wip"] = body.get("count", 0)
    if "detail" in body:
        state["metrics"]["detail"] = body["detail"]
    save_state(state)
    return {"status": "ok"}

@app.post("/api/set-completed")
async def set_completed(req: Request):
    body = await req.json()
    state = load_state()
    state["metrics"]["completed"] = body.get("count", 0)
    if "detail" in body:
        state["metrics"]["completed_detail"] = body["detail"]
    save_state(state)
    return {"status": "ok"}

@app.post("/api/set-ooda")
async def set_ooda(req: Request):
    body = await req.json()
    state = load_state()
    state["metrics"]["ooda_last"] = body.get("seconds", 0)
    state["activity_log"].insert(0, {"time": time.strftime("%H:%M:%S"), "type": "OODA",
        "message": f"Cycle complete: {body.get('seconds', 0)}s"})
    state["activity_log"] = state["activity_log"][:100]
    save_state(state)
    return {"status": "ok"}

@app.post("/api/add-log")
async def add_log(req: Request):
    body = await req.json()
    state = load_state()
    state["activity_log"].insert(0, {"time": time.strftime("%H:%M:%S"),
        "type": body.get("type", "INFO"), "message": body.get("message", "")})
    state["activity_log"] = state["activity_log"][:100]
    save_state(state)
    return {"status": "ok"}

@app.post("/api/update-properties")
async def update_properties(req: Request):
    body = await req.json()
    state = load_state()
    for key in ["tracked", "viewings", "offers"]:
        if key in body:
            state["properties"][key] = body[key]
    if "top" in body:
        state["properties"]["top"] = body["top"]
    save_state(state)
    return {"status": "ok"}

@app.post("/api/set-skills")
async def set_skills(req: Request):
    body = await req.json()
    state = load_state()
    state["skills"] = body.get("skills", state.get("skills", []))
    save_state(state)
    return {"status": "ok"}

# ── STATIC ──────────────────────────────────
@app.get("/")
def index():
    return FileResponse(ROOT / "index.html")

@app.get("/dashboard.html")
def dashboard():
    return FileResponse(ROOT / "index.html")

@app.get("/momentum.html")
def momentum():
    return FileResponse(ROOT / "assets" / "momentum.html")
