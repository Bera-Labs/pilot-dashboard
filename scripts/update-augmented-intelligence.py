#!/usr/bin/env python3
"""Validate and atomically apply one Augmented Intelligence analysis payload.

The model produces one JSON payload. This script validates it, then updates the
four coupled artifacts together: dashboard state, growth history, calibration,
and the canonical current synthesis Markdown file.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


def fail(message: str) -> None:
    raise ValueError(message)


def require(mapping: dict, key: str, expected_type):
    if key not in mapping:
        fail(f"missing required field: {key}")
    value = mapping[key]
    if not isinstance(value, expected_type):
        fail(f"{key} must be {expected_type}, got {type(value).__name__}")
    return value


def validate(payload: dict) -> None:
    require(payload, "last_run", str)
    try:
        datetime.fromisoformat(payload["last_run"].replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"last_run must be ISO-8601: {exc}")

    require(payload, "compound_velocity", (int, float))
    require(payload, "wip_count", int)
    require(payload, "action_completion_rate", (int, float))
    if not 0 <= payload["action_completion_rate"] <= 1:
        fail("action_completion_rate must be between 0 and 1")

    bottleneck = require(payload, "bottleneck", dict)
    for key in ("what", "why", "unlocked_by", "recurring", "recurrence_count"):
        require(bottleneck, key, bool if key == "recurring" else int if key == "recurrence_count" else str)

    trajectories = require(payload, "trajectories", dict)
    if not trajectories:
        fail("trajectories cannot be empty")

    actions = require(payload, "top_actions", list)
    if len(actions) != 3:
        fail("top_actions must contain exactly 3 actions")
    for index, action in enumerate(actions, 1):
        if not isinstance(action, dict):
            fail(f"top_actions[{index}] must be an object")
        for key in ("task_id", "action", "time", "impact", "status", "first_step", "done_when", "fallback"):
            require(action, key, str)

    forecast = require(payload, "forecast", dict)
    probabilities = []
    for key in ("bear", "base", "bull"):
        scenario = require(forecast, key, dict)
        require(scenario, "scenario", str)
        probability = require(scenario, "probability", (int, float))
        if not 0 <= probability <= 1:
            fail(f"forecast.{key}.probability must be between 0 and 1")
        probabilities.append(probability)
    if abs(sum(probabilities) - 1.0) > 0.001:
        fail(f"forecast probabilities must sum to 1.0, got {sum(probabilities):.4f}")

    strategy = require(payload, "stem_strategy", dict)
    for key in ("euclidean", "probabilistic", "bets", "warp_speed"):
        require(strategy, key, dict)

    require(payload, "patterns", list)
    require(payload, "mantra", str)
    require(payload, "data_sources", dict)
    require(payload, "evidence_summary", str)
    require(payload, "confidence", (int, float))
    if not 0 <= payload["confidence"] <= 1:
        fail("confidence must be between 0 and 1")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_json(path: Path, default: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else default
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def strategy_text(value: dict) -> str:
    return " ".join(str(v) for v in value.values() if v not in (None, ""))


def canonical_markdown(payload: dict) -> str:
    actions = "\n".join(
        f"{i}. **{a['action']}** (`{a['task_id']}`) — {a['time']}. "
        f"First: {a['first_step']} Done when: {a['done_when']} Fallback: {a['fallback']}"
        for i, a in enumerate(payload["top_actions"], 1)
    )
    forecast = payload["forecast"]
    return f'''---
canonical: true
status: current
confidence: {payload["confidence"]:.2f}
evidence: current-outliner-and-lifeos
updated_at: {payload["last_run"]}
---
# Current Augmented Intelligence

**STEM Model:** [[Euclidean Thinking]] and [[Probabilistic Thinking]] and [[Thinking in Bets]] and [[Warp-Speed Execution]]
**Data Source:** {payload["evidence_summary"]}

## Current Constraint
{payload["bottleneck"]["what"]}

{payload["bottleneck"]["why"]}

## Current Strategy
- **Euclidean:** {strategy_text(payload["stem_strategy"]["euclidean"])}
- **Probabilistic:** {strategy_text(payload["stem_strategy"]["probabilistic"])}
- **Thinking in Bets:** {strategy_text(payload["stem_strategy"]["bets"])}
- **Warp-Speed:** {strategy_text(payload["stem_strategy"]["warp_speed"])}

## Current Actions
{actions}

## Forecast
- Bear ({forecast["bear"]["probability"]:.0%}): {forecast["bear"]["scenario"]}
- Base ({forecast["base"]["probability"]:.0%}): {forecast["base"]["scenario"]}
- Bull ({forecast["bull"]["probability"]:.0%}): {forecast["bull"]["scenario"]}

## Evidence and Confidence
Confidence: {payload["confidence"]:.0%}

{payload["evidence_summary"]}

**Links:**
- [[WIP Induced Paralysis]]
- [[Asymmetric Micro-Bets]]
- [[The Calibration Gap]]
'''


def apply(payload: dict, dashboard_root: Path, calibration_file: Path, wiki_root: Path) -> dict:
    state_file = dashboard_root / "data" / "state.json"
    growth_file = dashboard_root / "data" / "growth.json"
    canonical_file = wiki_root / "connections" / "Current Augmented Intelligence.md"

    state = load_json(state_file, {})
    previous = state.get("momentum_analysis", {})
    same_run = previous.get("last_run") == payload["last_run"]
    if same_run:
        payload.setdefault("velocity_delta", previous.get("velocity_delta", 0))
        payload.setdefault("velocity_trend", previous.get("velocity_trend", "flat"))
        payload.setdefault("wip_delta", previous.get("wip_delta", 0))
    else:
        payload.setdefault("velocity_delta", round(payload["compound_velocity"] - previous.get("compound_velocity", payload["compound_velocity"]), 4))
        payload.setdefault("velocity_trend", "up" if payload["velocity_delta"] > 0 else "down" if payload["velocity_delta"] < 0 else "flat")
        payload.setdefault("wip_delta", payload["wip_count"] - previous.get("wip_count", payload["wip_count"]))
    state["momentum_analysis"] = payload
    state["updated"] = payload["last_run"]

    run_date = payload["last_run"][:10]
    growth = load_json(growth_file, {"last_updated": "", "history": []})
    history = growth.setdefault("history", [])
    previous_cumulative = max((item.get("cumulative_completions", 0) for item in history), default=0)
    current_completed = state.get("metrics", {}).get("completed", 0)
    growth_entry = {
        "date": run_date,
        "cumulative_completions": max(previous_cumulative, current_completed),
        "wip": payload["wip_count"],
        "velocity": payload["compound_velocity"],
        "completion_rate": payload["action_completion_rate"],
    }
    growth["history"] = sorted([item for item in history if item.get("date") != run_date] + [growth_entry], key=lambda item: item["date"])
    growth["last_updated"] = run_date

    calibration = load_json(calibration_file, {"version": "3.0.0", "predictions": [], "metrics": {}})
    predictions = calibration.setdefault("predictions", [])
    calibration_entry = {
        "date": payload["last_run"],
        "forecast": payload["forecast"],
        "bottleneck": payload["bottleneck"],
        "top_actions": [{**action, "status_at_next_run": None} for action in payload["top_actions"]],
        "compound_velocity": payload["compound_velocity"],
        "wip_count": payload["wip_count"],
        "action_completion_rate": payload["action_completion_rate"],
        "data_sources": payload["data_sources"],
        "confidence": payload["confidence"],
    }
    calibration["predictions"] = [entry for entry in predictions if entry.get("date") != payload["last_run"]] + [calibration_entry]
    calibration.setdefault("metrics", {})["last_review"] = payload["last_run"]
    calibration["metrics"]["total_runs"] = len(calibration["predictions"])

    atomic_write(state_file, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    atomic_write(growth_file, json.dumps(growth, indent=2, ensure_ascii=False) + "\n")
    atomic_write(calibration_file, json.dumps(calibration, indent=2, ensure_ascii=False) + "\n")
    atomic_write(canonical_file, canonical_markdown(payload))

    return {
        "state": str(state_file),
        "growth": str(growth_file),
        "calibration": str(calibration_file),
        "canonical": str(canonical_file),
        "run_date": run_date,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument("--dashboard-root", type=Path, default=Path("/root/pilot-dashboard"))
    parser.add_argument("--calibration", type=Path, default=Path("/root/.hermes/skills/stem-stack/nightly-momentum-engine/calibration.json"))
    parser.add_argument("--wiki-root", type=Path, default=Path("/root/wiki-augmented-intelligence"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        fail("payload root must be an object")
    validate(payload)
    if args.check:
        print(json.dumps({"status": "valid", "payload": str(args.payload)}, sort_keys=True))
        return
    result = apply(payload, args.dashboard_root, args.calibration, args.wiki_root)
    print(json.dumps({"status": "updated", **result}, sort_keys=True))


if __name__ == "__main__":
    main()
