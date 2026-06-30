import os, glob

for filepath in glob.glob("/root/wiki-augmented-intelligence/connections/*.md"):
    with open(filepath, "r") as f:
        content = f.read()
    
    # Add brackets to make bidirectional links back to concepts
    content = content.replace("**STEM Model:** Euclidean Thinking", "**STEM Model:** [[Euclidean Thinking]]")
    content = content.replace("**STEM Model:** Warp-Speed Execution", "**STEM Model:** [[Warp-Speed Execution]]")
    content = content.replace("**STEM Model:** Probabilistic Thinking", "**STEM Model:** [[Probabilistic Thinking]]")
    content = content.replace("**STEM Model:** Thinking in Bets", "**STEM Model:** [[Thinking in Bets]]")
    
    with open(filepath, "w") as f:
        f.write(content)

print("Links patched")
