"""Guard librarian.py's module docstring against CLI drift.

build_parser() uses the module docstring as its description, so these tests pin
the two to each other: every parser option must be documented, every flag-like
token in the docstring must be a real parser option, and --help must open with
the docstring's first line.
"""

import re
from pathlib import Path

from scripts import librarian

_DOC_FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")

# The docstring's invocation examples use uv's `uv run --with <pkg>` prefix.
# `--with` is uv's dependency flag, not a librarian option, so strip `uv run`
# and every `--with <pkg>` token before drift-checking flag tokens. A regex
# (rather than one fixed prefix) lets the Dependencies section document the
# faster-whisper extra without tripping the drift guard.
_UV_INVOCATION_RE = re.compile(r"uv run|--with\s+\S+")


def _doc_flag_tokens(doc):
    return _DOC_FLAG_RE.findall(_UV_INVOCATION_RE.sub("", doc))


def _parser_option_strings():
    return {
        option
        for action in librarian.build_parser()._actions
        for option in action.option_strings
    }


def test_every_parser_option_appears_in_module_docstring():
    options = {
        option
        for action in librarian.build_parser()._actions
        for option in action.option_strings
        if option not in ("-h", "--help")
    }
    assert options, "expected CLI options beyond --help"
    for option in sorted(options):
        assert option in librarian.__doc__, (
            f"{option} is defined by build_parser() but missing from librarian.__doc__"
        )


def test_every_documented_flag_is_a_real_parser_option():
    real = _parser_option_strings()
    tokens = _doc_flag_tokens(librarian.__doc__)
    assert tokens, "expected --flag tokens in librarian.__doc__"
    for token in tokens:
        assert token in real, (
            f"{token} appears in librarian.__doc__ but is not a build_parser() option"
        )


def test_help_contains_docstring_first_line():
    first_line = librarian.__doc__.strip().splitlines()[0].strip()
    assert first_line, "module docstring must have a non-empty first line"
    assert first_line in librarian.build_parser().format_help()


def test_testing_command_pins_match_requirements():
    """Every pkg==version pin in README's Testing command must exist in requirements.txt."""
    readme = Path("README.md").read_text(encoding="utf-8")
    testing_section = readme.split("## Testing", 1)[1]
    block = testing_section.split("```", 2)[1]
    pins = re.findall(r"[A-Za-z0-9_.\-]+==[A-Za-z0-9_.\-+]+", block)
    assert pins, "expected pkg==version pins in the README Testing command"

    requirements = {}
    for line in Path("requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "==" in line and not line.startswith("#"):
            name, _, version = line.partition("==")
            requirements[name.strip().casefold()] = version.strip()

    for pin in pins:
        name, version = pin.split("==")
        assert name.casefold() in requirements, (
            f"{pin} from the README Testing command is missing from requirements.txt"
        )
        assert requirements[name.casefold()] == version, (
            f"{pin} from the README Testing command does not match requirements.txt"
        )
