import os
import sys
import argparse
import re
from datetime import datetime
from scripts.config import LIBRARY_DIR, SYNTHESIS_DIR, run_ollama_command, initialize_directories, check_environment

def aggregate_library(category=None):
    """
    Reads all markdown files in the library and aggregates their content.
    If category is provided, only files in that category are included.
    """
    if not LIBRARY_DIR.exists():
        print(f"[!] Library directory not found: {LIBRARY_DIR}")
        return ""

    aggregated_text = ""
    file_count = 0

    # Pattern to skip index files
    index_pattern = re.compile(r'^\d+_Index_')

    for filename in sorted(os.listdir(LIBRARY_DIR)):
        if not filename.endswith(".md") or index_pattern.match(filename):
            continue

        filepath = os.path.join(LIBRARY_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Simple category check if requested (checks tags or title)
            if category:
                # Basic heuristic: check for tag or keyword in title
                if f"topic/{category.lower()}" not in content.lower() and category.lower() not in filename.lower():
                    continue

            aggregated_text += f"\n\n--- DOCUMENT: {filename} ---\n\n"
            aggregated_text += content
            file_count += 1

    print(f"[*] Aggregated {file_count} documents for synthesis.")
    return aggregated_text

def synthesize_knowledge(aggregated_text, topic_name):
    """
    Sends the aggregated text to the model for multi-document synthesis.
    """
    print(f"[*] Synthesizing strategy for: {topic_name}...")

    prompt = f"""
You are "The Strategist," a senior AI systems architect. Your goal is to synthesize multiple deep-dive technical reports into a single, cohesive "Master Strategy" document.

### Aggregated Library Data:
{aggregated_text}

---

### Instructions:
1. **Identify Consensus Patterns**: Where do these different experts (e.g., Daniel Miessler, Aniket Panjwani, AWS, Parker Prompts) agree?
2. **Highlight Contradictions**: Where do they disagree or provide different approaches to the same problem?
3. **The "Common Truths"**: Distill the most robust, non-obvious principles that appear across multiple sources.
4. **Actionable Roadmap**: Create a combined workflow or architectural pattern that leverages the best ideas from all documents.
5. **Skill Library Promotion**: Identify the top 3-5 skills that should be prioritized for the global "agent-skills-library" based on this synthesis.

    Generate a structured Markdown report titled: "Master Strategy: {topic_name}".
    Return ONLY the Markdown content.
    """

    try:
        clean_response = run_ollama_command(prompt, timeout=600) # Longer timeout for synthesis
        
        # Extract markdown if wrapped
        if "```markdown" in clean_response:
            clean_response = clean_response.split("```markdown")[1].split("```")[0].strip()
        elif "```" in clean_response:
            clean_response = clean_response.split("```")[1].split("```")[0].strip()
            
        return clean_response
    except Exception as e:
        print(f"[!] {e}")
        return None

def main():
    # Proactive Health Check
    if not check_environment():
        sys.exit(1)

    # Initialize Directories
    initialize_directories()

    parser = argparse.ArgumentParser(description="The Strategist: Synthesize library entries into a Master Strategy.")
    parser.add_argument("--topic", default="AI Orchestration & Automation", help="The topic name for the synthesis report.")
    parser.add_argument("--category", help="Optional category filter (e.g., ai, diet).")
    parser.add_argument("--output", help="Custom output filename in the synthesis/ directory.")
    
    args = parser.parse_args()

    aggregated_text = aggregate_library(args.category)
    
    if not aggregated_text:
        print("[!] No documents found to synthesize.")
        sys.exit(1)

    synthesis_report = synthesize_knowledge(aggregated_text, args.topic)

    if synthesis_report:
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d")
        safe_topic = re.sub(r'[^\w\s-]', '', args.topic).strip().replace(' ', '_')
        filename = args.output if args.output else f"{timestamp}_{safe_topic}.md"
        filepath = os.path.join(SYNTHESIS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Add basic frontmatter
            frontmatter = f"""---
tags:
  - p/analyze-youtube-videos
  - type/synthesis
  - topic/{args.topic.lower().replace(' ', '-')}
status: #status/active
created: {datetime.now().strftime("%Y-%m-%d")}
---

"""
            f.write(frontmatter + synthesis_report)
            
        print(f"[+] Master Strategy saved to: {filepath}")
    else:
        print("[!] Failed to generate synthesis report.")

if __name__ == "__main__":
    main()
