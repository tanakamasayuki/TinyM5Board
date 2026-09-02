"""Shared hooks for the TinyM5Board tests.

Clears `<sketch_dir>/output/` before every test. A trace left over from a
previous run would otherwise make a failure look like a pass.

Careful: this rmtree's any directory named `output`, unconditionally.
"""

import os
import shutil
from pathlib import Path


def pytest_runtest_setup(item):
    output_dir = Path(item.fspath).parent / "output"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # The board under test travels to the compiler as an environment
    # variable (see begin/build_config.toml). It has to be in place before
    # any fixture runs, because the `dut` fixture is what triggers the
    # build - setting it from an autouse fixture is already too late.
    board = getattr(item, "callspec", None)
    board = board.params.get("board") if board else None
    if board:
        os.environ["TINYM5_TEST_BOARD_HEADER"] = f"TinyM5Board{board}.h"


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="rewrite the begin() goldens from this run instead of comparing",
    )
