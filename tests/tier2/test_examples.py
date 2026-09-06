"""Tier 2 - the examples, built by the core that ships them.

The examples are the documentation (D20): one per feature, with the board
as a single line to change. That only holds if they build, and Tier 0
does not cover them - it builds a generated sketch per board, not the
sketches a reader will actually copy.

Each example carries its own `sketch.yaml` naming the board it defaults
to and pinning the core (D29), so this only has to run the build and
report what came back. Nothing runs.

The other half of Tier 2 in TEST_PLAN §4 - a sketch that stops with
`#error` on the boards it cannot serve - has nothing to check yet: every
example here reaches for missing hardware through `#if` and prints that
the board does not have it, which is the better shape when it fits.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = sorted(p.parent for p in (REPO / "examples").glob("*/sketch.yaml"))

pytestmark = pytest.mark.skipif(
    shutil.which("arduino-cli") is None, reason="arduino-cli is not on PATH")


def test_examples_are_present():
    assert EXAMPLES, "no examples with a sketch.yaml"


@pytest.mark.parametrize("sketch", EXAMPLES, ids=lambda p: p.name)
def test_example_compiles(sketch):
    r = subprocess.run(["arduino-cli", "compile"], cwd=sketch,
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, f"{sketch.name}:\n{r.stdout}\n{r.stderr}"
