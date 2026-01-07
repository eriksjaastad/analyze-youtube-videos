import os
import sys
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from scripts.config import LIBRARY_DIR, SYNTHESIS_DIR, run_ollama_command, initialize_directories, check_environment, logger, safe_slug

# Industrial Hardening: Context Ceiling
MAX_TOKENS = 32000 # Conservative estimate for DeepSeek-R1 local context

def atomic_write(path: Path, content: str) -> None:
    """Atomic write using a temp file and rename pattern."""
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    temp_path.rename(path)

def summarize_document(filename: str, content: str) -> str:
    """
    Summarize a single document to fit within context limits.
    Prevents OOM and truncation during final synthesis.
    """
    logger.info(f"[*] Summarizing {filename} to fit context budget...")
    prompt = f"""
Summarize the following technical report for a master synthesis. 
Extract the most critical architectural patterns, consensus points, and unique insights.
Keep it concise but high-density.

DOCUMENT: {filename}

CONTENT:
{content}
"""
    try:
        summary = run_ollama_command(prompt, timeout=300)
        return f"\n\n--- SUMMARY OF: {filename} ---\n\n{summary}"
    except Exception as e:
        logger.error(f"Failed to summarize {filename}: {e}")
        # Fallback to simple truncation if summarization fails
        return f"\n\n--- TRUNCATED DOCUMENT: {filename} ---\n\n{content[:2000]}..."

def aggregate_library(category: Optional[str] = None) -> str:
    """
    Reads all markdown files in the library and aggregates their content.
    If context budget is exceeded, switches to summarization strategy.
    """
    if not LIBRARY_DIR.exists():
        logger.error(f"Library directory not found: {LIBRARY_DIR}")
        return ""

    aggregated_text = ""
    file_count = 0
    total_chars = 0

    # Pattern to skip index files
    index_pattern = re.compile(r'^\d+_Index_')

    all_files = sorted([f for f in os.listdir(LIBRARY_DIR) if f.endswith(".md") and not index_pattern.match(f)])
    
    for filename in all_files:
        filepath = LIBRARY_DIR / filename
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Simple category check if requested (checks tags or title)
            if category:
                if f"topic/{category.lower()}" not in content.lower() and category.lower() not in filename.lower():
                    continue

            # Check context budget (approx 4 chars per token)
            current_chars = len(content)
            if (total_chars + current_chars) / 4 > MAX_TOKENS:
                logger.warning(f"Context budget exceeded. Summarizing remaining documents.")
                summary = summarize_document(filename, content)
                aggregated_text += summary
                total_chars += len(summary)
            else:
                aggregated_text += f"\n\n--- DOCUMENT: {filename} ---\n\n"
                aggregated_text += content
                total_chars += current_chars + 50 # padding for header
                
            file_count += 1

    logger.info(f"[*] Aggregated {file_count} documents for synthesis ({total_chars // 4} estimated tokens).")
    return aggregated_text

def synthesize_knowledge(aggregated_text: str, topic_name: str) -> Optional[str]:
    """
    Sends the aggregated text to the model for multi-document synthesis.
    """
    logger.info(f"[*] Synthesizing strategy for: {topic_name}...")

    prompt = f"""
You are "The Strategist," a senior AI systems architect. Your goal is to synthesize multiple deep-dive technical reports into a single, cohesive "Master Strategy" document.

### Aggregated Library Data:
{aggregated_text}

---

### Instructions:
1. **Identify Consensus Patterns**: Where do these different experts agree?
2. **Highlight Contradictions**: Where do they disagree or provide different approaches?
3. **The "Common Truths"**: Distill the most robust, non-obvious principles.
4. **Actionable Roadmap**: Create a combined workflow or architectural pattern leveraging the best ideas.
5. **Skill Library Promotion**: Identify the top 3-5 skills that should be prioritized for the global "agent-skills-library".

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
        logger.error(f"Synthesis failed: {e}")
        return None

def main() -> None:
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
        logger.error("No documents found to synthesize.")
        sys.exit(1)

    synthesis_report = synthesize_knowledge(aggregated_text, args.topic)

    if synthesis_report:
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d")
        safe_topic = safe_slug(args.topic)
        filename = args.output if args.output else f"{timestamp}_{safe_topic}.md"
        filepath = SYNTHESIS_DIR / filename
        
        # Traversal Guard
        if not filepath.resolve().is_relative_to(SYNTHESIS_DIR.resolve()):
            logger.error(f"Potential Path Traversal detected: {filepath}")
            sys.exit(1)
            
        # Add basic frontmatter
        frontmatter = f"""---
tags:
  - p/analyze-youtube-videos
  - type/synthesis
  - topic/{safe_slug(args.topic)}
status: #status/active
created: {datetime.now().strftime("%Y-%m-%d")}
---

"""
        atomic_write(filepath, frontmatter + synthesis_report)
        logger.info(f"[+] Master Strategy saved to: {filepath}")
    else:
        logger.error("Failed to generate synthesis report.")
        sys.exit(1)

if __name__ == "__main__":
    main()
