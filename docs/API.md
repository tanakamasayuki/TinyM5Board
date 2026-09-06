# API reference

> 日本語: [API.ja.md](API.ja.md) · New here? [the guide](GUIDE.md)

**Everything a board header brings with it.** Why any of it is shaped this
way is in [DECISIONS.ja.md](DECISIONS.ja.md) (Japanese, internal).

## 1. Ways in

### 1.1 Include your board (recommended)

```cpp
#include <TinyM5BoardStickC.h>
```

That brings one global, `Board`. **Not `M5`**: M5Unified defines a global
of that name, and a sketch that pulls in both should not break.

### 1.2 From a build flag

For a CI matrix or a PlatformIO env, where **the build picks the board**.

```cpp
#define TINYM5_STICKC          // or -DTINYM5_STICKC
#include <TinyM5Board.h>
```

The macro is `TINYM5_` plus the id in upper case (`TINYM5_ATOMLITE`,
`TINYM5_CORES3SE`, ...).

### 1.3 As a string

For build systems that can only pass one.

```cpp
#define TINYM5_BOARD_HEADER "TinyM5BoardAtomLite.h"
#include <TinyM5Board.h>
```

### 1.4 No global at all

```cpp
#define TINYM5_NO_GLOBAL_BOARD
#include <TinyM5BoardStickC.h>

TINYM5_BOARD Board;     // yours now: a static, a member, whatever suits
```

`TINYM5_BOARD` expands to **the class name for that board**, so
`TINYM5_BOARD::display()` answers without an instance.

**Two board headers in one sketch stop the build** with an `#error`. Only
the first would have taken effect, and driving the wrong pinout is worse
than not building.

## 2. Feature macros

**Defined on every board**, `0` where the hardware is missing. `if
constexpr` cannot stand in for them: both arms still go through name
lookup, so reaching for an absent member fails to compile either way.

| Macro | |
| --- | --- |
| `TINYM5_HAS_DISPLAY` | there is a screen |
| `TINYM5_HAS_DISPLAY_DSI` | that screen is MIPI-DSI (`displayDsi()` exists) |
| `TINYM5_HAS_BACKLIGHT` | `Board.Backlight` exists |
| `TINYM5_HAS_BATTERY` | `Board.Power` exists |
| `TINYM5_HAS_INTERNAL_I2C` | there is an internal bus |
| `TINYM5_HAS_EXTERNAL_I2C` | there is a Grove port |
| `TINYM5_HAS_RGB_LED` | there is an RGB LED |
| `TINYM5_HAS_BTN_A` `_B` `_C` `_EXT` `_PWR` | that button exists |
| `TINYM5_BOARD` | the class name for this board |
| `TINYM5_CORE2_HAS_AXP192` / `_AXP2101` | Core2 only; both `1`, decided at run time |

## 3. `Board`

### 3.1 Constants

All `static constexpr`. **Absent means `-1`** (`kRgbLedCount` is `0`).

| | |
| --- | --- |
| `kBoardId` | `TinyM5::BoardId`; the numbers are m5stack-board-id's |
| `kFamily` | `TinyM5::Family` |
| `kName` | `const char*` |
| `kI2cSda` `kI2cScl` | the internal bus |
| `kI2cExtSda` `kI2cExtScl` | Grove (Port A) |
| `kPowerHold` | the power latch |
| `kSdSpiCs` | the TF card's CS **when it shares the panel's SPI bus**, else `-1` |
| `kRgbLed` `kRgbLedCount` | pin and count |
| `kBtnA` `kBtnB` `kBtnC` `kBtnExt` `kBtnPwr` | the pin. **Present only on boards that have that button** (the macros are on every board); `-1` where the button lives inside the power chip or an expander |
| `kHasDisplay` `kHasBacklight` `kHasBattery` | the macros above, as `bool` |
| `kHasInternalI2c` `kHasExternalI2c` `kSharesI2cBus` | the I2C shape |

### 3.2 Methods

```cpp
bool begin(uint8_t flags = TinyM5::InitDefault);
void update();                                  // buttons; once per loop
static constexpr const char *getBoardName();
static constexpr TinyM5::BoardId getBoard();
static constexpr int8_t getPin(TinyM5::Pin);    // the constants, at run time
static void holdPower();                        // boards with POWER_HOLD
static constexpr TinyM5::Display display();     // boards with a screen
static constexpr TinyM5::DisplayDsi displayDsi();  // DSI boards
```

`begin()` returns **whether the chips answered**. A board with no chips
always returns true.

`flags` is a bit set of `TinyM5::Init`:

| | |
| --- | --- |
| `TinyM5::InitDefault` | do everything |
| `TinyM5::KeepSerial` | leave `Serial` alone - you opened it |
| `TinyM5::KeepI2c` | leave `Wire` / `Wire1` alone |

**`holdPower()` can be called before `begin()`.** If something else has to
happen first in `setup()`, latch the power on its own and do the rest
afterwards.

### 3.3 What `begin()` does, in order

The order is the point: get it wrong on real hardware and the board
switches off or the panel stays dark.

1. `holdPower()`
2. `Serial`, `Wire`, `Wire1`
3. `pinMode` for the button pins
4. the power chip (rail voltages, then rails on)
5. the I/O expander
6. anything specific to this board
7. the panel's reset
8. an EPD's BUSY pin, as an input
9. **the TF card into SPI mode**, where it shares the panel's bus
10. the backlight

## 4. `Board.BtnX`

`TinyM5BoardButton`. **The same type whether the button is a pin, a key
inside the power chip, or a line on an I/O expander.** The ones that cost
an I2C transaction are read once per debounce interval.

```cpp
void update();  void update(uint32_t msec);   // Board.update() calls this

bool isPressed();   bool isReleased();   bool isHolding();
bool wasPressed();  bool wasReleased();  bool wasChangePressed();
bool wasHold();

bool wasClicked();              // on the release, if it never became a hold
bool wasDecideClickCount();     // the run of clicks is over
bool wasSingleClicked();        // that, with a count of 1
bool wasDoubleClicked();        // that, with a count of 2
uint8_t getClickCount();
State getState();               // Nochange / Clicked / Hold / DecideClickCount

bool pressedFor(uint32_t ms);   bool releasedFor(uint32_t ms);
void setDebounceThresh(uint32_t ms);   // default 10
void setHoldThresh(uint32_t ms);       // default 500
uint32_t getDebounceThresh();  uint32_t getHoldThresh();
uint32_t lastChange();  uint32_t getUpdateMsec();
```

**Every `was*` is what that one `update()` found**, true for that call
only.

**The click count is not known when the click happens** - another may be
coming - so `wasDecideClickCount()` fires once the button has been quiet
for a hold threshold. Same state machine as M5Unified's `Button_Class`.

## 5. `Board.Power`

**The same questions on every chip:**

```cpp
bool begin(TwoWire &wire);          // Board.begin() calls this
bool isPresent();
TinyM5::Pmic getType();             // Adc / Axp192 / Axp2101 / M5pm1 / Aw32001
int16_t getBatteryVoltage();        // mV
int32_t getBatteryLevel();          // 0-100, or -1
TinyM5::Charge isCharging();        // Charging / Discharging / Unknown
```

What each chip adds is in its own header:

| Chip | Also has | Header |
| --- | --- | --- |
| divider on an ADC pin | `getAdcPin` `getAdcRatioX1000` | `PowerAdc.h` |
| AXP192 | VBUS, charge current and voltage, LDO voltages, RTC backup, `powerOff`, the power key, the chip's GPIOs | `PowerAxp192.h` |
| AXP2101 | VBUS, charging, `setLdoEnables`, ALDO voltages, `powerOff`, the power key | `PowerAxp2101.h` |
| M5PM1 | the chip's GPIOs and PWM, low-voltage cutoff, `powerOff`, the power key | `PowerM5pm1.h` |
| AW32001 + BQ27220 | charge current and voltage, `getBatteryCurrent` | `PowerAw32001.h` |
| the Core2's two | forwards to whichever answered | `PowerCore2.h` |

Where **`Board.BtnPwr` is a key inside the power chip**, it is already
calling `Power.isKeyPressed()` for you.

## 6. `Board.Backlight`

```cpp
void begin(uint8_t brightness = 128);   // Board.begin() calls this
void set(uint8_t brightness);           // 0 is off
uint8_t get();
static constexpr bool dimmable();       // are the values between real?
```

Six kinds behind that one call: a PWM pin, an AXP192 rail, an AXP2101
rail, the Core2's, a channel inside an M5IOE1 or an M5PM1, and a plain
switch on a PI4IO. **Every curve lands on the same numbers M5GFX uses.**
Only the switch answers false to `dimmable()`.

## 7. `Board.Io` / `Board.Io2`

Only on boards with an I/O expander, and **these are not spare pins**: the
panel's supply, its reset, or the buttons are behind them.

**The chips differ in shape.** Bring-up and read/write are what they
share:

```cpp
bool begin(TwoWire &wire);   bool isPresent();
void write(Io, bool level);  bool read(Io);
void resetPulse(Io);
```

| Chip | Shape |
| --- | --- |
| `IoExpanderM5ioe1` | per pin (`setInput` / `setOutput` / `setPushPull` / pulls / `enableRail`), plus four PWM channels |
| `IoExpanderPi4io` | per pin, plus high impedance (`enableInput` / `enableOutput`) and interrupt masks |
| `IoExpanderAw9523` | **per port** (`setDirections` / `setOutputs` / `setGpioMode`) - sixteen pins in two bytes |

**Boards with two have `Io` and `Io2`**, the second at the chip's other
address.

## 8. `TinyM5::Display`

```cpp
struct Display {
  DisplayBus bus;                       // Spi / QSpi / Dsi
  int8_t mosi, miso, sclk, dc, cs;
  int8_t io2, io3;                      // QSpi only, else -1
  int8_t rst;                           // always -1: begin() did it
  int8_t busy;                          // EPD only, else -1
  uint32_t freqWrite, freqRead;
  uint16_t width, height, offsetX, offsetY;
  uint8_t rotation;                     // M5GFX's offset_rotation
  bool invert;
  bool threeWire;                       // read and write share one line
};

struct DisplayDsi {                     // only when TINYM5_HAS_DISPLAY_DSI
  uint8_t busId, laneCount;   uint16_t laneMbps;
  uint8_t ldoChannel;         uint16_t ldoMillivolt;
  uint8_t dpiFreqMhz;
  uint16_t hsyncBackPorch, hsyncPulseWidth, hsyncFrontPorch;
  uint16_t vsyncBackPorch, vsyncPulseWidth, vsyncFrontPorch;
};
```

**The panel's part number is not here.** Boards ship under one name with
different glass, and telling them apart takes the SPI bus. That is the
graphics library's job.

## 9. Types

| | |
| --- | --- |
| `TinyM5::BoardId` | the m5stack-board-id numbers |
| `TinyM5::Family` | `Core` `Stick` `Atom` `Stamp` `Paper` `Unit` `Other` |
| `TinyM5::Pmic` | `Unknown` `Adc` `Axp192` `Axp2101` `M5pm1` `Aw32001` |
| `TinyM5::Charge` | `Unknown` `Discharging` `Charging` |
| `TinyM5::Pin` | what `getPin()` takes |
| `TinyM5::Init` | what `begin()` takes |
| `TinyM5::DisplayBus` | `Spi` `QSpi` `Dsi` |

## 10. What it deliberately does not have

**Decided against, not missing** ([REQUIREMENTS.ja.md](REQUIREMENTS.ja.md)
§4, Japanese).

| | Why |
| --- | --- |
| Drivers for the IMU, RTC, speaker, mic, touch or SD | None of them are board specific, so a board layer has no reason to own them. **The pins and the bus are handed over** |
| **Which** IMU or RTC a board has | It changes between production runs. The owner cannot tell either |
| The panel's part number | Same, and telling them apart takes the bus |
| Detecting the board at run time | A wrong answer is worse than no answer |
| Port B-E and the six SD pins | Not yet. **Columns can be added later** |

**Boards that ship under one name with different parts inside, where the
owner cannot tell which they have, are not in the library.** The list and
the reasoning are in [DEVELOPMENT_PLAN.ja.md](DEVELOPMENT_PLAN.ja.md) §2-9.
