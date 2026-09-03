// TinyM5Board - the Core2's backlight.
//
// A thin face over TinyM5BoardPowerCore2, which is where the two chips'
// rails and curves live. It exists so that `Board.Backlight.set()` reads
// the same on the Core2 as on every other board, even though behind it
// the brightness is a DC3 duty on one unit and a BLDO1 voltage on the
// next.
#pragma once

#include <stdint.h>

#include "PowerCore2.h"

class TinyM5BoardBacklightCore2 {
 public:
  explicit TinyM5BoardBacklightCore2(TinyM5BoardPowerCore2 &power) : _power(power) {}

  void begin(uint8_t brightness = 128) { set(brightness); }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    _power.setBacklight(brightness);
  }

  uint8_t get() const { return _brightness; }

 private:
  TinyM5BoardPowerCore2 &_power;
  uint8_t _brightness = 0;
};
