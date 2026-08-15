KINDS = ("journal", "project", "task", "habit", "note", "milestone", "episode")
EVIDENCE = ("observed", "calculated", "inferred", "unknown")
EDGE_RELS = (
    "child_of",
    "blocks",
    "unlocks",
    "mentions",
    "supports",
    "evidences",
    "watch_trigger",
    "derived_from",
)


class PacketError(ValueError):
    pass


def validate_packet(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise PacketError("packet must be an object")
    kind = (raw.get("kind") or "").strip().lower()
    if kind not in KINDS:
        raise PacketError(f"kind required: {', '.join(KINDS)}")
    title = (raw.get("title") or "").strip()
    if not title:
        raise PacketError("title required")
    evidence = (raw.get("evidence_class") or "observed").strip().lower()
    if evidence not in EVIDENCE:
        raise PacketError(f"evidence_class must be one of {EVIDENCE}")
    props = dict(raw.get("properties") or {})
    if kind == "task" and not str(props.get("done_when") or "").strip():
        raise PacketError("task requires properties.done_when")
    if kind == "project" and not str(props.get("win_condition") or "").strip():
        # allow compile to fill later; still require something explicit if missing
        if "win when" not in title.lower() and "win_condition" not in raw:
            props.setdefault("win_condition", "unspecified — set win condition")
    status = (raw.get("status") or ("active" if kind in ("project", "habit") else "open")).strip()
    packet = {
        "kind": kind,
        "title": title[:240],
        "body": (raw.get("body") or "").strip(),
        "evidence_class": evidence,
        "status": status,
        "tags": list(raw.get("tags") or []),
        "properties": props,
        "source": raw.get("source") or "source-ui",
    }
    if raw.get("id"):
        packet["id"] = raw["id"]
    return packet


def compile_text(text: str, kind_hint: str | None = None) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise PacketError("empty capture")
    kind = (kind_hint or "").strip().lower() or None
    rest = raw
    prefixes = ("project:", "task:", "habit:", "journal:", "note:", "milestone:")
    low = raw.lower()
    for p in prefixes:
        if low.startswith(p):
            kind = p[:-1]
            rest = raw[len(p):].strip()
            break
    props = {}
    if kind is None:
        if "done when" in low or "done_when" in low:
            kind = "task"
        elif rest.startswith("#") or len(rest) > 160:
            kind = "journal"
        else:
            kind = "note"
    if kind == "task":
        done = ""
        for sep in ("done when ", "done_when ", "done when:", "win when "):
            i = rest.lower().find(sep)
            if i >= 0:
                done = rest[i + len(sep):].strip()
                rest = rest[:i].strip(" —,-")
                break
        props["done_when"] = done or "stated complete by operator"
    if kind == "project":
        win = ""
        for sep in ("win when ", "win_condition ", "win:"):
            i = rest.lower().find(sep)
            if i >= 0:
                win = rest[i + len(sep):].strip()
                rest = rest[:i].strip(" —,-")
                break
        props["win_condition"] = win or rest
    if kind == "journal":
        from datetime import date
        props["date"] = date.today().isoformat()
    return validate_packet({
        "kind": kind,
        "title": rest[:240] or kind,
        "body": rest,
        "evidence_class": "observed",
        "properties": props,
        "source": "source-ui",
    })
