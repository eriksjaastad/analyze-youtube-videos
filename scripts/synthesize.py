import os
import sys
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from scripts.config import LIBRARY_DIR, SYNTHESIS_DIR, initialize_directories, check_environment, logger, safe_slug

# Industrial Hardening: Context Ceiling for document aggregation
MAX_TOKENS = 32000

def atomic_write(path: Path, content: str) -> None:
    """Atomic write using a temp file and rename pattern."""
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    temp_path.rename(path)

def summarize_document(filename: str, content: str) -> str:
    """
    Truncate a document to fit within context limits.
    Full summarization is handled by Claude during synthesis.
    """
    logger.info(f"[*] Truncating {filename} to fit context budget...")
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
    Prepares aggregated text for synthesis.
    Actual synthesis is performed by Claude (the agent), not by a local model.
    When run standalone, outputs the aggregated text for Claude to process.
    """
    raise NotImplementedError(
        "synthesize_knowledge requires an LLM. Run this through Claude Code, not standalone. "
        "Use: claude 'synthesize strategy for topic X'"
    )

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
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just show synthesis")
    
    args = parser.parse_args()

    aggregated_text = aggregate_library(args.category)
    
    if not aggregated_text:
        logger.error("No documents found to synthesize.")
        sys.exit(1)

    synthesis_report = synthesize_knowledge(aggregated_text, args.topic)

    if synthesis_report:
        if args.dry_run:
            logger.info("--- DRY RUN: Synthesis Report ---")
            logger.info(synthesis_report)
            logger.info("---------------------------------")
            logger.info("✨ Dry run complete. No files written.")
            return

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
