# TinyM5Board

> 日本語: [README.ja.md](README.ja.md)

**Brings an M5Stack board up and hands you its pinout. It does not draw.**

Power on, rails up, panel out of reset, backlight lit, buttons and battery
readable. What happens next - drawing text, reading a sensor - belongs to
whichever library you chose for it.

> **Not released yet, and not run on real hardware yet.** Every board is
> transcribed from M5Stack's own libraries (M5Unified and M5GFX), frozen
> against a host-side golden of what `begin()` does to the bus, and
> compiled for its own SoC. **Read the pinouts as transcriptions rather
> than measurements** until a board has been through the manual check.

## Thirty seconds

Install TinyM5Board from the Arduino library manager and include **the one
header for your board**.

```cpp
#include <TinyM5BoardAtomLite.h>   // <- change this to your board

void setup()
{
  Board.begin();

  Serial.printf("board : %s\n", Board.getBoardName());
  Serial.printf("i2c   : sda=%d scl=%d\n", Board.kI2cSda, Board.kI2cScl);
#if TINYM5_HAS_BATTERY
  Serial.printf("batt  : %d mV\n", Board.Power.getBatteryVoltage());
#endif
}

void loop()
{
  Board.update();
#if TINYM5_HAS_BTN_A
  if (Board.BtnA.wasClicked()) Serial.println("BtnA");
#endif
}
```

**Moving to another board is that one include.** Everything else reads the
same everywhere.

- New here → **[the guide](docs/GUIDE.md)**
- Every constant, method and macro → **[API reference](docs/API.md)**
- Working code → **[examples/](examples/README.md)**

## Why use it

| | |
| --- | --- |
| **No graphics library comes with it** | A board with no screen pays nothing. A board with one gets the panel's particulars, and you draw with whatever you like |
| **The board is fixed at build time** | Nothing is detected at run time, so there is no detection code and no wrong detection |
| **The same spelling everywhere** | The StickC's power key is inside its PMIC, the StampPLC's buttons hang off an I/O expander, the AtomLite's is a plain GPIO. **All three are `Board.BtnA.wasClicked()`** |
| **Header only** | What you do not include is never compiled |

**What it will not do**: draw, carry IMU or RTC drivers, or guess which
board it is running on. The reasoning is in
[docs/REQUIREMENTS.ja.md](docs/REQUIREMENTS.ja.md) (Japanese).

## Boards

<!-- BEGIN BOARD TABLE -->

**Atom**

| Board | Include | Screen | Battery | Buttons |
| --- | --- | --- | --- | --- |
| M5AtomLite | `<TinyM5BoardAtomLite.h>` | no | no | BtnA |
| M5AtomMatrix | `<TinyM5BoardAtomMatrix.h>` | no | no | BtnA |
| M5AtomU | `<TinyM5BoardAtomU.h>` | no | no | BtnA |
| M5AtomVoice | `<TinyM5BoardAtomVoice.h>` | no | no | BtnA |
| M5AtomS3Lite | `<TinyM5BoardAtomS3Lite.h>` | no | no | BtnA |
| M5AtomS3U | `<TinyM5BoardAtomS3U.h>` | no | no | BtnA |

**Core**

| Board | Include | Screen | Battery | Buttons |
| --- | --- | --- | --- | --- |
| M5Tough | `<TinyM5BoardTough.h>` | yes | yes | BtnPwr |
| M5StackCore2 | `<TinyM5BoardCore2.h>` | yes | yes | BtnPwr |
| M5ToughC5 | `<TinyM5BoardToughC5.h>` | yes | yes | BtnPwr |
| M5ChainCaptain | `<TinyM5BoardChainCaptain.h>` | yes | yes | BtnA, BtnB, BtnC, BtnPwr |
| M5StackCoreS3 | `<TinyM5BoardCoreS3.h>` | yes | yes | BtnPwr |
| M5StackCoreS3SE | `<TinyM5BoardCoreS3SE.h>` | yes | yes | BtnPwr |
| M5StackChan | `<TinyM5BoardStackChan.h>` | yes | yes | BtnPwr |
| M5CoreP4X | `<TinyM5BoardCoreP4X.h>` | yes | yes | BtnPwr |

**Other**

| Board | Include | Screen | Battery | Buttons |
| --- | --- | --- | --- | --- |
| M5TimerCam | `<TinyM5BoardTimerCam.h>` | no | yes | no |
| M5Capsule | `<TinyM5BoardCapsule.h>` | no | yes | BtnA, BtnB |
| M5AirQ | `<TinyM5BoardAirQ.h>` | yes | yes | BtnA, BtnB |
| M5Cardputer | `<TinyM5BoardCardputer.h>` | yes | yes | BtnA |
| M5CardputerADV | `<TinyM5BoardCardputerADV.h>` | yes | yes | BtnA |
| M5VAMeter | `<TinyM5BoardVAMeter.h>` | yes | no | BtnA, BtnB |
| ArduinoNessoN1 | `<TinyM5BoardNessoN1.h>` | yes | yes | BtnA, BtnB |
| M5Dial | `<TinyM5BoardDial.h>` | yes | no | BtnA, BtnB |
| M5DinMeter | `<TinyM5BoardDinMeter.h>` | yes | yes | BtnA, BtnB |
| M5NanoC6 | `<TinyM5BoardNanoC6.h>` | no | no | BtnA |
| M5NanoH2 | `<TinyM5BoardNanoH2.h>` | no | no | BtnA |
| M5Station | `<TinyM5BoardStation.h>` | yes | yes | BtnA, BtnB, BtnC, BtnPwr |
| M5StopWatch | `<TinyM5BoardStopWatch.h>` | yes | yes | BtnA, BtnB, BtnPwr |

**Paper**

| Board | Include | Screen | Battery | Buttons |
| --- | --- | --- | --- | --- |
| M5StackCoreInk | `<TinyM5BoardCoreInk.h>` | yes | yes | BtnA, BtnB, BtnC, BtnExt, BtnPwr |
| M5Paper | `<TinyM5BoardPaper.h>` | yes | yes | BtnA, BtnB, BtnC |
| M5PaperMono | `<TinyM5BoardPaperMono.h>` | yes | yes | BtnA, BtnB, BtnPwr |

**Stamp**

| Board | Include | Screen | Battery | Buttons |
| --- | --- | --- | --- | --- |
| M5StampPico | `<TinyM5BoardStampPico.h>` | no | no | BtnA |
| M5StampS3 | `<TinyM5BoardStampS3.h>` | no | no | BtnA |
| M5StampC3 | `<TinyM5BoardStampC3.h>` | no | no | BtnA |
| M5StampC3U | `<TinyM5BoardStampC3U.h>` | no | no | BtnA |
| M5StampPLC | `<TinyM5BoardStampPLC.h>` | yes | no | BtnA, BtnB, BtnC |

**Stick**

| Board | Include | Screen | Battery | Buttons |
| --- | --- | --- | --- | --- |
| M5StickC Plus2 | `<TinyM5BoardStickCPlus2.h>` | yes | yes | BtnA, BtnB, BtnPwr |
| M5StickC | `<TinyM5BoardStickC.h>` | yes | yes | BtnA, BtnB, BtnPwr |
| M5StickC Plus | `<TinyM5BoardStickCPlus.h>` | yes | yes | BtnA, BtnB, BtnPwr |
| M5StickS3 | `<TinyM5BoardStickS3.h>` | yes | yes | BtnA, BtnB, BtnPwr |

<!-- END BOARD TABLE -->

If yours is missing, open an
[issue](https://github.com/tanakamasayuki/TinyM5Board/issues) with the
name. **Any board whose schematic can be read can be added.** The ones
that cannot be, and why, are in
[docs/DEVELOPMENT_PLAN.ja.md](docs/DEVELOPMENT_PLAN.ja.md) §2-9.

## Requirements

- **arduino-esp32 3.x** (checked against 3.3.11)
- Arduino IDE, arduino-cli or PlatformIO

No library dependencies.

## License

MIT. See [LICENSE](LICENSE).

## For contributors

The internal records are Japanese only and start at
[docs/README.ja.md](docs/README.ja.md). Adding a board is
[docs/BOARD_CATALOG.ja.md](docs/BOARD_CATALOG.ja.md); the tests are
[tests/README.md](tests/README.md).
