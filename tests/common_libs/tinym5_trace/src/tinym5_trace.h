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
// Known gap: Wire.begin() is not hookable, so it does not appear in the
// ordered part of the trace. The pins and clock it left behind are
// recorded in the state section instead. Every I2C *transaction* is
// ordered correctly, which is what matters for a rail bring-up sequence.
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
  Wire.setWriteHook(onI2cWrite<0>);
  Wire.setReadHook(onI2cRead<0>);
  Wire1.setWriteHook(onI2cWrite<1>);
  Wire1.setReadHook(onI2cRead<1>);
  line("--- begin() ---");
}

inline void bus(const char *label, TwoWire &w)
{
  if (!w.begun()) {
    line("%s: not begun", label);
    return;
  }
  line("%s: begun sda=%d scl=%d hz=%u", label, w.sda(), w.scl(), (unsigned)w.getClock());
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
  line("has display=%d backlight=%d battery=%d extI2c=%d shared=%d",
       TINYM5_BOARD::kHasDisplay, TINYM5_BOARD::kHasBacklight,
       TINYM5_BOARD::kHasBattery, TINYM5_BOARD::kHasExternalI2c,
       TINYM5_BOARD::kSharesI2cBus);
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
  line("--- state ---");
  bus("i2c0", Wire);
  bus("i2c1", Wire1);
  HostArduino::clearPinHooks();
  Wire.clearHooks();
  Wire1.clearHooks();
  if (file()) {
    fclose(file());
    file() = nullptr;
  }
  Serial.printf("TEST done %s\n", name());
}

}  // namespace TinyM5Trace
