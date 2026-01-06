import os
import sys
import argparse
import requests
import re

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-r1:14b"

def heal_code(file_path, error_content):
    """
    Sends the code and the error to Ollama to generate a 'healed' version.
    """
    if not os.path.exists(file_path):
        print(f"[!] File not found: {file_path}")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        original_code = f.read()

    print(f"[*] Analyzing error and healing {file_path}...")

    prompt = f"""
You are a "Skill Healer," a senior software engineer specialized in self-correcting AI agents. 
Your task is to analyze a piece of code and a corresponding error log, then provide a fixed version of the code.

### 🛠 Original Code ({file_path}):
```python
{original_code}
```

### ❌ Error Log:
```text
{error_content}
```

### 🧠 Instructions:
1. Identify the root cause of the error.
2. Provide the ENTIRE corrected code block.
3. Ensure the fix is deterministic and robust (following the "Code Before Prompts" philosophy).
4. Do not include any explanations outside of the code block.

Return ONLY the corrected code.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2, # Low temperature for precise code fixes
            "num_ctx": 32768
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180) # Longer timeout for reasoning
        response.raise_for_status()
        
        full_response = response.json().get("response", "")
        
        # Strip <think> tags if present
        clean_code = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
        
        # Extract code from markdown blocks if the model wrapped it
        code_match = re.search(r'```(?:python)?\n(.*?)\n```', clean_code, re.DOTALL)
        if code_match:
            clean_code = code_match.group(1)
            
        return clean_code
    except Exception as e:
        print(f"[!] Ollama error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="The Skill Healer: Convert errors into code fixes.")
    parser.add_argument("--skill", required=True, help="Path to the script or skill file to fix.")
    parser.add_argument("--error", required=True, help="The error message or path to an error log file.")
    
    args = parser.parse_args()

    # Handle error input (string or file)
    error_content = args.error
    if os.path.exists(args.error):
        with open(args.error, 'r', encoding='utf-8') as f:
            error_content = f.read()

    healed_code = heal_code(args.skill, error_content)

    if healed_code:
        # Create a backup before overwriting
        backup_path = f"{args.skill}.bak"
        with open(backup_path, 'w', encoding='utf-8') as f:
            with open(args.skill, 'r', encoding='utf-8') as original:
                f.write(original.read())
        
        with open(args.skill, 'w', encoding='utf-8') as f:
            f.write(healed_code)
            
        print(f"[+] Successfully healed {args.skill}!")
        print(f"[*] Backup created at {backup_path}")
    else:
        print("[!] Failed to heal the skill.")

if __name__ == "__main__":
    main()

