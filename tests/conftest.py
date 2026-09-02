"""Shared hooks for the TinyM5Board tests.

Clears every `output/` directory once, at the start of the session. A
trace left over from a previous run would otherwise make a failure look
like a pass.

It is deliberately not done per test. `pytest_runtest_setup` is also
where the embedded plugin builds and starts the sketch, and hook
ordering between the two is not something to rely on: clearing the
directory after the sketch has already written its trace deletes the
very file the test is about to read.

Careful: this rmtree's any directory named `output` under tests/.
"""

import shutil
from pathlib import Path

TESTS = Path(__file__).parent


def pytest_sessionstart(session):
    for output_dir in TESTS.rglob("output"):
        if output_dir.is_dir():
            shutil.rmtree(output_dir)


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="rewrite the begin() goldens from this run instead of comparing",
    )
