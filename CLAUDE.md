# Claude Instructions for analyze-youtube-videos

## Project Context
`analyze-youtube-videos` is a local-first autonomous agent system for analyzing YouTube content and extracting strategic insights. It follows the Erik Project Scaffolding patterns.

## Core Standards
- **YAML First**: Use YAML as the source of truth for indices (`library/index.yaml`) and configurations.
- **Local First**: Prioritize Ollama (DeepSeek-R1) for all logic and analysis.
- **Warden Pattern**: All scripts must pass the `check_environment()` guard in `scripts/config.py`.
- **Atomic Writes**: Use the temp-file-and-rename pattern for all file modifications.
- **Security**: Always use `safe_slug()` for user-provided strings and implement path traversal guards.

## Workflow
1. Use `librarian.py` to ingest new videos.
2. Use `synthesize.py` to generate topic-level strategies.
3. Use `bridge.py` to promote high-value patterns to the global skills library.

