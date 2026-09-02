// TinyM5Board - backlight fed from an AXP192 LDO.
//
// On the StickC and the StickC Plus the panel's backlight is LDO2, so
// "brightness" is an output voltage rather than a duty cycle: 1.8 V plus
// 0.1 V per step, and the useful range is steps 5 to 15.
//
// The curve is M5GFX's (Light_M5StickC), kept identical so a board looks
// the same brightness under either library. Zero switches the rail off
// rather than driving it to its floor.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "PowerAxp192.h"

class TinyM5BoardBacklightAxp192 {
 public:
  explicit TinyM5BoardBacklightAxp192(TinyM5BoardPowerAxp192 &pmic) : _pmic(pmic) {}

  void begin(uint8_t brightness = 128) { set(brightness); }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    auto &reg = _pmic.reg();
    if (brightness) {
      reg.bitOn(0x12, TinyM5BoardPowerAxp192::Ldo2);
    } else {
      reg.bitOff(0x12, TinyM5BoardPowerAxp192::Ldo2);
    }
    // Upper nibble is LDO2; the lower one is LDO3 and must survive.
    reg.write8(0x28, (uint8_t)(step(brightness) << 4), 0x0F);
  }

  uint8_t get() const { return _brightness; }

  /// The LDO step for a brightness, exposed so the curve can be checked
  /// without a chip to talk to.
  static constexpr uint8_t step(uint8_t brightness)
  {
    return brightness ? (uint8_t)((((brightness >> 1) + 8) / 13) + 5) : 0;
  }

 private:
  TinyM5BoardPowerAxp192 &_pmic;
  uint8_t _brightness = 0;
};
