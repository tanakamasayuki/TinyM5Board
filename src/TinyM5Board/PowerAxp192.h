// TinyM5Board - AXP192 power management chip.
//
// Fitted to the StickC, the StickC Plus, the Core2 v1.0, the Tough and
// the Station. Which rail feeds what is board knowledge and lives in the
// board header; this file only knows the chip.
//
// Two things about it shape the API above.
//
// The AXP192 has no fuel gauge. A percentage is an estimate from the
// voltage and swings with load, which is why getBatteryVoltage() is the
// primary reading and getBatteryLevel() is the convenience on top. A
// design that only reports a percentage is unusable on this chip.
//
// The power key never reaches a GPIO on the Stick. It latches in reg 0x46
// and is cleared by writing the bits back, so a press survives until it
// is read - which is what lets Board.BtnPwr behave like the plain GPIO
// button on the StickC Plus2 next to it.
//
// Integer arithmetic throughout: half the M5 line-up has no FPU.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"
#include "I2cReg.h"

class TinyM5BoardPowerAxp192 {
 public:
  static constexpr uint8_t kAddress = 0x34;
  static constexpr uint8_t kChipId = 0x03;

  /// Output rails, as bits of register 0x12. A board header names the
  /// ones its schematic actually uses.
  enum Rail : uint8_t {
    Dcdc1 = 1 << 0,
    Dcdc3 = 1 << 1,
    Ldo2 = 1 << 2,
    Ldo3 = 1 << 3,
    Dcdc2 = 1 << 4,
    Exten = 1 << 6,
  };

  constexpr explicit TinyM5BoardPowerAxp192(uint8_t rails) : _rails(rails) {}

  /// Returns false when nothing answers as an AXP192 at 0x34. On these
  /// boards the chip is soldered on, so that is a real fault rather than
  /// a missing option.
  bool begin(TwoWire &wire)
  {
    _reg.attach(wire, kAddress);
    if (_reg.read8(0x03, 0xFF) != kChipId) return false;
    _reg.bitOn(0x12, _rails);
    // The battery ADCs are off out of reset; without this every reading
    // comes back 0.
    _reg.write8(0x82, 0xFF);
    _ok = true;
    return true;
  }

  bool isPresent() const { return _ok; }
  TinyM5::Pmic getType() const { return TinyM5::Pmic::Axp192; }

  // ---- readings ----

  /// Battery voltage in mV. 12-bit at 1.1 mV per count.
  int16_t getBatteryVoltage() { return (int16_t)((_reg.read12(0x78) * 11) / 10); }

  /// + charging, - discharging, in mA. 13-bit at 0.5 mA per count.
  int32_t getBatteryCurrent()
  {
    const int32_t charge = _reg.read13(0x7A);
    if (charge) return charge / 2;
    return -(int32_t)(_reg.read13(0x7C) / 2);
  }

  /// VBUS voltage in mV. 12-bit at 1.7 mV per count.
  int16_t getVBUSVoltage() { return (int16_t)((_reg.read12(0x5A) * 17) / 10); }

  /// 0-100, or -1 when the voltage cannot be read. Same curve as
  /// M5Unified so both libraries report the same number.
  int32_t getBatteryLevel()
  {
    const int32_t mv = getBatteryVoltage();
    if (mv <= 0) return -1;
    const int32_t level = (mv - 3300) * 100 / (4150 - 3350);
    return level < 0 ? 0 : (level > 100 ? 100 : level);
  }

  TinyM5::Charge isCharging()
  {
    return (_reg.read8(0x00) & 0x04) ? TinyM5::Charge::Charging
                                     : TinyM5::Charge::Discharging;
  }

  bool isVBUSPresent() { return (_reg.read8(0x00) & 0x20) != 0; }
  bool isBatteryPresent() { return (_reg.read8(0x01) & 0x20) != 0; }

  // ---- settings ----

  void setBatteryCharge(bool enable)
  {
    enable ? _reg.bitOn(0x33, 0x80) : _reg.bitOff(0x33, 0x80);
  }

  /// Target charge current. The chip's steps are not linear, so the value
  /// is rounded down to the nearest one it can actually do.
  void setChargeCurrent(uint16_t max_mA)
  {
    static constexpr uint16_t steps[] = {100, 190, 280, 360, 450, 550, 630, 700,
                                         780, 880, 960, 1000, 1080, 1160, 1240, 1320};
    uint8_t n = 0;
    while (n < 15 && steps[n + 1] <= max_mA) ++n;
    _reg.write8(0x33, n, 0xF0);
  }

  /// 4100 / 4150 / 4200 / 4360 mV, rounded down.
  void setChargeVoltage(uint16_t max_mV)
  {
    const uint8_t n = max_mV >= 4360 ? 3 : max_mV >= 4200 ? 2 : max_mV >= 4150 ? 1 : 0;
    _reg.write8(0x33, (uint8_t)(n << 5), 0x9F);
  }

  /// Charging for the RTC backup cell. Left off, the clock does not
  /// survive a power cycle.
  void setRtcBackupCharge(bool enable)
  {
    enable ? _reg.bitOn(0x35, 0x80) : _reg.bitOff(0x35, 0x80);
  }

  void powerOff() { _reg.bitOn(0x32, 0x80); }

  /// The power key. bit0 long press, bit1 short press. Latched until
  /// read; reading clears it.
  uint8_t getKeyState()
  {
    const uint8_t val = _reg.read8(0x46) & 0x03;
    if (val) _reg.write8(0x46, val);
    return val;
  }

  /// For the backlight classes that drive an LDO on this chip.
  TinyM5::I2cReg &reg() { return _reg; }

 private:
  TinyM5::I2cReg _reg;
  uint8_t _rails;
  bool _ok = false;
};
