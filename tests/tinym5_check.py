"""Shared body of the begin() golden test.

One directory per board. The plugin's `dut` fixture is module scoped and
the build path follows the sketch directory, so sharing one sketch across
boards makes the second module attach to the first one's still-running
process and read a trace that was never written.

`tools/gen_boards.py` generates the sketch, the profile and the test from
the catalogue, so adding a board cannot forget to add its test.
"""

from pathlib import Path

import pytest

BEGIN = Path(__file__).parent / "begin"
GOLDEN = BEGIN / "golden"


def check_begin(dut, request, board):
    # Board-qualified on purpose: the expect buffer is shared across the
    # session, so a bare "TEST done" matches the previous board's run and
    # the trace read below has not been written yet.
    dut.expect(f"TEST start {board}", timeout=60)
    dut.expect(f"TEST done {board}", timeout=60)

    trace = (BEGIN / board / "output" / "trace.txt").read_text(encoding="utf-8")
    golden = GOLDEN / f"{board}.txt"

    if request.config.getoption("--update-golden"):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(trace, encoding="utf-8")
        pytest.skip(f"golden updated: {golden.name}")

    assert golden.exists(), (
        f"no golden for {board}. Run with --update-golden, then read the diff "
        f"against M5GFX before committing it."
    )
    assert trace == golden.read_text(encoding="utf-8"), (
        f"{board}: begin() no longer matches its frozen golden"
    )
