// TinyM5Board - battery on a boards that has no PMIC.
//
// Ten of the M5 boards read the battery straight off an ADC pin through
// a divider, with no power management chip involved at all. The divider
// ratio is board knowledge and is not always 2: the TimerCam's is 1.513.
//
// Absorbing that difference is the whole point of this class. The sketch
// asks Board.Power.getBatteryVoltage() and does not learn whether the
// answer came from a fuel gauge, a PMIC register or a resistor pair.
//
// Integer arithmetic only. Half the M5 line-up is RISC-V with no FPU, so
// a float here would pull in the soft-float library. The ratio is
// therefore carried as parts per thousand.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"

class TinyM5BoardPowerAdc {
 public:
  /// `ratioX1000` is the divider ratio times 1000 - 2000 for a plain
  /// half-divider, 1513 for the TimerCam.
  constexpr TinyM5BoardPowerAdc(int8_t pin, uint16_t ratioX1000)
      : _pin(pin), _ratio(ratioX1000)
  {
  }

  bool begin() { return true; }

  /// Battery voltage in mV, or 0 when it cannot be read.
  int16_t getBatteryVoltage()
  {
    // The Arduino core owns the attenuation and the calibration; reading
    // through analogReadMilliVolts keeps that ownership rather than
    // fighting it with per-pin overrides.
    const uint32_t mv = analogReadMilliVolts(_pin);
    return (int16_t)((mv * _ratio) / 1000);
  }

  /// 0-100, or -1 when the voltage cannot be read.
  ///
  /// The curve is M5Unified's (Power_Class.cpp:2345), kept identical so
  /// that the two libraries report the same number on the same board.
  /// Note the asymmetric constants - the span is 4150-3350 while the
  /// offset is 3300. That is what upstream does, and matching it matters
  /// more here than tidying it.
  int32_t getBatteryLevel()
  {
    const int32_t mv = getBatteryVoltage();
    if (mv <= 0) return -1;
    const int32_t level = (mv - 3300) * 100 / (4150 - 3350);
    return level < 0 ? 0 : (level > 100 ? 100 : level);
  }

  /// Not knowable without a PMIC: a bare divider sees the pack voltage
  /// and nothing about current direction.
  TinyM5::Charge isCharging() const { return TinyM5::Charge::Unknown; }

  TinyM5::Pmic getType() const { return TinyM5::Pmic::Adc; }

  int8_t getAdcPin() const { return _pin; }
  uint16_t getAdcRatioX1000() const { return _ratio; }

 private:
  int8_t _pin;
  uint16_t _ratio;
};
