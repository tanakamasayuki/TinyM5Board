// TinyM5Board - backlight fed from an AXP192 rail.
//
// Three boards, three different rails, three different curves - and none
// of them is a duty cycle. The StickC dims its panel by moving LDO2's
// output voltage, the Tough uses LDO3, the Core2 uses DC3. `Board.
// Backlight.set()` is the same call on all of them, which is the point
// of having a board layer at all.
//
// The curves are M5GFX's (Light_M5StickC / Light_M5Tough /
// Light_M5StackCore2), kept identical so a board looks the same
// brightness under either library. All integer.
//
// The channel is a template parameter rather than a runtime switch, so a
// board links only the curve it actually uses.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "PowerAxp192.h"

namespace TinyM5 {

/// Which rail on the AXP192 feeds the backlight.
enum class Axp192Light : uint8_t {
  Ldo2,  ///< StickC / StickC Plus
  Ldo3,  ///< Tough / Station
  Dc3,   ///< Core2 v1.0
};

}  // namespace TinyM5

template <TinyM5::Axp192Light CHANNEL>
class TinyM5BoardBacklightAxp192 {
 public:
  explicit TinyM5BoardBacklightAxp192(TinyM5BoardPowerAxp192 &pmic) : _pmic(pmic) {}

  void begin(uint8_t brightness = 128) { set(brightness); }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    auto &reg = _pmic.reg();
    const uint8_t value = level(brightness);

    if constexpr (CHANNEL == TinyM5::Axp192Light::Ldo2) {
      brightness ? reg.bitOn(0x12, TinyM5BoardPowerAxp192::Ldo2)
                 : reg.bitOff(0x12, TinyM5BoardPowerAxp192::Ldo2);
      // Upper nibble is LDO2; the lower one is LDO3 and must survive.
      reg.write8(0x28, (uint8_t)(value << 4), 0x0F);
    } else if constexpr (CHANNEL == TinyM5::Axp192Light::Ldo3) {
      brightness ? reg.bitOn(0x12, TinyM5BoardPowerAxp192::Ldo3)
                 : reg.bitOff(0x12, TinyM5BoardPowerAxp192::Ldo3);
      reg.write8(0x28, value, 0xF0);
    } else {
      brightness ? reg.bitOn(0x12, TinyM5BoardPowerAxp192::Dcdc3)
                 : reg.bitOff(0x12, TinyM5BoardPowerAxp192::Dcdc3);
      reg.write8(0x27, value, 0x80);
    }
  }

  uint8_t get() const { return _brightness; }

  /// Every backlight answers this, so a sketch can ask without knowing
  /// what is behind it. Only the ones wired to a plain switch say no.
  static constexpr bool dimmable() { return true; }

  /// The rail setting for a brightness, exposed so the curve can be
  /// checked without a chip to talk to.
  static constexpr uint8_t level(uint8_t brightness)
  {
    if (!brightness) return 0;
    if constexpr (CHANNEL == TinyM5::Axp192Light::Ldo2) {
      return (uint8_t)((((brightness >> 1) + 8) / 13) + 5);
    } else if constexpr (CHANNEL == TinyM5::Axp192Light::Ldo3) {
      return brightness > 4 ? (uint8_t)((brightness / 24) + 5) : brightness;
    } else {
      return (uint8_t)((brightness >> 3) + 72);
    }
  }

 private:
  TinyM5BoardPowerAxp192 &_pmic;
  uint8_t _brightness = 0;
};
