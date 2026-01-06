import os
import sys
import argparse
import json
import re
from pathlib import Path
from scripts.config import GLOBAL_LIBRARY_PATH, run_ollama_command, validate_json_data, initialize_directories, check_environment

def call_ollama(prompt):
    """Standardized Ollama CLI call."""
    print(f"Calling Ollama with prompt: {prompt[:100]}...")
    try:
        return run_ollama_command(prompt)
    except Exception as e:
        print(f"❌ Error calling Ollama: {str(e)}")
        return None

def extract_skill_data(source_path, skill_name):
    """Read the source file and extract context about the skill."""
    if not os.path.exists(source_path):
        return None
    
    with open(source_path, "r") as f:
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

def evaluate_utility(skill_name, context):
    """Use Ollama to evaluate if this skill is worth promoting."""
    prompt = f"""
    You are an expert AI orchestrator. Evaluate if the following potential "Skill" is worth adding to a permanent Global Skills Library.
    
    Skill Name: {skill_name}
    
    Context from research:
    {context}
    
    Evaluation Criteria:
    1. Is this a repeating pattern in high-value work?
    2. Does it solve a known friction point in current projects?
    3. Is it "production-ready" or just a vague idea?
    4. Does it provide a "better way" than current habits?
    
    Respond with:
    1. DECISION: [PROMOTE] or [REJECT]
    2. REASONING: (A few sentences explaining why, referencing the criteria above)
    3. RECOMMENDED_TYPE: (e.g., Development, Analysis, Security)
    4. RECOMMENDED_COMPLEXITY: (Low, Medium, High)
    """
    
    return call_ollama(prompt)

def generate_templates(skill_name, evaluation, context):
    """Use Ollama to generate the actual file contents based on the evaluation and context."""
    prompt = f"""
    Generate three files for a new skill called "{skill_name}".
    Use the following evaluation and research context to populate the details.
    
    Evaluation:
    {evaluation}
    
    Research Context:
    {context}
    
    FILES TO GENERATE:
    
    1. SKILL.md (Claude Adapter)
    Follow this format:
    # Claude Skill: [Name]
    > Adapter for: playbooks/[slug]/
    > Version: 1.0.0
    ## Skill Overview
    ... (What it does, when to activate, activation prompt)
    
    2. RULE.md (Cursor Rule)
    Follow this format:
    # Cursor Rule: [Name]
    ## Quick Reference
    ... (Playbook location, how to use in Cursor, progress updates)
    
    3. README.md (Canonical Playbook)
    Follow this format:
    # [Name] Playbook
    ## What This Skill Does
    ## The Process (Step by step)
    ## Best Practices
    
    Output the result as a raw JSON object with keys "SKILL_MD", "RULE_MD", and "README_MD". 
    Do NOT use markdown code blocks like ```json ... ```. Just output the raw JSON string starting with {{ and ending with }}.
    Ensure all three fields contain the full content of the files as described.
    """
    
    response = call_ollama(prompt)
    if response is None:
        return None
    
    # DeepSeek-R1 often puts the JSON after a <think> block (though we strip it now)
    # We want to find the first '{' and the last '}'
    start_idx = response.find('{')
    end_idx = response.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        json_str = response[start_idx:end_idx+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON Decode Error: {str(e)}")
            print(f"Attempted to parse: {json_str[:200]}...")
            return None
    
    print(f"❌ Could not find JSON object in response: {response[:200]}...")
    return None

def parse_decision(evaluation_text):
    """Regex pattern to match DECISION: [PROMOTE] or [REJECT] at the start of a line."""
    if evaluation_text is None:
        return "UNKNOWN"
    # Strict regex: ^DECISION:\s*\[(PROMOTE|REJECT)\]
    decision_pattern = re.compile(r'^DECISION:\s*\[(PROMOTE|REJECT)\]', re.IGNORECASE | re.MULTILINE)
    
    match = decision_pattern.search(evaluation_text)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"

def main():
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
    
    print(f"🌉 Bridging '{args.skill}' from {args.source}...")
    
    context = extract_skill_data(args.source, args.skill)
    if not context:
        print("❌ Could not find skill context in source.")
        return

    print("🧠 Evaluating utility with DeepSeek-R1...")
    evaluation = evaluate_utility(args.skill, context)
    if evaluation is None:
        print("❌ Ollama call failed during evaluation.")
        return

    print("\n--- EVALUATION ---")
    print(evaluation)
    print("------------------\n")
    
    decision = parse_decision(evaluation)
    if decision == "REJECT" and not args.dry_run:
        print("🛑 Skill rejected by evaluation. Use --force to override (not implemented).")
        return
    
    if decision == "UNKNOWN" and not args.dry_run:
        print("⚠️ Could not determine decision from evaluation. Aborting for safety.")
        return

    if args.dry_run:
        print("✨ Dry run complete. No files written.")
        return

    print("📝 Generating production files...")
    templates = generate_templates(args.skill, evaluation, context)
    
    if not templates:
        print("❌ Failed to generate templates.")
        return

    # Strict JSON Validation Gate
    is_valid, error_msg = validate_json_data(templates)
    if not is_valid:
        print(f"❌ {error_msg}")
        return

    # Prepare paths
    slug = args.skill.lower().replace(" ", "-")
    skill_dir = GLOBAL_LIBRARY_PATH / "claude-skills" / slug
    rule_dir = GLOBAL_LIBRARY_PATH / "cursor-rules" / slug
    playbook_dir = GLOBAL_LIBRARY_PATH / "playbooks" / slug
    
    # Create directories
    for d in [skill_dir, rule_dir, playbook_dir]:
        d.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created {d}")

    # Write files
    with open(skill_dir / "SKILL.md", "w") as f:
        f.write(templates["SKILL_MD"])
    with open(rule_dir / "RULE.md", "w") as f:
        f.write(templates["RULE_MD"])
    with open(playbook_dir / "README.md", "w") as f:
        f.write(templates["README_MD"])
    
    print(f"✅ Skill '{args.skill}' successfully promoted to production library!")

if __name__ == "__main__":
    main()
