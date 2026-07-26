#!/usr/bin/env python3
"""Validate and atomically apply one Augmented Intelligence analysis payload.

The model produces one analysis JSON payload and one structured intelligence
specification. This script validates both, then updates the coupled dashboard
state, growth history, calibration, canonical synthesis, and MoE graph source.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import NoReturn


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def require(mapping: dict, key: str, expected_type):
    if key not in mapping:
        fail(f"missing required field: {key}")
    value = mapping[key]
    if not isinstance(value, expected_type):
        fail(f"{key} must be {expected_type}, got {type(value).__name__}")
    return value


def require_object_rows(rows: list, name: str) -> list[dict]:
    objects: list[dict] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            fail(f"{name}[{index}] must be an object")
        row_id = require(row, "id", str)
        if not row_id:
            fail(f"{name}[{index}].id cannot be empty")
        if row_id in seen:
            fail(f"duplicate {name} id: {row_id}")
        seen.add(row_id)
        objects.append(row)
    return objects


def require_references(owner: str, values: list, known: set[str], kind: str) -> None:
    if not all(isinstance(value, str) and value for value in values):
        fail(f"{owner} {kind} references must be non-empty strings")
    missing = sorted(set(values) - known)
    if missing:
        fail(f"{owner} references unknown {kind}: {missing}")


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


def validate_intelligence_spec(spec: dict, payload: dict) -> None:
    if require(spec, "schema_version", str) != "3.0.0":
        fail("intelligence spec schema_version must be 3.0.0")
    generated_at = require(spec, "generated_at", str)
    try:
        generated_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        run_dt = datetime.fromisoformat(payload["last_run"].replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"intelligence spec generated_at must be ISO-8601: {exc}")
    if generated_dt != run_dt:
        fail("intelligence spec generated_at must match analysis last_run")

    method = require(spec, "method", dict)
    if require(method, "name", str) != "Mixture of Experts":
        fail("intelligence spec method must be Mixture of Experts")
    experts = require_object_rows(require(method, "experts", list), "experts")
    models = require_object_rows(require(spec, "models", list), "models")
    evidence = require_object_rows(require(spec, "evidence", list), "evidence")
    syntheses = require_object_rows(require(spec, "syntheses", list), "syntheses")
    decisions = require_object_rows(require(spec, "decisions", list), "decisions")
    actions = require_object_rows(require(spec, "actions", list), "actions")
    blueprint = require(spec, "blueprint", dict)
    phases = require_object_rows(require(blueprint, "phases", list), "phases")
    if not experts or not models or not evidence or not syntheses or not decisions:
        fail("intelligence spec evidence, models, experts, syntheses, and decisions cannot be empty")
    if len(actions) != 3:
        fail("intelligence spec must contain exactly three current actions")
    if not phases:
        fail("intelligence blueprint must contain at least one phase")

    model_ids = {row["id"] for row in models}
    evidence_ids = {row["id"] for row in evidence}
    expert_ids = {row["id"] for row in experts}
    synthesis_ids = {row["id"] for row in syntheses}
    decision_ids = {row["id"] for row in decisions}
    action_ids = {row["id"] for row in actions}
    current_task_ids = {row.get("task_id") for row in actions}
    conditional_task_ids: set[str] = set()
    for phase in phases:
        queue = phase.get("queue")
        if not isinstance(queue, list):
            fail(f"{phase['id']}.queue must be a list")
        for index, queued in enumerate(queue):
            if not isinstance(queued, dict):
                fail(f"{phase['id']}.queue[{index}] must be an object")
            task_id = queued.get("task_id")
            if isinstance(task_id, str) and task_id:
                conditional_task_ids.add(task_id)
    contextual_task_ids = current_task_ids | conditional_task_ids

    for row in models:
        for key in ("label", "role", "source"):
            require(row, key, str)
        require_references(row["id"], require(row, "evidence_ids", list), evidence_ids, "evidence")
    for row in evidence:
        for key in ("label", "summary"):
            require(row, key, str)
    for row in experts:
        for key in ("label", "mission", "proposal", "falsified_by"):
            require(row, key, str)
        for key in ("assumptions", "derivation", "risks"):
            values = require(row, key, list)
            if not all(isinstance(value, str) and value for value in values):
                fail(f"{row['id']}.{key} must contain non-empty strings")
        refs = require(row, "model_ids", list)
        require_references(row["id"], refs, model_ids, "models")
    for row in syntheses:
        for key in ("title", "problem", "solution"):
            require(row, key, str)
        model_refs = require(row, "model_ids", list)
        if len(model_refs) < 2:
            fail(f"{row['id']} must use at least two models")
        require_references(row["id"], model_refs, model_ids, "models")
        expert_refs = require(row, "expert_ids", list)
        require_references(row["id"], expert_refs, expert_ids, "experts")
        require_references(row["id"], require(row, "evidence_ids", list), evidence_ids, "evidence")

        applications = require(row, "context_applications", list)
        if not applications:
            fail(f"{row['id']}.context_applications cannot be empty")
        seen_sources: set[tuple[str, str]] = set()
        for index, application in enumerate(applications):
            if not isinstance(application, dict):
                fail(f"{row['id']}.context_applications[{index}] must be an object")
            for key in ("source_type", "source_id", "label", "application", "decision_implication"):
                require(application, key, str)
            source_type = application["source_type"]
            source_id = application["source_id"]
            if source_type == "model":
                if source_id not in model_refs:
                    fail(f"{row['id']} context model {source_id!r} is not used by the synthesis")
            elif source_type == "expert":
                if source_id not in expert_refs:
                    fail(f"{row['id']} context expert {source_id!r} is not used by the synthesis")
            else:
                fail(f"{row['id']} context source_type must be model or expert")
            source_key = (source_type, source_id)
            if source_key in seen_sources:
                fail(f"{row['id']} duplicates context source {source_type}:{source_id}")
            seen_sources.add(source_key)
            source_refs = require(application, "source_refs", list)
            if not source_refs or not all(isinstance(ref, str) and ref for ref in source_refs):
                fail(f"{row['id']} context source_refs must contain non-empty strings")

        context_decision = require(row, "context_decision", dict)
        for key in ("choice", "why", "alternative", "review"):
            require(context_decision, key, str)
        context_actions = require(row, "context_actions", list)
        if not context_actions:
            fail(f"{row['id']}.context_actions cannot be empty")
        for index, action in enumerate(context_actions):
            if not isinstance(action, dict):
                fail(f"{row['id']}.context_actions[{index}] must be an object")
            for key in ("task_id", "label", "state", "move", "done_when"):
                require(action, key, str)
            if action["task_id"] not in contextual_task_ids:
                fail(f"{row['id']} context action references task outside current/conditional blueprint: {action['task_id']}")
            if action["state"] not in {"current", "conditional"}:
                fail(f"{row['id']} context action state must be current or conditional")
            if action["state"] == "current" and action["task_id"] not in current_task_ids:
                fail(f"{row['id']} current context action must reference a current controller task")
            if action["state"] == "conditional" and action["task_id"] not in conditional_task_ids:
                fail(f"{row['id']} conditional context action must reference a gated queue task")
    for row in decisions:
        for key in ("label", "rationale"):
            require(row, key, str)
        require_references(row["id"], require(row, "solution_ids", list), synthesis_ids, "solutions")
    for row in actions:
        for key in ("label", "task_id", "timebox", "first_step", "done_when"):
            require(row, key, str)
        require_references(row["id"], require(row, "decision_ids", list), decision_ids, "decisions")
    for row in phases:
        require(row, "order", int)
        for key in ("horizon", "title", "status", "decision", "gate"):
            require(row, key, str)
        require_references(row["id"], require(row, "decision_ids", list), decision_ids, "decisions")
        require_references(row["id"], require(row, "action_ids", list), action_ids, "actions")
        queue = require(row, "queue", list)
        for index, queued in enumerate(queue):
            if not isinstance(queued, dict):
                fail(f"{row['id']}.queue[{index}] must be an object")
            for key in ("task_id", "label", "depends_on"):
                require(queued, key, str)

    spec_task_ids = {item["task_id"] for item in actions}
    payload_task_ids = {item["task_id"] for item in payload["top_actions"]}
    if len(spec_task_ids) != 3 or spec_task_ids != payload_task_ids:
        fail("intelligence spec actions must match three unique analysis top_actions task IDs")



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


def canonical_markdown(payload: dict, spec: dict) -> str:
    actions = "\n".join(
        f"{i}. **{a['action']}** (`{a['task_id']}`) — {a['time']}. "
        f"First: {a['first_step']} Done when: {a['done_when']} Fallback: {a['fallback']}"
        for i, a in enumerate(payload["top_actions"], 1)
    )
    forecast = payload["forecast"]
    model_names = ", ".join(model["label"] for model in spec["models"])
    expert_names = ", ".join(expert["label"] for expert in spec["method"]["experts"])
    blueprint = spec["blueprint"]
    phases = "\n".join(
        f"{phase['order']}. **{phase['horizon']} — {phase['title']}** ({phase['status']}): "
        f"{phase['decision']} Gate: {phase['gate']}"
        for phase in blueprint["phases"]
    )
    return f'''---
canonical: true
status: current
confidence: {payload["confidence"]:.2f}
evidence: current-outliner-and-lifeos
updated_at: {payload["last_run"]}
---
# Current Augmented Intelligence

**Method:** Mixture of Experts
**Experts:** {expert_names}
**Models:** {model_names}
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

## Decision-to-Execution Blueprint
**Timeframe:** {blueprint["timeframe"]}

{phases}

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


def apply(payload: dict, spec: dict, dashboard_root: Path, calibration_file: Path, wiki_root: Path) -> dict:
    state_file = dashboard_root / "data" / "state.json"
    growth_file = dashboard_root / "data" / "growth.json"
    intelligence_file = dashboard_root / "data" / "augmented-intelligence.json"
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
    metrics = calibration.setdefault("metrics", {})
    # Formal prediction rows may be incomplete; preserve the attributable historical run counter.
    prior_total_runs = metrics.get("total_runs", len(predictions))
    if isinstance(prior_total_runs, bool) or not isinstance(prior_total_runs, int) or prior_total_runs < 0:
        fail("calibration metrics.total_runs must be a non-negative integer")
    is_new_calibration_run = not any(entry.get("date") == payload["last_run"] for entry in predictions)
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
    metrics["last_review"] = payload["last_run"]
    metrics["total_runs"] = max(
        prior_total_runs + (1 if is_new_calibration_run else 0),
        len(calibration["predictions"]),
    )

    atomic_write(state_file, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    atomic_write(growth_file, json.dumps(growth, indent=2, ensure_ascii=False) + "\n")
    atomic_write(calibration_file, json.dumps(calibration, indent=2, ensure_ascii=False) + "\n")
    atomic_write(intelligence_file, json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    atomic_write(canonical_file, canonical_markdown(payload, spec))

    return {
        "state": str(state_file),
        "growth": str(growth_file),
        "calibration": str(calibration_file),
        "intelligence_spec": str(intelligence_file),
        "canonical": str(canonical_file),
        "run_date": run_date,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    parser.add_argument("--intelligence-spec", type=Path, required=True)
    parser.add_argument("--dashboard-root", type=Path, default=Path("/root/pilot-dashboard"))
    parser.add_argument("--calibration", type=Path, default=Path("/root/.hermes/skills/stem-stack/nightly-momentum-engine/calibration.json"))
    parser.add_argument("--wiki-root", type=Path, default=Path("/root/wiki-augmented-intelligence"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    spec = json.loads(args.intelligence_spec.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        fail("payload root must be an object")
    if not isinstance(spec, dict):
        fail("intelligence spec root must be an object")
    validate(payload)
    validate_intelligence_spec(spec, payload)
    if args.check:
        print(json.dumps({"status": "valid", "payload": str(args.payload), "intelligence_spec": str(args.intelligence_spec)}, sort_keys=True))
        return
    result = apply(payload, spec, args.dashboard_root, args.calibration, args.wiki_root)
    print(json.dumps({"status": "updated", **result}, sort_keys=True))


if __name__ == "__main__":
    main()
