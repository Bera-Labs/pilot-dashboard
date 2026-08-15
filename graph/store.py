"""SQLite graph ledger + JSON projection."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from graph.packet import EDGE_RELS, validate_packet

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  op TEXT NOT NULL,
  actor TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '',
  evidence_class TEXT NOT NULL,
  status TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '[]',
  properties TEXT NOT NULL DEFAULT '{}',
  source TEXT NOT NULL,
  created_at TEXT NOT NULL,
  modified_at TEXT NOT NULL,
  rev INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS edges (
  id TEXT PRIMARY KEY,
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  rel TEXT NOT NULL,
  evidence_class TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  observed_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def can_write(token_env: str | None, header: str | None, client_host: str | None) -> bool:
    if not token_env:
        return False
    if header and header == token_env:
        return True
    return client_host in ("127.0.0.1", "::1")


class GraphStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "source.db"
        self.events_path = self.root / "events.jsonl"
        self.current_path = self.root / "current.json"
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def commit(self, raw: dict, parent_id: str | None = None, rel: str = "child_of", actor: str = "hermes") -> dict:
        packet = validate_packet(raw)
        ts = now_iso()
        nid = packet.get("id") or new_id("n")
        with self._connect() as conn:
            existing = conn.execute("SELECT rev, created_at FROM nodes WHERE id=?", (nid,)).fetchone()
            if existing:
                rev = existing["rev"] + 1
                created = existing["created_at"]
                conn.execute(
                    """UPDATE nodes SET kind=?, title=?, body=?, evidence_class=?, status=?,
                       tags=?, properties=?, source=?, modified_at=?, rev=? WHERE id=?""",
                    (
                        packet["kind"], packet["title"], packet["body"], packet["evidence_class"],
                        packet["status"], json.dumps(packet["tags"]), json.dumps(packet["properties"]),
                        packet["source"], ts, rev, nid,
                    ),
                )
                op = "upsert_node"
            else:
                rev = 1
                created = ts
                conn.execute(
                    """INSERT INTO nodes (id, kind, title, body, evidence_class, status, tags,
                       properties, source, created_at, modified_at, rev)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        nid, packet["kind"], packet["title"], packet["body"], packet["evidence_class"],
                        packet["status"], json.dumps(packet["tags"]), json.dumps(packet["properties"]),
                        packet["source"], created, ts, rev,
                    ),
                )
                op = "insert_node"
            edge = None
            if parent_id:
                if rel not in EDGE_RELS:
                    raise ValueError(f"bad rel {rel}")
                eid = new_id("e")
                edge = {
                    "id": eid,
                    "from": nid,
                    "to": parent_id,
                    "rel": rel,
                    "evidence_class": packet["evidence_class"],
                    "valid_from": ts,
                    "valid_to": None,
                    "observed_at": ts,
                    "recorded_at": ts,
                }
                conn.execute(
                    """INSERT INTO edges (id, src, dst, rel, evidence_class, valid_from, valid_to, observed_at, recorded_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (eid, nid, parent_id, rel, packet["evidence_class"], ts, None, ts, ts),
                )
            event = {"id": new_id("ev"), "ts": ts, "op": op, "actor": actor, "node_id": nid, "edge": edge}
            conn.execute(
                "INSERT INTO events (id, ts, op, actor, payload) VALUES (?,?,?,?,?)",
                (event["id"], ts, op, actor, json.dumps(event, sort_keys=True)),
            )
            conn.commit()
        self._append_event(event)
        node = {
            "id": nid,
            **{k: packet[k] for k in ("kind", "title", "body", "evidence_class", "status", "tags", "properties", "source")},
            "created_at": created,
            "modified_at": ts,
            "rev": rev,
        }
        self.materialize()
        return node

    def link(self, src: str, dst: str, rel: str = "child_of", evidence_class: str = "observed", actor: str = "hermes") -> dict:
        if rel not in EDGE_RELS:
            raise ValueError(f"bad rel {rel}")
        ts = now_iso()
        eid = new_id("e")
        edge = {
            "id": eid, "from": src, "to": dst, "rel": rel,
            "evidence_class": evidence_class,
            "valid_from": ts, "valid_to": None,
            "observed_at": ts, "recorded_at": ts,
        }
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO edges (id, src, dst, rel, evidence_class, valid_from, valid_to, observed_at, recorded_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (eid, src, dst, rel, evidence_class, ts, None, ts, ts),
            )
            event = {"id": new_id("ev"), "ts": ts, "op": "add_edge", "actor": actor, "edge": edge}
            conn.execute(
                "INSERT INTO events (id, ts, op, actor, payload) VALUES (?,?,?,?,?)",
                (event["id"], ts, "add_edge", actor, json.dumps(event, sort_keys=True)),
            )
            conn.commit()
        self._append_event(event)
        self.materialize()
        return edge

    def set_status(self, nid: str, status: str, actor: str = "source-ui") -> dict:
        ts = now_iso()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id=?", (nid,)).fetchone()
            if not row:
                raise KeyError(nid)
            conn.execute("UPDATE nodes SET status=?, modified_at=?, rev=rev+1 WHERE id=?", (status, ts, nid))
            if status in ("done", "retired"):
                conn.execute("UPDATE edges SET valid_to=? WHERE src=? AND valid_to IS NULL", (ts, nid))
            event = {"id": new_id("ev"), "ts": ts, "op": "set_status", "actor": actor, "node_id": nid, "status": status}
            conn.execute(
                "INSERT INTO events (id, ts, op, actor, payload) VALUES (?,?,?,?,?)",
                (event["id"], ts, "set_status", actor, json.dumps(event, sort_keys=True)),
            )
            conn.commit()
        self._append_event(event)
        self.materialize()
        return self.snapshot()

    def habit_check(self, nid: str, day: str, actor: str = "source-ui") -> dict:
        ts = now_iso()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id=?", (nid,)).fetchone()
            if not row:
                raise KeyError(nid)
            props = json.loads(row["properties"] or "{}")
            log = list(props.get("log") or [])
            if day in log:
                log.remove(day)
            else:
                log.append(day)
                log.sort()
            props["log"] = log
            conn.execute(
                "UPDATE nodes SET properties=?, modified_at=?, rev=rev+1 WHERE id=?",
                (json.dumps(props), ts, nid),
            )
            event = {"id": new_id("ev"), "ts": ts, "op": "habit_check", "actor": actor, "node_id": nid, "day": day}
            conn.execute(
                "INSERT INTO events (id, ts, op, actor, payload) VALUES (?,?,?,?,?)",
                (event["id"], ts, "habit_check", actor, json.dumps(event, sort_keys=True)),
            )
            conn.commit()
        self._append_event(event)
        self.materialize()
        return self.snapshot()

    def _append_event(self, event: dict) -> None:
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

    def snapshot(self) -> dict:
        with self._connect() as conn:
            nodes = [dict(r) for r in conn.execute(
                "SELECT * FROM nodes ORDER BY kind, title, id"
            )]
            edges = [dict(r) for r in conn.execute(
                "SELECT * FROM edges ORDER BY rel, src, dst, id"
            )]
        out_nodes = []
        for n in nodes:
            out_nodes.append({
                "id": n["id"],
                "kind": n["kind"],
                "title": n["title"],
                "body": n["body"],
                "evidence_class": n["evidence_class"],
                "status": n["status"],
                "tags": json.loads(n["tags"]),
                "properties": json.loads(n["properties"]),
                "source": n["source"],
                "created_at": n["created_at"],
                "modified_at": n["modified_at"],
                "rev": n["rev"],
            })
        out_edges = []
        for e in edges:
            out_edges.append({
                "id": e["id"],
                "from": e["src"],
                "to": e["dst"],
                "rel": e["rel"],
                "evidence_class": e["evidence_class"],
                "valid_from": e["valid_from"],
                "valid_to": e["valid_to"],
                "observed_at": e["observed_at"],
                "recorded_at": e["recorded_at"],
            })
        counts: dict[str, int] = {}
        for n in out_nodes:
            counts[n["kind"]] = counts.get(n["kind"], 0) + 1
        return {
            "schema": "source-graph/1",
            "generated_at": now_iso(),
            "counts": counts,
            "nodes": out_nodes,
            "edges": out_edges,
        }

    def materialize(self) -> dict:
        snap = self.snapshot()
        # drop generated_at for byte-stable second pass of node/edge content
        stable = {
            "schema": snap["schema"],
            "counts": snap["counts"],
            "nodes": snap["nodes"],
            "edges": snap["edges"],
        }
        # include generated_at but keep nodes/edges order stable
        payload = {"schema": snap["schema"], "generated_at": snap["generated_at"], **stable}
        # Wait - including generated_at makes second materialize differ.
        # Tests compare full current.json. Use snapshot without clock for equality:
        payload = stable
        tmp = self.current_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.current_path)
        return payload


def default_store() -> GraphStore:
    return GraphStore(Path(__file__).resolve().parents[1] / "data" / "graph")
