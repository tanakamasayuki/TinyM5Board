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
        power_on="""\
// The CH552 USB bridge puts 4 V on GPIO 0, which drags the WiFi
// sensitivity down. Driving the pin high from this side biases it to
// 3.3 V and suppresses the overvoltage. (M5Unified.cpp:2299)
pinMode(0, OUTPUT);
digitalWrite(0, HIGH);
""",
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
        display=dict(bus="spi2", mosi=15, miso=-1, sclk=13, dc=14, cs=5, rst=12,
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
        display=dict(bus="spi2", mosi=15, miso=14, sclk=13, dc=23, cs=5, rst=18,
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
        display=dict(bus="spi2", mosi=15, miso=14, sclk=13, dc=23, cs=5, rst=18,
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
        display=dict(bus="spi2", mosi=23, miso=-1, sclk=18, dc=19, cs=5, rst=15,
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
             "here. The SD card shares the LCD's SPI bus and is not yet taken\n"
             "out of SD mode - see docs/DEVELOPMENT_PLAN.ja.md.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        buttons={"Pwr": "pek"},
        pmic="axp192",
        rails=("ldo2",),
        rail_mv=dict(ldo2=3300),  # LCD power
        backlight=("axp192_ldo3",),
        display=dict(bus="spi2", mosi=23, miso=38, sclk=18, dc=15, cs=5, rst=-1,
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
             "here. The SD card shares the LCD's SPI bus and is not yet taken\n"
             "out of SD mode - see docs/DEVELOPMENT_PLAN.ja.md.\n"
             "The panel is an ILI9342C or an ILI9342E depending on the unit,\n"
             "which is read from the touch controller's firmware id - a\n"
             "graphics library's job, so no panel type is reported here.",
        i2c_int=(21, 22),
        i2c_ext=(32, 33),
        rgb_led=(25, 1),
        buttons={"Pwr": "pek"},
        pmic="core2",
        backlight=("core2",),
        display=dict(bus="spi2", mosi=23, miso=38, sclk=18, dc=15, cs=5, rst=-1,
                     freq_write=40000000, freq_read=16000000,
                     w=320, h=240, ox=0, oy=0, rotation=3, invert=True,
                     three_wire=True),
    ),
]


# --- derivation ------------------------------------------------------------

# Columns a board may leave out. Omitting one says "this board has no such
# hardware", which is also what the kHas* flags are derived from.
OPTIONAL = dict(note="", i2c_ext=None, power_hold=None, rgb_led=None,
                buttons={}, pmic=None, bat_adc=None, rails=(), rail_mv={},
                backlight=None, display=None, power_on="")

# Rail names as a board header spells them, mapped to the driver's enum.
# The class that owns `Power` for each `pmic` value. A PEK button reads
# through it, so it has to be nameable from the generated header.
POWER_CLASS = {
    "adc": "TinyM5BoardPowerAdc",
    "axp192": "TinyM5BoardPowerAxp192",
    "core2": "TinyM5BoardPowerCore2",
}
RAIL_ENUM = {"axp192": "TinyM5BoardPowerAxp192"}


def derive(b):
    soc = SOC[b["soc"]]
    d = dict(OPTIONAL)
    d.update(b)
    d["has_ext_i2c"] = d["i2c_ext"] is not None
    d["shares_i2c"] = d["i2c_ext"] is not None and d["i2c_ext"] == d["i2c_int"]
    d["has_display"] = d["display"] is not None
    d["has_backlight"] = d["backlight"] is not None
    d["has_battery"] = d["pmic"] is not None
    # Wire1 only exists where the SoC has a second I2C controller, and
    # only matters when the external bus is a different one.
    d["use_wire1"] = d["has_ext_i2c"] and not d["shares_i2c"] and soc["i2c_num"] > 1
    d["classic"] = soc["classic"]
    return d


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
    elif b["pmic"] == "core2":
        a('#include "TinyM5Board/PowerCore2.h"\n')
    if b["backlight"]:
        if b["backlight"][0] == "pwm":
            a('#include "TinyM5Board/BacklightPwm.h"\n')
        elif b["backlight"][0].startswith("axp192_"):
            a('#include "TinyM5Board/BacklightAxp192.h"\n')
        elif b["backlight"][0] == "core2":
            a('#include "TinyM5Board/BacklightCore2.h"\n')
    a("\n")

    a(f"class {cls} {{\n public:\n")

    a("  // ---- identity ----\n")
    a(f"  static constexpr TinyM5::BoardId kBoardId = TinyM5::BoardId::{b['id']};\n")
    a(f"  static constexpr TinyM5::Family kFamily = TinyM5::Family::{b['family']};\n")
    a(f'  static constexpr const char *kName = "{b["name"]}";\n\n')

    a("  // ---- pins ----\n")
    a(f"  static constexpr int8_t kI2cSda = {b['i2c_int'][0]};\n")
    a(f"  static constexpr int8_t kI2cScl = {b['i2c_int'][1]};\n")
    if d["has_ext_i2c"]:
        a(f"  static constexpr int8_t kI2cExtSda = {b['i2c_ext'][0]};\n")
        a(f"  static constexpr int8_t kI2cExtScl = {b['i2c_ext'][1]};\n")
    else:
        a("  static constexpr int8_t kI2cExtSda = -1;\n")
        a("  static constexpr int8_t kI2cExtScl = -1;\n")
    a(f"  static constexpr int8_t kPowerHold = {b['power_hold'] if b['power_hold'] is not None else -1};\n")
    if b["rgb_led"]:
        a(f"  static constexpr int8_t kRgbLed = {b['rgb_led'][0]};\n")
        a(f"  static constexpr uint8_t kRgbLedCount = {b['rgb_led'][1]};\n")
    else:
        a("  static constexpr int8_t kRgbLed = -1;\n")
        a("  static constexpr uint8_t kRgbLedCount = 0;\n")
    for name, spec in b["buttons"].items():
        # -1 says "there is no pin": the key is inside the power chip.
        pin = -1 if spec == "pek" else button_pin(spec)
        a(f"  static constexpr int8_t kBtn{name} = {pin};\n")
    a("\n")

    a("  // ---- what this board has ----\n")
    a("  // Derived from the catalogue columns, so a flag cannot disagree\n")
    a("  // with the thing it describes.\n")
    for flag, val in (("kHasDisplay", d["has_display"]),
                      ("kHasBacklight", d["has_backlight"]),
                      ("kHasBattery", d["has_battery"]),
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
    elif b["pmic"] == "core2":
        a("  // ---- power ----\n")
        a("  // Two chips are possible under this one product name, so the\n")
        a("  // bring-up, the panel reset and the backlight all live behind\n")
        a("  // this one object. It asks the chip which it is.\n")
        a("  TinyM5BoardPowerCore2 Power;\n\n")
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
    if b["buttons"]:
        a("  // ---- buttons ----\n")
        for name, spec in b["buttons"].items():
            if spec == "pek":
                a("  // No pin: the power key lives in the PMIC and is read over\n")
                a("  // I2C, rate limited so update() does not flood the bus.\n")
                a(f"  TinyM5BoardButton Btn{name}{{\n")
                a("      [](void *p) {\n")
                a(f"        return static_cast<{POWER_CLASS[b['pmic']]} *>(p)->getKeyState() != 0;\n")
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
    a("    if (!(flags & TinyM5::KeepI2c)) {\n")
    a("      Wire.begin(kI2cSda, kI2cScl);\n")
    if d["use_wire1"]:
        a("      Wire1.begin(kI2cExtSda, kI2cExtScl);\n")
    a("    }\n")
    for name, spec in b["buttons"].items():
        if spec == "pek":
            continue
        mode = "INPUT" if (d["classic"] and 34 <= button_pin(spec) <= 39) else "INPUT_PULLUP"
        a(f"    pinMode(kBtn{name}, {mode});\n")
    if b["pmic"] == "adc":
        a("    Power.begin();\n")
    elif b["pmic"] == "axp192":
        a("    // The chip is soldered on, so no answer is a real fault. The\n")
        a("    // rails have to be up before the panel is taken out of reset.\n")
        a("    const bool ok = Power.begin(Wire);\n")
    elif b["pmic"] == "core2":
        a("    // Asks the chip which of the two it is, then runs that one's\n")
        a("    // bring-up - including the panel reset, which is a rail on one\n")
        a("    // chip and a chip GPIO on the other.\n")
        a("    const bool ok = Power.begin(Wire);\n")
    if b["power_on"]:
        # The catalogue holds the snippet unindented; place it in the body here
        # so that a hand-written escape hatch does not have to know about
        # the generated context it lands in.
        for line in b["power_on"].rstrip("\n").split("\n"):
            a(f"    {line}\n" if line else "\n")
    if b["display"] and b["display"]["rst"] >= 0:
        a(f"    TinyM5::resetPulse({b['display']['rst']});\n")
    if b["backlight"]:
        a("    Backlight.begin();\n")
    a("    return ok;\n  }\n\n" if b["pmic"] in ("axp192", "core2")
      else "    return true;\n  }\n\n")

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
        a(f"        /*mosi*/ {dd['mosi']}, /*miso*/ {dd['miso']}, /*sclk*/ {dd['sclk']},\n")
        a(f"        /*dc*/ {dd['dc']}, /*cs*/ {dd['cs']},\n")
        a("        /*rst*/ -1,  // begin() has already pulsed it\n")
        a(f"        /*freqWrite*/ {dd['freq_write']}, /*freqRead*/ {dd['freq_read']},\n")
        a(f"        /*width*/ {dd['w']}, /*height*/ {dd['h']},\n")
        a(f"        /*offsetX*/ {dd['ox']}, /*offsetY*/ {dd['oy']},\n")
        a(f"        /*rotation*/ {dd.get('rotation', 0)}, /*invert*/ {'true' if dd['invert'] else 'false'},\n")
        a(f"        /*threeWire*/ {'true' if dd.get('three_wire') else 'false'}}};\n")
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
                       ("TINYM5_HAS_EXTERNAL_I2C", d["has_ext_i2c"]),
                       ("TINYM5_HAS_RGB_LED", bool(d["rgb_led"]))):
        a(f"#define {macro} {1 if val else 0}\n")
    # Buttons vary more than anything else: the Tough has none at all (its
    # A/B/C are touch zones), the Stick has a power key inside the PMIC,
    # the Station has three. A portable sketch has to ask.
    for name in ("A", "B", "C", "Pwr"):
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
      - dir: ../../../
      - dir: ../../common_libs/tinym5_trace

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
    for b in BOARDS:
        files[SRC / f"TinyM5Board{b['id']}.h"] = emit_board(b)
        for suffix, model in variants(b):
            name = b["id"] + suffix
            d = TESTS / "begin" / name
            files[d / f"{name}.ino"] = emit_sketch(b, model, name)
            files[d / "sketch.yaml"] = SKETCH_YAML
            files[d / f"test_{name}.py"] = emit_test(b, name)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if anything is out of date")
    args = ap.parse_args()

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
