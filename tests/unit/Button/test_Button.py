"""The button state machine.

Every expectation lives in the sketch, next to the stimulus that produces
it. Nothing here is board specific, which is why it sits outside `begin/`
and is not generated.
"""

from tinym5_check import check_unit


def test_button(dut):
    check_unit(dut, "Button")
