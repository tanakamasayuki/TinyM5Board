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

  /// `ldo2mV` / `ldo3mV` are applied *before* the rails are switched on,
  /// which is the order M5GFX uses: bringing a rail up at its reset
  /// voltage and correcting it afterwards puts the wrong voltage on the
  /// panel for a moment. Zero leaves a rail's voltage alone.
  constexpr explicit TinyM5BoardPowerAxp192(uint8_t rails, uint16_t ldo2mV = 0,
                                            uint16_t ldo3mV = 0)
      : _rails(rails), _ldo2mV(ldo2mV), _ldo3mV(ldo3mV)
  {
  }

  /// Returns false when nothing answers as an AXP192 at 0x34. On these
  /// boards the chip is soldered on, so that is a real fault rather than
  /// a missing option.
  bool begin(TwoWire &wire)
  {
    _reg.attach(wire, kAddress);
    if (_reg.read8(0x03, 0xFF) != kChipId) return false;
    if (_ldo2mV) setLdo2Millivolt(_ldo2mV);
    if (_ldo3mV) setLdo3Millivolt(_ldo3mV);
    if (_rails) _reg.bitOn(0x12, _rails);
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

  // ---- the chip's own GPIOs ----
  //
  // On the Core2 and the Tough these are not spare pins: IO4 is the LCD
  // reset line and IO1 is the touch controller's. That is why those
  // boards report `display().rst == -1` - the reset has already happened
  // over I2C by the time a graphics library sees the panel, and there is
  // no pin for it to pulse.

  enum class Gpio : uint8_t { Io0, Io1, Io2, Io3, Io4 };

  /// Configure as a push-pull output.
  void gpioOutput(Gpio gpio)
  {
    switch (gpio) {
      case Gpio::Io0: _reg.write8(0x90, 0x02, 0xF8); break;
      case Gpio::Io1: _reg.write8(0x92, 0x02, 0xF8); break;
      case Gpio::Io2: _reg.write8(0x93, 0x02, 0xF8); break;
      // IO3 and IO4 share one register: bit7 turns the pair on, and two
      // bits each select the function.
      case Gpio::Io3: _reg.write8(0x95, 0x81, 0x7C); break;
      case Gpio::Io4: _reg.write8(0x95, 0x84, 0x72); break;
    }
  }

  /// Configure as an open-drain output. The Tough's touch reset needs
  /// this rather than push-pull.
  void gpioOpenDrain(Gpio gpio)
  {
    switch (gpio) {
      case Gpio::Io0: _reg.write8(0x90, 0x00, 0xF8); break;
      case Gpio::Io1: _reg.write8(0x92, 0x00, 0xF8); break;
      case Gpio::Io2: _reg.write8(0x93, 0x00, 0xF8); break;
      default: break;  // IO3 / IO4 have no open-drain mode
    }
  }

  void gpioWrite(Gpio gpio, bool level)
  {
    // IO0-2 signal in 0x94, IO3-4 in 0x96.
    const bool high = (uint8_t)gpio >= (uint8_t)Gpio::Io3;
    const uint8_t reg = high ? 0x96 : 0x94;
    const uint8_t bit = (uint8_t)(1u << ((uint8_t)gpio - (high ? 3 : 0)));
    level ? _reg.bitOn(reg, bit) : _reg.bitOff(reg, bit);
  }

  /// Reset pulse on one of the chip's GPIOs, matching TinyM5::resetPulse
  /// for a real pin.
  void gpioResetPulse(Gpio gpio, uint16_t lowMs = 2, uint16_t settleMs = 10)
  {
    gpioWrite(gpio, true);
    delay(1);
    gpioWrite(gpio, false);
    delay(lowMs);
    gpioWrite(gpio, true);
    delay(settleMs);
  }

  // ---- rail voltages ----
  //
  // LDO2 and LDO3 share register 0x28, one nibble each: 1.8 V plus 0.1 V
  // per step.

  void setLdo2Millivolt(uint16_t mv) { _reg.write8(0x28, (uint8_t)(step(mv) << 4), 0x0F); }
  void setLdo3Millivolt(uint16_t mv) { _reg.write8(0x28, step(mv), 0xF0); }

  static constexpr uint8_t step(uint16_t mv)
  {
    return mv <= 1800 ? 0 : (uint8_t)((mv - 1800) / 100 > 15 ? 15 : (mv - 1800) / 100);
  }

  /// For the backlight classes that drive a rail on this chip.
  TinyM5::I2cReg &reg() { return _reg; }

 private:
  TinyM5::I2cReg _reg;
  uint8_t _rails;
  uint16_t _ldo2mV;
  uint16_t _ldo3mV;
  bool _ok = false;
};
