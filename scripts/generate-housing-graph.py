#!/usr/bin/env python3
"""
Housing Wiki Augmented Graph Generator
Pulls from ~/wiki/connections/, ~/wiki/entities/, and ~/wiki/comparisons/
Outputs D3.js-ready JSON to ~/pilot-dashboard/data/
"""
import os, re, json, glob, yaml

WIKI_DIR = "/root/wiki"
OUT_FILE = "/root/pilot-dashboard/data/housing-graph.json"

def parse_frontmatter(content):
    """Extract YAML frontmatter if present."""
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            try:
                return yaml.safe_load(content[3:end])
            except:
                pass
    return {}

def process_file(filepath, group):
    """Parse a markdown file into a graph node with links."""
    filename = os.path.basename(filepath)
    title = filename.replace('.md', '')
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    fm = parse_frontmatter(content)
    
    node = {
        "id": title,
        "group": group,
        "stem_models": fm.get("stem_models", []),
        "confidence": fm.get("confidence", ""),
        "sources": fm.get("sources", [])
    }
    
    return node, content

def build_graph():
    nodes = []
    links = []
    syntheses = []
    node_ids = set()
    
    # Process all markdown files in the wiki
    for dir_name, group_name in [
        ("entities", "community"),
        ("comparisons", "comparison"),
        ("connections", "connection"),
    ]:
        pattern = f"{WIKI_DIR}/{dir_name}/*.md"
        for filepath in glob.glob(pattern):
            node, content = process_file(filepath, group_name)
            nodes.append(node)
            node_ids.add(node["id"])
            
            # Extract wikilinks [[target]]
            linked = re.findall(r'\[\[(.*?)\]\]', content)
            for target in linked:
                # Clean target: remove path-like prefixes
                clean = target.split('/')[-1] if '/' in target else target
                links.append({"source": node["id"], "target": clean})
            
            # For connection files, extract synthesis data
            if group_name == "connection":
                model_match = re.search(
                    r'\*\*STEM Model:\*\*\s*(?:\[\[)?([^\]\n]+)(?:\]\])?', content
                )
                model = model_match.group(1).strip() if model_match else "Unknown"
                
                # Problem / Axiom / Bottleneck
                problem = ""
                for pattern in [
                    r'## The False Axiom\n(.*?)(?=\n##|$)',
                    r'## The Hidden Probability\n(.*?)(?=\n##|$)',
                    r'## The Axiom\n(.*?)(?=\n##|$)',
                    r'## The Bet\n(.*?)(?=\n##|$)',
                    r'## The Current Bet Frame\n(.*?)(?=\n##|$)',
                    r'## The Contradiction\n(.*?)(?=\n##|$)',
                    r'## The Reality.*?\n(.*?)(?=\n##|$)',
                ]:
                    m = re.search(pattern, content, re.DOTALL)
                    if m:
                        problem = m.group(1).strip()
                        break
                
                # Solution / Strategy / Reframe
                solution = ""
                for pattern in [
                    r'## Novel Strategy\n(.*?)(?=\n##|$)',
                    r'## Novel Solution\n(.*?)(?=\n##|$)',
                    r'## The Reframe\n(.*?)(?=\n##|$)',
                    r'## Strategy\n(.*?)(?=\n##|$)',
                    r'## The Asymmetric Payoff\n(.*?)(?=\n##|$)',
                    r'## Optimal Entry Window\n(.*?)(?=\n##|$)',
                ]:
                    m = re.search(pattern, content, re.DOTALL)
                    if m:
                        solution = m.group(1).strip()
                        break
                
                syntheses.append({
                    "title": node["id"],
                    "model": model,
                    "problem": problem,
                    "solution": solution
                })
    
    # Ensure all link targets exist as nodes
    for link in links:
        if link['target'] not in node_ids:
            nodes.append({
                "id": link['target'],
                "group": "unknown",
                "stem_models": [],
                "confidence": "",
                "sources": []
            })
            node_ids.add(link['target'])
    
    return {"nodes": nodes, "links": links, "syntheses": syntheses}

if __name__ == "__main__":
    graph = build_graph()
    
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(graph, f, indent=2)
    
    print(f"✅ Housing graph generated: {len(graph['nodes'])} nodes, "
          f"{len(graph['links'])} links, {len(graph['syntheses'])} syntheses")
    print(f"   Saved to {OUT_FILE}")
