"""The button state machine.

The sketch checks itself - every expectation is written next to the
stimulus that produces it - so this only has to run it and report what
went wrong. Nothing here is board specific, which is why it sits outside
`begin/` and is not generated.
"""

from pathlib import Path

CHECKS = Path(__file__).parent / "output" / "checks.txt"


def test_button(dut):
    dut.expect("TEST start Button", timeout=60)
    dut.expect("TEST done Button", timeout=60)

    lines = CHECKS.read_text(encoding="utf-8").splitlines()
    failed = [ln for ln in lines if ln.startswith("FAIL")]
    assert not failed, "\n".join(["button state machine:"] + failed)
    assert any(ln.startswith("ok") for ln in lines), "no checks ran"
