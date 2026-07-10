"""Static-analysis guard: every CSS custom property referenced in ride.css
must be defined in the same file.

Pure-function exception per CLAUDE.md TDD rule: this reads the real stylesheet
(the only richer data form than a synthetic string) and analyses it with regex,
so no corpus fixture applies.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STYLESHEET = REPO_ROOT / "static" / "css" / "ride.css"

# `--ride-foo:` at a declaration position (definition).
DEFINITION = re.compile(r"(--ride-[a-z0-9-]+)\s*:")
# `var(--ride-foo` reference; an optional literal fallback may follow.
REFERENCE = re.compile(r"var\(\s*(--ride-[a-z0-9-]+)")


def test_every_referenced_ride_token_is_defined():
    css = STYLESHEET.read_text(encoding="utf-8")
    defined = set(DEFINITION.findall(css))
    referenced = set(REFERENCE.findall(css))
    undefined = sorted(referenced - defined)
    assert not undefined, f"undefined --ride tokens referenced: {undefined}"
