// Records what Board.begin() does, so that a host run can be diffed
// against a golden file.
//
// Everything here rides on the bus observation port that
// host-arduino-core provides: the GPIO half in <HostBus.h>, the I2C half
// on TwoWire. There is no instrumentation inside TinyM5Board itself - the
// library under test is compiled exactly as a sketch would compile it.
//
// The trace is written to output/trace.txt next to the sketch and echoed
// to serial, matching how the other host tests in this repository report.
//
// All four halves of the port are recorded into one ordered stream, which
// is the whole point: what a bring-up gets wrong is usually the order.
// host-arduino-core 1.6.0 closed the two gaps that used to leave holes in
// it - `Wire.begin()` now announces itself through a lifecycle hook, and
// the analog / PWM half makes a backlight being configured and lit
// visible instead of silent.
#pragma once

#include <Arduino.h>
#include <HostBus.h>
#include <Wire.h>
#include <stdarg.h>
#include <stdio.h>
#include <sys/stat.h>

namespace TinyM5Trace {

inline FILE *&file()
{
  static FILE *f = nullptr;
  return f;
}

inline void line(const char *fmt, ...)
{
  char buf[256];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  if (file()) {
    fprintf(file(), "%s\n", buf);
  }
  Serial.println(buf);
}

inline const char *modeName(uint8_t mode)
{
  switch (mode) {
    case INPUT: return "INPUT";
    case OUTPUT: return "OUTPUT";
    case INPUT_PULLUP: return "INPUT_PULLUP";
#ifdef INPUT_PULLDOWN
    case INPUT_PULLDOWN: return "INPUT_PULLDOWN";
#endif
    default: return "?";
  }
}

/// A device model the test can put on the bus. Returning `handled=false`
/// leaves the address unanswered, which is the honest reply for a board
/// with nothing on that bus. A board with a PMIC installs one of these so
/// that the chip-detection branch can be driven both ways.
struct Device {
  uint8_t (*onWrite)(uint8_t bus, uint8_t addr, const uint8_t *data, size_t len);
  size_t (*onRead)(uint8_t bus, uint8_t addr, uint8_t *data, size_t len);
};

inline Device &device()
{
  static Device d = {nullptr, nullptr};
  return d;
}

inline void hex(char *out, size_t outlen, const uint8_t *data, size_t len)
{
  size_t n = 0;
  for (size_t i = 0; i < len && n + 3 < outlen; ++i) {
    n += snprintf(out + n, outlen - n, i ? " %02X" : "%02X", data[i]);
  }
  out[n] = 0;
}

inline void onI2cLifecycle(TwoWire::LifecycleEvent event, const TwoWire &wire, void *)
{
  const uint8_t bus = wire.busNum();
  switch (event) {
    case TwoWire::kBegin:
      line("i2c%u begin sda=%d scl=%d hz=%u", bus, wire.sda(), wire.scl(),
           (unsigned)wire.getClock());
      break;
    case TwoWire::kEnd: line("i2c%u end", bus); break;
    case TwoWire::kSetPins:
      line("i2c%u pins sda=%d scl=%d", bus, wire.sda(), wire.scl());
      break;
    case TwoWire::kSetClock: line("i2c%u clock hz=%u", bus, (unsigned)wire.getClock()); break;
    case TwoWire::kSetTimeout: break;  // not board data
  }
}

inline void onAnalogWrite(HostArduino::AnalogWriteEvent event,
                          const HostArduino::AnalogOut &out, void *)
{
  switch (event) {
    case HostArduino::kAnalogAttach:
      line("pwm attach pin=%u ch=%u freq=%u res=%u", out.pin, out.channel,
           (unsigned)out.frequency, out.resolution);
      break;
    case HostArduino::kAnalogConfig:
      line("pwm config pin=%u freq=%u res=%u", out.pin, (unsigned)out.frequency,
           out.resolution);
      break;
    case HostArduino::kAnalogWrite:
      line("pwm write  pin=%u duty=%u", out.pin, (unsigned)out.duty);
      break;
    case HostArduino::kAnalogDetach: line("pwm detach pin=%u", out.pin); break;
    case HostArduino::kAnalogTone:
      line("pwm tone   pin=%u freq=%u", out.pin, (unsigned)out.frequency);
      break;
    case HostArduino::kAnalogDac: line("dac write  pin=%u value=%u", out.pin, (unsigned)out.duty); break;
  }
}

inline void onPinMode(uint8_t pin, uint8_t mode, void *)
{
  line("pinMode(%u, %s)", pin, modeName(mode));
}

inline void onPinWrite(uint8_t pin, uint8_t value, void *)
{
  line("digitalWrite(%u, %u)", pin, value);
}

template <uint8_t BUS>
uint8_t onI2cWrite(uint8_t addr, const uint8_t *data, size_t len, bool stop, void *)
{
  char buf[192];
  hex(buf, sizeof(buf), data, len);
  line("i2c%u write 0x%02X [%s]%s", BUS, addr, buf, stop ? "" : " (no stop)");
  return device().onWrite ? device().onWrite(BUS, addr, data, len) : 2;
}

template <uint8_t BUS>
size_t onI2cRead(uint8_t addr, uint8_t *data, size_t len, bool stop, void *)
{
  (void)stop;
  const size_t n = device().onRead ? device().onRead(BUS, addr, data, len) : 0;
  char buf[192];
  hex(buf, sizeof(buf), data, n);
  line("i2c%u read  0x%02X %u -> [%s]", BUS, addr, (unsigned)len, buf);
  return n;
}

inline const char *&name()
{
  static const char *n = "";
  return n;
}

/// Start recording. Call before Board.begin().
///
/// The board name goes on the TEST lines because pytest-embedded shares
/// one expect buffer across the session: a bare "TEST done" would be
/// matched against the previous board's run and the test would read a
/// trace that had not been written yet.
inline void start(const char *board)
{
  name() = board;
  mkdir("output", 0755);
  file() = fopen("output/trace.txt", "w");
  Serial.printf("TEST start %s\n", board);
  HostArduino::resetPinState();
  HostArduino::setPinModeHook(onPinMode);
  HostArduino::setPinWriteHook(onPinWrite);
  HostArduino::setAnalogWriteHook(onAnalogWrite);
  Wire.setWriteHook(onI2cWrite<0>);
  Wire.setReadHook(onI2cRead<0>);
  Wire.setLifecycleHook(onI2cLifecycle);
  Wire1.setWriteHook(onI2cWrite<1>);
  Wire1.setReadHook(onI2cRead<1>);
  Wire1.setLifecycleHook(onI2cLifecycle);
  line("--- begin() ---");
}

/// Stop recording and close the trace.
///
/// The board's own data goes in as well as the bus traffic. A wrong
/// panel offset or a wrong I2C pin is exactly the sort of thing that
/// never shows up as a crash, and the catalogue is the product - so the
/// golden covers it rather than only covering the sequence.
inline void finish()
{
  line("--- board ---");
  line("name=%s id=%d", TINYM5_BOARD::kName, (int)TINYM5_BOARD::kBoardId);
  line("pins i2c=%d/%d ext=%d/%d led=%d/%u hold=%d", TINYM5_BOARD::kI2cSda,
       TINYM5_BOARD::kI2cScl, TINYM5_BOARD::kI2cExtSda, TINYM5_BOARD::kI2cExtScl,
       TINYM5_BOARD::kRgbLed, TINYM5_BOARD::kRgbLedCount, TINYM5_BOARD::kPowerHold);
  line("has display=%d backlight=%d battery=%d intI2c=%d extI2c=%d shared=%d",
       TINYM5_BOARD::kHasDisplay, TINYM5_BOARD::kHasBacklight,
       TINYM5_BOARD::kHasBattery, TINYM5_BOARD::kHasInternalI2c,
       TINYM5_BOARD::kHasExternalI2c, TINYM5_BOARD::kSharesI2cBus);
#if TINYM5_HAS_DISPLAY
  {
    const auto d = TINYM5_BOARD::display();
    line("--- display ---");
    line("spi mosi=%d miso=%d sclk=%d dc=%d cs=%d rst=%d 3wire=%d", d.mosi, d.miso,
         d.sclk, d.dc, d.cs, d.rst, d.threeWire);
    line("freq write=%u read=%u", (unsigned)d.freqWrite, (unsigned)d.freqRead);
    line("panel %ux%u offset=%u,%u rotation=%u invert=%d", d.width, d.height,
         d.offsetX, d.offsetY, d.rotation, d.invert);
  }
#endif
#if TINYM5_HAS_BATTERY
  // What the board makes of a known reading. The divider ratio and the
  // chip's LSB size are board and chip data that nothing else in the
  // trace would exercise - a wrong ratio reports a plausible-looking
  // voltage rather than failing.
  line("--- battery ---");
  line("mV=%d level=%d", (int)Board.Power.getBatteryVoltage(),
       (int)Board.Power.getBatteryLevel());
#endif
  HostArduino::clearPinHooks();
  HostArduino::clearAnalogHooks();
  Wire.clearHooks();
  Wire.setLifecycleHook(nullptr);
  Wire1.clearHooks();
  Wire1.setLifecycleHook(nullptr);
  if (file()) {
    fclose(file());
    file() = nullptr;
  }
  Serial.printf("TEST done %s\n", name());
}

}  // namespace TinyM5Trace
