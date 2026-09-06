#!/usr/bin/env python3
"""Generate the board catalogue into src/.

    python3 tools/gen_boards.py            # write the headers
    python3 tools/gen_boards.py --check    # fail if anything is out of date

Writes one header per board at the top of `src/`, plus `src/TinyM5Board.h`
(the build-flag entry point) and `src/TinyM5Board/BoardId.h`.

## Why the board headers sit at the top of src/

Measured with arduino-cli 1.5.0: **library resolution only works on a
header directly under `src/`.** A sketch whose only include is
`<TinyM5Board/boards/AtomLite.h>` does not find the library at all, so
that layout would force every sketch to write `<TinyM5Board.h>` as well.
One header at the top of `src/` resolves on its own, and typing
`#include <TinyM5Board` makes the IDE offer every board.

So: **top of `src/` is the entry, `src/TinyM5Board/` is the inside.**

## What an entry carries

Only what a schematic tells you and a datasheet does not. Everything
derivable is derived here rather than typed in:

    kHasInternalI2c   whether i2c_int is set - a Stamp or a Nano has
                      only the Grove port, and that one goes on `Wire`
    kHasExternalI2c   whether i2c_ext is set
    kSharesI2cBus     whether the two I2C pin pairs are the same
    kHasDisplay/...   whether the matching column is set
    Wire1 exists      from `soc`
    button pin mode   from `soc` - GPIO 34-39 on the classic ESP32 are
                      input-only and have no pull resistors

Carrying `kHasBacklight` as a column would let it disagree with
`backlight`. Deriving it means that cannot be written down.

## Data goes in the table, procedure goes in code

Rail bring-up is not tabular. The StickC pokes one AXP192 register; the
StopWatch configures five M5IOE1 pins and pulses two resets. A table that
can express the second one has become a DSL nobody can read - and
M5Unified reached the same conclusion, keeping `_pin_table_*` as data and
the per-board bring-up as a `switch`.

`power_on` is therefore an optional escape hatch holding C++. Most boards
leave it empty because POWER_HOLD, rail enable, LCD reset, buttons and
backlight all fall out of the columns. What goes in it must still name
roles rather than registers - `Axp192::enable(w, Axp192::Ldo2)`, never
`0x12`. That keeps it to a handful of lines.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
TESTS = REPO / "tests"

# --- SoC properties --------------------------------------------------------
#
# Facts about the chip, not the board. Boards name their SoC and these
# follow. `classic` is the original ESP32, whose GPIO 34-39 are input-only.

SOC = {
    "esp32": dict(classic=True, i2c_num=2),
    "esp32s2": dict(classic=False, i2c_num=1),
    "esp32s3": dict(classic=False, i2c_num=2),
    "esp32c3": dict(classic=False, i2c_num=1),
    "esp32c5": dict(classic=False, i2c_num=2),
    "esp32c6": dict(classic=False, i2c_num=2),
    "esp32c61": dict(classic=False, i2c_num=2),
    "esp32h2": dict(classic=False, i2c_num=2),
    "esp32p4": dict(classic=False, i2c_num=3),
}

# --- the catalogue ---------------------------------------------------------
#
# `note` is what a reader needs to recognise their own board. It is not a
# changelog.
#
# i2c_int / i2c_ext are (sda, scl). rgb_led is (pin, count).
# buttons maps a name to a pin, or to (pin, active_low).

# Bring-up that more than one board shares, written once. Upstream shares
# it the same way - several `case` labels falling into one body - and a
# copy per entry is a copy that drifts.

ATOM_CH552_FIX = """\
// The CH552 USB bridge puts 4 V on GPIO 0, which drags the WiFi
// sensitivity down. Driving the pin high from this side biases it to
// 3.3 V and suppresses the overvoltage. (M5Unified.cpp:2299)
pinMode(0, OUTPUT);
digitalWrite(0, HIGH);
"""

# The CoreS3, the CoreS3 SE and the StackChan are one branch upstream, in
# M5GFX and in M5Unified alike. What tells them apart is a camera and a
# servo expander, and neither is a rail or a panel.
CORE_S3_POWER_ON = """\
// Every one of the sixteen expander pins comes up in LED-driver mode, so
// saying "these are GPIOs" is not optional. 1 = input for the direction,
// 1 = plain GPIO for the mode. (M5GFX.cpp, the CoreS3 branch)
Io.setDirections(0b00011000, 0b00001100);
Io.setPushPullP0();
Io.setGpioMode(0xFF, 0xFF);
// P1_0 and P1_1 high: the second is the panel's reset line. The VBUS 5V
// output (P1_7) is left off - see the note above.
Io.setOutputs(0b00000101, 0b00000011);
Io.resetPulse(TinyM5BoardIoExpanderAw9523::Io::P1_1);
// ALDO3 is the camera rail and ALDO4 the TF slot. Upstream enables both
// on all three of these boards, including the SE that has no camera, so
// this is transcribed rather than trimmed.
Power.setLdoEnables(0xBF);
Power.setAldo3Millivolt(3300);
Power.setAldo4Millivolt(3300);
"""


BOARDS = [
    dict(
        id="AtomLite",
        name="M5AtomLite",
        board_id=128,
        family="Atom",
        soc="esp32",
        note="The plain ATOM: no screen, no PMIC, one button and one RGB LED.\n"
             "The ATOM Matrix and ATOM U share this pinout but differ in the\n"
             "LED count, so they are separate entries.",
        i2c_int=(25, 21),
        i2c_ext=(26, 32),
        power_hold=None,
        rgb_led=(27, 1),
        buttons={"A": 39},
        pmic=None,
        backlight=None,
        display=None,
        power_on=ATOM_CH552_FIX,
    ),
    dict(
        id="AtomMatrix",
        name="M5AtomMatrix",
        board_id=141,
        family="Atom",
        soc="esp32",
        note="The ATOM with a 5x5 RGB LED matrix on the front, and the front\n"
             "panel itself as the button. The pinout is the ATOM Lite's; the\n"
             "LED count is what differs, and a count is not something a sketch\n"
             "can probe for.",
        i2c_int=(25, 21),
        i2c_ext=(26, 32),
        power_hold=None,
        rgb_led=(27, 25),
        buttons={"A": 39},
        pmic=None,
        backlight=None,
        display=None,
        power_on=ATOM_CH552_FIX,
    ),
    dict(
        id="AtomU",
        name="M5AtomU",
        board_id=130,
        family="Atom",
        soc="esp32",
        note="The ATOM in a USB-A plug, with a microphone. Same pins, same\n"
             "button and the same single LED as the ATOM Lite - the shell and\n"
             "the identity are what differ.",
        i2c_int=(25, 21),
        i2c_ext=(26, 32),
        power_hold=None,
        rgb_led=(27, 1),
        buttons={"A": 39},
        pmic=None,
        backlight=None,
        display=None,
        power_on=ATOM_CH552_FIX,
    ),
    dict(
        id="AtomVoice",
        name="M5AtomVoice",
        board_id=142,
        family="Atom",
        soc="esp32",
        note="The ATOM with a speaker and a microphone. Sold as the ATOM Echo;\n"
             "upstream renamed the identifier and kept board_M5AtomEcho as a\n"
             "deprecated alias for the same id, 142.\n"
             "Audio is a device rather than bring-up, so what this header\n"
             "carries is the ATOM Lite's pinout.",
        i2c_int=(25, 21),
        i2c_ext=(26, 32),
        power_hold=None,
        rgb_led=(27, 1),
        buttons={"A": 39},
        pmic=None,
        backlight=None,
        display=None,
        power_on=ATOM_CH552_FIX,
    ),
    dict(
        id="AtomS3Lite",
        name="M5AtomS3Lite",
        board_id=137,
        family="Atom",
        soc="esp32s3",
        note="The AtomS3 without the screen: an ESP32-S3 in the ATOM shell,\n"
             "one RGB LED and the front button on GPIO 41.\n"
             "No CH552 here - the S3 speaks USB itself, so the GPIO 0 bias the\n"
             "classic ATOM needs does not apply.",
        i2c_int=(38, 39),
        i2c_ext=(2, 1),
        power_hold=None,
        rgb_led=(35, 1),
        buttons={"A": 41},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="AtomS3U",
        name="M5AtomS3U",
        board_id=138,
        family="Atom",
        soc="esp32s3",
        note="The AtomS3 Lite in a USB-A plug, with a microphone. Same pins\n"
             "and the same button.",
        i2c_int=(38, 39),
        i2c_ext=(2, 1),
        power_hold=None,
        rgb_led=(35, 1),
        buttons={"A": 41},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="TimerCam",
        name="M5TimerCam",
        board_id=132,
        family="Other",
        soc="esp32",
        note="A camera on a battery, with no screen and no buttons.\n"
             "Its divider is 1.513 rather than the usual 2, which is why the\n"
             "ratio is a column and not a constant.",
        i2c_int=(12, 14),
        i2c_ext=(4, 13),
        power_hold=33,
        rgb_led=None,
        buttons={},
        pmic="adc",
        bat_adc=(38, 1513),
        backlight=None,
        display=None,
        power_on="""\
// The status LED comes up lit. Leaving it on would burn current on a
// board that runs from a battery. (M5Unified Power_Class.cpp:612)
pinMode(2, OUTPUT);
digitalWrite(2, LOW);
""",
    ),
    dict(
        id="Capsule",
        name="M5Capsule",
        board_id=139,
        family="Other",
        soc="esp32s3",
        note="A sealed battery-powered capsule with no screen.\n"
             "BtnB is the boot button on GPIO 0.",
        i2c_int=(8, 10),
        i2c_ext=(13, 15),
        power_hold=46,
        rgb_led=(21, 1),
        buttons={"A": 42, "B": 0},
        pmic="adc",
        bat_adc=(6, 2000),
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="AirQ",
        name="M5AirQ",
        board_id=15,
        family="Other",
        soc="esp32s3",
        note="An air quality meter behind a 200x200 electrophoretic panel.\n"
             "Two controllers have shipped under this name - a GDEW0154D67 and\n"
             "a GDEW0154M09 - but they share the pins and the geometry, so the\n"
             "difference is the driver's to find and not this header's to\n"
             "carry.\n"
             "The sensors on the internal bus are devices; what this carries is\n"
             "the panel, the two buttons and the battery.",
        i2c_int=(11, 12),
        i2c_ext=(13, 15),
        power_hold=46,
        rgb_led=(21, 1),
        buttons={"A": 0, "B": 8},
        pmic="adc",
        bat_adc=(14, 2000),
        backlight=None,
        display=dict(bus="spi", mosi=6, miso=-1, sclk=5, dc=3, cs=4, rst=2,
                     busy=1,
                     freq_write=40000000, freq_read=16000000,
                     w=200, h=200, ox=0, oy=0, rotation=0, invert=False,
                     three_wire=True),
        power_on="",
    ),
    dict(
        id="Cardputer",
        name="M5Cardputer",
        board_id=14,
        family="Other",
        soc="esp32s3",
        note="A keyboard with a screen. No internal I2C bus - the Grove port is\n"
             "the only one - and the card is on a bus of its own, so nothing\n"
             "has to be quietened before the panel.\n"
             "The keyboard is a matrix behind a 74HC138 on GPIO 8/9 and read\n"
             "through GPIO 5/6/7. That is a device driver's job; what this\n"
             "header carries is the panel, the button and the battery.",
        i2c_int=None,
        i2c_ext=(2, 1),
        power_hold=None,
        rgb_led=(21, 1),
        buttons={"A": 0},
        pmic="adc",
        bat_adc=(10, 2000),
        backlight=("pwm", 38, 256, 16),
        display=dict(bus="spi", mosi=35, miso=-1, sclk=36, dc=34, cs=37, rst=33,
                     freq_write=40000000, freq_read=16000000,
                     w=135, h=240, ox=52, oy=40, rotation=0, invert=True,
                     three_wire=True),
        power_on="",
    ),
    dict(
        id="CardputerADV",
        name="M5CardputerADV",
        board_id=24,
        family="Other",
        soc="esp32s3",
        note="The Cardputer with an internal I2C bus of its own on GPIO 8/9,\n"
             "where the plain one has only the Grove port. Same panel, same\n"
             "button, same battery; upstream tells the two apart by probing\n"
             "those pins.",
        i2c_int=(8, 9),
        i2c_ext=(2, 1),
        power_hold=None,
        rgb_led=(21, 1),
        buttons={"A": 0},
        pmic="adc",
        bat_adc=(10, 2000),
        backlight=("pwm", 38, 256, 16),
        display=dict(bus="spi", mosi=35, miso=-1, sclk=36, dc=34, cs=37, rst=33,
                     freq_write=40000000, freq_read=16000000,
                     w=135, h=240, ox=52, oy=40, rotation=0, invert=True,
                     three_wire=True),
        power_on="",
    ),
    dict(
        id="VAMeter",
        name="M5VAMeter",
        board_id=16,
        family="Other",
        soc="esp32s3",
        note="A volt and current meter with a square screen. Same panel bus as\n"
             "the Cardputer - upstream tells the two apart by probing GPIO 5\n"
             "and 6 - but 240x240 rather than 135x240, and a different\n"
             "backlight curve.\n"
             "No battery: it runs from what it is measuring. The INA-style\n"
             "sensors on the internal bus are devices, not bring-up.",
        i2c_int=(5, 6),
        i2c_ext=(8, 9),
        power_hold=None,
        rgb_led=None,
        buttons={"A": 2, "B": 0},
        pmic=None,
        backlight=("pwm", 38, 512, 64),
        display=dict(bus="spi", mosi=35, miso=-1, sclk=36, dc=34, cs=37, rst=33,
                     freq_write=40000000, freq_read=16000000,
                     w=240, h=240, ox=0, oy=0, rotation=0, invert=True,
                     three_wire=True),
        power_on="",
    ),
    dict(
        id="NessoN1",
        name="ArduinoNessoN1",
        board_id=23,
        family="Other",
        soc="esp32c6",
        note="A LoRa handheld, and the first board here with two expanders.\n"
             "One holds the buttons and the radio's control lines; the other\n"
             "holds the panel's reset, the backlight and the system rails, so\n"
             "both are bring-up rather than devices.\n"
             "Its Grove port is the internal bus - one set of pins, level\n"
             "shifted - so kSharesI2cBus is true and only Wire is opened.\n"
             "Power is a pair too: an AW32001 charger with a BQ27220 gauge\n"
             "beside it, because neither answers both questions.",
        i2c_int=(10, 8),
        i2c_ext=(10, 8),
        power_hold=None,
        rgb_led=None,
        buttons={"A": ("io", "P0"), "B": ("io", "P1")},
        pmic="aw32001",
        io_expander=("pi4io", "pi4io"),
        backlight=("pi4io_switch", "Io2", "P6", False),
        display=dict(bus="spi", mosi=21, miso=22, sclk=20, dc=16, cs=17, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=135, h=240, ox=52, oy=40, rotation=0, invert=True,
                     three_wire=True),
        power_on="""\
// The first expander (0x43) is the radio's and the buttons'. P0 and P1
// are the two front buttons, P2-P4 are unused, P5 the LNA enable, P6 the
// RF switch and P7 the LoRa module's reset, which is released here.
// (M5GFX.cpp and M5Unified Power_Class.cpp agree register for register.)
Io.enableInput(TinyM5BoardIoExpanderPi4io::Io::P0);
Io.enableInput(TinyM5BoardIoExpanderPi4io::Io::P1);
Io.setPullNone(TinyM5BoardIoExpanderPi4io::Io::P2);
Io.setPullNone(TinyM5BoardIoExpanderPi4io::Io::P3);
Io.setPullNone(TinyM5BoardIoExpanderPi4io::Io::P4);
Io.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P5, false);
Io.setPullNone(TinyM5BoardIoExpanderPi4io::Io::P5);
Io.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P6, false, false);
Io.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P7, true, false);
// Only the two buttons may pull the interrupt line. Nothing here waits
// on it - the buttons are polled - but the board comes up with this mask
// and changing it is not this library's decision to make.
Io.setInputDefault(0b00000011);
Io.setInterruptMask(0b11111100);
// The second expander (0x44) is the system's. P0 switches the whole
// board off and stays low, P1 is the panel's reset, P2 the external 5 V,
// P6 the backlight and P7 the status LED, which is off when high.
Io2.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P0, false);
Io2.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P1, false);
Io2.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P2, false);
Io2.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P6, false);
Io2.enableOutput(TinyM5BoardIoExpanderPi4io::Io::P7, true, false);
// P3 and P4 are not connected and P5 senses VIN. Upstream pulls all
// three down rather than leaving them floating, and so does this.
//
// Upstream also takes P5 out of high impedance. That would enable the
// driver on a pin the board reads, so it is left as the chip's reset
// leaves it - the one place here that does not follow M5GFX register
// for register.
Io2.setPullDown(TinyM5BoardIoExpanderPi4io::Io::P3);
Io2.setPullDown(TinyM5BoardIoExpanderPi4io::Io::P4);
Io2.setPullDown(TinyM5BoardIoExpanderPi4io::Io::P5);
// The panel's reset is on that expander rather than a pin, so the pulse
// happens here instead of through TinyM5::resetPulse().
Io2.resetPulse(TinyM5BoardIoExpanderPi4io::Io::P1);
""",
    ),
    dict(
        id="Dial",
        name="M5Dial",
        board_id=12,
        family="Other",
        soc="esp32s3",
        note="A knob with a round screen. The GC9A01 has no MISO wired, so\n"
             "nothing reads back from it, and the panel is the only thing on\n"
             "that bus.\n"
             "POWER_HOLD but no battery reporting: M5Unified gives this board\n"
             "no ADC channel, so there is no Power here to ask.\n"
             "The encoder, the RFID reader and the touch layer are devices;\n"
             "what this header carries is the pinout they sit on.",
        i2c_int=(11, 12),
        i2c_ext=(13, 15),
        power_hold=46,
        rgb_led=(21, 1),
        buttons={"A": 42, "B": 0},
        pmic=None,
        backlight=("pwm", 9, 44100, 0),
        display=dict(bus="spi", mosi=5, miso=-1, sclk=6, dc=4, cs=7, rst=8,
                     freq_write=80000000, freq_read=16000000,
                     w=240, h=240, ox=0, oy=0, rotation=0, invert=True,
                     three_wire=True),
        power_on="",
    ),
    dict(
        id="DinMeter",
        name="M5DinMeter",
        board_id=13,
        family="Other",
        soc="esp32s3",
        note="The Dial's pinout on a DIN rail, with an ST7789 in place of the\n"
             "round panel: same bus, same pins, different geometry and a\n"
             "different backlight curve.\n"
             "Unlike the Dial this one reports a battery, through the ADC on\n"
             "GPIO 10.",
        i2c_int=(11, 12),
        i2c_ext=(13, 15),
        power_hold=46,
        rgb_led=(21, 1),
        buttons={"A": 42, "B": 0},
        pmic="adc",
        bat_adc=(10, 2000),
        backlight=("pwm", 9, 256, 16),
        display=dict(bus="spi", mosi=5, miso=-1, sclk=6, dc=4, cs=7, rst=8,
                     freq_write=40000000, freq_read=16000000,
                     w=135, h=240, ox=52, oy=40, rotation=2, invert=True,
                     three_wire=True),
        power_on="",
    ),
    dict(
        id="NanoC6",
        name="M5NanoC6",
        board_id=140,
        family="Other",
        soc="esp32c6",
        note="An ESP32-C6 with a USB-A plug. Only the Grove port, so that is\n"
             "what Wire opens.\n"
             "The blue status LED on GPIO 7 is a device rather than a rail -\n"
             "M5Unified drives it through setLed() - so bring-up leaves it\n"
             "alone. The RGB LED here is the one on GPIO 20.",
        i2c_int=None,
        i2c_ext=(2, 1),
        power_hold=None,
        rgb_led=(20, 1),
        buttons={"A": 9},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="NanoH2",
        name="M5NanoH2",
        board_id=151,
        family="Other",
        soc="esp32h2",
        note="The NanoC6's ESP32-H2 twin: same shape, same button, and the\n"
             "RGB LED on GPIO 11 instead of 20.",
        i2c_int=None,
        i2c_ext=(2, 1),
        power_hold=None,
        rgb_led=(11, 1),
        buttons={"A": 9},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="StickCPlus2",
        name="M5StickC Plus2",
        board_id=17,
        family="Stick",
        soc="esp32",
        note="The Stick without a PMIC. POWER_HOLD on GPIO 4 is what keeps it\n"
             "alive: let go of the power button before that pin is high and the\n"
             "board switches itself off.\n"
             "The pinout moved from the StickC Plus - DC is 14 (was 23) and RST\n"
             "is 12 (was 18).",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        power_hold=4,
        rgb_led=None,
        buttons={"A": 37, "B": 39, "Pwr": 35},
        pmic="adc",
        bat_adc=(38, 2000),
        backlight=("pwm", 27, 256, 40),
        display=dict(bus="spi", mosi=15, miso=-1, sclk=13, dc=14, cs=5, rst=12,
                     freq_write=40000000, freq_read=15000000,
                     w=135, h=240, ox=52, oy=40, invert=True),
        power_on="",
    ),
    dict(
        id="StickC",
        name="M5StickC",
        board_id=6,
        family="Stick",
        soc="esp32",
        note="The original Stick. Without the AXP192 rails the screen stays\n"
             "black however correct the SPI wiring is - the single most common\n"
             "way to get stuck on this board.\n"
             "Its panel wants a gamma command after init (CMD_GAMMASET 0x08)\n"
             "that a graphics library has to send; this library does not drive\n"
             "panels.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        rgb_led=None,
        buttons={"A": 37, "B": 39, "Pwr": "pek"},
        pmic="axp192",
        rails=("dcdc1", "ldo2", "ldo3", "exten"),
        backlight=("axp192_ldo2",),
        display=dict(bus="spi", mosi=15, miso=14, sclk=13, dc=23, cs=5, rst=18,
                     freq_write=27000000, freq_read=14000000,
                     w=80, h=160, ox=26, oy=1, rotation=2, invert=True,
                     three_wire=True),
    ),
    dict(
        id="StickCPlus",
        name="M5StickC Plus",
        board_id=13,
        family="Stick",
        soc="esp32",
        note="Same board as the StickC as far as power and pins go - only the\n"
             "glass changed, from an ST7735S to a bigger ST7789.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        rgb_led=None,
        buttons={"A": 37, "B": 39, "Pwr": "pek"},
        pmic="axp192",
        rails=("dcdc1", "ldo2", "ldo3", "exten"),
        backlight=("axp192_ldo2",),
        display=dict(bus="spi", mosi=15, miso=14, sclk=13, dc=23, cs=5, rst=18,
                     freq_write=40000000, freq_read=15000000,
                     w=135, h=240, ox=52, oy=40, invert=True,
                     three_wire=True),
    ),
    dict(
        id="Station",
        name="M5Station",
        board_id=9,
        family="Other",
        soc="esp32",
        note="A DIN-rail controller with the StickC Plus's screen turned\n"
             "sideways. AXP192 like the Stick, but the panel reset is a real\n"
             "GPIO here rather than a chip pin.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        rgb_led=(4, 1),
        buttons={"A": 37, "B": 38, "C": 39, "Pwr": "pek"},
        pmic="axp192",
        rails=("ldo2",),
        backlight=("axp192_ldo3",),
        display=dict(bus="spi", mosi=23, miso=-1, sclk=18, dc=19, cs=5, rst=15,
                     freq_write=40000000, freq_read=15000000,
                     w=135, h=240, ox=52, oy=40, rotation=1, invert=True,
                     three_wire=True),
    ),
    dict(
        id="Tough",
        name="M5Tough",
        board_id=8,
        family="Core",
        soc="esp32",
        note="A sealed Core2. Nothing about the screen is a pin: LDO2 feeds it,\n"
             "the chip's IO4 resets it and LDO3 dims it, so begin() has to talk\n"
             "to the AXP192 before there is anything to draw on.\n"
             "Its buttons are touch zones, not GPIOs, so only the power key is\n"
             "here. The SD card shares the LCD's SPI bus, so begin() puts the\n"
             "card into SPI mode before anything reads the panel.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        buttons={"Pwr": "pek"},
        pmic="axp192",
        rails=("ldo2",),
        rail_mv=dict(ldo2=3300),  # LCD power
        backlight=("axp192_ldo3",),
        display=dict(bus="spi", mosi=23, miso=38, sclk=18, dc=15, cs=5, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=320, h=240, ox=0, oy=0, rotation=3, invert=True,
                     three_wire=True),
        power_on="""\
// Nothing here is a pin. IO4 is the panel's reset line and IO1 is the
// touch controller's, so both have to be configured on the chip before
// either can be pulsed. (M5GFX.cpp reg_data_axp192_first)
Power.gpioOutput(TinyM5BoardPowerAxp192::Gpio::Io4);     // LCD RST
Power.gpioOpenDrain(TinyM5BoardPowerAxp192::Gpio::Io1);  // touch RST
Power.gpioResetPulse(TinyM5BoardPowerAxp192::Gpio::Io4);
Power.gpioResetPulse(TinyM5BoardPowerAxp192::Gpio::Io1);
""",
        sd_spi_cs=4,
    ),
    dict(
        id="Core2",
        name="M5StackCore2",
        board_id=2,
        family="Core",
        soc="esp32",
        note="Two different power chips ship under this one name: the v1.0 has\n"
             "an AXP192 and the v1.1 an AXP2101, at the same address, and they\n"
             "feed the panel from different rails. begin() asks which it is\n"
             "rather than guessing - define TINYM5_CORE2_PMIC_AXP2101 (or\n"
             "_AXP192) to skip the question and drop the other driver.\n"
             "Its A/B/C are touch zones, not GPIOs, so only the power key is\n"
             "here. The SD card shares the LCD's SPI bus, so begin() puts the\n"
             "card into SPI mode before anything reads the panel.\n"
             "The panel is an ILI9342C or an ILI9342E depending on the unit,\n"
             "which is read from the touch controller's firmware id - a\n"
             "graphics library's job, so no panel type is reported here.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        rgb_led=(25, 1),
        buttons={"Pwr": "pek"},
        pmic="core2",
        backlight=("core2",),
        display=dict(bus="spi", mosi=23, miso=38, sclk=18, dc=15, cs=5, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=320, h=240, ox=0, oy=0, rotation=3, invert=True,
                     three_wire=True),
        sd_spi_cs=4,
    ),
    dict(
        id="StickS3",
        name="M5StickS3",
        board_id=26,
        family="Stick",
        soc="esp32s3",
        note="The Stick with M5Stack's own PMIC instead of an AXP192. Nothing\n"
             "reaches the panel until the chip's GPIO2 is driven high, and the\n"
             "chip itself stops answering if its idle-sleep timeout was ever\n"
             "set - a setting that survives a power cycle. begin() clears it\n"
             "every time for that reason.",
        i2c_int=(47, 48),
        i2c_ext=(9, 10),
        buttons={"A": 11, "B": 12, "Pwr": "pek"},
        pmic="m5pm1",
        backlight=("pwm", 38, 256, 16),
        display=dict(bus="spi", mosi=39, miso=-1, sclk=40, dc=45, cs=41, rst=21,
                     freq_write=40000000, freq_read=16000000,
                     w=135, h=240, ox=52, oy=40, invert=True,
                     three_wire=True),
        power_on="""\
// GPIO2 switches L3B, which is the panel's supply. Push-pull output,
// driven high, then a moment for the rail to settle before the reset.
// (M5GFX.cpp, the StickS3 branch)
Power.gpioEnableRail(TinyM5BoardPowerM5pm1::Gpio::Io2);
delay(100);
""",
    ),
    dict(
        id="ChainCaptain",
        name="M5ChainCaptain",
        board_id=32,
        family="Core",
        soc="esp32s3",
        note="Two M5Stack chips side by side: an M5PM1 for power and an M5IOE1\n"
             "for everything the panel needs. Its supply is IO12 and its reset\n"
             "is IO1, both on the expander, so no GPIO on the SoC touches the\n"
             "screen at all.\n"
             "Both chips sleep on an idle bus and keep that setting across a\n"
             "power cycle, which is why begin() clears it on each of them.\n"
             "M5GFX also requires OPI-PSRAM here, for its own framebuffer; this\n"
             "library allocates nothing and does not care.",
        i2c_int=(3, 2),
        i2c_ext=(7, 6),
        buttons={"A": 1, "B": 4, "C": 5, "Pwr": "pek"},
        pmic="m5pm1",
        io_expander="m5ioe1",
        backlight=("m5ioe1_pwm", "Ch3", "Io11", 1000),
        display=dict(bus="spi", mosi=16, miso=-1, sclk=15, dc=46, cs=45, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=240, h=240, ox=0, oy=0, rotation=2, invert=True,
                     three_wire=True),
        power_on="""\
// IO12 switches the panel's supply and IO1 is its reset line. Neither is
// a pin on the SoC. (M5GFX.cpp, the ChainCaptain branch)
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io12);
Io.resetPulse(TinyM5BoardIoExpanderM5ioe1::Io::Io1);
// The audio amplifier comes up enabled and pops. Silence it here; making
// it play is the sketch's business, not the board's.
pinMode(21, OUTPUT);
digitalWrite(21, LOW);
""",
    ),
    dict(
        id="CoreS3",
        name="M5StackCoreS3",
        board_id=10,
        family="Core",
        soc="esp32s3",
        note="An AXP2101 for power and an AW9523B for the rest. The panel's\n"
             "reset is P1_1 on the expander, so no pin on the SoC touches it.\n"
             "The CoreS3 SE and the StackChan share this bring-up; they differ\n"
             "only in the camera and a second expander, neither of which is\n"
             "power or display.\n"
             "**GPIO 35 is both the SPI MISO and the panel's D/C.** A graphics\n"
             "library driving this screen has to re-point that pin on every CS\n"
             "transition; this library reports both roles and does not perform\n"
             "that trick - it belongs inside the SPI transaction layer.\n"
             "Its A/B/C are touch zones, not GPIOs. Its card shares the panel's\n"
             "SPI bus, so begin() quietens it first.",
        i2c_int=(12, 11),
        i2c_ext=(2, 1),
        buttons={"Pwr": "pek"},
        pmic="axp2101",
        io_expander="aw9523",
        backlight=("axp2101_dldo1",),
        display=dict(bus="spi", mosi=37, miso=35, sclk=36, dc=35, cs=3, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=320, h=240, ox=0, oy=0, rotation=3, invert=True,
                     three_wire=True),
        power_on=CORE_S3_POWER_ON,
        sd_spi_cs=4,
    ),
    dict(
        id="CoreS3SE",
        name="M5StackCoreS3SE",
        board_id=17,
        family="Core",
        soc="esp32s3",
        note="The CoreS3 without the camera. Every register brought up here is\n"
             "the CoreS3's, down to the camera rail: upstream tells the two\n"
             "apart by looking for the GC0308, which is a device rather than\n"
             "anything the bring-up depends on.\n"
             "The same GPIO 35 note applies - MISO and the panel's D/C share\n"
             "that pin, and re-pointing it belongs to the SPI transaction\n"
             "layer. Its A/B/C are touch zones, not GPIOs.",
        i2c_int=(12, 11),
        i2c_ext=(2, 1),
        buttons={"Pwr": "pek"},
        pmic="axp2101",
        io_expander="aw9523",
        backlight=("axp2101_dldo1",),
        display=dict(bus="spi", mosi=37, miso=35, sclk=36, dc=35, cs=3, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=320, h=240, ox=0, oy=0, rotation=3, invert=True,
                     three_wire=True),
        power_on=CORE_S3_POWER_ON,
        sd_spi_cs=4,
    ),
    dict(
        id="StackChan",
        name="M5StackChan",
        board_id=27,
        family="Core",
        soc="esp32s3",
        note="The CoreS3 with the Stack-chan servo board. That board carries a\n"
             "second expander - an M5IOE1 at 0x6F, which is how upstream tells\n"
             "this apart from a plain CoreS3 - but it drives servos rather than\n"
             "a rail or the panel, so bring-up is the CoreS3's and this header\n"
             "does not touch it.\n"
             "The same GPIO 35 note applies, and A/B/C are touch zones.",
        i2c_int=(12, 11),
        i2c_ext=(2, 1),
        buttons={"Pwr": "pek"},
        pmic="axp2101",
        io_expander="aw9523",
        backlight=("axp2101_dldo1",),
        display=dict(bus="spi", mosi=37, miso=35, sclk=36, dc=35, cs=3, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=320, h=240, ox=0, oy=0, rotation=3, invert=True,
                     three_wire=True),
        power_on=CORE_S3_POWER_ON,
        sd_spi_cs=4,
    ),
    dict(
        id="StopWatch",
        name="M5StopWatch",
        board_id=30,
        family="Other",
        soc="esp32s3",
        note="A round AMOLED on four data lines. This is the first QSPI panel\n"
             "here, and the reason TinyM5::Display carries a bus kind at all:\n"
             "mosi and miso are io0 and io1 rather than a direction each, io2\n"
             "and io3 are the other two, and there is no D/C pin - the command\n"
             "rides in the transfer's instruction phase.\n"
             "Brightness is a panel command on an AMOLED, so there is no\n"
             "backlight here for this library to own.\n"
             "The same two chips as the PaperMono: an M5PM1 for power and an\n"
             "M5IOE1 for the panel's reset, the touch layer and the audio\n"
             "amplifier - which is left off, because a board bring-up that\n"
             "makes a noise is a bug.",
        i2c_int=(47, 48),
        i2c_ext=(10, 11),
        power_hold=None,
        rgb_led=None,
        buttons={"A": 2, "B": 1, "Pwr": "pek"},
        pmic="m5pm1",
        rails=("Charge", "Dcdc5V", "Ldo3V3", "Led"),
        io_expander="m5ioe1",
        backlight=None,
        display=dict(bus="qspi", mosi=41, miso=42, io2=46, io3=45, sclk=40,
                     dc=-1, cs=39, rst=-1,
                     freq_write=80000000, freq_read=1000000,
                     w=468, h=468, ox=6, oy=0, rotation=0, invert=False,
                     three_wire=True),
        power_on="""\
// The panel's chip select is a real pin and goes high before anything
// touches the bus. (M5GFX.cpp, the StopWatch branch)
pinMode(39, OUTPUT);
digitalWrite(39, HIGH);
// On the expander: IO1 is the mux control, IO4 the touch layer's reset,
// IO5 the panel's, IO8 a rail, and IO3 the audio amplifier.
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io1);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io4);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io5);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io8);
// The amplifier's enable is configured but left low. Bringing a board up
// is not an excuse to make a noise.
Io.setPushPull(TinyM5BoardIoExpanderM5ioe1::Io::Io3);
Io.setOutput(TinyM5BoardIoExpanderM5ioe1::Io::Io3);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io3, false);
delay(10);
// The panel and the touch layer come out of reset together.
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io4, false);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io5, false);
delay(8);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io4, true);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io5, true);
delay(2);
// The second half of the amplifier, on IO10.
Io.setPushPull(TinyM5BoardIoExpanderM5ioe1::Io::Io10);
Io.setOutput(TinyM5BoardIoExpanderM5ioe1::Io::Io10);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io10, false);
// The panel's tearing-effect line. An input the driver may wait on; it
// is pulled up here so that first read is not a coin toss.
pinMode(38, INPUT_PULLUP);
""",
    ),
    dict(
        id="CoreInk",
        name="M5StackCoreInk",
        board_id=6,
        family="Paper",
        soc="esp32",
        note="A 200x200 electrophoretic panel on a classic ESP32, and the\n"
             "board with the most buttons here: A/B/C on the front, an EXT on\n"
             "GPIO 5 and a power key on GPIO 27 - a pin rather than a PMIC\n"
             "register on this one.\n"
             "Two controllers have shipped under the name, a GDEW0154D67 and a\n"
             "GDEW0154M09, with the same pins and size.\n"
             "Its divider is 25.1/5.1, which is neither of the two ratios the\n"
             "other ADC boards use.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        power_hold=12,
        rgb_led=None,
        buttons={"A": 37, "B": 38, "C": 39, "Ext": 5, "Pwr": 27},
        pmic="adc",
        bat_adc=(35, 4922),
        backlight=None,
        display=dict(bus="spi", mosi=23, miso=34, sclk=18, dc=15, cs=9, rst=0,
                     busy=4,
                     freq_write=40000000, freq_read=16000000,
                     w=200, h=200, ox=0, oy=0, rotation=0, invert=False,
                     three_wire=True),
        power_on="",
    ),
    dict(
        id="Paper",
        name="M5Paper",
        board_id=7,
        family="Paper",
        soc="esp32",
        note="The original 960x540 electrophoretic tablet, on a classic ESP32.\n"
             "Its IT8951 controller takes commands as SPI words rather than\n"
             "through a D/C pin, and holds BUSY (GPIO 27) while it refreshes.\n"
             "The card is on the panel's bus, so begin() quietens it first.\n"
             "GPIO 5 switches the 5 V output on the Grove port. It is left\n"
             "configured and off: what is plugged in is not something a board\n"
             "bring-up gets to guess (D35).",
        i2c_int=(21, 22),
        i2c_ext=(25, 32),
        power_hold=2,
        rgb_led=None,
        buttons={"A": 37, "B": 38, "C": 39},
        pmic="adc",
        bat_adc=(35, 2000),
        backlight=None,
        display=dict(bus="spi", mosi=12, miso=13, sclk=14, dc=-1, cs=15, rst=23,
                     busy=27,
                     freq_write=40000000, freq_read=20000000,
                     w=960, h=540, ox=0, oy=0, rotation=3, invert=False,
                     three_wire=False),
        sd_spi_cs=4,
        power_on="""\
// The Grove port's 5 V switch. Configured but not turned on - see the
// note above. (M5Unified Power_Class.cpp:632)
pinMode(5, OUTPUT);
digitalWrite(5, LOW);
""",
    ),
    dict(
        id="PaperMono",
        name="M5PaperMono",
        board_id=29,
        family="Paper",
        soc="esp32s3",
        note="An 800x480 electrophoretic panel, and the first board here whose\n"
             "screen is not an LCD. The bus is still plain SPI - what an EPD\n"
             "adds is the BUSY line, GPIO 18, which the controller holds for\n"
             "the hundreds of milliseconds a refresh takes.\n"
             "An M5PM1 for power and an M5IOE1 for the rest: the panel's\n"
             "supply, its reset, the touch layer and the card slot are all\n"
             "expander pins. The front light is a PWM channel inside the\n"
             "M5PM1 rather than a pin.\n"
             "Its card is on a bus of its own, so nothing has to be quietened\n"
             "before the panel is read.",
        i2c_int=(47, 48),
        i2c_ext=None,
        power_hold=None,
        rgb_led=None,
        buttons={"A": 2, "B": 3, "Pwr": "pek"},
        pmic="m5pm1",
        rails=("Charge", "Dcdc5V", "Ldo3V3", "Led"),
        io_expander="m5ioe1",
        backlight=("m5pm1_pwm", "Ch0", "Io3", 5000),
        display=dict(bus="spi", mosi=14, miso=-1, sclk=15, dc=17, cs=16, rst=-1,
                     busy=18,
                     freq_write=40000000, freq_read=10000000,
                     w=800, h=480, ox=0, oy=0, rotation=3, invert=False,
                     three_wire=True),
        power_on="""\
// The panel's chip select is a real pin and has to be high before
// anything else touches the bus. (M5GFX.cpp, the PaperMono branch)
pinMode(16, OUTPUT);
digitalWrite(16, HIGH);
// Everything else the panel needs is on the expander: IO3 is its supply,
// IO5 its reset, IO6 the touch layer's reset, IO13 the touch layer's
// supply and IO14 the card slot's.
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io3);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io13);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io14);
Io.setPushPull(TinyM5BoardIoExpanderM5ioe1::Io::Io5);
Io.setOutput(TinyM5BoardIoExpanderM5ioe1::Io::Io5);
Io.setPushPull(TinyM5BoardIoExpanderM5ioe1::Io::Io6);
Io.setOutput(TinyM5BoardIoExpanderM5ioe1::Io::Io6);
// The panel and the touch layer come out of reset together.
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io5, false);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io6, false);
delay(8);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io5, true);
Io.write(TinyM5BoardIoExpanderM5ioe1::Io::Io6, true);
delay(2);
""",
    ),
    dict(
        id="CoreP4X",
        name="M5CoreP4X",
        board_id=31,
        family="Core",
        soc="esp32p4",
        note="An ESP32-P4 with a MIPI-DSI panel - the first board here whose\n"
             "screen has no pins at all. The lanes come out of the DSI\n"
             "peripheral, so what is board knowledge is how many are wired,\n"
             "how fast they run, which internal LDO feeds the PHY and the\n"
             "blanking the glass was cut for. That is displayDsi(); the\n"
             "geometry is in display() like everywhere else.\n"
             "An M5PM1 for power and an M5IOE1 for the rest: the touch reset,\n"
             "the backlight, the panel's supply and reset, and the 3V3 rail\n"
             "that MBUS, the card slot, the IMU, the infrared and Ethernet all\n"
             "share are expander pins.",
        i2c_int=(11, 9),
        i2c_ext=(18, 16),
        power_hold=None,
        rgb_led=None,
        buttons={"Pwr": "pek"},
        pmic="m5pm1",
        rails=("Boost",),
        io_expander="m5ioe1",
        backlight=("m5ioe1_pwm", "Ch1", "Io9", 1000),
        display=dict(bus="dsi", w=480, h=480, ox=0, oy=0, rotation=2,
                     invert=False, three_wire=False),
        display_dsi=dict(bus_id=0, lanes=2, mbps=600, ldo_ch=3, ldo_mv=2500,
                         dpi_mhz=24, hbp=40, hpw=2, hfp=40,
                         vbp=8, vpw=4, vfp=200),
        power_on="""\
// Five expander pins, all of them supplies or resets: IO8 the touch
// layer's reset, IO9 the backlight, IO10 the panel's supply, IO11 its
// reset, and IO12 the 3V3 rail shared by MBUS, the card slot, the IMU,
// the infrared receiver and Ethernet. (M5GFX.cpp, the CoreP4X branch)
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io8);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io9);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io10);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io11);
Io.enableRail(TinyM5BoardIoExpanderM5ioe1::Io::Io12);
// The panel wants its supply settled before anything talks to it.
delay(150);
""",
    ),
    dict(
        id="StampPico",
        name="M5StampPico",
        board_id=133,
        family="Stamp",
        soc="esp32",
        note="The ATOM as a solderable module: the same button on GPIO 39 and\n"
             "the same LED on GPIO 27, but the generic I2C pins rather than\n"
             "the ATOM's.\n"
             "A module has no USB bridge, so the GPIO 0 bias the ATOM needs is\n"
             "absent here - and that is upstream's reading of it too.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        power_hold=None,
        rgb_led=(27, 1),
        buttons={"A": 39},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="StampS3",
        name="M5StampS3",
        board_id=136,
        family="Stamp",
        soc="esp32s3",
        note="A solderable ESP32-S3 module. It has no internal I2C bus at\n"
             "all - the Grove port is the only one, so that is the bus Wire\n"
             "opens and kI2cSda reads -1.\n"
             "The button is the boot pin, GPIO 0.",
        i2c_int=None,
        i2c_ext=(13, 15),
        power_hold=None,
        rgb_led=(21, 1),
        buttons={"A": 0},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="StampC3",
        name="M5StampC3",
        board_id=134,
        family="Stamp",
        soc="esp32c3",
        note="The RISC-V module. Like the StampS3 it has only the Grove port,\n"
             "and its one I2C controller is what that port gets.\n"
             "Upstream tells this from the C3U by a strong external pull-up on\n"
             "GPIO 20 - not something a build-time choice needs, but it is why\n"
             "these are two entries rather than one.",
        i2c_int=None,
        i2c_ext=(1, 0),
        power_hold=None,
        rgb_led=(2, 1),
        buttons={"A": 3},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="StampC3U",
        name="M5StampC3U",
        board_id=135,
        family="Stamp",
        soc="esp32c3",
        note="The StampC3 with a USB-A plug. Same bus and the same LED; the\n"
             "button moves from GPIO 3 to GPIO 9.",
        i2c_int=None,
        i2c_ext=(1, 0),
        power_hold=None,
        rgb_led=(2, 1),
        buttons={"A": 9},
        pmic=None,
        backlight=None,
        display=None,
        power_on="",
    ),
    dict(
        id="StampPLC",
        name="M5StampPLC",
        board_id=21,
        family="Stamp",
        soc="esp32s3",
        note="A DIN-rail controller. Its three front buttons are not pins:\n"
             "they hang off the PI4IO expander, so reading one costs an I2C\n"
             "transaction and Board.BtnA is rate limited accordingly.\n"
             "The backlight is the same expander's P7 and is a plain switch -\n"
             "on or off, nothing between. Board.Backlight.dimmable() says so.\n"
             "Its card shares the LCD's SPI bus, so begin() puts the card into\n"
             "SPI mode before anything reads the panel.",
        i2c_int=(13, 15),
        i2c_ext=(2, 1),
        rgb_led=(21, 1),
        buttons={"A": ("io", "P2"), "B": ("io", "P1"), "C": ("io", "P0")},
        io_expander="pi4io",
        backlight=("pi4io_switch", "P7", True),
        display=dict(bus="spi", mosi=8, miso=9, sclk=7, dc=6, cs=12, rst=3,
                     freq_write=40000000, freq_read=16000000,
                     w=135, h=240, ox=52, oy=40, rotation=1, invert=True,
                     three_wire=True),
        power_on="""\
// The buttons are expander inputs with pull-ups. They also have to come
// out of high impedance - out of reset every pin on this chip drives
// nothing. (M5Unified.cpp, the StampPLC case)
Io.enableInput(TinyM5BoardIoExpanderPi4io::Io::P0);
Io.enableInput(TinyM5BoardIoExpanderPi4io::Io::P1);
Io.enableInput(TinyM5BoardIoExpanderPi4io::Io::P2);
""",
        sd_spi_cs=10,
    ),
]


# --- derivation ------------------------------------------------------------

# Columns a board may leave out. Omitting one says "this board has no such
# hardware", which is also what the kHas* flags are derived from.
OPTIONAL = dict(note="", i2c_int=None, i2c_ext=None, power_hold=None, rgb_led=None,
                buttons={}, pmic=None, bat_adc=None, rails=(), rail_mv={},
                io_expander=None, backlight=None, display=None, display_dsi=None,
                sd_spi_cs=None, power_on="")

# Rail names as a board header spells them, mapped to the driver's enum.
# The class that owns `Power` for each `pmic` value. A PEK button reads
# through it, so it has to be nameable from the generated header.
POWER_CLASS = {
    "adc": "TinyM5BoardPowerAdc",
    "axp192": "TinyM5BoardPowerAxp192",
    "core2": "TinyM5BoardPowerCore2",
    "m5pm1": "TinyM5BoardPowerM5pm1",
    "axp2101": "TinyM5BoardPowerAxp2101",
    "aw32001": "TinyM5BoardPowerAw32001",
}
IOE_CLASS = {
    "m5ioe1": "TinyM5BoardIoExpanderM5ioe1",
    "aw9523": "TinyM5BoardIoExpanderAw9523",
    "pi4io": "TinyM5BoardIoExpanderPi4io",
}

RAIL_ENUM = {"axp192": "TinyM5BoardPowerAxp192"}

# What the panel is wired as. Not which SPI peripheral it lands on: any
# pin can reach any host through the GPIO matrix, so that is the graphics
# library's choice rather than the board's.
BUS_ENUM = {"spi": "Spi", "qspi": "QSpi", "dsi": "Dsi"}


def derive(b):
    soc = SOC[b["soc"]]
    d = dict(OPTIONAL)
    d.update(b)
    d["has_int_i2c"] = d["i2c_int"] is not None
    d["has_ext_i2c"] = d["i2c_ext"] is not None
    d["shares_i2c"] = (d["has_int_i2c"] and d["has_ext_i2c"]
                       and d["i2c_ext"] == d["i2c_int"])
    d["has_display"] = d["display"] is not None
    d["has_backlight"] = d["backlight"] is not None
    d["has_battery"] = d["pmic"] is not None
    # Wire1 only exists where the SoC has a second I2C controller, and
    # only matters when the external bus is a different one.
    d["use_wire1"] = (d["has_int_i2c"] and d["has_ext_i2c"]
                      and not d["shares_i2c"] and soc["i2c_num"] > 1)
    if (d["has_int_i2c"] and d["has_ext_i2c"] and not d["shares_i2c"]
            and soc["i2c_num"] < 2):
        raise SystemExit(f"{d['id']}: two separate I2C buses on a {d['soc']}, "
                         "which has one controller - the catalogue cannot say "
                         "which one begin() should open")
    # The Stamp and Nano modules have no internal bus at all: the Grove
    # port is the only one, so it is the one `Wire` opens. A sketch that
    # says Wire.begin() itself would otherwise be reaching for a bus this
    # board does not have.
    d["wire0"] = d["i2c_int"] if d["has_int_i2c"] else d["i2c_ext"]
    # The card is only this library's business when it sits on the panel's
    # bus, so the column cannot mean anything without a panel to share.
    if d["has_display"]:
        dd = d["display"]
        if dd.get("bus", "spi") not in BUS_ENUM:
            raise SystemExit(f"{d['id']}: unknown display bus {dd['bus']!r}")
        if (dd.get("io2", -1) >= 0) != (dd.get("bus", "spi") == "qspi"):
            raise SystemExit(f"{d['id']}: io2 / io3 belong to a qspi panel and "
                             "are required on one - on four data lines the "
                             "other two are not optional")
        if (dd.get("bus") == "dsi") != (d["display_dsi"] is not None):
            raise SystemExit(f"{d['id']}: a dsi panel needs display_dsi and "
                             "nothing else may carry it - the lanes, the LDO "
                             "and the timings have no meaning on a bus with "
                             "pins")
        if dd.get("bus") == "dsi" and any(dd.get(k, -1) >= 0 for k in
                                          ("mosi", "miso", "sclk", "dc", "cs", "rst")):
            raise SystemExit(f"{d['id']}: a dsi panel has no pins to report")
    d["has_dsi"] = d["display_dsi"] is not None
    # One chip or two. The NessoN1 puts its buttons on one and the
    # panel's reset and backlight on the other, so both are bring-up.
    kinds = d["io_expander"]
    if kinds is None:
        kinds = ()
    elif isinstance(kinds, str):
        kinds = (kinds,)
    d["io_expanders"] = [
        dict(kind=k, member="Io" if i == 0 else f"Io{i + 1}", index=i)
        for i, k in enumerate(kinds)
    ]
    if len(d["io_expanders"]) > 2:
        raise SystemExit(f"{d['id']}: three expanders - the second address is "
                         "the last one this driver knows")
    d["has_sd_spi"] = d["sd_spi_cs"] is not None
    if d["has_sd_spi"]:
        if not d["has_display"]:
            raise SystemExit(f"{d['id']}: sd_spi_cs on a board with no display - "
                             "a card on a bus of its own is a driver's problem, "
                             "not a bring-up's")
        if d["display"]["miso"] < 0:
            raise SystemExit(f"{d['id']}: sd_spi_cs needs MISO - the card is asked "
                             "whether it is already in SPI mode, and the answer "
                             "comes back on that wire")
    d["classic"] = soc["classic"]
    return d


def button_names():
    """Every button name in the catalogue.

    Every board defines a macro for every one of them, including the
    ones it does not have. A sketch that asks about a button only the
    CoreInk carries has to get an answer on the other thirty-four rather
    than a preprocessor error.
    """
    return sorted({name for b in BOARDS for name in b.get("buttons", {})})


def ioe_of(d, spec):
    """Which expander a spec means.

    The short form - ("io", "P0") - is the first one, which is the only
    one on every board but the NessoN1. The long form names the member:
    ("io", "Io2", "P0").
    """
    named = [e for e in d["io_expanders"] if e["member"] in spec]
    if named:
        return named[0]
    if not d["io_expanders"]:
        raise SystemExit(f"{d['id']}: {spec} needs an expander and the board "
                         "has none")
    return d["io_expanders"][0]


def button_pin(spec):
    return spec[0] if isinstance(spec, tuple) else spec


def button_active_low(spec):
    return spec[1] if isinstance(spec, tuple) else True


# --- emitters --------------------------------------------------------------

BANNER = "// Generated by tools/gen_boards.py - edit the catalogue there, not this file.\n"


def emit_board(entry):
    d = derive(entry)
    b = d
    cls = f"TinyM5Board{b['id']}"
    o = []
    a = o.append

    a(f"// {cls}\n//\n")
    for line in b["note"].split("\n"):
        a(f"// {line}\n")
    a("//\n")
    a(BANNER)
    a("#pragma once\n\n")
    a("#ifdef TINYM5_BOARD\n")
    a('#error "TinyM5Board: one board per sketch. A second board header was included, '
      'and only the first one would have taken effect - name the one you meant."\n')
    a("#endif\n\n")
    a('#include <Wire.h>\n\n')
    a('#include "TinyM5Board/Common.h"\n')
    if b["buttons"]:
        a('#include "TinyM5Board/Button.h"\n')
    if b["pmic"] == "adc":
        a('#include "TinyM5Board/PowerAdc.h"\n')
    elif b["pmic"] == "axp192":
        a('#include "TinyM5Board/PowerAxp192.h"\n')
    elif b["pmic"] == "axp2101":
        a('#include "TinyM5Board/PowerAxp2101.h"\n')
    elif b["pmic"] == "core2":
        a('#include "TinyM5Board/PowerCore2.h"\n')
    elif b["pmic"] == "m5pm1":
        a('#include "TinyM5Board/PowerM5pm1.h"\n')
    elif b["pmic"] == "aw32001":
        a('#include "TinyM5Board/PowerAw32001.h"\n')
    if d["has_sd_spi"]:
        a('#include "TinyM5Board/SdSpiMode.h"\n')
    for kind in dict.fromkeys(e["kind"] for e in d["io_expanders"]):
        header = IOE_CLASS[kind].removeprefix("TinyM5Board")
        a(f'#include "TinyM5Board/{header}.h"\n')
    if b["backlight"]:
        if b["backlight"][0] == "pwm":
            a('#include "TinyM5Board/BacklightPwm.h"\n')
        elif b["backlight"][0].startswith("axp192_"):
            a('#include "TinyM5Board/BacklightAxp192.h"\n')
        elif b["backlight"][0] == "core2":
            a('#include "TinyM5Board/BacklightCore2.h"\n')
        elif b["backlight"][0] == "m5ioe1_pwm":
            a('#include "TinyM5Board/BacklightM5ioe1.h"\n')
        elif b["backlight"][0] == "m5pm1_pwm":
            a('#include "TinyM5Board/BacklightM5pm1.h"\n')
        elif b["backlight"][0] == "pi4io_switch":
            a('#include "TinyM5Board/BacklightPi4io.h"\n')
        elif b["backlight"][0].startswith("axp2101_"):
            a('#include "TinyM5Board/BacklightAxp2101.h"\n')
    a("\n")

    a(f"class {cls} {{\n public:\n")

    a("  // ---- identity ----\n")
    a(f"  static constexpr TinyM5::BoardId kBoardId = TinyM5::BoardId::{b['id']};\n")
    a(f"  static constexpr TinyM5::Family kFamily = TinyM5::Family::{b['family']};\n")
    a(f'  static constexpr const char *kName = "{b["name"]}";\n\n')

    a("  // ---- pins ----\n")
    if d["has_int_i2c"]:
        a(f"  static constexpr int8_t kI2cSda = {d['i2c_int'][0]};\n")
        a(f"  static constexpr int8_t kI2cScl = {d['i2c_int'][1]};\n")
    else:
        # No internal bus. The Grove port below is the only one, and it is
        # what begin() opens on Wire.
        a("  static constexpr int8_t kI2cSda = -1;\n")
        a("  static constexpr int8_t kI2cScl = -1;\n")
    if d["has_ext_i2c"]:
        a(f"  static constexpr int8_t kI2cExtSda = {b['i2c_ext'][0]};\n")
        a(f"  static constexpr int8_t kI2cExtScl = {b['i2c_ext'][1]};\n")
    else:
        a("  static constexpr int8_t kI2cExtSda = -1;\n")
        a("  static constexpr int8_t kI2cExtScl = -1;\n")
    a(f"  static constexpr int8_t kPowerHold = {b['power_hold'] if b['power_hold'] is not None else -1};\n")
    # Not one of the four queryable pins (BOARD_CATALOG §3): it is here
    # because begin() uses it, the way the internal I2C pins are.
    if d["has_sd_spi"]:
        a("  /// The TF card's chip select. The card shares the panel's SPI bus\n")
        a("  /// on this board, so begin() has to quieten it before anything\n")
        a("  /// reads the panel.\n")
        a(f"  static constexpr int8_t kSdSpiCs = {d['sd_spi_cs']};\n")
    else:
        a("  /// -1: no card on the panel's SPI bus.\n")
        a("  static constexpr int8_t kSdSpiCs = -1;\n")
    if b["rgb_led"]:
        a(f"  static constexpr int8_t kRgbLed = {b['rgb_led'][0]};\n")
        a(f"  static constexpr uint8_t kRgbLedCount = {b['rgb_led'][1]};\n")
    else:
        a("  static constexpr int8_t kRgbLed = -1;\n")
        a("  static constexpr uint8_t kRgbLedCount = 0;\n")
    for name, spec in b["buttons"].items():
        # -1 says "there is no pin on the SoC": the key is inside the power
        # chip, or the button hangs off an I/O expander.
        pin = -1 if (spec == "pek" or (isinstance(spec, tuple) and spec[0] == "io")) \
            else button_pin(spec)
        a(f"  static constexpr int8_t kBtn{name} = {pin};\n")
    a("\n")

    a("  // ---- what this board has ----\n")
    a("  // Derived from the catalogue columns, so a flag cannot disagree\n")
    a("  // with the thing it describes.\n")
    for flag, val in (("kHasDisplay", d["has_display"]),
                      ("kHasBacklight", d["has_backlight"]),
                      ("kHasBattery", d["has_battery"]),
                      ("kHasInternalI2c", d["has_int_i2c"]),
                      ("kHasExternalI2c", d["has_ext_i2c"]),
                      ("kSharesI2cBus", d["shares_i2c"])):
        a(f"  static constexpr bool {flag} = {'true' if val else 'false'};\n")
    a("\n")

    if b["pmic"] == "adc":
        a("  // ---- power ----\n")
        a(f"  TinyM5BoardPowerAdc Power{{{b['bat_adc'][0]}, {b['bat_adc'][1]}}};\n\n")
    elif b["pmic"] == "axp192":
        cls_p = RAIL_ENUM["axp192"]
        rails = " | ".join(f"{cls_p}::{r.capitalize()}" for r in b["rails"]) or "0"
        mv = b["rail_mv"]
        args = rails
        if mv.get("ldo2") or mv.get("ldo3"):
            args += f", {mv.get('ldo2', 0)}, {mv.get('ldo3', 0)}"
        a("  // ---- power ----\n")
        a("  // The rails this board's schematic actually uses, and the voltages\n")
        a("  // that are not the chip's default. The driver knows which bit is\n")
        a("  // which; the board knows what they feed.\n")
        a(f"  {cls_p} Power{{{args}}};\n\n")
    elif b["pmic"] == "m5pm1":
        rails = " | ".join(f"TinyM5BoardPowerM5pm1::{r}" for r in b["rails"]) or "0"
        a("  // ---- power ----\n")
        a(f"  TinyM5BoardPowerM5pm1 Power{{{rails}}};\n\n")
    elif b["pmic"] == "axp2101":
        a("  // ---- power ----\n")
        a("  TinyM5BoardPowerAxp2101 Power;\n\n")
    elif b["pmic"] == "aw32001":
        a("  // ---- power ----\n")
        a("  // Two chips behind one member: the charger and the gauge that\n")
        a("  // measures what it is charging.\n")
        a("  TinyM5BoardPowerAw32001 Power;\n\n")
    elif b["pmic"] == "core2":
        a("  // ---- power ----\n")
        a("  // Two chips are possible under this one product name, so the\n")
        a("  // bring-up, the panel reset and the backlight all live behind\n")
        a("  // this one object. It asks the chip which it is.\n")
        a("  TinyM5BoardPowerCore2 Power;\n\n")
    if d["io_expanders"]:
        a("  // ---- I/O expander ----\n")
        a("  // Not spare pins: at least one line the panel needs is in here.\n")
        for e in d["io_expanders"]:
            cls_io = IOE_CLASS[e["kind"]]
            if e["index"] == 0:
                a(f"  {cls_io} {e['member']};\n")
            else:
                a("  // The second one answers at the other address.\n")
                a(f"  {cls_io} {e['member']}{{{cls_io}::kAddressAlt}};\n")
        a("\n")
    if b["backlight"]:
        a("  // ---- backlight ----\n")
        if b["backlight"][0] == "pwm":
            _, bpin, bfreq, boff = b["backlight"]
            a(f"  TinyM5BoardBacklightPwm Backlight{{{bpin}, {bfreq}, {boff}}};\n\n")
        elif b["backlight"][0].startswith("axp192_"):
            ch = b["backlight"][0].split("_")[1].capitalize()
            a(f"  TinyM5BoardBacklightAxp192<TinyM5::Axp192Light::{ch}> Backlight{{Power}};\n\n")
        elif b["backlight"][0] == "core2":
            a("  TinyM5BoardBacklightCore2 Backlight{Power};\n\n")
        elif b["backlight"][0].startswith("axp2101_"):
            ch = b["backlight"][0].split("_")[1].capitalize()
            a(f"  TinyM5BoardBacklightAxp2101<TinyM5::Axp2101Light::{ch}> Backlight{{Power}};\n\n")
        elif b["backlight"][0].startswith("axp2101_"):
            ch = b["backlight"][0].split("_")[1].capitalize()
            a(f"  TinyM5BoardBacklightAxp2101<TinyM5::Axp2101Light::{ch}> Backlight{{Power}};\n\n")
        elif b["backlight"][0] == "pi4io_switch":
            e = ioe_of(d, b["backlight"])
            pin, active_low = b["backlight"][-2], b["backlight"][-1]
            a(f"  // On/off only - this board has no way to dim.\n"
              f"  TinyM5BoardBacklightPi4io Backlight{{\n"
              f"      {e['member']}, TinyM5BoardIoExpanderPi4io::Io::{pin}, "
              f"{'true' if active_low else 'false'}}};\n\n")
        elif b["backlight"][0] == "m5pm1_pwm":
            _, ch, pin, hz = b["backlight"]
            a(f"  TinyM5BoardBacklightM5pm1 Backlight{{\n"
              f"      Power, TinyM5BoardPowerM5pm1::Pwm::{ch},\n"
              f"      TinyM5BoardPowerM5pm1::Gpio::{pin}, {hz}}};\n\n")
        elif b["backlight"][0] == "m5ioe1_pwm":
            _, ch, pin, hz = b["backlight"]
            a(f"  TinyM5BoardBacklightM5ioe1 Backlight{{\n"
              f"      Io, TinyM5BoardIoExpanderM5ioe1::Pwm::{ch},\n"
              f"      TinyM5BoardIoExpanderM5ioe1::Io::{pin}, {hz}}};\n\n")
    if b["buttons"]:
        a("  // ---- buttons ----\n")
        # Say the I2C thing once rather than beside every button.
        if any(spec == "pek" or (isinstance(spec, tuple) and spec[0] == "io")
               for spec in b["buttons"].values()):
            a("  // Some of these are not pins on the SoC - they live in the\n")
            a("  // power chip or the expander and are read over I2C, so those\n")
            a("  // are rate limited to the debounce interval.\n")
        for name, spec in b["buttons"].items():
            if isinstance(spec, tuple) and spec and spec[0] == "io":
                e = ioe_of(d, spec)
                cls_io = IOE_CLASS[e["kind"]]
                a(f"  TinyM5BoardButton Btn{name}{{\n")
                a("      [](void *p) {\n")
                a(f"        return !static_cast<{cls_io} *>(p)->read(\n")
                a(f"            {cls_io}::Io::{spec[-1]});\n")
                a("      },\n")
                a(f"      &{e['member']}, true}};\n")
                continue
            if spec == "pek":
                a(f"  TinyM5BoardButton Btn{name}{{\n")
                a("      [](void *p) {\n")
                a(f"        return static_cast<{POWER_CLASS[b['pmic']]} *>(p)->isKeyPressed();\n")
                a("      },\n")
                a("      &Power, true};\n")
                continue
            pin, low = button_pin(spec), button_active_low(spec)
            cmp_ = "LOW" if low else "HIGH"
            a(f"  TinyM5BoardButton Btn{name}{{[] {{ return digitalRead(kBtn{name}) == {cmp_}; }}}};\n")
        a("\n")

    a("  bool begin(uint8_t flags = TinyM5::InitDefault)\n  {\n")
    if b["power_hold"] is not None:
        a("    holdPower();\n")
    a("    if (!(flags & TinyM5::KeepSerial)) {\n      Serial.begin(115200);\n    }\n")
    if d["wire0"]:
        first = "kI2cSda, kI2cScl" if d["has_int_i2c"] else "kI2cExtSda, kI2cExtScl"
        a("    if (!(flags & TinyM5::KeepI2c)) {\n")
        a(f"      Wire.begin({first});\n")
        if d["use_wire1"]:
            a("      Wire1.begin(kI2cExtSda, kI2cExtScl);\n")
        a("    }\n")
    for name, spec in b["buttons"].items():
        if spec == "pek" or (isinstance(spec, tuple) and spec[0] == "io"):
            continue
        mode = "INPUT" if (d["classic"] and 34 <= button_pin(spec) <= 39) else "INPUT_PULLUP"
        a(f"    pinMode(kBtn{name}, {mode});\n")
    if b["pmic"] == "adc":
        a("    Power.begin();\n")
    elif b["pmic"] == "axp192":
        a("    // The chip is soldered on, so no answer is a real fault. The\n")
        a("    // rails have to be up before the panel is taken out of reset.\n")
        a("    const bool ok = Power.begin(Wire);\n")
    elif b["pmic"] == "m5pm1":
        a("    // The idle-sleep timeout and the watchdog are disabled in here;\n")
        a("    // both survive a power cycle and both can make this board look\n")
        a("    // dead if something else set them.\n")
        a("    const bool ok = Power.begin(Wire);\n")
    elif b["pmic"] in ("axp2101", "aw32001"):
        a("    const bool ok = Power.begin(Wire);\n")
    elif b["pmic"] == "core2":
        a("    // Asks the chip which of the two it is, then runs that one's\n")
        a("    // bring-up - including the panel reset, which is a rail on one\n")
        a("    // chip and a chip GPIO on the other.\n")
        a("    const bool ok = Power.begin(Wire);\n")
    if d["io_expanders"] and d["io_expanders"][0]["kind"] == "m5ioe1":
        a("    // Same idle-sleep trap as the PMIC, and the same fix.\n")
    for e in d["io_expanders"]:
        # Not chained with &&: a chip that is missing must not stop the
        # next one from being brought up.
        a(f"    const bool ioOk{e['index'] or ''} = {e['member']}.begin(Wire);\n")
    if b["power_on"]:
        # The catalogue holds the snippet unindented; place it in the body here
        # so that a hand-written escape hatch does not have to know about
        # the generated context it lands in.
        for line in b["power_on"].rstrip("\n").split("\n"):
            a(f"    {line}\n" if line else "\n")
    if b["display"] and b["display"].get("rst", -1) >= 0:
        a(f"    TinyM5::resetPulse({b['display'].get('rst', -1)});\n")
    if b["display"] and b["display"].get("busy", -1) >= 0:
        a("    // The panel holds this line while it refreshes. Nothing here\n")
        a("    // waits on it, but a floating pin would make the driver's first\n")
        a("    // read a coin toss.\n")
        a(f"    pinMode({b['display']['busy']}, INPUT);\n")
    if d["has_sd_spi"]:
        dd = d["display"]
        a("    // The card is on the panel's wires. Left in SD mode it answers\n")
        a("    // the panel id read that a graphics library starts with.\n")
        a(f"    TinyM5::sdToSpiMode(/*sclk*/ {dd.get('sclk', -1)}, /*miso*/ {dd.get('miso', -1)},\n")
        a(f"                        /*mosi*/ {dd.get('mosi', -1)}, kSdSpiCs);\n")
    if b["backlight"]:
        a("    Backlight.begin();\n")
    ret = ("ok" if b["pmic"] in ("axp192", "axp2101", "core2", "m5pm1", "aw32001")
           else "true")
    for e in d["io_expanders"]:
        ret = f"{ret} && ioOk{e['index'] or ''}"
    a(f"    return {ret};\n  }}\n\n")

    if b["power_hold"] is not None:
        a("  /// Latch the power rail on. Called by begin(), and safe to call\n")
        a("  /// first thing in setup() when begin() cannot run that early.\n")
        a("  static void holdPower()\n  {\n")
        a("    pinMode(kPowerHold, OUTPUT);\n    digitalWrite(kPowerHold, HIGH);\n  }\n\n")

    a("  void update()\n  {\n")
    if b["buttons"]:
        ms = "    const uint32_t ms = millis();\n"
        a(ms)
        for name in b["buttons"]:
            a(f"    Btn{name}.update(ms);\n")
    a("  }\n\n")

    if b["display"]:
        dd = b["display"]
        a("  /// Everything a graphics library needs to drive this panel. This\n")
        a("  /// library owns no driver and draws nothing.\n")
        a("  static constexpr TinyM5::Display display()\n  {\n")
        a("    return TinyM5::Display{\n")
        a(f"        /*bus*/ TinyM5::DisplayBus::{BUS_ENUM[dd.get('bus', 'spi')]},\n")
        a(f"        /*mosi*/ {dd.get('mosi', -1)}, /*miso*/ {dd.get('miso', -1)}, /*sclk*/ {dd.get('sclk', -1)},\n")
        a(f"        /*dc*/ {dd.get('dc', -1)}, /*cs*/ {dd.get('cs', -1)},\n")
        a(f"        /*io2*/ {dd.get('io2', -1)}, /*io3*/ {dd.get('io3', -1)},\n")
        if dd.get("rst", -1) >= 0:
            a("        /*rst*/ -1,  // begin() has already pulsed it\n")
        else:
            a("        /*rst*/ -1,  // this panel has no reset pin of its own\n")
        a(f"        /*busy*/ {dd.get('busy', -1)},\n")
        a(f"        /*freqWrite*/ {dd.get('freq_write', 0)}, /*freqRead*/ {dd.get('freq_read', 0)},\n")
        a(f"        /*width*/ {dd['w']}, /*height*/ {dd['h']},\n")
        a(f"        /*offsetX*/ {dd['ox']}, /*offsetY*/ {dd['oy']},\n")
        a(f"        /*rotation*/ {dd.get('rotation', 0)}, /*invert*/ {'true' if dd['invert'] else 'false'},\n")
        a(f"        /*threeWire*/ {'true' if dd.get('three_wire') else 'false'}}};\n")
        a("  }\n\n")
    if d["has_dsi"]:
        z = d["display_dsi"]
        a("  /// The lanes, the PHY's supply and the timings. Everything a\n")
        a("  /// DSI panel needs that a pin number cannot say.\n")
        a("  static constexpr TinyM5::DisplayDsi displayDsi()\n  {\n")
        a("    return TinyM5::DisplayDsi{\n")
        a(f"        /*busId*/ {z['bus_id']}, /*laneCount*/ {z['lanes']},\n")
        a(f"        /*laneMbps*/ {z['mbps']},\n")
        a(f"        /*ldoChannel*/ {z['ldo_ch']}, /*ldoMillivolt*/ {z['ldo_mv']},\n")
        a(f"        /*dpiFreqMhz*/ {z['dpi_mhz']},\n")
        a(f"        /*hsync*/ {z['hbp']}, {z['hpw']}, {z['hfp']},\n")
        a(f"        /*vsync*/ {z['vbp']}, {z['vpw']}, {z['vfp']}}};\n")
        a("  }\n\n")
    a("  static constexpr const char *getBoardName() { return kName; }\n")
    a("  static constexpr TinyM5::BoardId getBoard() { return kBoardId; }\n\n")

    a("  static constexpr int8_t getPin(TinyM5::Pin pin)\n  {\n    switch (pin) {\n")
    for enum, expr in (("InI2cSda", "kI2cSda"), ("InI2cScl", "kI2cScl"),
                       ("ExI2cSda", "kI2cExtSda"), ("ExI2cScl", "kI2cExtScl"),
                       ("RgbLed", "kRgbLed"), ("PowerHold", "kPowerHold")):
        a(f"      case TinyM5::Pin::{enum}: return {expr};\n")
    a("    }\n    return -1;\n  }\n")

    a("};\n\n")

    a("// The same answers for the preprocessor.\n")
    a("//\n")
    a("// `if constexpr` cannot stand in for these. Outside a template both\n")
    a("// arms of an `if constexpr` still go through name lookup, so a sketch\n")
    a("// that reaches for Board.Power on a board without a battery fails to\n")
    a("// compile even in the branch that is discarded. Absent hardware is\n")
    a("// absent rather than stubbed out, so portable sketches need #if.\n")
    for macro, val in (("TINYM5_HAS_DISPLAY", d["has_display"]),
                       ("TINYM5_HAS_BACKLIGHT", d["has_backlight"]),
                       ("TINYM5_HAS_BATTERY", d["has_battery"]),
                       ("TINYM5_HAS_DISPLAY_DSI", d["has_dsi"]),
                       ("TINYM5_HAS_INTERNAL_I2C", d["has_int_i2c"]),
                       ("TINYM5_HAS_EXTERNAL_I2C", d["has_ext_i2c"]),
                       ("TINYM5_HAS_RGB_LED", bool(d["rgb_led"]))):
        a(f"#define {macro} {1 if val else 0}\n")
    # Buttons vary more than anything else: the Tough has none at all (its
    # A/B/C are touch zones), the Stick has a power key inside the PMIC,
    # the Station has three. A portable sketch has to ask.
    for name in button_names():
        a(f"#define TINYM5_HAS_BTN_{name.upper()} {1 if name in d['buttons'] else 0}\n")
    a("\n")

    a("// The board this sketch drives, written once so that portable code can\n")
    a("// name it without naming the product.\n")
    a(f"#define TINYM5_BOARD {cls}\n\n")
    a("#ifndef TINYM5_NO_GLOBAL_BOARD\n")
    a("// Deliberately not called `M5`: M5Unified defines a global of that name\n")
    a("// (M5Unified.cpp:58), so sharing it would break any sketch that also\n")
    a("// pulls in one of the official Unit libraries.\n")
    a(f"inline {cls} Board;\n")
    a("#endif\n")
    return "".join(o)


def emit_board_id():
    o = ["// Board identifiers. The numbers match m5stack-board-id, so they can\n",
         "// be compared with M5GFX and M5Unified without depending on either.\n",
         "//\n", BANNER, "#pragma once\n\n#include <stdint.h>\n\nnamespace TinyM5 {\n\n",
         "enum class BoardId : uint16_t {\n  Unknown = 0,\n"]
    for b in sorted(BOARDS, key=lambda x: x["board_id"]):
        o.append(f"  {b['id']} = {b['board_id']},\n")
    o.append("};\n\n}  // namespace TinyM5\n")
    return "".join(o)


def emit_entry():
    o = ["// TinyM5Board - build-flag entry point.\n//\n",
         "// The direct spelling is preferred and is what the examples use:\n//\n",
         "//     #include <TinyM5BoardAtomLite.h>\n//\n",
         "// This header is the other way in, for when the board comes from the\n",
         "// build system rather than the source - a CI matrix over every board,\n",
         "// or a PlatformIO env per board:\n//\n",
         "//     #define TINYM5_ATOMLITE\n",
         "//     #include <TinyM5Board.h>\n//\n",
         "// Some build systems can only pass a string. For those there is\n",
         "// TINYM5_BOARD_HEADER, which takes the header name itself:\n//\n",
         '//     -DTINYM5_BOARD_HEADER="TinyM5BoardAtomLite.h"\n//\n',
         "// Arduino's own board macros are never consulted. Picking a\n",
         "// near-enough board in the IDE because yours is not in the list is\n",
         "// common, and ARDUINO_M5STACK_CORE2 cannot tell a v1.0 from a v1.1\n",
         "// even when it is correct, so guessing from them would manufacture\n",
         "// wrong answers rather than find right ones.\n//\n",
         BANNER, "#pragma once\n\n", '#include "TinyM5Board/Common.h"\n\n',
         "#if defined(TINYM5_BOARD)\n",
         "// A board header was included directly. Nothing to choose.\n",
         "#elif defined(TINYM5_BOARD_HEADER)\n",
         "// Named as a string. This header has already put the library on the\n",
         "// include path, so the computed include resolves from there.\n",
         "#include TINYM5_BOARD_HEADER\n"]
    for i, b in enumerate(BOARDS):
        kw = "#elif"
        o.append(f'{kw} defined(TINYM5_{b["id"].upper()})\n#include "TinyM5Board{b["id"]}.h"\n')
    o.append('#else\n#error "TinyM5Board: no board selected. Include the header for your board '
             '(for example <TinyM5BoardAtomLite.h>), or define its macro (for example '
             'TINYM5_ATOMLITE) before including this one. The board list is in the README."\n')
    o.append("#endif\n")
    return "".join(o)


# --- tier 0 ----------------------------------------------------------------
#
# The begin() goldens run on the host core, which is not the compiler that
# ships the code. Tier 0 asks the other question: does the header for this
# board compile for the SoC the board actually has? Nothing runs - a zero
# exit from `arduino-cli compile` is the whole result.
#
# The generic dev module for each SoC, rather than the board's own FQBN.
# A board variant only sets pin aliases and a flash layout, and this
# library reads neither (D11) - picking the board in the IDE is the exact
# thing it refuses to trust. One target per SoC also keeps a run down to
# one core to download.

TIER0_FQBN = {
    "esp32": "esp32:esp32:esp32",
    "esp32s2": "esp32:esp32:esp32s2",
    "esp32s3": "esp32:esp32:esp32s3",
    "esp32c3": "esp32:esp32:esp32c3",
    "esp32c5": "esp32:esp32:esp32c5",
    "esp32c6": "esp32:esp32:esp32c6",
    "esp32h2": "esp32:esp32:esp32h2",
    "esp32p4": "esp32:esp32:esp32p4",
}

TIER0_YAML = """\
# Generated by tools/gen_boards.py.
profiles:
  {soc}:
    fqbn: {fqbn}
    platforms:
      - platform: esp32:esp32 (3.3.11)
        platform_index_url: https://espressif.github.io/arduino-esp32/package_esp32_index.json
    libraries:
      - dir: ../../../../

default_profile: {soc}
"""

# Every feature macro, checked for existing at all and then against the
# constant it was derived from. A macro that disagrees with its constant
# is the one mistake deriving them cannot rule out, because a sketch
# reads the macro and the code beside it reads the constant.
TIER0_MACROS = ("TINYM5_HAS_DISPLAY", "TINYM5_HAS_DISPLAY_DSI",
                "TINYM5_HAS_BACKLIGHT", "TINYM5_HAS_BATTERY",
                "TINYM5_HAS_INTERNAL_I2C", "TINYM5_HAS_EXTERNAL_I2C",
                "TINYM5_HAS_RGB_LED")


def emit_tier0(b):
    d = derive(b)
    macros = TIER0_MACROS + tuple(f"TINYM5_HAS_BTN_{n.upper()}"
                                  for n in button_names())
    cond = " \\\n    || ".join(f"!defined({m})" for m in macros)
    o = [f"""// Tier 0 for the {b["name"]}: does this header stand on its own?
//
// Nothing here runs. What it proves is that the toolchain that ships the
// code accepts this board's header for the SoC the board actually has,
// that the build-flag entry point reaches it, and that the feature
// macros and the constants beside them say the same thing.
//
// Generated by tools/gen_boards.py.

// The global instance is opt-out, and defining one of our own is what
// proves the switch works: if the header had made one too, this would
// not compile.
#define TINYM5_NO_GLOBAL_BOARD

// Named by a macro rather than by an include. The begin() tests take the
// direct include, so between the two tiers both spellings are covered.
#define TINYM5_{b["id"].upper()}
#include <TinyM5Board.h>

TINYM5_BOARD Board;

#if {cond}
#error "TinyM5Board: a feature macro is missing. Portable sketches ask with #if, so one that is absent on a board is a sketch that stops being portable there."
#endif

static_assert(TINYM5_BOARD::kBoardId == TinyM5::BoardId::{b["id"]},
              "the entry point selected a different board");
static_assert(TINYM5_BOARD::kFamily == TinyM5::Family::{b["family"]},
              "family does not match the catalogue");

// Macro against constant, for every flag that has a constant to compare
// with.
static_assert(TINYM5_HAS_DISPLAY == TINYM5_BOARD::kHasDisplay, "display");
static_assert(TINYM5_HAS_BACKLIGHT == TINYM5_BOARD::kHasBacklight, "backlight");
static_assert(TINYM5_HAS_BATTERY == TINYM5_BOARD::kHasBattery, "battery");
static_assert(TINYM5_HAS_INTERNAL_I2C == TINYM5_BOARD::kHasInternalI2c, "internal I2C");
static_assert(TINYM5_HAS_EXTERNAL_I2C == TINYM5_BOARD::kHasExternalI2c, "external I2C");
static_assert(TINYM5_HAS_RGB_LED == (TINYM5_BOARD::kRgbLed >= 0), "RGB LED");

// The pin lookup and the constants are two spellings of one answer
// (D28), so they cannot be allowed to drift apart.
static_assert(TINYM5_BOARD::getPin(TinyM5::Pin::InI2cSda) == TINYM5_BOARD::kI2cSda, "sda");
static_assert(TINYM5_BOARD::getPin(TinyM5::Pin::InI2cScl) == TINYM5_BOARD::kI2cScl, "scl");
static_assert(TINYM5_BOARD::getPin(TinyM5::Pin::ExI2cSda) == TINYM5_BOARD::kI2cExtSda, "ext sda");
static_assert(TINYM5_BOARD::getPin(TinyM5::Pin::ExI2cScl) == TINYM5_BOARD::kI2cExtScl, "ext scl");
static_assert(TINYM5_BOARD::getPin(TinyM5::Pin::RgbLed) == TINYM5_BOARD::kRgbLed, "led");
static_assert(TINYM5_BOARD::getPin(TinyM5::Pin::PowerHold) == TINYM5_BOARD::kPowerHold, "hold");

// Every feature path, compiled for the real target. A sketch reaches
// these through the same #if, so anything that only works on the host
// shows up here.
void setup()
{{
  Board.begin();
  Serial.println(Board.getBoardName());
"""]
    a = o.append
    if d["has_battery"]:
        a("  Serial.println(Board.Power.getBatteryVoltage());\n")
        a("  Serial.println((int)Board.Power.getType());\n")
    for e in d["io_expanders"]:
        a(f"  Serial.println(Board.{e['member']}.isPresent());\n")
    if d["has_backlight"]:
        a("  Board.Backlight.set(128);\n")
        a("  Serial.println(Board.Backlight.get());\n")
    if d["has_display"]:
        a("  Serial.println(TINYM5_BOARD::display().width);\n")
    if d["has_dsi"]:
        a("  Serial.println(TINYM5_BOARD::displayDsi().laneCount);\n")
    a("}\n\nvoid loop()\n{\n  Board.update();\n")
    for name in button_names():
        if name in d["buttons"]:
            a(f"  if (Board.Btn{name}.wasClicked() || Board.Btn{name}.wasDoubleClicked()\n")
            a(f"      || Board.Btn{name}.wasHold()) {{\n")
            a(f"    Serial.println(Board.Btn{name}.getClickCount());\n")
            a("  }\n")
    a("}\n")
    return "".join(o)


# --- keywords.txt ----------------------------------------------------------
#
# The IDE colours what this file lists and nothing else, so a list typed
# by hand is a list that is wrong the first time a driver gains a method.
# Everything below is read back out of the headers instead - the ones
# emitted above and the hand-written ones beside them - so the only way to
# fall out of the file is to stop being public.

CLASS_RE = re.compile(r"^(?:class|struct)\s+(\w+)\s*\{")
ENUM_RE = re.compile(r"^enum\s+(?:class\s+)?(\w+)")
ACCESS_RE = re.compile(r"^(public|private|protected):")
# One member per line at two spaces of indent, which is how every header
# here is written. A leading lower case letter is what separates a method
# from a constructor: the classes are all upper case.
METHOD_RE = re.compile(r"^ {2}(?:[\w:<>&*\[\]]+[\s&*]+)+([a-z]\w*)\s*\(")
CONST_RE = re.compile(r"^ {2}static constexpr [\w:*&]+ (k\w+)")
MACRO_RE = re.compile(r"^#define (TINYM5_\w+)")


def scan(text):
    """Public names in one header.

    Shallow on purpose. The only C++ it has to follow is the shape these
    headers are written in, and brace depth is what keeps a private
    helper - or anything called from inside a body - out of the list.
    """
    classes, enums, methods, consts, macros, flags = [], [], [], [], [], []
    depth = 0
    class_depth = None
    public = False
    unscoped_enum = None
    for line in text.splitlines():
        stripped = line.strip()
        if unscoped_enum is not None:
            # Values of a scoped enum are always written with the type
            # name, which is coloured already. Values of an unscoped one
            # are what a sketch actually types - TinyM5::KeepI2c.
            if stripped.startswith("}"):
                unscoped_enum = None
            else:
                m = re.match(r"([A-Z]\w*)", stripped)
                if m:
                    flags.append(m.group(1))
        elif class_depth is None:
            m = CLASS_RE.match(stripped)
            if m:
                classes.append(m.group(1))
                class_depth = depth
                public = stripped.startswith("struct")
            elif ENUM_RE.match(stripped):
                enums.append(ENUM_RE.match(stripped).group(1))
                if not stripped.startswith("enum class") and stripped.endswith("{"):
                    unscoped_enum = enums[-1]
        else:
            m = ACCESS_RE.match(stripped)
            if m:
                public = m.group(1) == "public"
            elif depth == class_depth + 1:
                if stripped.startswith("enum class"):
                    enums.append(ENUM_RE.match(stripped).group(1))
                elif public:
                    for pat, out in ((METHOD_RE, methods), (CONST_RE, consts)):
                        m = pat.match(line)
                        if m:
                            out.append(m.group(1))
        m = MACRO_RE.match(line)
        if m:
            macros.append(m.group(1))
        depth += line.count("{") - line.count("}")
        if class_depth is not None and depth <= class_depth:
            class_depth = None
            public = False
    return classes, enums, methods, consts, macros, flags


def emit_keywords(board_texts):
    """The syntax colouring map, from the headers rather than from memory.

    `board_texts` is what the board headers were just written with, so
    the constants and the TINYM5_* macros in here cannot disagree with
    the ones a sketch will see.
    """
    types, methods, consts, macros = set(), set(), set(), set()
    sources = [p.read_text(encoding="utf-8") for p in sorted(SRC.glob("TinyM5Board/*.h"))]
    for text in sources + list(board_texts.values()):
        cls, enums, meth, const, macro, flags = scan(text)
        types.update(cls, enums)
        methods.update(meth)
        consts.update(const, flags)
        macros.update(macro)
    # The board classes are their own group: a reader scanning this file
    # is usually looking for their own board.
    boards = [f"TinyM5Board{b['id']}" for b in BOARDS]
    types.difference_update(boards)
    macros.update(f"TINYM5_{b['id'].upper()}" for b in BOARDS)
    macros.update(("TINYM5_BOARD", "TINYM5_BOARD_HEADER", "TINYM5_NO_GLOBAL_BOARD"))

    def block(title, names, kind):
        out = ["#" * 39 + f"\n# {title}\n" + "#" * 39 + "\n\n"]
        out += [f"{n}\t{kind}\n" for n in names]
        out.append("\n")
        return "".join(out)

    return ("#" * 39 + "\n# Syntax Coloring Map For TinyM5Board\n" + "#" * 39 + "\n"
            + "#\n" + BANNER.replace("//", "#")
            + "# Enum values are absent unless the enum is unscoped: the rest are\n"
              "# always written with their type, and colouring a bare `Core` or\n"
              "# `Unknown` would reach into code that has nothing to do with this\n"
              "# library.\n\n"
            + block("Datatypes (KEYWORD1)", ["Board"] + sorted(types), "KEYWORD1")
            + block("Boards (KEYWORD1)", boards, "KEYWORD1")
            + block("Methods and Functions (KEYWORD2)", sorted(methods), "KEYWORD2")
            + block("Constants (LITERAL1)", sorted(consts) + sorted(macros), "LITERAL1"))


# --- driver ----------------------------------------------------------------

SKETCH_YAML = """\
# Generated by tools/gen_boards.py.
profiles:
  host:
    fqbn: lang-ship:host:host
    port: socket://localhost
    platforms:
      - platform: lang-ship:host (1.6.0)
        platform_index_url: https://tanakamasayuki.github.io/lang-ship-arduino-core/package_lang-ship_index.json
    libraries:
      - dir: ../../../../
      - dir: ../../../common_libs/tinym5_trace

default_profile: host
"""


# What has to answer on the bus for a board's begin() to get past its
# chip detection. Without this the driver bails out and the trace stops
# at the first read.
# What has to answer on the bus, and what a known battery reading looks
# like in that chip's registers.
AXP192_MODEL = ("""\
// The AXP192 has to answer or begin() stops at its detection read and
// the rest of the trace never happens.
TinyM5Trace::useChip(0, 0x34, 0x03, 0x03);
// 0xE34 counts at 1.1 mV each == 4000 mV, so the golden shows whether
// the conversion is right rather than just plausible.
TinyM5Trace::model().set(0x78, 0xE3);
TinyM5Trace::model().set(0x79, 0x04);
""")

AXP2101_MODEL = ("""\
// The AXP2101 answers instead, which is the other half of the branch
// begin() takes. Same address, different id.
TinyM5Trace::useChip(0, 0x34, 0x03, 0x4A);
// This chip reports millivolts directly (0x0FA0 == 4000) and has a real
// fuel gauge in 0xA4, so the level is read rather than estimated.
TinyM5Trace::model().set(0x34, 0x0F);
TinyM5Trace::model().set(0x35, 0xA0);
TinyM5Trace::model().set(0xA4, 87);
""")


M5PM1_MODEL = ("""\
// The M5PM1 has to answer at its own address, 0x6E rather than 0x34.
// Its id is four bytes and the driver only checks that the read
// succeeded, the same as M5Stack's own library.
TinyM5Trace::useChip(0, 0x6E, 0x00, 0x50);
// Millivolts, little-endian: 0x0FA0 == 4000. No fuel gauge on this chip,
// so the level in the golden is the estimate from that voltage.
TinyM5Trace::model().set(0x22, 0xA0);
TinyM5Trace::model().set(0x23, 0x0F);
""")


M5IOE1_MODEL = ("""\
// The expander answers as well. Two chips on one bus is why the model is
// a list rather than a single register file.
TinyM5Trace::addChip(0, 0x4F, 0x00, 0x01);
""")


PI4IO_MODEL = ("""\
// The expander is the only chip on this board's bus. Its id register
// only has to be non-zero, and the button pins read high (released)
// because the model starts every register at zero... so seed them.
TinyM5Trace::useChip(0, 0x43, 0x01, 0xA0);
TinyM5Trace::model().set(0x0F, 0xFF);
// Every pin comes out of reset high impedance, which is what makes
// enableInput / enableOutput visible in the trace below.
TinyM5Trace::model().set(0x07, 0xFF);
""")

AW9523_MODEL = ("""\
// The expander answers too, and identifies itself through 0x10.
TinyM5Trace::addChip(0, 0x58, 0x10, 0x23);
""")


AW32001_MODEL = ("""\
// The charger answers with its id, which is the same as its address.
TinyM5Trace::useChip(0, 0x49, 0x0A, 0x49);
// The gauge next to it reports millivolts little-endian in 0x08: 0x0FA0
// is 4000, so the golden shows the assembly rather than a plausible
// number.
TinyM5Trace::addChip(0, 0x55, 0x08, 0xA0).set(0x09, 0x0F);
""")


PI4IO_PAIR_MODEL = ("""\
// Two expanders on one bus, at the two addresses the chip can take.
TinyM5Trace::addChip(0, 0x43, 0x01, 0xA0).set(0x07, 0xFF);
TinyM5Trace::addChip(0, 0x44, 0x01, 0xA0).set(0x07, 0xFF);
""")


def variants(b):
    """One test per chip a board could be carrying.

    A board whose power chip is only known at runtime needs both branches
    exercised, and the host is the only place both can be: nobody owns
    two Core2s of different vintage.
    """
    d = derive(b)
    if d["pmic"] == "core2":
        return [("Axp192", AXP192_MODEL), ("Axp2101", AXP2101_MODEL)]
    if d["pmic"] == "axp192":
        return [("", AXP192_MODEL)]
    if d["pmic"] == "axp2101":
        model = AXP2101_MODEL
        if d["io_expanders"] and d["io_expanders"][0]["kind"] == "aw9523":
            model += AW9523_MODEL
        return [("", model)]
    if d["pmic"] == "m5pm1":
        if d["io_expanders"] and d["io_expanders"][0]["kind"] == "m5ioe1":
            return [("", M5PM1_MODEL + M5IOE1_MODEL)]
        return [("", M5PM1_MODEL)]
    if d["pmic"] is None and any(e["kind"] == "pi4io" for e in d["io_expanders"]):
        return [("", PI4IO_MODEL)]
    if d["pmic"] == "aw32001":
        model = AW32001_MODEL
        if any(e == "pi4io" for e in (d["io_expander"] or ())):
            model += PI4IO_PAIR_MODEL
        return [("", model)]
    if d["pmic"] == "adc":
        pin = d["bat_adc"][0]
        return [("", f"// 2000 mV at the pin, so the golden shows what this board's\n"
                     f"// divider ratio makes of it.\n"
                     f"HostArduino::setAnalogMilliVolts({pin}, 2000);\n")]
    return [("", "")]


def emit_sketch(b, model, name):
    d = derive(b)
    model_include = '#include <tinym5_model_i2c.h>\n' if "useChip" in model else ""
    model_setup = ""
    if model:
        model_setup = "\n" + "".join(f"  {ln}\n" if ln else "\n"
                                     for ln in model.rstrip("\n").split("\n"))
    return f'''// What Board.begin() does on the {b["name"]}, recorded for the golden.
//
// The include is the spelling the README recommends, so the test walks
// the same path a user does.
//
// Generated by tools/gen_boards.py.
#include <TinyM5Board{b["id"]}.h>
#include <tinym5_trace.h>
{model_include}
void setup()
{{
  Serial.begin(115200);
  TinyM5Trace::start("{name}");
{model_setup}
  Board.begin();

  TinyM5Trace::finish();
}}

void loop() {{ delay(10); }}
'''


def emit_test(b, name):
    return f'''"""begin() golden for {b["name"]} ({name}).

One directory per board because the plugin's `dut` fixture is module
scoped and the build follows the sketch directory: sharing one sketch
across boards makes the second module talk to the first one's process.

Generated by tools/gen_boards.py - a board without a test is a board
nobody would notice breaking.
"""

from tinym5_check import check_begin


def test_begin(dut, request):
    check_begin(dut, request, "{name}")
'''


def outputs():
    files = {SRC / "TinyM5Board" / "BoardId.h": emit_board_id(),
             SRC / "TinyM5Board.h": emit_entry()}
    boards = {}
    for b in BOARDS:
        boards[SRC / f"TinyM5Board{b['id']}.h"] = emit_board(b)
    files.update(boards)
    # Reads the board headers back, so it has to be built from the same
    # text they are written from rather than from what is on disk.
    files[REPO / "keywords.txt"] = emit_keywords(boards)
    for b in BOARDS:
        soc = b["soc"]
        if soc not in TIER0_FQBN:
            raise SystemExit(f"{b['id']}: no tier 0 target for soc {soc}")
        d = TESTS / "tier0" / "boards" / b["id"]
        files[d / f"{b['id']}.ino"] = emit_tier0(b)
        files[d / "sketch.yaml"] = TIER0_YAML.format(soc=soc, fqbn=TIER0_FQBN[soc])
        for suffix, model in variants(b):
            name = b["id"] + suffix
            # Grouped by family so that the family is also the unit a CI
            # matrix and a local run select on: `pytest begin/Stick`.
            d = TESTS / "begin" / b["family"] / name
            files[d / f"{name}.ino"] = emit_sketch(b, model, name)
            files[d / "sketch.yaml"] = SKETCH_YAML
            files[d / f"test_{name}.py"] = emit_test(b, name)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if anything is out of date")
    ap.add_argument("--families", action="store_true",
                    help="print the families as a JSON array, for a CI matrix")
    args = ap.parse_args()

    if args.families:
        # Sorted so the matrix order does not depend on catalogue order.
        print(json.dumps(sorted({b["family"] for b in BOARDS})))
        return 0

    stale = []
    for path, text in outputs().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        stale.append(path.relative_to(REPO))
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    if args.check:
        if stale:
            print("out of date:", *(f"\n  {p}" for p in stale), sep="")
            return 1
        print(f"up to date ({len(BOARDS)} boards)")
        return 0
    print(f"wrote {len(stale)} file(s) for {len(BOARDS)} board(s)" if stale
          else f"already up to date ({len(BOARDS)} boards)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
