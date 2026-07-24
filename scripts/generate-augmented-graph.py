#!/usr/bin/env python3
"""Build the Augmented Intelligence graph deterministically.

Canonicalizes wiki IDs, preserves display labels, records provenance/freshness,
and emits warnings instead of silently creating duplicate concept nodes.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

WIKI_DIR = Path("/root/wiki-augmented-intelligence")
OUT_FILE = Path("/root/pilot-dashboard/data/augmented-graph.json")
SCHEMA_VERSION = "2.0.0"


def canonical_label(value: str) -> str:
    value = value.replace("_", " ")
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", canonical_label(value)).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "untitled"


def extract_section(content: str, names: list[str]) -> str:
    for name in names:
        match = re.search(
            rf"^##\s+{name}\s*$\n(.*?)(?=^##\s+|\Z)",
            content,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
    return ""


def extract_frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in content[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"\'')
    return result


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")


paths = sorted(
    [Path(p) for p in glob.glob(str(WIKI_DIR / "concepts" / "*.md"))]
    + [Path(p) for p in glob.glob(str(WIKI_DIR / "connections" / "*.md"))],
    key=lambda p: str(p).casefold(),
)

if not paths:
    raise SystemExit(f"No wiki files found under {WIKI_DIR}")

nodes_by_id: dict[str, dict] = {}
links: set[tuple[str, str]] = set()
syntheses: list[dict] = []
warnings: list[str] = []
known_labels: dict[str, str] = {}

# Register authored files first so all wikilinks resolve to canonical authored nodes.
for path in paths:
    label = canonical_label(path.stem)
    node_id = slugify(label)
    group = "concept" if path.parent.name == "concepts" else "connection"
    if node_id in nodes_by_id:
        warnings.append(f"duplicate canonical id '{node_id}' from {path}")
        continue
    nodes_by_id[node_id] = {
        "id": node_id,
        "label": label,
        "group": group,
        "source": str(path),
        "updated_at": iso_mtime(path),
    }
    known_labels[canonical_label(label).casefold()] = node_id

for path in paths:
    label = canonical_label(path.stem)
    source_id = slugify(label)
    if source_id not in nodes_by_id:
        continue
    content = path.read_text(encoding="utf-8")
    frontmatter = extract_frontmatter(content)

    for raw_target in re.findall(r"\[\[(.*?)\]\]", content):
        target_label = canonical_label(raw_target.split("|", 1)[0])
        target_id = known_labels.get(target_label.casefold(), slugify(target_label))
        if target_id not in nodes_by_id:
            nodes_by_id[target_id] = {
                "id": target_id,
                "label": target_label,
                "group": "unknown",
                "source": None,
                "updated_at": None,
            }
            warnings.append(f"unresolved wikilink '{target_label}' referenced by {path.name}")
        if source_id != target_id:
            links.add((source_id, target_id))

    if path.parent.name != "connections":
        continue

    model_match = re.search(r"\*\*STEM Model:\*\*\s*(.+)", content)
    model_line = model_match.group(1).strip() if model_match else "Unknown"
    model_names = re.findall(r"\[\[(.*?)\]\]", model_line)
    model = " · ".join(canonical_label(m) for m in model_names) if model_names else canonical_label(model_line)

    problem = extract_section(
        content,
        [
            r"The False Axiom",
            r"The Bottleneck",
            r"The Danger",
            r"The Current Bet Frame",
            r"The Axiom / Bottleneck",
            r"Current Constraint",
        ],
    )
    solution = extract_section(
        content,
        [r"Novel Solution", r"Novel Solution / Strategy", r"The Reframe(?:\s*\([^)]*\))?", r"Current Strategy"],
    )

    if not problem:
        warnings.append(f"missing problem section: {path.name}")
    if not solution:
        warnings.append(f"missing solution section: {path.name}")
    if model == "Unknown":
        warnings.append(f"missing STEM model: {path.name}")

    syntheses.append(
        {
            "id": source_id,
            "title": label,
            "model": model,
            "problem": problem,
            "solution": solution,
            "raw": content,
            "source": str(path),
            "updated_at": iso_mtime(path),
            "status": frontmatter.get("status", "current"),
            "confidence": frontmatter.get("confidence"),
            "evidence": frontmatter.get("evidence"),
            "is_current": frontmatter.get("canonical", "false").lower() == "true" or source_id == "current-augmented-intelligence",
        }
    )

nodes = sorted(nodes_by_id.values(), key=lambda n: (n["group"], n["label"].casefold(), n["id"]))
link_rows = [{"source": s, "target": t} for s, t in sorted(links)]
syntheses.sort(key=lambda s: (not s["is_current"], s["title"].casefold(), s["id"]))

snapshot_at = max(iso_mtime(path) for path in paths)
source_fingerprint = hashlib.sha256(
    "".join(f"{path}:{path.read_text(encoding='utf-8')}" for path in paths).encode()
).hexdigest()

payload = {
    "meta": {
        "schema_version": SCHEMA_VERSION,
        "generated_at": snapshot_at,
        "source_fingerprint": source_fingerprint,
        "source_root": str(WIKI_DIR),
        "node_count": len(nodes),
        "link_count": len(link_rows),
        "synthesis_count": len(syntheses),
        "warnings": sorted(set(warnings)),
    },
    "nodes": nodes,
    "links": link_rows,
    "syntheses": syntheses,
}

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
new_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
old_text = OUT_FILE.read_text(encoding="utf-8") if OUT_FILE.exists() else ""
OUT_FILE.write_text(new_text, encoding="utf-8")

print(
    json.dumps(
        {
            "status": "changed" if old_text != new_text else "unchanged",
            "output": str(OUT_FILE),
            "nodes": len(nodes),
            "links": len(link_rows),
            "syntheses": len(syntheses),
            "warnings": len(set(warnings)),
            "fingerprint": source_fingerprint[:12],
        },
        sort_keys=True,
    )
)
