"""Taking the TF card off the panel's SPI bus.

The begin() goldens cover the branch a silent bus produces. This one puts
a card on the other end, so the branch where it is already in SPI mode -
and must not be reset - gets exercised too.
"""

from tinym5_check import check_unit


def test_sd_spi_mode(dut):
    check_unit(dut, "SdSpiMode")
