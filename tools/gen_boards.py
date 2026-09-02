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
]


# --- derivation ------------------------------------------------------------

def derive(b):
    soc = SOC[b["soc"]]
    d = dict(b)
    d["has_ext_i2c"] = b["i2c_ext"] is not None
    d["shares_i2c"] = b["i2c_ext"] is not None and b["i2c_ext"] == b["i2c_int"]
    d["has_display"] = b["display"] is not None
    d["has_backlight"] = b["backlight"] is not None
    d["has_battery"] = b["pmic"] is not None
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


def emit_board(b):
    d = derive(b)
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
        a(f"  static constexpr int8_t kBtn{name} = {button_pin(spec)};\n")
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

    if b["buttons"]:
        a("  // ---- buttons ----\n")
        for name, spec in b["buttons"].items():
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
        mode = "INPUT" if (d["classic"] and 34 <= button_pin(spec) <= 39) else "INPUT_PULLUP"
        a(f"    pinMode(kBtn{name}, {mode});\n")
    if b["power_on"]:
        # The catalogue holds the snippet unindented; place it in the body here
        # so that a hand-written escape hatch does not have to know about
        # the generated context it lands in.
        for line in b["power_on"].rstrip("\n").split("\n"):
            a(f"    {line}\n" if line else "\n")
    a("    return true;\n  }\n\n")

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
                       ("TINYM5_HAS_EXTERNAL_I2C", d["has_ext_i2c"])):
        a(f"#define {macro} {1 if val else 0}\n")
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

def outputs():
    files = {SRC / "TinyM5Board" / "BoardId.h": emit_board_id(),
             SRC / "TinyM5Board.h": emit_entry()}
    for b in BOARDS:
        files[SRC / f"TinyM5Board{b['id']}.h"] = emit_board(b)
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
