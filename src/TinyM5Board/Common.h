// TinyM5Board - shared types.
//
// Included by every board header. It knows nothing about any particular
// board, and nothing about any graphics library.
//
// This is NOT the entry point. A sketch includes either the board header
// it wants (<TinyM5BoardAtomLite.h>) or <TinyM5Board.h> after defining
// the board macro. Including this file alone gets you the types and no
// board.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "BoardId.h"

namespace TinyM5 {

/// Which product line a board belongs to. This is how a user finds their
/// own board, so it follows the product names rather than the features -
/// the Atom family holds both the AtomS3 (a screen) and the AtomLite
/// (none), and `kHasDisplay` is what tells those apart.
enum class Family : uint8_t {
  Core,
  Stick,
  Atom,
  Stamp,
  Paper,
  Unit,
  Other,
};

/// Charge state. Same shape as M5Unified's `is_charging_t`.
enum class Charge : uint8_t {
  Unknown,
  Discharging,
  Charging,
};

/// Pins that can be looked up by name. Deliberately short: everything
/// here has a table in M5Unified to transcribe from, and a pinout that is
/// wrong is worse than no pinout at all. The IMU and the RTC are absent
/// on purpose - M5Unified does not expose them either, and the chip that
/// answers on those pins changes between production runs.
enum class Pin : uint8_t {
  InI2cSda,
  InI2cScl,
  ExI2cSda,
  ExI2cScl,
  RgbLed,
  PowerHold,
};

/// What `begin()` should leave alone. By default it brings up everything
/// it knows about, because it runs first and anything it clobbers can be
/// set up again afterwards.
enum Init : uint8_t {
  InitDefault = 0,
  KeepSerial = 1 << 0,  ///< Serial is already open at the baud you want
  KeepI2c = 1 << 1,     ///< Wire / Wire1 are already begun
};

/// Display particulars, handed to whatever graphics library the sketch
/// uses. This library owns no panel driver and draws nothing.
struct Display {
  int8_t mosi, miso, sclk, dc, cs;
  int8_t rst;        ///< -1 = begin() has already reset it; do not touch
  int8_t backlight;  ///< -1 = not a PWM pin; use Board.Backlight
  uint32_t freqWrite, freqRead;
  uint16_t width, height, offsetX, offsetY;
  uint8_t rotation;
  bool invert;
};

/// Drive a reset line low and back. Board headers call this rather than
/// spelling out the pulse, so the timing lives in one place.
inline void resetPulse(int8_t pin, uint16_t lowMs = 2, uint16_t settleMs = 10)
{
  if (pin < 0) return;
  pinMode(pin, OUTPUT);
  digitalWrite(pin, HIGH);
  delay(1);
  digitalWrite(pin, LOW);
  delay(lowMs);
  digitalWrite(pin, HIGH);
  delay(settleMs);
}

/// GPIO 34-39 on the original ESP32 are input-only and carry no internal
/// pull resistors, so a button on one of them has to be plain INPUT. This
/// is a property of the SoC, so it is derived here rather than being
/// carried as a column in the board catalogue.
constexpr uint8_t buttonPinMode(int8_t pin, bool esp32Classic)
{
  return (esp32Classic && pin >= 34 && pin <= 39) ? INPUT : INPUT_PULLUP;
}

}  // namespace TinyM5
