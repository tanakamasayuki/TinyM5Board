# Guide

> 日本語: [GUIDE.ja.md](GUIDE.ja.md) · Index: [../README.md](../README.md)

**For a first time through.** Half an hour gets your board up, with its
buttons and its battery readable.

## 1. What you need

- One M5Stack board ([the list](../README.md#boards))
- Arduino IDE 2.x or arduino-cli
- **arduino-esp32 3.x** ("esp32 by Espressif Systems" in the board manager)

Install `TinyM5Board` from the library manager.

## 2. Name your board

**Nothing is detected.** You say which board this sketch is for:

```cpp
#include <TinyM5BoardStickC.h>
```

Typing `#include <TinyM5Board` makes the IDE offer every one. If you are
not sure which is yours, [the table](../README.md#boards) has them all.

> **Why not detect it?**
> Detection is wrong sometimes. Boards ship under one name with different
> parts inside, and a wrong pinout is worse than no pinout
> ([REQUIREMENTS.ja.md](REQUIREMENTS.ja.md) §4, Japanese).

## 3. Call `Board.begin()`

```cpp
#include <TinyM5BoardStickC.h>

void setup()
{
  Board.begin();
}

void loop()
{
  Board.update();
}
```

`Board` is the global the header you included brings with it. **What
`begin()` does**:

1. **Latches the power on** (boards with POWER_HOLD) - late here and the
   board switches itself off
2. Opens Serial and I2C
3. Brings up the power chip and turns on the rails it feeds
4. Brings up the I/O expander
5. Takes the panel out of reset
6. Quietens the TF card on the boards where it shares the panel's bus
7. Turns the backlight on

**`update()` is only for buttons.** Call it once at the top of `loop()`.

## 4. What you can ask

### Pins

```cpp
Board.kI2cSda      // the internal bus
Board.kI2cScl
Board.kI2cExtSda   // Grove (Port A), or -1
Board.kI2cExtScl
Board.kRgbLed      // or -1
Board.kPowerHold
```

**`Wire` is whichever bus the board actually has.** The internal one where
there is one; on the Stamp and Nano modules, which have none, the Grove
port is what `Wire` opens.

### Buttons

```cpp
Board.update();                    // once, at the top of loop()

Board.BtnA.wasPressed()            // the moment it went down
Board.BtnA.wasReleased()           // the moment it came up
Board.BtnA.wasHold()               // the moment it became a hold (500 ms)
Board.BtnA.wasClicked()            // pressed and let go before that
Board.BtnA.wasDoubleClicked()      // the moment two clicks became final
Board.BtnA.isPressed()             // right now
```

**Boards disagree about buttons more than about anything else.** A button
a board does not have is absent rather than stubbed out, so portable code
asks first:

```cpp
#if TINYM5_HAS_BTN_A
  if (Board.BtnA.wasClicked()) { ... }
#endif
```

`TINYM5_HAS_BTN_A` / `_B` / `_C` / `_EXT` / `_PWR` are **defined on every
board**, and are `0` where the button is missing.

### Battery

```cpp
#if TINYM5_HAS_BATTERY
  Board.Power.getBatteryVoltage();   // mV
  Board.Power.getBatteryLevel();     // 0-100 (%)
  Board.Power.isCharging();          // TinyM5::Charge::Charging, ...
#endif
```

**The same call whatever the chip is** - a divider on an ADC pin, an
AXP192, an AXP2101, an M5PM1, an AW32001. On the Core2, where two
different chips ship under one name, `begin()` asks the chip which it is.

### Backlight

```cpp
#if TINYM5_HAS_BACKLIGHT
  Board.Backlight.set(128);          // 0 off, 255 full
  Board.Backlight.dimmable();        // can it do the values between?
#endif
```

A PWM pin, a power chip's rail voltage, a channel inside an expander -
all of them are that `set()`. On boards whose backlight is **a plain
switch**, like the StampPLC, `dimmable()` returns false and `set()` lands
on off or on.

## 5. Drawing

**This library does not draw.** It hands over the particulars instead:

```cpp
#if TINYM5_HAS_DISPLAY
  const auto d = Board.display();
  d.mosi, d.miso, d.sclk, d.dc, d.cs;   // the bus
  d.freqWrite, d.freqRead;
  d.width, d.height, d.offsetX, d.offsetY, d.rotation, d.invert;
  d.threeWire;                          // read and write share one line
#endif
```

Feed that into M5GFX, TinyGFX, LovyanGFX or whatever you use.

**Three things to watch**:

- **`d.rst` is always `-1`.** `begin()` has already pulsed the reset, and
  this is the signal not to do it again
- **`d.threeWire == true`** (the Stick family and others) means a bus
  configured for four wires **cannot read back** from the panel
- **`d.bus` is not always `Spi`.** On `QSpi`, `mosi` and `miso` are two of
  four data lines and the others are `io2` / `io3`; on `Dsi` every pin is
  `-1` and the lanes and timings are in `Board.displayDsi()`

## 6. Moving to another board

**Change the include.** Anything behind a `#if` drops out by itself. The
four sketches in [examples/](../examples/README.md) are all written that
way, so they move as they are.

## 7. When it does not work

| What you see | Usually |
| --- | --- |
| **The board switches off** | Is `Board.begin()` the **first thing** in `setup()`? Boards with POWER_HOLD switch off if it is not |
| **`no board selected`** | You included `<TinyM5Board.h>` itself. Include **your board's header** instead |
| **`one board per sketch`** | Two board headers. Only the first would have taken effect - keep the one you meant |
| **`Board.Power` does not exist** | That board has no battery. Wrap it in `#if TINYM5_HAS_BATTERY` |
| **`if constexpr` did not help** | Both arms of an `if constexpr` still go through name lookup. **Use `#if`** |
| **The screen stays dark** | Did you call `Board.Backlight.set(...)`? `begin()` lights it at 128, but a graphics library can turn it back off |
| **The picture is offset** | Are you passing `d.offsetX` / `offsetY` / `rotation` to the graphics library? |
| **The battery reading looks wrong** | Divider ratios differ per board (not all of them are 2.0). If it still looks wrong, open an issue |

## Next

- [API reference](API.md) - every constant, method and macro
- [examples/](../examples/README.md) - four sketches that run
