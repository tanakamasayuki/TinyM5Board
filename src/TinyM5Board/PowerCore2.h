// TinyM5Board - the Core2's power, whichever chip is fitted.
//
// This is a *board* driver, not a chip driver, and deliberately so. The
// Core2 v1.0 carries an AXP192 and the v1.1 an AXP2101, at the same I2C
// address, under the same product name - and which rail feeds the panel
// differs between them:
//
//     v1.0   LDO2  = LCD power   IO4   = LCD reset   DC3   = backlight
//     v1.1   ALDO4 = LCD power   ALDO2 = LCD reset   BLDO1 = backlight
//
// So there is nothing to share below this level. The bring-up, the reset
// and the backlight all have to be written twice, and the only question
// is who chooses. The answer is that the board asks the chip to identify
// itself (docs/DECISIONS.ja.md D5): register 0x03 reads 0x03 or 0x4A,
// nothing is written before the answer comes back, and being wrong is not
// possible because the board is already fixed at build time.
//
// This is not the runtime board detection this library refuses to do.
// That one tries candidate boards and pokes pins that may belong to
// something else; this reads one register at one address on a board that
// is already known. Candidates are tried; a chip is asked to name itself.
//
// Someone who knows their unit can say so and drop the other half:
//
//     #define TINYM5_CORE2_PMIC_AXP2101
//     #include <TinyM5BoardCore2.h>
//
// The version is on the sticker underneath. Without the define both
// drivers link: measured at 480 bytes over pinning it to the AXP192 and
// 776 over the AXP2101 (arduino-esp32 3.3.11). That is the price of not
// needing to know, and on a 4 MB board it is not a reason to make
// someone open the case.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"
#include "PowerAxp192.h"
#include "PowerAxp2101.h"

#if defined(TINYM5_CORE2_PMIC_AXP192) && defined(TINYM5_CORE2_PMIC_AXP2101)
#error "TinyM5Board: define at most one of TINYM5_CORE2_PMIC_AXP192 / TINYM5_CORE2_PMIC_AXP2101. Leave both undefined to let begin() ask the chip."
#endif

#if !defined(TINYM5_CORE2_PMIC_AXP2101)
#define TINYM5_CORE2_HAS_AXP192 1
#else
#define TINYM5_CORE2_HAS_AXP192 0
#endif
#if !defined(TINYM5_CORE2_PMIC_AXP192)
#define TINYM5_CORE2_HAS_AXP2101 1
#else
#define TINYM5_CORE2_HAS_AXP2101 0
#endif

class TinyM5BoardPowerCore2 {
 public:
  bool begin(TwoWire &wire)
  {
    // One read, at the address both chips share. Asking each driver to
    // probe in turn would read the same register twice and put a failed
    // detection into the trace that a real board never performs.
    TinyM5::I2cReg id;
    id.attach(wire, TinyM5BoardPowerAxp192::kAddress);
    const uint8_t chip = id.read8(0x03, 0xFF);

#if TINYM5_CORE2_HAS_AXP192
    if (chip == TinyM5BoardPowerAxp192::kChipId) {
      _type = TinyM5::Pmic::Axp192;
      _192.attach(wire);
      _192.init();
      // LCD power first, then the pin that resets the panel. IO4 is that
      // pin - there is no GPIO for it, which is why display().rst is -1.
      _192.setLdo2Millivolt(3300);
      _192.reg().bitOn(0x12, TinyM5BoardPowerAxp192::Ldo2);
      _192.gpioOutput(TinyM5BoardPowerAxp192::Gpio::Io4);
      _192.gpioResetPulse(TinyM5BoardPowerAxp192::Gpio::Io4);
      return true;
    }
#endif
#if TINYM5_CORE2_HAS_AXP2101
    if (chip == TinyM5BoardPowerAxp2101::kChipId) {
      _type = TinyM5::Pmic::Axp2101;
      _2101.attach(wire);
      _2101.init();
      auto &reg = _2101.reg();
      reg.write8(0x90, 0x08, 0x7B);  // ALDO4 on (LCD/TP/TF), ALDO3 + DLDO1 off
      reg.write8(0x80, 0x05, 0xFF);  // DCDC1 + DCDC3 on
      reg.write8(0x82, 0x12);        // DCDC1 3.3 V
      reg.write8(0x84, 0x6A);        // DCDC3 3.3 V
      // ALDO2 is the panel's reset line here, not a GPIO.
      reg.bitOff(0x90, 0x02);
      delay(2);
      reg.bitOn(0x90, 0x02);
      delay(10);
      return true;
    }
#endif
    _type = TinyM5::Pmic::Unknown;
    return false;
  }

  TinyM5::Pmic getType() const { return _type; }
  bool isPresent() const { return _type != TinyM5::Pmic::Unknown; }

  // ---- readings ----
  //
  // getBatteryLevel() is worth a note: on the v1.1 it is the chip's fuel
  // gauge, on the v1.0 an estimate from the voltage. Same call, different
  // confidence - which is why getBatteryVoltage() is the one to build on.

  int16_t getBatteryVoltage() { return dispatch(&A192::getBatteryVoltage, &A2101::getBatteryVoltage); }
  int32_t getBatteryLevel() { return dispatch(&A192::getBatteryLevel, &A2101::getBatteryLevel); }
  int16_t getVBUSVoltage() { return dispatch(&A192::getVBUSVoltage, &A2101::getVBUSVoltage); }
  TinyM5::Charge isCharging() { return dispatch(&A192::isCharging, &A2101::isCharging); }
  bool isVBUSPresent() { return dispatch(&A192::isVBUSPresent, &A2101::isVBUSPresent); }
  uint8_t getKeyState() { return dispatch(&A192::getKeyState, &A2101::getKeyState); }
  bool isKeyPressed() { return dispatch(&A192::isKeyPressed, &A2101::isKeyPressed); }

  void setBatteryCharge(bool enable)
  {
#if TINYM5_CORE2_HAS_AXP192
    if (_type == TinyM5::Pmic::Axp192) return _192.setBatteryCharge(enable);
#endif
#if TINYM5_CORE2_HAS_AXP2101
    if (_type == TinyM5::Pmic::Axp2101) return _2101.setBatteryCharge(enable);
#endif
  }

  void powerOff()
  {
#if TINYM5_CORE2_HAS_AXP192
    if (_type == TinyM5::Pmic::Axp192) return _192.powerOff();
#endif
#if TINYM5_CORE2_HAS_AXP2101
    if (_type == TinyM5::Pmic::Axp2101) return _2101.powerOff();
#endif
  }

  /// Backlight, because the rail differs with the chip: DC3 at 0x27 on
  /// the v1.0, BLDO1 at 0x96 on the v1.1. Both curves are M5GFX's.
  void setBacklight(uint8_t brightness)
  {
#if TINYM5_CORE2_HAS_AXP192
    if (_type == TinyM5::Pmic::Axp192) {
      auto &reg = _192.reg();
      brightness ? reg.bitOn(0x12, TinyM5BoardPowerAxp192::Dcdc3)
                 : reg.bitOff(0x12, TinyM5BoardPowerAxp192::Dcdc3);
      reg.write8(0x27, brightness ? (uint8_t)((brightness >> 3) + 72) : 0, 0x80);
      return;
    }
#endif
#if TINYM5_CORE2_HAS_AXP2101
    if (_type == TinyM5::Pmic::Axp2101) {
      auto &reg = _2101.reg();
      brightness ? reg.bitOn(0x90, 0x10) : reg.bitOff(0x90, 0x10);
      reg.write8(0x96, brightness ? (uint8_t)((brightness + 641) >> 5) : 0);
      return;
    }
#endif
  }

 private:
  using A192 = TinyM5BoardPowerAxp192;
  using A2101 = TinyM5BoardPowerAxp2101;

  template <typename R>
  R dispatch(R (A192::*m192)(), R (A2101::*m2101)())
  {
    (void)m192;
    (void)m2101;
#if TINYM5_CORE2_HAS_AXP192
    if (_type == TinyM5::Pmic::Axp192) return (_192.*m192)();
#endif
#if TINYM5_CORE2_HAS_AXP2101
    if (_type == TinyM5::Pmic::Axp2101) return (_2101.*m2101)();
#endif
    return R{};
  }

#if TINYM5_CORE2_HAS_AXP192
  // No rails and no voltages here: begin() runs the Core2's own sequence
  // rather than the generic one, because the two chips do not share it.
  A192 _192{0};
#endif
#if TINYM5_CORE2_HAS_AXP2101
  A2101 _2101;
#endif
  TinyM5::Pmic _type = TinyM5::Pmic::Unknown;
};
