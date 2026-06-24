#!/usr/bin/env python3
"""Generate wiki-graph.json from ~/wiki-superhuman/ concept pages.
Reads frontmatter confidence and wikilinks to build the intervention→outcome graph.
"""
import json, os, re, yaml
from pathlib import Path
from collections import defaultdict

WIKI = Path(os.path.expanduser("~/wiki-superhuman"))
CONCEPTS = WIKI / "concepts"
OUTPUT = Path(os.path.expanduser("~/.hermes/skills/stem-stack/pilot-dashboard/data/wiki-graph.json"))

# Map wiki pages to graph nodes
# Format: (wiki_page_slug, graph_node_id, node_label, node_type, override_confidence?)
WIKI_TO_NODE = [
    ("exercise-cognitive-enhancement", "exercise", "Exercise", "intervention", None),
    ("dopamine-recovery-neurobiology", "dopamine_recovery", "Dopamine Recovery", "outcome", None),
    ("mindfulness-cognitive-enhancement", "mindfulness", "Mindfulness", "intervention", None),
    ("supplements-brainfog-cognition", None, None, None, None),  # skip — split into individual supplements below
    ("supplements-addiction-recovery", None, None, None, None),  # skip — split
    ("willpower-training", "willpower_training", "Willpower Training", "intervention", None),
    ("habit-formation-vs-willpower", "habit_formation", "Habit Formation", "intervention", None),
    ("brain-fog-mechanism", "brain_fog", "Brain Fog", "outcome", None),
    ("exercise-sleep-nutrition-synthesis", None, None, None, None),  # synthesis, not a single node
]

# Additional intervention nodes with their confidence and descriptions
EXTRA_INTERVENTIONS = [
    ("sleep", "Sleep", "intervention", "high", "7-9 hrs consistent"),
    ("creatine", "Creatine", "intervention", "high", "5g/day"),
    ("nac", "NAC", "intervention", "high", "1200-2400mg/day"),
    ("omega3", "Omega-3", "intervention", "medium", "1-2g EPA+DHA"),
    ("resistance", "Resistance Training", "intervention", "medium", "2-3x/wk, 12 wks"),
    ("iron", "Iron", "intervention", "medium", "Only if deficient"),
    ("rhodiola", "Rhodiola", "intervention", "medium", "SHR-5 extract"),
    ("curcumin", "Curcumin", "intervention", "low", "800mg, ≥24 wks"),
    ("cold_exposure", "Cold Exposure", "intervention", "low", "2-5 min cold shower"),
    ("omega3_addiction", "Omega-3 (addiction)", "intervention", "low", "No addiction trials"),
    ("tyrosine_mg_zn", "Tyrosine, Mg, Zn", "intervention", "none", "Zero clinical evidence"),
    ("taurine", "Taurine", "intervention", "none", "No effect (meta-analysis)"),
    ("beetroot", "Beetroot", "intervention", "none", "Inconclusive"),
    ("self_compassion", "Self-Compassion", "intervention", "medium", "Faster lapse recovery"),
]

EXTRA_OUTCOMES = [
    ("executive_function", "Executive Function"),
    ("memory", "Memory"),
    ("attention", "Attention"),
    ("processing_speed", "Processing Speed"),
    ("mental_fatigue", "Mental Fatigue"),
    ("neuroplasticity", "Neuroplasticity"),
    ("cravings", "Cravings"),
    ("addiction_recovery", "Addiction Recovery"),
    ("mood", "Mood / Depression"),
    ("physical_fatigue", "Physical Fatigue"),
    ("stress", "Stress"),
    ("self_control", "Self-Control"),
    ("relapse", "Relapse Prevention"),
]

# Edges: from intervention → to outcome, with evidence strength
EDGES = [
    # Exercise
    ("exercise", "executive_function", "strong"),
    ("exercise", "neuroplasticity", "strong"),
    ("exercise", "brain_fog", "strong"),
    ("exercise", "mental_fatigue", "strong"),
    ("exercise", "addiction_recovery", "moderate"),
    ("exercise", "dopamine_recovery", "moderate"),
    ("exercise", "mood", "strong"),
    # Sleep
    ("sleep", "brain_fog", "strong"),
    ("sleep", "executive_function", "strong"),
    ("sleep", "attention", "strong"),
    ("sleep", "memory", "moderate"),
    # Mindfulness
    ("mindfulness", "attention", "strong"),
    ("mindfulness", "executive_function", "strong"),
    ("mindfulness", "stress", "strong"),
    ("mindfulness", "cravings", "moderate"),
    ("mindfulness", "self_control", "moderate"),
    # Creatine
    ("creatine", "memory", "strong"),
    ("creatine", "attention", "strong"),
    ("creatine", "processing_speed", "strong"),
    ("creatine", "mental_fatigue", "strong"),
    ("creatine", "brain_fog", "moderate"),
    # NAC
    ("nac", "cravings", "strong"),
    ("nac", "addiction_recovery", "strong"),
    ("nac", "relapse", "strong"),
    # Omega-3 (brain)
    ("omega3", "attention", "moderate"),
    ("omega3", "memory", "moderate"),
    ("omega3", "brain_fog", "weak"),
    # Resistance
    ("resistance", "neuroplasticity", "strong"),
    ("resistance", "executive_function", "moderate"),
    # Iron
    ("iron", "mental_fatigue", "moderate"),
    ("iron", "memory", "moderate"),
    # Rhodiola
    ("rhodiola", "physical_fatigue", "strong"),
    ("rhodiola", "stress", "strong"),
    ("rhodiola", "mental_fatigue", "weak"),
    # Curcumin
    ("curcumin", "memory", "weak"),
    ("curcumin", "brain_fog", "weak"),
    # Cold exposure
    ("cold_exposure", "dopamine_recovery", "weak"),
    # Omega-3 (addiction)
    ("omega3_addiction", "addiction_recovery", "weak"),
    ("omega3_addiction", "brain_fog", "weak"),
    # None-evidence
    ("tyrosine_mg_zn", "brain_fog", "none"),
    ("tyrosine_mg_zn", "dopamine_recovery", "none"),
    ("taurine", "brain_fog", "none"),
    ("beetroot", "brain_fog", "none"),
    # Habit formation
    ("habit_formation", "self_control", "strong"),
    ("habit_formation", "addiction_recovery", "strong"),
    ("habit_formation", "relapse", "strong"),
    # Willpower training
    ("willpower_training", "self_control", "weak"),
    # Self-compassion
    ("self_compassion", "relapse", "moderate"),
    ("self_compassion", "addiction_recovery", "moderate"),
]


def read_frontmatter(path):
    """Extract YAML frontmatter and body summary from a wiki page."""
    try:
        with open(path) as f:
            content = f.read()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm = yaml.safe_load(content[3:end])
                body = content[end+3:].strip()
                # Remove the H1 title line
                body = re.sub(r'^# .+\n+', '', body)
                # Take first paragraph (up to first ## or blank line + next section)
                summary_match = re.match(r'(.+?)(?:\n##|\n\n##|\n\*\*|\n\n\*\*)', body, re.DOTALL)
                if summary_match:
                    summary = summary_match.group(1).strip()
                else:
                    # Just take first 300 chars
                    summary = body[:300].strip()
                # Clean up — remove markdown links, keep text
                summary = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', summary)
                summary = re.sub(r'\^\[[^\]]+\]', '', summary)
                summary = re.sub(r'\n{3,}', '\n\n', summary)
                fm['_summary'] = summary[:400]
                return fm
    except Exception:
        pass
    return {}


def build_graph():
    nodes = []
    
    # Add interventions from EXTRA_INTERVENTIONS
    for nid, label, ntype, conf, desc in EXTRA_INTERVENTIONS:
        nodes.append({
            "id": nid, "label": label, "type": ntype,
            "confidence": conf, "desc": desc
        })
    
    # Add outcomes
    for oid, label in EXTRA_OUTCOMES:
        nodes.append({"id": oid, "label": label, "type": "outcome"})
    
    # Add wiki-sourced nodes with confidence from frontmatter
    for slug, nid, label, ntype, _ in WIKI_TO_NODE:
        if nid is None:
            continue
        page_path = CONCEPTS / f"{slug}.md"
        fm = read_frontmatter(page_path) if page_path.exists() else {}
        conf = fm.get("confidence", "medium")
        summary = fm.get("_summary", "")
        
        existing = next((n for n in nodes if n["id"] == nid), None)
        if existing:
            existing["confidence"] = conf
            if summary:
                existing["summary"] = summary
        else:
            nodes.append({
                "id": nid, "label": label, "type": ntype,
                "confidence": conf, "summary": summary
            })
    
    edges = [{"from": f, "to": t, "strength": s, "type": "evidence"} for f, t, s in EDGES]
    
    # Parse wikilinks from concept pages and add as cross-reference edges
    page_to_node = {
        "brain-fog-mechanism": "brain_fog",
        "dopamine-recovery-neurobiology": "dopamine_recovery",
        "dopamine-recovery-protocol": None,
        "exercise-cognitive-enhancement": "exercise",
        "exercise-sleep-nutrition-synthesis": None,
        "habit-formation-vs-willpower": "habit_formation",
        "mindfulness-cognitive-enhancement": "mindfulness",
        "supplements-addiction-recovery": "nac",
        "supplements-brainfog-cognition": "creatine",
        "willpower-training": "willpower_training",
    }
    
    seen_crosslinks = set()
    for md_file in sorted(CONCEPTS.glob("*.md")):
        slug = md_file.stem
        from_node = page_to_node.get(slug)
        if from_node is None:
            continue
        
        with open(md_file) as f:
            content = f.read()
        links = re.findall(r'\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]', content)
        
        for link in links:
            to_node = page_to_node.get(link)
            if to_node and to_node != from_node:
                key = (from_node, to_node)
                if key not in seen_crosslinks:
                    seen_crosslinks.add(key)
                    edges.append({
                        "from": from_node, "to": to_node,
                        "strength": "crosslink", "type": "crosslink"
                    })
    
    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    graph = build_graph()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(graph, f, indent=2)
    print(f"✓ wiki-graph.json regenerated: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
