# The Source — graph ledger

Canonical life store. Graph is truth. Vectors (later) are a rebuildable index.

```
data/graph/
  SCHEMA.md
  events.jsonl      # append-only audit
  current.json      # public projection (Vercel GET)
  source.db         # local SQLite (gitignored; rebuilt from events if needed)
  imports/          # outliner fingerprints
```

## Node
id, kind (journal|project|task|habit|note|milestone|episode), title, body,
evidence_class (observed|calculated|inferred|unknown), status, tags[], properties{},
source, created_at, modified_at, rev

## Edge (bi-temporal)
from, to, rel (child_of|blocks|unlocks|mentions|supports|evidences|watch_trigger|derived_from)
valid_from, valid_to, observed_at, recorded_at

Invalidate — set valid_to — never delete history.

## Write
Local only. `GRAPH_WRITE_TOKEN` must be set. Loopback or `X-Graph-Token`.
Vercel: token unset → POST 403.
