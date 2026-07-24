#!/usr/bin/env python3
"""Safely deploy Augmented Intelligence data artifacts as one Git commit."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED = {
    "data/state.json",
    "data/growth.json",
    "data/augmented-graph.json",
}


def run(args: list[str], root: Path, check: bool = True) -> str:
    result = subprocess.run(args, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}")
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/root/pilot-dashboard"))
    parser.add_argument("--message", default="update augmented intelligence state")
    parser.add_argument("--live-api", default="https://pilot-dashboard-seven.vercel.app/api/augmented-graph")
    parser.add_argument("--skip-live-verify", action="store_true")
    args = parser.parse_args()
    root = args.root

    remote = run(["git", "remote", "get-url", "origin"], root)
    parsed = urlsplit(remote)
    if parsed.username or parsed.password:
        raise RuntimeError("origin URL contains embedded credentials; configure a credential helper first")

    branch = run(["git", "branch", "--show-current"], root)
    if branch != "main":
        raise RuntimeError(f"expected branch main, found {branch}")

    run(["git", "fetch", "origin", "main"], root)
    head = run(["git", "rev-parse", "HEAD"], root)
    remote_head = run(["git", "rev-parse", "origin/main"], root)
    if head != remote_head:
        raise RuntimeError("local HEAD differs from origin/main; refusing to push unknown commits")

    run(["python3", "scripts/generate-augmented-graph.py"], root)
    graph = json.loads((root / "data" / "augmented-graph.json").read_text())
    if graph.get("meta", {}).get("schema_version") != "2.0.0":
        raise RuntimeError("augmented graph schema validation failed")

    status_result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    dirty = set()
    for line in status_result.stdout.splitlines():
        if not line:
            continue
        path = line[3:].split(" -> ")[-1]
        dirty.add(path)
    unexpected = sorted(dirty - ALLOWED)
    if unexpected:
        raise RuntimeError(f"unexpected dirty files; refusing deploy: {unexpected}")

    changed = sorted(dirty & ALLOWED)
    if not changed:
        print(json.dumps({"status": "unchanged", "head": head}, sort_keys=True))
        return

    run(["git", "add", "--", *changed], root)
    staged = run(["git", "diff", "--cached", "--name-only"], root).splitlines()
    if set(staged) - ALLOWED:
        raise RuntimeError(f"staged files outside allowlist: {staged}")
    run(["git", "commit", "-m", args.message], root)
    run(["git", "push", "origin", "main"], root)
    new_head = run(["git", "rev-parse", "HEAD"], root)
    run(["git", "fetch", "origin", "main"], root)
    if new_head != run(["git", "rev-parse", "origin/main"], root):
        raise RuntimeError("remote commit verification failed")

    live_verified = False
    if not args.skip_live_verify:
        fingerprint = graph["meta"]["source_fingerprint"]
        for _ in range(6):
            try:
                with urllib.request.urlopen(args.live_api, timeout=15) as response:
                    live = json.load(response)
                if live.get("meta", {}).get("source_fingerprint") == fingerprint:
                    live_verified = True
                    break
            except Exception:
                pass
            time.sleep(10)
        if not live_verified:
            raise RuntimeError("push succeeded but live Vercel fingerprint did not update within 60 seconds")

    print(json.dumps({"status": "deployed", "commit": new_head, "files": changed, "live_verified": live_verified}, sort_keys=True))


if __name__ == "__main__":
    main()
