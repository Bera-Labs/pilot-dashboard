import os, re, json, glob

wiki_dir = "/root/wiki-augmented-intelligence"
out_file = "/root/pilot-dashboard/data/augmented-graph.json"

nodes = []
links = []
syntheses = []
node_ids = set()

def process_file(filepath, group):
    filename = os.path.basename(filepath)
    title = filename.replace('.md', '')
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    nodes.append({"id": title, "group": group})
    node_ids.add(title)
    
    # Extract links [[Node]]
    linked = re.findall(r'\[\[(.*?)\]\]', content)
    for target in linked:
        links.append({"source": title, "target": target})
        
    if group == "connection":
        # Extract STEM model
        model_match = re.search(r'\*\*STEM Model:\*\*\s*(?:\[\[)?([^\]\n]+)(?:\]\])?', content)
        model = model_match.group(1).strip() if model_match else "Unknown"
        
        # Extract Novel Solution / Reframe / Strategy
        solution_match = re.search(r'## Novel Solution\n(.*?)(?=\n##|$)', content, re.DOTALL)
        solution = solution_match.group(1).strip() if solution_match else ""
        if not solution:
            solution_match = re.search(r'## The Reframe.*?\n(.*?)(?=\n##|$)', content, re.DOTALL)
            solution = solution_match.group(1).strip() if solution_match else content[:200] + "..."
            
        # Extract Problem / Bottleneck / Axiom
        problem_match = re.search(r'## The False Axiom\n(.*?)(?=\n##|$)', content, re.DOTALL)
        problem = problem_match.group(1).strip() if problem_match else ""
        if not problem:
            problem_match = re.search(r'## The Bottleneck\n(.*?)(?=\n##|$)', content, re.DOTALL)
            problem = problem_match.group(1).strip() if problem_match else ""
        if not problem:
            problem_match = re.search(r'## The Danger.*?\n(.*?)(?=\n##|$)', content, re.DOTALL)
            problem = problem_match.group(1).strip() if problem_match else ""
        if not problem:
             problem_match = re.search(r'## The Current Bet Frame\n(.*?)(?=\n##|$)', content, re.DOTALL)
             problem = problem_match.group(1).strip() if problem_match else ""
            
        syntheses.append({
            "title": title,
            "model": model,
            "problem": problem,
            "solution": solution,
            "raw": content
        })

# Process files
for f in glob.glob(f"{wiki_dir}/concepts/*.md"):
    process_file(f, "concept")
    
for f in glob.glob(f"{wiki_dir}/connections/*.md"):
    process_file(f, "connection")

# Ensure all targets exist
for link in links:
    if link['target'] not in node_ids:
        nodes.append({"id": link['target'], "group": "unknown"})
        node_ids.add(link['target'])

os.makedirs(os.path.dirname(out_file), exist_ok=True)
with open(out_file, 'w') as f:
    json.dump({"nodes": nodes, "links": links, "syntheses": syntheses}, f, indent=2)

print("Augmented Graph data generated successfully at", out_file)
