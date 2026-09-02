"""What `Board.begin()` does to the bus, against a golden file.

This is the centre of the suite. The pin table and the bring-up order are
the product, and a host run makes both observable: host-arduino-core
announces every `pinMode` / `digitalWrite` and every I2C transaction, so
the trace is produced without a line of instrumentation inside the
library.

Goldens are frozen. They are not re-derived from M5GFX on every run -
see docs/TEST_PLAN.ja.md 1. Regenerate deliberately with
`--update-golden` and read the diff before committing it.
"""

from pathlib import Path

import pytest

SKETCH = Path(__file__).parent
GOLDEN = SKETCH / "golden"

# One entry per board that has a golden. The header name is what gets
# handed to the build; the golden is named after the board id.
BOARDS = ["AtomLite"]


def pytest_generate_tests(metafunc):
    if "board" in metafunc.fixturenames:
        metafunc.parametrize("board", BOARDS, indirect=False)


# The board is exported to the environment by the root conftest, before
# any fixture runs - the `dut` fixture is what starts the build, so an
# autouse fixture here would be too late.


def test_begin(dut, board, request):
    dut.expect("TEST start", timeout=60)
    dut.expect("TEST done", timeout=60)

    trace = (SKETCH / "output" / "trace.txt").read_text(encoding="utf-8")
    golden = GOLDEN / f"{board}.txt"

    if request.config.getoption("--update-golden"):
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(trace, encoding="utf-8")
        pytest.skip(f"golden updated: {golden.name}")

    assert golden.exists(), (
        f"no golden for {board}. Run with --update-golden, then read the "
        f"diff against M5GFX before committing it."
    )
    assert trace == golden.read_text(encoding="utf-8"), (
        f"{board}: begin() no longer matches its frozen golden"
    )
