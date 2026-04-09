import sys
import argparse
import re
from pathlib import Path
from typing import Optional, Dict
from scripts.config import LOCAL_SKILLS_PATH, validate_json_data, initialize_directories, check_environment, safe_slug, logger

def extract_skill_data(source_path: str, skill_name: str) -> Optional[str]:
    """Read the source file and extract context about the skill."""
    source = Path(source_path)
    if not source.exists():
        logger.error(f"Source path {source_path} does not exist.")
        return None
    
    with open(source, "r", encoding='utf-8') as f:
        content = f.read()
    
    # Try to find the skill name in the content and get surrounding context
    lines = content.split('\n')
    context = []
    found = False
    for line in lines:
        if skill_name.lower() in line.lower():
            found = True
        if found:
            context.append(line)
            if len(context) > 50: # Get a decent chunk of context
                break
    
    return "\n".join(context) if context else content

def evaluate_utility(skill_name: str, context: str) -> Optional[str]:
    """
    Evaluate if a skill is worth promoting to the Global Skills Library.
    This function is intended to be called by Claude (the agent), not standalone.
    Pass the evaluation prompt to Claude and return the response.
    """
    raise NotImplementedError(
        "evaluate_utility requires an LLM. Run this through Claude Code, not standalone. "
        "Use: claude 'evaluate skill X from source Y'"
    )

def generate_templates(skill_name: str, evaluation: str, context: str) -> Optional[Dict[str, str]]:
    """
    Generate skill file contents based on evaluation and context.
    This function is intended to be called by Claude (the agent), not standalone.
    """
    raise NotImplementedError(
        "generate_templates requires an LLM. Run this through Claude Code, not standalone."
    )

def parse_decision(evaluation_text: Optional[str]) -> str:
    """Regex pattern to match DECISION: [PROMOTE] or [REJECT] at the start of a line."""
    if evaluation_text is None:
        return "UNKNOWN"
    # Strict regex: ^DECISION:\s*\[(PROMOTE|REJECT)\]
    decision_pattern = re.compile(r'^DECISION:\s*\[(PROMOTE|REJECT)\]', re.IGNORECASE | re.MULTILINE)
    
    match = decision_pattern.search(evaluation_text)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"

def atomic_write(path: Path, content: str) -> None:
    """Atomic write using a temp file and rename pattern."""
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    temp_path.rename(path)

def main() -> None:
    # Proactive Health Check
    if not check_environment():
        sys.exit(1)

    # Initialize Directories
    initialize_directories()

    parser = argparse.ArgumentParser(description="Bridge Research to Production Skills")
    parser.add_argument("--source", required=True, help="Source report or synthesis file")
    parser.add_argument("--skill", required=True, help="Name of the skill to extract")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just show evaluation")
    
    args = parser.parse_args()
    
    logger.info(f"🌉 Bridging '{args.skill}' from {args.source}...")
    
    context = extract_skill_data(args.source, args.skill)
    if not context:
        logger.error("Could not find skill context in source.")
        return

    logger.info("🧠 Evaluating utility...")
    evaluation = evaluate_utility(args.skill, context)
    if evaluation is None:
        logger.error("Evaluation failed.")
        return

    logger.info("\n--- EVALUATION ---")
    logger.info(evaluation)
    logger.info("------------------\n")
    
    decision = parse_decision(evaluation)
    if decision == "REJECT" and not args.dry_run:
        logger.warning("🛑 Skill rejected by evaluation. Use --force to override (not implemented).")
        return
    
    if decision == "UNKNOWN" and not args.dry_run:
        logger.error("⚠️ Could not determine decision from evaluation. Aborting for safety.")
        return

    if args.dry_run:
        logger.info("✨ Dry run complete. No files written.")
        return

    logger.info("📝 Generating production files...")
    templates = generate_templates(args.skill, evaluation, context)
    
    if not templates:
        logger.error("Failed to generate templates.")
        return

    # Strict JSON Validation Gate
    is_valid, error_msg = validate_json_data(templates)
    if not is_valid:
        logger.error(error_msg)
        return

    # Write skill to project-local skills/ directory
    slug = safe_slug(args.skill)
    skill_path = (LOCAL_SKILLS_PATH / f"{slug}.md").resolve()

    # Traversal Guard
    skills_root = LOCAL_SKILLS_PATH.resolve()
    if not skill_path.is_relative_to(skills_root):
        logger.error(f"Potential Path Traversal detected: {skill_path}")
        return
    LOCAL_SKILLS_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"Verified directory {LOCAL_SKILLS_PATH}")

    # Atomic Write
    atomic_write(skill_path, templates["SKILL_MD"])

    logger.info(f"Skill '{args.skill}' written to {skill_path}")

if __name__ == "__main__":
    main()
