#!/usr/bin/env python3
"""
Generate masterplan-graph.json from ~/wiki-masterplan/
Intelligent emergent connections: projects ↔ frameworks ↔ patterns → solutions.

Node groups:
  - project: active and aspirational life projects
  - framework: mental models & execution systems (Apex, Lead Domino, Katana, etc.)
  - pattern: current problematic patterns (time blindness, fear avoidance, etc.)
  - upgrade: known solutions/upgrades waiting to be applied
  - solution: emergent — computed via cross-referencing (pattern × framework = strategy)
  - bucket: 360 life areas
  - goal: probable outcomes / end-states

Edge types:
  - blocks: pattern → project (this pattern blocks this project)
  - addresses: framework/upgrade → pattern (this framework addresses this pattern)
  - contains: project → bucket (this project belongs to this bucket)
  - leads_to: project/framework → goal (this leads to this outcome)
  - synthesis: solution → [pattern, framework, project] (emergent connection)
"""
import json, os, re, yaml
from pathlib import Path
from collections import defaultdict

WIKI = Path(os.path.expanduser("~/wiki-masterplan"))
ENTITIES = WIKI / "entities"
CONCEPTS = WIKI / "concepts"
OUTPUT = Path(os.path.expanduser("~/pilot-dashboard/data/masterplan-graph.json"))

# ── NODE DEFINITIONS ──────────────────────

# Projects: from entity pages
PROJECTS = {
    "housing": {"label": "Housing", "group": "project", "status": "active", "desc": "Home buying — Bentonville/Centerton, <$450K"},
    "taxes": {"label": "Taxes", "group": "project", "status": "active", "desc": "Tax filing with YesMyTaxes"},
    "maintenance": {"label": "Maintenance", "group": "project", "status": "active", "desc": "Life admin: bills, DMV, cleaning"},
    "parents-trip": {"label": "Parents Trip", "group": "project", "status": "active", "desc": "Parents visiting — flights, insurance"},
    "nyc-and-niagara-trip": {"label": "NYC & Niagara Trip", "group": "project", "status": "active", "desc": "Trip planning — flights, hotels, itinerary"},
    "brain": {"label": "Brain", "group": "project", "status": "aspirational", "desc": "ADHD treatment, cognition upgrade — THE LEAD DOMINO"},
    "penis": {"label": "Penis", "group": "project", "status": "aspirational", "desc": "Phimosis cure, abstinence, addiction recovery"},
    "lifestyle": {"label": "Lifestyle", "group": "project", "status": "aspirational", "desc": "Exercise, meditation, sleep, anti-aging diet"},
    "high-value-male": {"label": "High Value Male", "group": "project", "status": "aspirational", "desc": "Identity upgrade — main character energy"},
    "hairloss": {"label": "Hairloss", "group": "project", "status": "aspirational", "desc": "Hair regrowth research"},
    "lung-health": {"label": "Lung Health Scan", "group": "project", "status": "aspirational", "desc": "Lung checkup — strange feeling"},
    "roommate": {"label": "Roommate", "group": "project", "status": "aspirational", "desc": "Living situation"},
}

# Frameworks & Models
FRAMEWORKS = {
    "lead-domino": {"label": "Lead Domino", "group": "framework", "desc": "Root strategy — simplify clutter to finite paths. One thing that makes everything else easier."},
    "apex-track-monster": {"label": "Apex Track Monster", "group": "framework", "desc": "Execution engine: drive, models, rewire, rules. Gaming the future."},
    "katana": {"label": "The Katana", "group": "framework", "desc": "Chunk day into 2 halves: low-stakes morning, finisher afternoon."},
    "building-speed": {"label": "Building Speed", "group": "framework", "desc": "Progressive difficulty: easy mode → level up → hard mode."},
    "model-1": {"label": "Model #1: Daily Units", "group": "framework", "desc": "Each day = unit of momentum. Score: Cost vs Heuristic. 1-hour blocks."},
    "model-2": {"label": "Model #2: Hardware Change", "group": "framework", "desc": "Change DNA of hardware — become the person, don't just schedule."},
    "rewire-protocol": {"label": "Rewire Protocol", "group": "framework", "desc": "Fog-break: stand → squats → breathe → return to ONE task."},
    "power-up": {"label": "Power-Up Protocol", "group": "framework", "desc": "Easy mode ⛴️ → Level up 🏎️ → Hard mode 🚀"},
    "360-buckets": {"label": "360 Buckets", "group": "framework", "desc": "Blindly invest in all life areas for compound growth."},
    "back-from-future": {"label": "Back from the Future", "group": "framework", "desc": "Simulate future self looking back — what mattered?"},
    "one-hour-blocks": {"label": "1-Hour Execution Blocks", "group": "framework", "desc": "Primary tool — focus for 60 min on highest Heuristic/Cost task."},
}

# Current Patterns (problems)
PATTERNS = {
    "time-blindness": {"label": "Time Blindness", "group": "pattern", "desc": "Can't perceive/feel future as continuous — root ADHD symptom. 'The key blocker.'"},
    "fear-avoidance": {"label": "Fear & Pain Avoidance", "group": "pattern", "desc": "Running from fear inflicts 10x more pain. Not making hard decisions."},
    "all-or-nothing": {"label": "All-or-Nothing Dopamine", "group": "pattern", "desc": "Need colossal targets for any motivation. No middle gear."},
    "energy-vampires": {"label": "Energy Vampires", "group": "pattern", "desc": "Unidentified sources sucking energy, focus, and life."},
    "self-disconnect": {"label": "Self Disconnect", "group": "pattern", "desc": "Even 0.1→0.2 version gap feels like different person. Loses context."},
    "emotional-flooding": {"label": "Emotional Flooding", "group": "pattern", "desc": "Emotionally charged with everything — burns fuel tank, depletes executive function."},
    "learned-helplessness": {"label": "Learned Helplessness", "group": "pattern", "desc": "'You can't flip the script. You are too weak.' Self-limiting belief."},
    "juvenile-identity": {"label": "Juvenile Identity", "group": "pattern", "desc": "Lived like a juvenile boy — self-image gap vs aspirational."},
}

# Upgrades (solutions you already know)
UPGRADES = {
    "let-go-fomo": {"label": "Let Go of FOMO", "group": "upgrade", "desc": "Can't have it all. Time constraints. Choose your sacrifices."},
    "jet-stream-daily": {"label": "Daily Jet Stream", "group": "upgrade", "desc": "Don't break the chain. Be in the jet stream every day."},
    "do-it-despite-fear": {"label": "Act Despite Fear", "group": "upgrade", "desc": "Fear or not, gotta do it. Time constraints — can't be a pussy anymore."},
    "self-awareness-checks": {"label": "Self-Awareness Checks", "group": "upgrade", "desc": "Get out of the loop when detected. Build into Katana."},
    "week-by-week-jumps": {"label": "Weekly Jumps", "group": "upgrade", "desc": "Make jumps week by week. Warp speed, hyper-momentum."},
    "balanced-targets": {"label": "Balanced Big Targets", "group": "upgrade", "desc": "Targets big enough for activation energy but balanced with practicality."},
    "small-timeframes": {"label": "Think in Smaller Timeframes", "group": "upgrade", "desc": "'Next hour,' 'this morning,' 'this evening.' ADHD-compatible planning."},
    "hard-programmed-rules": {"label": "Hard Programmed Rules", "group": "upgrade", "desc": "Remove decisions. Pre-made choices = no deliberation."},
}

# Goals / Probable Outcomes
GOALS = {
    "neuro-typicality": {"label": "Neuro-Typicality", "group": "goal", "desc": "ADHD treated → brain works like it should."},
    "superior-cognition": {"label": "Superior Cognition", "group": "goal", "desc": "Peak mental performance. Fast, clear, focused."},
    "colossal-momentum": {"label": "Colossal Momentum", "group": "goal", "desc": "Jet stream every day. Chain unbroken. Speed compounds."},
    "home-ownership": {"label": "Home Ownership", "group": "goal", "desc": "Settled in Bentonville/Centerton home. Major life milestone."},
    "high-value-identity": {"label": "High Value Identity", "group": "goal", "desc": "Main character energy. Charisma, presence, power."},
    "fire-back": {"label": "Bring the Fire Back", "group": "goal", "desc": "Anti-aging body. Energy, vitality, strength."},
    "counter-entropy": {"label": "Counter-Attack Entropy", "group": "goal", "desc": "Order from chaos. Systems running. Life organized."},
}

# 360 Buckets
BUCKETS = {
    "bucket-body": {"label": "Body (Exercise + Diet)", "group": "bucket", "desc": "Anti-aging diet, 9round workout"}, 
    "bucket-brain-bucket": {"label": "Brain (Cognition)", "group": "bucket", "desc": "ADHD treatment, tDCS, TMS, neurofeedback"},
    "bucket-identity": {"label": "Identity", "group": "bucket", "desc": "Mental models, decision framework, fearless, super momentum"},
    "bucket-social": {"label": "Social", "group": "bucket", "desc": "High value male charisma — eye contact, tone, presence"},
    "bucket-finances": {"label": "Finances", "group": "bucket", "desc": "Rent, food, housing"},
    "bucket-skill": {"label": "Skill", "group": "bucket", "desc": "Learning path — professional growth"},
    "bucket-work": {"label": "Work", "group": "bucket", "desc": "Career — define scope and targets"},
}

# ── EDGES ─────────────────────────────────

# Which patterns block which projects?
PATTERN_BLOCKS_PROJECT = [
    ("time-blindness", "housing", "strong"),
    ("time-blindness", "taxes", "strong"),
    ("time-blindness", "brain", "strong"),
    ("time-blindness", "all", "moderate"),  # blocks everything
    ("fear-avoidance", "taxes", "strong"),
    ("fear-avoidance", "housing", "strong"),
    ("fear-avoidance", "brain", "strong"),
    ("fear-avoidance", "penis", "strong"),
    ("fear-avoidance", "nyc-and-niagara-trip", "moderate"),
    ("all-or-nothing", "lifestyle", "strong"),
    ("all-or-nothing", "high-value-male", "strong"),
    ("all-or-nothing", "brain", "strong"),
    ("energy-vampires", "all", "moderate"),
    ("self-disconnect", "all", "strong"),
    ("emotional-flooding", "housing", "moderate"),
    ("emotional-flooding", "taxes", "moderate"),
    ("learned-helplessness", "brain", "strong"),
    ("learned-helplessness", "penis", "strong"),
    ("learned-helplessness", "high-value-male", "strong"),
    ("juvenile-identity", "high-value-male", "strong"),
    ("juvenile-identity", "roommate", "moderate"),
]

# Which frameworks/upgrades address which patterns?
FRAMEWORK_ADDRESSES_PATTERN = [
    ("lead-domino", "all-or-nothing", "strong"),  # simplifies to ONE path
    ("lead-domino", "time-blindness", "strong"),  # finite paths = external structure
    ("apex-track-monster", "all-or-nothing", "strong"),  # harnesses dopamine for drive
    ("apex-track-monster", "self-disconnect", "strong"),  # model #1 = daily continuity
    ("apex-track-monster", "learned-helplessness", "strong"),  # disproves by action
    ("katana", "emotional-flooding", "strong"),  # chunking reduces overwhelm
    ("katana", "time-blindness", "moderate"),  # half-day chunks
    ("building-speed", "all-or-nothing", "strong"),  # easy mode first
    ("building-speed", "learned-helplessness", "moderate"),  # progressive proof
    ("model-1", "self-disconnect", "strong"),  # daily unit bridges gap
    ("model-1", "time-blindness", "strong"),  # each day = measurable
    ("model-2", "juvenile-identity", "strong"),  # become the person
    ("model-2", "learned-helplessness", "strong"),  # hardware change
    ("rewire-protocol", "emotional-flooding", "strong"),  # breaks fog loop
    ("power-up", "all-or-nothing", "strong"),  # leveled progression
    ("one-hour-blocks", "time-blindness", "strong"),  # concrete timebox
    ("one-hour-blocks", "fear-avoidance", "strong"),  # small commitment
    ("back-from-future", "time-blindness", "strong"),  # makes future feel real
    ("back-from-future", "fear-avoidance", "moderate"),  # perspective shift
    ("let-go-fomo", "all-or-nothing", "strong"),  # kills the "everything" trap
    ("jet-stream-daily", "self-disconnect", "strong"),  # chain = continuity
    ("jet-stream-daily", "time-blindness", "strong"),  # external rhythm
    ("do-it-despite-fear", "fear-avoidance", "strong"),
    ("do-it-despite-fear", "learned-helplessness", "strong"),
    ("self-awareness-checks", "emotional-flooding", "strong"),
    ("self-awareness-checks", "self-disconnect", "moderate"),
    ("week-by-week-jumps", "all-or-nothing", "moderate"),  # compound gains
    ("balanced-targets", "all-or-nothing", "strong"),  # sweet spot
    ("small-timeframes", "time-blindness", "strong"),  # ADHD-compatible
    ("hard-programmed-rules", "fear-avoidance", "strong"),  # no choice = no fear
]

# Projects → buckets
PROJECT_TO_BUCKET = [
    ("brain", "bucket-brain-bucket", "strong"),
    ("lifestyle", "bucket-body", "strong"),
    ("penis", "bucket-body", "moderate"),
    ("hairloss", "bucket-body", "weak"),
    ("lung-health", "bucket-body", "moderate"),
    ("high-value-male", "bucket-identity", "strong"),
    ("high-value-male", "bucket-social", "strong"),
    ("housing", "bucket-finances", "strong"),
    ("taxes", "bucket-finances", "strong"),
    ("maintenance", "bucket-finances", "moderate"),
]

# Projects/goals → outcomes
LEADS_TO = [
    ("brain", "neuro-typicality", "strong"),
    ("brain", "superior-cognition", "strong"),
    ("lifestyle", "fire-back", "strong"),
    ("apex-track-monster", "colossal-momentum", "strong"),
    ("lead-domino", "counter-entropy", "strong"),
    ("housing", "home-ownership", "strong"),
    ("high-value-male", "high-value-identity", "strong"),
    ("jet-stream-daily", "colossal-momentum", "strong"),
]


# ── EMERGENT SYNTHESES ────────────────────
# Computed by cross-referencing: pattern × framework = actionable solution
# "If pattern X is blocking project Y, and framework Z addresses pattern X, then..."
EMERGENT_SOLUTIONS = [
    {
        "id": "solution-time-blindness-katana-blocks",
        "title": "Slice the Day, Not the Year",
        "problem": "Time blindness makes long-term planning impossible. The future doesn't feel real.",
        "solution": "Use The Katana to chunk every day into 2 halves. Morning = 1 external task (Track B). Afternoon = 1 internal task (Track A). Use 1-hour blocks. Never plan beyond 'this morning' or 'this afternoon.' The Katana + 1-hour blocks are ADHD-native planning — they don't require feeling the future.",
        "model": "The Katana × Time Blindness",
        "inputs": ["katana", "one-hour-blocks", "small-timeframes", "time-blindness"],
        "outputs": ["housing", "taxes", "maintenance", "all"],
    },
    {
        "id": "solution-apex-vs-helplessness",
        "title": "Action Is the Only Refutation",
        "problem": "Learned helplessness: 'You can't flip the script. You are too weak.' This belief blocks the brain project, penis project, and identity upgrade.",
        "solution": "Model #1 from Apex: Each day is a unit of momentum. Start at Level 1 — 1 small task per day. Every completed day is EVIDENCE that disproves 'you are too weak.' After 7 days, the belief has 7 counter-examples. After 30 days, it's dead. The Apex Track Monster's drive: 'gaming the future is the game' — lay the bridge and go back and forth like flash.",
        "model": "Apex Track Monster × Learned Helplessness",
        "inputs": ["apex-track-monster", "model-1", "building-speed", "learned-helplessness"],
        "outputs": ["brain", "penis", "high-value-male", "all"],
    },
    {
        "id": "solution-lead-domino-parallel",
        "title": "Parallelize the Impossible",
        "problem": "The false axiom: 'I must fix my ADHD before I can take any action.' This creates infinite deadlock — brain doesn't get fixed because no action is taken, and no action is taken because brain isn't fixed.",
        "solution": "The Lead Domino + Euclidean 5th Postulate shatter: Run TWO parallel tracks. Track A (hardware): brain diagnosis, exercise, sleep. Track B (backlog): housing calls, tax calls, trip bookings. Each completed Track B task provides dopamine that fuels Track A. Each Track A win makes Track B easier. They FEED each other. The Lead Domino isn't sequential — it's parallel. ADHD treatment starts with a 10-minute phone call. You can make phone calls with a broken brain.",
        "model": "Lead Domino × Euclidean Thinking",
        "inputs": ["lead-domino", "model-2", "do-it-despite-fear", "fear-avoidance", "all-or-nothing"],
        "outputs": ["brain", "housing", "taxes", "parents-trip", "nyc-and-niagara-trip"],
    },
    {
        "id": "solution-dopamine-flywheel",
        "title": "The Dopamine Flywheel",
        "problem": "All-or-nothing dopamine system requires colossal targets for any motivation. Small tasks feel pointless. But colossal targets are paralyzing. Result: zero throughput.",
        "solution": "Building Speed protocol + Model #1: Put the game on EASY MODE first. 1 small task = day won. The dopamine comes from COMPLETION, not magnitude. After 7 days of easy mode → level up. After 21 days → hard mode. This creates a dopamine flywheel: complete → dopamine → complete more → more dopamine. The 'glimpse of might' milestone starts with ONE 10-minute walk. Not a gym membership. Not a 6-month plan. ONE walk.",
        "model": "Building Speed × All-or-Nothing Dopamine",
        "inputs": ["building-speed", "model-1", "power-up", "balanced-targets", "all-or-nothing"],
        "outputs": ["lifestyle", "brain", "high-value-male", "all"],
    },
    {
        "id": "solution-rewire-emotional-flooding",
        "title": "The Fog Circuit Breaker",
        "problem": "Emotional flooding burns the fuel tank. Every setback feels catastrophic. The brain loops, executive function crashes, and hours are lost.",
        "solution": "The Rewire Protocol IS the circuit breaker. When fog hits: (1) stand up immediately — breaks the loop physically, (2) 2-3 min squats/marching — blood flow resets neurotransmitters, (3) 1-2 min slow breathing — vagal tone activation, (4) return to ONE task — single tab, single app. Paired with self-awareness checks from Meta Upgrades: 'get out of the loop whenever detected.' This protocol takes 5 minutes and pays back hours.",
        "model": "Rewire Protocol × Emotional Flooding",
        "inputs": ["rewire-protocol", "self-awareness-checks", "hard-programmed-rules", "emotional-flooding"],
        "outputs": ["all"],
    },
    {
        "id": "solution-fear-avoidance-minimax",
        "title": "Minimax the Fear: Catalogue & Conquer",
        "problem": "Fear avoidance blocks housing (calling bankers), taxes (talking to accountants), brain (doctors), and trips (booking). Every avoided task compounds into bigger fear + real consequences.",
        "solution": "Use Minimax from Warp-Speed: Categorize every avoided task. REVERSIBLE decisions (doctor appointment, phone call) → MAXIMUM SPEED — do it NOW. IRREVERSIBLE with known downside (tax filing, housing offer) → aggressive with pre-set stop-loss. IRREVERSIBLE with fat-tail risk → go slow. Then apply 'Act Despite Fear' upgrade: 'Fear or not, gotta do it. Time constraints.' The 10-10-10 lens: will this fear matter in 10 months? If no → it's noise. If yes → it's a Lead Domino item — prioritize above everything.",
        "model": "Minimax × Fear Avoidance",
        "inputs": ["do-it-despite-fear", "hard-programmed-rules", "lead-domino", "fear-avoidance"],
        "outputs": ["housing", "taxes", "brain", "penis", "all"],
    },
    {
        "id": "solution-jetstream-identity-bridge",
        "title": "The Jet Stream Identity Bridge",
        "problem": "Self-disconnect: even 0.1→0.2 version gaps feel like different people. Past Sai's failures feel like a different person's failures. But so do past Sai's wins. No continuity = no momentum.",
        "solution": "The Jet Stream (don't break the chain) + Model #1 (each day = unit) create EXTERNAL continuity. The chain is a physical record. Day 18's Sai didn't break the chain because Day 17's Sai won. The wiki IS the bridge — it remembers who you were yesterday so you don't have to. Paired with 'Back from the Future': simulate 45-year-old Sai looking back. Did he see a continuous trajectory of growth, or fragmented bursts? The answer guides today's action.",
        "model": "Daily Jet Stream × Self Disconnect",
        "inputs": ["jet-stream-daily", "model-1", "back-from-future", "self-disconnect"],
        "outputs": ["all"],
    },
    {
        "id": "solution-energy-vampire-audit",
        "title": "Monthly Vampire Exorcism",
        "problem": "Energy vampires — unidentified sources sucking focus and life. Could be social media, people, clutter, indecision, open loops, unprocessed inputs. They're invisible by definition.",
        "solution": "Shannon's Information Theory from Warp-Speed: Brain has finite channel capacity. Audit your S/N ratio monthly. Track every energy dip for one week. Identify the top 3 vampires. Kill one per month. The first candidates: open browser tabs, unread messages, decisions waiting to be made, people who drain you. Each vampire removed = bandwidth reclaimed. At 75% noise → 32% potential. Remove vampires → increase signal.",
        "model": "Shannon's Law × Energy Vampires",
        "inputs": ["self-awareness-checks", "energy-vampires"],
        "outputs": ["all"],
    },
    {
        "id": "solution-weekly-compound-jumps",
        "title": "The Weekly Phase Transition Protocol",
        "problem": "Progress feels invisible day-to-day. Without visible progress, the all-or-nothing dopamine system loses activation energy. Motivation crashes.",
        "solution": "Weekly review (Saturday cadence) + 'Make jumps week by week' upgrade. Every Saturday: (1) score the week on Cost vs Heuristic, (2) count completed tasks — make the number VISIBLE, (3) set NEXT week's ONE big jump, (4) update the wiki. The Phase Transitions framework: identify the nearest threshold (habit at ~66 days, first milestone at 7 days, 'glimpse of might' at first workout). Front-load energy to cross the nearest threshold. Once crossed, the next threshold is closer. Each weekly jump is a visible compound gain.",
        "model": "Phase Transitions × Weekly Jumps",
        "inputs": ["week-by-week-jumps", "model-1", "jet-stream-daily", "all-or-nothing"],
        "outputs": ["all"],
    },
]


# ── BUILD GRAPH ────────────────────────────

def build():
    nodes = []
    node_ids = set()
    
    def add_node(nid, data):
        if nid not in node_ids:
            node_ids.add(nid)
            nodes.append({"id": nid, **data})
    
    # Add all node types
    for nid, data in PROJECTS.items():
        add_node(nid, data)
    for nid, data in FRAMEWORKS.items():
        add_node(nid, data)
    for nid, data in PATTERNS.items():
        add_node(nid, data)
    for nid, data in UPGRADES.items():
        add_node(nid, data)
    for nid, data in GOALS.items():
        add_node(nid, data)
    for nid, data in BUCKETS.items():
        add_node(nid, data)
    
    # Add solution nodes
    for sol in EMERGENT_SOLUTIONS:
        sid = sol["id"]
        add_node(sid, {
            "label": sol["title"],
            "group": "solution",
            "desc": sol["solution"][:200] + "...",
        })
    
    edges = []
    def add_edge(source, target, strength="moderate", etype="default"):
        edges.append({"source": source, "target": target, "strength": strength, "type": etype})
    
    # Pattern blocks project
    for pattern, project, strength in PATTERN_BLOCKS_PROJECT:
        if project == "all":
            for pid in PROJECTS:
                add_edge(pattern, pid, strength, "blocks")
        else:
            add_edge(pattern, project, strength, "blocks")
    
    # Framework addresses pattern
    for fw, pattern, strength in FRAMEWORK_ADDRESSES_PATTERN:
        add_edge(fw, pattern, strength, "addresses")
    
    # Project to bucket
    for proj, bucket, strength in PROJECT_TO_BUCKET:
        add_edge(proj, bucket, strength, "contains")
    
    # Leads to
    for src, tgt, strength in LEADS_TO:
        add_edge(src, tgt, strength, "leads_to")
    
    # Solution edges: input frameworks/patterns → solution
    for sol in EMERGENT_SOLUTIONS:
        sid = sol["id"]
        for inp in sol["inputs"]:
            if inp in node_ids:
                add_edge(inp, sid, "strong", "synthesis_input")
        for out in sol["outputs"]:
            if out == "all":
                for pid in PROJECTS:
                    add_edge(sid, pid, "strong", "solves")
            elif out in node_ids:
                add_edge(sid, out, "strong", "solves")
    
    # Extract syntheses for the dashboard cards
    syntheses = []
    for sol in EMERGENT_SOLUTIONS:
        syntheses.append({
            "title": sol["title"],
            "model": sol["model"],
            "problem": sol["problem"],
            "solution": sol["solution"],
        })
    
    return {"nodes": nodes, "edges": edges, "syntheses": syntheses}


if __name__ == "__main__":
    graph = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(graph, f, indent=2)
    print(f"✓ masterplan-graph.json generated: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges, {len(graph['syntheses'])} syntheses")
    # Print node counts by group
    groups = defaultdict(int)
    for n in graph["nodes"]:
        groups[n["group"]] += 1
    for g, c in sorted(groups.items()):
        print(f"  {g}: {c}")
