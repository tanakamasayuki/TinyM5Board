// TinyM5Board - AW32001 charger, with the BQ27220 gauge beside it.
//
// Two chips answering as one `Board.Power`, because neither is enough on
// its own: the AW32001 controls the charge and reports whether it is
// running, and knows nothing about the pack's voltage; the BQ27220
// measures the pack and does not charge it. Upstream wires them together
// the same way (Power_Class.cpp, the NessoN1 and Tab5 cases).
//
// The class is named for the charger because that is the chip a board
// picks: the gauge is what M5Stack puts next to it.
#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <stdint.h>

#include "Common.h"
#include "I2cReg.h"

class TinyM5BoardPowerAw32001 {
 public:
  static constexpr uint8_t kAddress = 0x49;      ///< the charger
  static constexpr uint8_t kGaugeAddress = 0x55; ///< the gauge
  static constexpr uint8_t kChipId = 0x49;       ///< reg 0x0A, same as the address

  constexpr TinyM5BoardPowerAw32001() = default;

  void attach(TwoWire &wire)
  {
    _reg.attach(wire, kAddress);
    _gauge.attach(wire, kGaugeAddress);
  }

  bool probe(TwoWire &wire)
  {
    attach(wire);
    return _reg.read8(0x0A, 0x00) == kChipId;
  }

  bool begin(TwoWire &wire)
  {
    if (!probe(wire)) return false;
    init();
    return true;
  }

  void init()
  {
    // The charge-safety timer resets the charger on its own if nothing
    // acknowledges it. Boards that sit on a bench charging slowly hit it.
    _reg.write8(0x05, (uint8_t)(_reg.read8(0x05) & 0x1F));
    _ok = true;
  }

  bool isPresent() const { return _ok; }
  TinyM5::Pmic getType() const { return TinyM5::Pmic::Aw32001; }

  // ---- battery ----

  /// Millivolts, straight from the gauge (BQ27220 register 0x08, little
  /// endian). The charger cannot answer this.
  int16_t getBatteryVoltage()
  {
    uint8_t buf[2] = {0, 0};
    if (!_gauge.read(0x08, buf, sizeof(buf))) return 0;
    return (int16_t)((uint16_t)buf[0] | ((uint16_t)buf[1] << 8));
  }

  /// The gauge reports a current but no percentage, so this is the same
  /// estimate from voltage the other gaugeless boards use.
  int32_t getBatteryLevel()
  {
    const int32_t mv = getBatteryVoltage();
    if (mv <= 0) return -1;
    const int32_t level = (mv - 3300) * 100 / (4150 - 3350);
    return level < 0 ? 0 : (level > 100 ? 100 : level);
  }

  /// Signed: negative while the pack is being charged.
  int16_t getBatteryCurrent()
  {
    uint8_t buf[2] = {0, 0};
    if (!_gauge.read(0x14, buf, sizeof(buf))) return 0;
    return (int16_t)((uint16_t)buf[0] | ((uint16_t)buf[1] << 8));
  }

  /// Status bits 4:3 of register 0x08: 0 idle, 1 pre-charge, 2 charging,
  /// 3 done. The first and the last are both "not charging" to a sketch.
  TinyM5::Charge isCharging()
  {
    const uint8_t state = (uint8_t)((_reg.read8(0x08) >> 3) & 0b11);
    return (state == 1 || state == 2) ? TinyM5::Charge::Charging
                                      : TinyM5::Charge::Discharging;
  }

  // ---- charging ----

  /// Bit 3 of the power configuration register is charge *disable*.
  void setBatteryCharge(bool enable)
  {
    enable ? _reg.bitOff(0x01, 1 << 3) : _reg.bitOn(0x01, 1 << 3);
  }

  /// 8 to 512 mA, in steps of 8.
  void setChargeCurrent(uint16_t mA)
  {
    int value = mA / 8;
    if (value > 0) --value;
    if (value > 63) value = 63;
    _reg.write8(0x02, (uint8_t)value);
  }

  /// 3600 to 4545 mV, in steps of 15. The top two bits of the register
  /// are something else and are left alone.
  void setChargeVoltage(uint16_t mV)
  {
    int value = ((int)mV - 3600) / 15;
    if (value > 0) --value;
    if (value < 0) value = 0;
    if (value > 63) value = 63;
    _reg.write8(0x04, (uint8_t)((_reg.read8(0x04) & 0xC0) | value));
  }

  TinyM5::I2cReg &reg() { return _reg; }
  TinyM5::I2cReg &gauge() { return _gauge; }

 private:
  TinyM5::I2cReg _reg;
  TinyM5::I2cReg _gauge;
  bool _ok = false;
};
