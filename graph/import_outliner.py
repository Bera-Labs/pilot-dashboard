"""Read-only Outliner → Source graph import. Never writes back to Outliner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from graph.store import GraphStore

KIND_MAP = {
    "project": "project",
    "task": "task",
    "milestone": "milestone",
    "braindump": "note",
    "template": "note",
    "quarter": "note",
}


def _parse_surface(dump: dict, key: str):
    v = dump.get(key)
    if isinstance(v, list) and v and isinstance(v[0], dict) and "text" in v[0]:
        try:
            return json.loads(v[0]["text"])
        except json.JSONDecodeError:
            return v
    return v


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_outliner(store: GraphStore, dump_path: Path) -> dict:
    raw_bytes = dump_path.read_bytes()
    fp = hashlib.sha256(raw_bytes).hexdigest()
    dump = json.loads(raw_bytes)
    nodes = _parse_surface(dump, "get_all_nodes") or {}
    if not isinstance(nodes, dict):
        raise TypeError("get_all_nodes must be an id→node map")
    habits = _parse_surface(dump, "get_habits") or {}
    notes = _parse_surface(dump, "get_notes") or []
    if isinstance(habits, dict):
        habit_list = list(habits.values())
    else:
        habit_list = list(habits)

    imported = []
    id_map = {}  # outliner id -> graph id
    for oid, n in nodes.items():
        otype = n.get("type")
        kind = KIND_MAP.get(otype, "note")
        title = (n.get("content") or "").strip() or f"untitled {kind}"
        props = dict(n.get("properties") or {})
        if kind == "task":
            props.setdefault("done_when", "operator marks complete")
            completed = props.get("completed")
            status = "done" if completed not in (None, "", "null") else "open"
        elif kind == "project":
            props.setdefault("win_condition", title)
            status = "active"
        else:
            status = "open"
        node = store.commit({
            "kind": kind,
            "title": title,
            "body": n.get("body") or "",
            "evidence_class": "observed",
            "status": status,
            "tags": list(n.get("tags") or []),
            "properties": props,
            "source": "import:outliner",
        }, actor="import")
        id_map[oid] = node["id"]
        imported.append(node["id"])

    # parent edges (second pass)
    for oid, n in nodes.items():
        parent = n.get("parent")
        if parent and parent in id_map and oid in id_map and parent != oid:
            store.link(id_map[oid], id_map[parent], rel="child_of", actor="import")

    for h in habit_list:
        hid = h.get("id")
        if hid in id_map:
            continue
        log = h.get("log") or []
        days = []
        if isinstance(log, dict):
            days = sorted(log.keys())
        elif isinstance(log, list):
            days = [str(x) for x in log]
        store.commit({
            "kind": "habit",
            "title": h.get("name") or "habit",
            "evidence_class": "observed",
            "status": "active",
            "properties": {"log": days, "autoCheck": h.get("autoCheck")},
            "source": "import:outliner",
        }, actor="import")

    for note in notes:
        if not isinstance(note, dict):
            continue
        store.commit({
            "kind": "journal",
            "title": (note.get("text") or "")[:80] or "note",
            "body": note.get("text") or "",
            "evidence_class": "observed",
            "properties": {
                "date": (note.get("createdAt") or "")[:10],
                "context": note.get("context"),
            },
            "source": "import:outliner",
        }, actor="import")

    report = {
        "source": str(dump_path),
        "fingerprint": fp,
        "imported_nodes": len(imported),
        "outliner_nodes": len(nodes),
        "snapshot": store.snapshot()["counts"],
    }
    (store.root / "imports").mkdir(exist_ok=True)
    (store.root / "imports" / f"{fp[:12]}.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default="/root/outliner_data.json")
    ap.add_argument("--graph", default=str(Path(__file__).resolve().parents[1] / "data" / "graph"))
    args = ap.parse_args()
    store = GraphStore(args.graph)
    print(json.dumps(import_outliner(store, Path(args.dump)), indent=2))
