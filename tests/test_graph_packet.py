"""The Source — packet + ledger contract."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graph.packet import PacketError, compile_text, validate_packet
from graph.store import GraphStore


class TestValidatePacket(unittest.TestCase):
    def test_rejects_missing_kind(self):
        with self.assertRaises(PacketError):
            validate_packet({"title": "x", "evidence_class": "observed"})

    def test_rejects_bad_evidence_class(self):
        with self.assertRaises(PacketError):
            validate_packet({"kind": "task", "title": "x", "evidence_class": "vibes"})

    def test_task_requires_done_when(self):
        with self.assertRaises(PacketError):
            validate_packet({"kind": "task", "title": "check CD", "evidence_class": "observed"})

    def test_valid_task_passes(self):
        p = validate_packet({
            "kind": "task",
            "title": "Line-by-line CD check",
            "evidence_class": "observed",
            "properties": {"done_when": "figures verified or named blocker"},
        })
        self.assertEqual(p["kind"], "task")
        self.assertEqual(p["status"], "open")


class TestCompileText(unittest.TestCase):
    def test_project_prefix(self):
        p = compile_text("project: Home base transition win when closed and moved")
        self.assertEqual(p["kind"], "project")

    def test_done_when_implies_task(self):
        p = compile_text("CD check done when written repair confirm")
        self.assertEqual(p["kind"], "task")
        self.assertIn("done_when", p["properties"])

    def test_journal_prefix(self):
        p = compile_text("journal: felt fog after the call")
        self.assertEqual(p["kind"], "journal")


class TestGraphCommit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = GraphStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_commit_then_read_back(self):
        node = self.store.commit({
            "kind": "project",
            "title": "Home base",
            "evidence_class": "observed",
            "properties": {"win_condition": "closed and moved"},
        })
        snap = self.store.snapshot()
        self.assertEqual(len(snap["nodes"]), 1)
        self.assertEqual(snap["nodes"][0]["title"], "Home base")
        self.assertTrue((self.root / "current.json").exists())
        current = json.loads((self.root / "current.json").read_text())
        self.assertEqual(current["nodes"][0]["id"], node["id"])

    def test_child_edge_is_bitemporal(self):
        proj = self.store.commit({
            "kind": "project",
            "title": "Housing",
            "evidence_class": "observed",
            "properties": {"win_condition": "close"},
        })
        task = self.store.commit({
            "kind": "task",
            "title": "Verify CD",
            "evidence_class": "observed",
            "properties": {"done_when": "line-by-line done"},
        }, parent_id=proj["id"], rel="child_of")
        snap = self.store.snapshot()
        self.assertEqual(len(snap["edges"]), 1)
        e = snap["edges"][0]
        self.assertEqual(e["from"], task["id"])
        self.assertEqual(e["to"], proj["id"])
        self.assertEqual(e["rel"], "child_of")
        for k in ("valid_from", "valid_to", "observed_at", "recorded_at"):
            self.assertIn(k, e)
        self.assertIsNone(e["valid_to"])

    def test_second_materialize_is_deterministic(self):
        self.store.commit({"kind": "note", "title": "hello", "evidence_class": "observed"})
        a = (self.root / "current.json").read_text()
        self.store.materialize()
        b = (self.root / "current.json").read_text()
        self.assertEqual(a, b)


class TestWriteGate(unittest.TestCase):
    def test_no_token_means_not_writable(self):
        from graph.store import can_write
        self.assertFalse(can_write(token_env=None, header=None, client_host="1.2.3.4"))

    def test_loopback_ok_when_token_set(self):
        from graph.store import can_write
        self.assertTrue(can_write(token_env="secret", header=None, client_host="127.0.0.1"))

    def test_remote_needs_header(self):
        from graph.store import can_write
        self.assertFalse(can_write(token_env="secret", header=None, client_host="8.8.8.8"))
        self.assertTrue(can_write(token_env="secret", header="secret", client_host="8.8.8.8"))


if __name__ == "__main__":
    unittest.main()
