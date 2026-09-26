"""Guard librarian.py's module docstring against CLI drift.

build_parser() uses the module docstring as its description, so these tests pin
the two to each other: every parser option must be documented, every flag-like
token in the docstring must be a real parser option, and --help must open with
the docstring's first line.
"""

import re

from scripts import librarian

_DOC_FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")

# The docstring's invocation examples are required to use the prefix
# `uv run --with pyyaml`. `--with` is uv's dependency flag, not a librarian
# option, so strip exactly that prefix before drift-checking flag tokens.
_INVOCATION_PREFIX = "uv run --with pyyaml"


def _doc_flag_tokens(doc):
    return _DOC_FLAG_RE.findall(doc.replace(_INVOCATION_PREFIX, "uv run"))


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
