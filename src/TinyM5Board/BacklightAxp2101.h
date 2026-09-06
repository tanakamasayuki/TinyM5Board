// TinyM5Board - backlight fed from an AXP2101 rail.
//
// The Core2 v1.1 uses BLDO1 and the CoreS3 DLDO1, with the same curve on
// both: the brightness is an output voltage, 0.5 V to 3.5 V in 100 mV
// steps, and M5GFX maps 0-255 onto it as `(b + 641) >> 5`.
//
// The rail is a template parameter so a board links only its own.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "PowerAxp2101.h"

namespace TinyM5 {

enum class Axp2101Light : uint8_t {
  Bldo1,  ///< Core2 v1.1
  Dldo1,  ///< CoreS3 family
};

}  // namespace TinyM5

template <TinyM5::Axp2101Light CHANNEL>
class TinyM5BoardBacklightAxp2101 {
 public:
  explicit TinyM5BoardBacklightAxp2101(TinyM5BoardPowerAxp2101 &pmic) : _pmic(pmic) {}

  void begin(uint8_t brightness = 128) { set(brightness); }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    auto &reg = _pmic.reg();
    // Both rails are switched from register 0x90, different bits.
    constexpr uint8_t kEnableBit = (CHANNEL == TinyM5::Axp2101Light::Bldo1) ? 0x10 : 0x80;
    constexpr uint8_t kVoltageReg = (CHANNEL == TinyM5::Axp2101Light::Bldo1) ? 0x96 : 0x99;
    brightness ? reg.bitOn(0x90, kEnableBit) : reg.bitOff(0x90, kEnableBit);
    reg.write8(kVoltageReg, level(brightness));
  }

  uint8_t get() const { return _brightness; }

  /// Every backlight answers this, so a sketch can ask without knowing
  /// what is behind it. Only the ones wired to a plain switch say no.
  static constexpr bool dimmable() { return true; }

  /// The rail setting for a brightness, so the curve is checkable without
  /// a chip to talk to.
  static constexpr uint8_t level(uint8_t brightness)
  {
    return brightness ? (uint8_t)((brightness + 641) >> 5) : 0;
  }

 private:
  TinyM5BoardPowerAxp2101 &_pmic;
  uint8_t _brightness = 0;
};
