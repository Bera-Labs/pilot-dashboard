#!/usr/bin/env python3
"""Build the Augmented Intelligence mixture-of-experts graph deterministically.

The source contract is structured data rather than inferred wiki links. The
resulting graph makes the reasoning chain explicit:
Outliner evidence -> model framing -> expert derivation -> integrated solution ->
decision -> action -> time-bound execution phase.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path("/root/pilot-dashboard")
SOURCE_FILE = ROOT / "data" / "augmented-intelligence.json"
OUT_FILE = ROOT / "data" / "augmented-graph.json"
SCHEMA_VERSION = "3.0.0"


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def require_list(mapping: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = mapping.get(key)
    if not isinstance(value, list):
        fail(f"{key} must be a list")
    if not all(isinstance(item, dict) for item in value):
        fail(f"{key} must contain objects")
    return cast(list[dict[str, Any]], value)


def index_unique(rows: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        node_id = row.get("id")
        if not isinstance(node_id, str) or not node_id:
            fail(f"{kind} row missing id")
        if node_id in result:
            fail(f"duplicate {kind} id: {node_id}")
        result[node_id] = row
    return result


def require_refs(owner: str, refs: list[str], known: set[str], kind: str) -> None:
    missing = sorted(set(refs) - known)
    if missing:
        fail(f"{owner} references unknown {kind}: {missing}")


def require_text(mapping: dict[str, Any], key: str, owner: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"{owner}.{key} must be a non-empty string")
    return value


def require_string_list(mapping: dict[str, Any], key: str, owner: str) -> list[str]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        fail(f"{owner}.{key} must be a non-empty list of strings")
    return cast(list[str], value)


def validate_life_strategy(
    strategy: Any,
    known_models: set[str],
    known_tasks: set[str],
) -> dict[str, Any]:
    if not isinstance(strategy, dict):
        fail("life_strategy must be an object")
    require_text(strategy, "title", "life_strategy")
    require_text(strategy, "timeframe", "life_strategy")

    position = strategy.get("position")
    if not isinstance(position, dict):
        fail("life_strategy.position must be an object")
    for key in ("headline", "summary", "momentum", "tension", "leverage", "confidence"):
        require_text(position, key, "life_strategy.position")
    require_string_list(position, "source_refs", "life_strategy.position")

    moves = require_list(strategy, "winning_moves")
    if not 1 <= len(moves) <= 3:
        fail("life_strategy.winning_moves must contain one to three moves")
    ranks: list[int] = []
    for move in moves:
        owner = f"life_strategy.winning_moves[{move.get('rank', '?')}]"
        rank = move.get("rank")
        if not isinstance(rank, int):
            fail(f"{owner}.rank must be an integer")
        ranks.append(rank)
        for key in ("title", "move", "why_now", "tradeoff", "timeframe", "win_condition"):
            require_text(move, key, owner)
        require_string_list(move, "unlocks", owner)
        task_ids = require_string_list(move, "task_ids", owner)
        require_refs(owner, task_ids, known_tasks, "tasks")
        require_string_list(move, "source_refs", owner)
        model_ids = require_string_list(move, "model_ids", owner)
        require_refs(owner, model_ids, known_models, "models")
    if sorted(ranks) != list(range(1, len(moves) + 1)):
        fail("life_strategy.winning_moves ranks must be contiguous from 1")

    insights = require_list(strategy, "hidden_leverage")
    if not 2 <= len(insights) <= 4:
        fail("life_strategy.hidden_leverage must contain two to four insights")
    for index, insight in enumerate(insights, 1):
        owner = f"life_strategy.hidden_leverage[{index}]"
        for key in ("title", "insight", "why_it_matters", "mechanism", "falsifier"):
            require_text(insight, key, owner)
        require_string_list(insight, "source_refs", owner)
        model_ids = require_string_list(insight, "model_ids", owner)
        require_refs(owner, model_ids, known_models, "models")

    timeline = require_list(strategy, "timeline")
    if len(timeline) != 3:
        fail("life_strategy.timeline must contain exactly three horizons")
    if len({require_text(row, "id", "life_strategy.timeline") for row in timeline}) != 3:
        fail("life_strategy.timeline ids must be unique")
    for row in timeline:
        owner = f"life_strategy.timeline[{row['id']}]"
        for key in ("label", "window", "objective", "win_condition", "pivot_if"):
            require_text(row, key, owner)
        require_string_list(row, "moves", owner)

    signals = require_list(strategy, "pivot_signals")
    if not 1 <= len(signals) <= 5:
        fail("life_strategy.pivot_signals must contain one to five signals")
    for index, signal in enumerate(signals, 1):
        owner = f"life_strategy.pivot_signals[{index}]"
        for key in ("signal", "meaning", "response"):
            require_text(signal, key, owner)
        require_string_list(signal, "source_refs", owner)

    provenance = strategy.get("reasoning_provenance")
    if not isinstance(provenance, dict):
        fail("life_strategy.reasoning_provenance must be an object")
    for key in ("summary", "wiki_fingerprint", "evidence_scope"):
        require_text(provenance, key, "life_strategy.reasoning_provenance")
    model_ids = require_string_list(provenance, "model_ids", "life_strategy.reasoning_provenance")
    require_refs("life_strategy.reasoning_provenance", model_ids, known_models, "models")
    return cast(dict[str, Any], strategy)


def graph_node(node_id: str, label: str, group: str, summary: str, **extra: Any) -> dict[str, Any]:
    node = {
        "id": node_id,
        "label": label,
        "group": group,
        "summary": summary,
        **extra,
    }
    if group in {"decision", "action", "phase"} and len(label) > 15:
        node["graph_label"] = label[:14].rstrip() + "…"
    return node


def main() -> None:
    source_text = SOURCE_FILE.read_text(encoding="utf-8")
    spec = json.loads(source_text)
    if spec.get("schema_version") != SCHEMA_VERSION:
        fail(f"expected source schema {SCHEMA_VERSION}")

    method = spec.get("method")
    blueprint = spec.get("blueprint")
    if not isinstance(method, dict) or method.get("name") != "Mixture of Experts":
        fail("method must be Mixture of Experts")
    if not isinstance(blueprint, dict):
        fail("blueprint must be an object")

    evidence = require_list(spec, "evidence")
    models = require_list(spec, "models")
    syntheses = require_list(spec, "syntheses")
    decisions = require_list(spec, "decisions")
    actions = require_list(spec, "actions")
    experts = require_list(method, "experts")
    phases = require_list(blueprint, "phases")

    evidence_by_id = index_unique(evidence, "evidence")
    model_by_id = index_unique(models, "model")
    expert_by_id = index_unique(experts, "expert")
    synthesis_by_id = index_unique(syntheses, "synthesis")
    decision_by_id = index_unique(decisions, "decision")
    action_by_id = index_unique(actions, "action")
    index_unique(phases, "phase")

    if len(actions) != 3 or len({row.get("task_id") for row in actions}) != 3:
        fail("exactly three unique current task-backed actions are required")

    current_task_ids = {require_text(row, "task_id", row["id"]) for row in actions}
    conditional_task_ids: set[str] = set()
    for phase in phases:
        for queued in phase.get("queue", []):
            if not isinstance(queued, dict):
                fail(f"{phase['id']}.queue must contain objects")
            conditional_task_ids.add(require_text(queued, "task_id", phase["id"]))
    contextual_task_ids = current_task_ids | conditional_task_ids
    life_strategy = validate_life_strategy(spec.get("life_strategy"), set(model_by_id), contextual_task_ids)

    nodes: list[dict[str, Any]] = []
    links: set[tuple[str, str, str]] = set()

    for row in evidence:
        nodes.append(
            graph_node(
                row["id"],
                row["label"],
                "evidence",
                row["summary"],
                evidence_class=row.get("kind", "unknown"),
                source_refs=row.get("source_refs", []),
            )
        )

    for row in models:
        evidence_ids = row.get("evidence_ids", [])
        require_refs(row["id"], evidence_ids, set(evidence_by_id), "evidence")
        nodes.append(
            graph_node(
                row["id"],
                row["label"],
                "model",
                row["role"],
                family=row.get("family"),
                source=row.get("source"),
                evidence_ids=evidence_ids,
            )
        )
        for evidence_id in evidence_ids:
            links.add((evidence_id, row["id"], "frames"))

    for row in experts:
        model_ids = row.get("model_ids", [])
        require_refs(row["id"], model_ids, set(model_by_id), "models")
        nodes.append(
            graph_node(
                row["id"],
                row["label"],
                "expert",
                row["mission"],
                model_ids=model_ids,
                evidence_ids=sorted(evidence_by_id),
                assumptions=row.get("assumptions", []),
                derivation=row.get("derivation", []),
                proposal=row.get("proposal"),
                risks=row.get("risks", []),
                falsified_by=row.get("falsified_by"),
            )
        )
        for model_id in model_ids:
            links.add((model_id, row["id"], "equips"))

    for row in syntheses:
        model_ids = row.get("model_ids", [])
        expert_ids = row.get("expert_ids", [])
        evidence_ids = row.get("evidence_ids", [])
        require_refs(row["id"], model_ids, set(model_by_id), "models")
        require_refs(row["id"], expert_ids, set(expert_by_id), "experts")
        require_refs(row["id"], evidence_ids, set(evidence_by_id), "evidence")
        if len(model_ids) < 2:
            fail(f"{row['id']} must use at least two models")
        applications = row.get("context_applications")
        if not isinstance(applications, list) or not applications:
            fail(f"{row['id']}.context_applications must be a non-empty list")
        seen_sources: set[tuple[str, str]] = set()
        for application in applications:
            if not isinstance(application, dict):
                fail(f"{row['id']}.context_applications must contain objects")
            source_type = require_text(application, "source_type", row["id"])
            source_id = require_text(application, "source_id", row["id"])
            require_text(application, "label", row["id"])
            require_text(application, "application", row["id"])
            require_text(application, "decision_implication", row["id"])
            source_refs = application.get("source_refs")
            if not isinstance(source_refs, list) or not source_refs or not all(isinstance(ref, str) and ref for ref in source_refs):
                fail(f"{row['id']}.context_applications source_refs must contain non-empty strings")
            if source_type == "model" and source_id not in model_ids:
                fail(f"{row['id']} context model is not used by the synthesis: {source_id}")
            if source_type == "expert" and source_id not in expert_ids:
                fail(f"{row['id']} context expert is not used by the synthesis: {source_id}")
            if source_type not in {"model", "expert"}:
                fail(f"{row['id']} context source_type must be model or expert")
            source_key = (source_type, source_id)
            if source_key in seen_sources:
                fail(f"{row['id']} duplicates context source {source_type}:{source_id}")
            seen_sources.add(source_key)
        context_decision = row.get("context_decision")
        if not isinstance(context_decision, dict):
            fail(f"{row['id']}.context_decision must be an object")
        for key in ("choice", "why", "alternative", "review"):
            require_text(context_decision, key, row["id"])
        context_actions = row.get("context_actions")
        if not isinstance(context_actions, list) or not context_actions:
            fail(f"{row['id']}.context_actions must be a non-empty list")
        for action in context_actions:
            if not isinstance(action, dict):
                fail(f"{row['id']}.context_actions must contain objects")
            task_id = require_text(action, "task_id", row["id"])
            state = require_text(action, "state", row["id"])
            for key in ("label", "move", "done_when"):
                require_text(action, key, row["id"])
            if task_id not in contextual_task_ids:
                fail(f"{row['id']} context action references task outside the blueprint: {task_id}")
            if state == "current" and task_id not in current_task_ids:
                fail(f"{row['id']} current context action is not in the controller: {task_id}")
            if state == "conditional" and task_id not in conditional_task_ids:
                fail(f"{row['id']} conditional context action is not gated: {task_id}")
            if state not in {"current", "conditional"}:
                fail(f"{row['id']} context action state must be current or conditional")
        nodes.append(
            graph_node(
                row["id"],
                row["title"],
                "solution",
                row["solution"].split("\n", 1)[0].lstrip("# "),
                status=row.get("status"),
                confidence=row.get("confidence"),
                is_current=bool(row.get("is_current")),
            )
        )
        for expert_id in expert_ids:
            links.add((expert_id, row["id"], "derives"))

    for row in decisions:
        solution_ids = row.get("solution_ids", [])
        require_refs(row["id"], solution_ids, set(synthesis_by_id), "solutions")
        nodes.append(
            graph_node(
                row["id"],
                row["label"],
                "decision",
                row["rationale"],
                choice=row.get("choice"),
                tradeoff=row.get("tradeoff"),
                review=row.get("review"),
            )
        )
        for solution_id in solution_ids:
            links.add((solution_id, row["id"], "selects"))

    for position, row in enumerate(actions, 1):
        decision_ids = row.get("decision_ids", [])
        require_refs(row["id"], decision_ids, set(decision_by_id), "decisions")
        nodes.append(
            graph_node(
                row["id"],
                row["label"],
                "action",
                row["done_when"],
                task_id=row.get("task_id"),
                timebox=row.get("timebox"),
                status=row.get("status"),
                order=position,
                queue_state="active-controller",
                decision_ids=decision_ids,
            )
        )
        for decision_id in decision_ids:
            links.add((decision_id, row["id"], "executes"))

    queue_node_ids: set[str] = set()
    for row in phases:
        decision_ids = row.get("decision_ids", [])
        action_ids = row.get("action_ids", [])
        require_refs(row["id"], decision_ids, set(decision_by_id), "decisions")
        require_refs(row["id"], action_ids, set(action_by_id), "actions")
        nodes.append(
            graph_node(
                row["id"],
                row["title"],
                "phase",
                row["decision"],
                order=row.get("order"),
                horizon=row.get("horizon"),
                window=row.get("window"),
                status=row.get("status"),
                gate=row.get("gate"),
            )
        )
        for decision_id in decision_ids:
            links.add((decision_id, row["id"], "governs"))
        for action_id in action_ids:
            links.add((action_id, row["id"], "scheduled_in"))
        for position, queued in enumerate(row.get("queue", []), 1):
            task_id = queued.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                fail(f"{row['id']} queue item missing task_id")
            queue_id = f"queue-{task_id}"
            if queue_id not in queue_node_ids:
                nodes.append(
                    graph_node(
                        queue_id,
                        queued["label"],
                        "action",
                        f"Conditional queue item; depends on {queued['depends_on']}.",
                        task_id=task_id,
                        status="conditional",
                        queue_state="future-gated",
                        queue_position=position,
                        decision_ids=decision_ids,
                    )
                )
                queue_node_ids.add(queue_id)
            for decision_id in decision_ids:
                links.add((decision_id, queue_id, "executes"))
            links.add((queue_id, row["id"], "scheduled_in"))

    labels = {model_id: row["label"] for model_id, row in model_by_id.items()}
    synthesis_cards = []
    for row in syntheses:
        synthesis_cards.append(
            {
                "id": row["id"],
                "title": row["title"],
                "model": " · ".join(labels[model_id] for model_id in row["model_ids"]),
                "problem": row["problem"],
                "solution": row["solution"],
                "context_applications": row["context_applications"],
                "context_decision": row["context_decision"],
                "context_actions": row["context_actions"],
                "disagreement": row.get("disagreement"),
                "status": row.get("status"),
                "confidence": row.get("confidence"),
                "is_current": bool(row.get("is_current")),
                "expert_ids": row.get("expert_ids", []),
                "evidence_ids": row.get("evidence_ids", []),
            }
        )
    synthesis_cards.sort(key=lambda row: (not row["is_current"], row["title"].casefold()))

    node_ids = [node["id"] for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        duplicates = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
        fail(f"duplicate graph node ids: {duplicates}")

    links_rows = [
        {"source": source, "target": target, "relation": relation}
        for source, target, relation in sorted(links)
    ]
    fingerprint = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    payload = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": spec["generated_at"],
            "source_fingerprint": fingerprint,
            "source": str(SOURCE_FILE),
            "method": method["name"],
            "node_count": len(nodes),
            "link_count": len(links_rows),
            "synthesis_count": len(synthesis_cards),
            "warnings": [],
        },
        "method": method,
        "nodes": sorted(nodes, key=lambda row: (row["group"], row["label"].casefold(), row["id"])),
        "links": links_rows,
        "syntheses": synthesis_cards,
        "decisions": decisions,
        "actions": actions,
        "blueprint": blueprint,
        "life_strategy": life_strategy,
    }

    new_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    old_text = OUT_FILE.read_text(encoding="utf-8") if OUT_FILE.exists() else ""
    OUT_FILE.write_text(new_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "changed" if old_text != new_text else "unchanged",
                "output": str(OUT_FILE),
                "nodes": len(nodes),
                "links": len(links_rows),
                "syntheses": len(synthesis_cards),
                "phases": len(phases),
                "warnings": 0,
                "fingerprint": fingerprint[:12],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
