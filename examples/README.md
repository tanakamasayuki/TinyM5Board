# Examples

> 日本語: [README.ja.md](README.ja.md) · New here? [the guide](../docs/GUIDE.md)

**One per feature, with the board as a single line to change.**

There is no example per board: forty of them would still leave someone
unable to find theirs. What these show instead is **that the same sketch
runs on all of them**. Change the include at the top to your board.

| | What it shows |
| --- | --- |
| **[Hello](Hello/Hello.ino)** | Bring-up and the pinout. **It uses no screen** - more of these boards have none than have one |
| **[Buttons](Buttons/Buttons.ino)** | A GPIO button, a key inside a power chip and a line on an expander, **read by the same six lines** |
| **[Battery](Battery/Battery.ino)** | The **same questions** to a divider, an AXP192, an AXP2101, an M5PM1 and an AW32001 |
| **[Backlight](Backlight/Backlight.ino)** | A PWM pin, a rail voltage, a channel inside an expander and a plain switch, through **one `set()`** |

## Running them

In the Arduino IDE: **File → Examples → TinyM5Board**, change the include
at the top, upload.

With arduino-cli, each example carries its own `sketch.yaml`:

```sh
cd examples/Hello
arduino-cli compile -u -p /dev/ttyUSB0
```

That file **pins the default board and the core version**. For another
board, pass `--fqbn` or edit it.

## The shape they share

**Hardware a board does not have is avoided with `#if`, and said so.**

```cpp
#if TINYM5_HAS_BATTERY
  Serial.printf("%d mV\n", Board.Power.getBatteryVoltage());
#else
  Serial.println("this board has no battery");
#endif
```

`if constexpr` will not do: both arms still go through name lookup. The
reasoning is in [the guide](../docs/GUIDE.md) and the
[API reference](../docs/API.md).
