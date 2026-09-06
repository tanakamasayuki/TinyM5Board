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

/// Which chip answers the power questions. Same shape as M5Unified's
/// `pmic_t`, so `Board.Power.getType()` transfers.
enum class Pmic : uint8_t {
  Unknown,
  Adc,  ///< no chip at all - a divider straight onto an ADC pin
  Axp192,
  Axp2101,
  M5pm1,
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
///
/// There is no backlight pin here on purpose. On more than half the
/// boards with a screen the backlight is a PMIC LDO or an expander's PWM
/// channel rather than a pin, and `Board.Backlight` is the one way to
/// reach all of them. Handing the pin to a graphics library as well would
/// give the brightness two owners.
struct Display {
  int8_t mosi, miso, sclk, dc, cs;
  int8_t rst;  ///< always -1: begin() has already pulsed it. Do not touch
  /// The panel's BUSY line, and -1 on the panels that do not have one.
  /// Only the electrophoretic displays do: a refresh takes hundreds of
  /// milliseconds and the controller holds this line while it runs.
  /// begin() never waits on it - that is the driver's business - but the
  /// pin is board knowledge and nothing else would report it.
  int8_t busy;
  uint32_t freqWrite, freqRead;
  uint16_t width, height, offsetX, offsetY;
  uint8_t rotation;
  bool invert;
  /// One data line for both directions: reads come back on MOSI. The
  /// Stick panels are wired this way and a bus set up for four wires
  /// will not read from them.
  bool threeWire;
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
