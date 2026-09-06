// TinyM5Board - M5PM1, M5Stack's own power management chip.
//
// The one to write next after the AXP192, because it is on nine boards:
// StickS3, StopWatch, PaperMono, ChainCaptain, PaperColor, PaperDIY,
// CoreP4X, ToughC5 and CoreMatrix.
//
// Two things about it are unlike the AXP chips and both reach begin().
//
// **It goes to sleep on an idle bus.** Register 0x09 carries an I2C idle
// timeout, and the chip stops answering once it expires. Worse, the
// setting survives a power cycle - the PMIC is always powered, so a
// shutdown does not reset it. Something else having written that register
// once is enough to make the board look broken forever after, which is
// why begin() writes it back to 0 every time rather than only when it
// looks wrong.
//
// **It has a watchdog.** Register 0x0A counts down in seconds and resets
// the system when it reaches zero. begin() disables it, the same as
// M5Unified does.
//
// There is no fuel gauge, so a percentage is estimated from the voltage
// exactly as on the AXP192. The voltage itself is easier than either AXP:
// registers 0x22/0x23 report millivolts directly, little-endian.
//
// Register map from M5Stack's own M5PM1 library (MIT). The research notes
// under docs/research/ recorded this chip's power side as unknown because
// M5GFX only ever touches its display side; that is resolved here.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"
#include "I2cReg.h"

class TinyM5BoardPowerM5pm1 {
 public:
  static constexpr uint8_t kAddress = 0x6E;

  /// The chip's GPIOs. On several boards these are the only way to reach
  /// a rail or a reset line, so a board header drives them by name.
  enum class Gpio : uint8_t { Io0, Io1, Io2, Io3, Io4 };

  /// Rails in register 0x06. Which of them feeds what is board knowledge.
  enum Rail : uint8_t {
    Charge = 1 << 0,   ///< CHG_EN
    Dcdc5V = 1 << 1,   ///< DCDC_EN
    Ldo3V3 = 1 << 2,   ///< LDO_EN
    Boost = 1 << 3,    ///< BOOST_EN, the 5VINOUT / Grove port
    Led = 1 << 4,      ///< LED_EN default level
  };

  constexpr explicit TinyM5BoardPowerM5pm1(uint8_t rails = 0) : _rails(rails) {}

  void attach(TwoWire &wire) { _reg.attach(wire, kAddress); }

  bool probe(TwoWire &wire)
  {
    attach(wire);
    // Any answer identifies it: the id is four bytes and M5Stack's own
    // driver only checks that the read succeeded.
    uint8_t id[4] = {0, 0, 0, 0};
    return _reg.read(0x00, id, sizeof(id));
  }

  bool begin(TwoWire &wire)
  {
    if (!probe(wire)) return false;
    init();
    return true;
  }

  void init()
  {
    // Both of these are why a board with this chip can appear dead: the
    // idle-sleep timeout survives a power cycle, and the watchdog resets
    // the system on its own.
    _reg.write8(0x09, 0x00);  // I2C_CFG: no idle sleep
    _reg.write8(0x0A, 0x00);  // WDT_CNT: watchdog off
    if (_rails) _reg.bitOn(0x06, _rails);
    _ok = true;
  }

  bool isPresent() const { return _ok; }
  TinyM5::Pmic getType() const { return TinyM5::Pmic::M5pm1; }

  // ---- readings ----

  /// Battery voltage in mV, reported directly and little-endian.
  int16_t getBatteryVoltage()
  {
    uint8_t v[2] = {0, 0};
    if (!_reg.read(0x22, v, 2)) return 0;
    return (int16_t)(((uint16_t)v[1] << 8) | v[0]);
  }

  int16_t getVBUSVoltage()
  {
    uint8_t v[2] = {0, 0};
    if (!_reg.read(0x24, v, 2)) return 0;
    return (int16_t)(((uint16_t)v[1] << 8) | v[0]);
  }

  /// 0-100, or -1. Estimated from the voltage - this chip has no fuel
  /// gauge, so the same caveat as the AXP192 applies. Same curve, so the
  /// number agrees with M5Unified.
  int32_t getBatteryLevel()
  {
    const int32_t mv = getBatteryVoltage();
    if (mv <= 0) return -1;
    const int32_t level = (mv - 3300) * 100 / (4150 - 3350);
    return level < 0 ? 0 : (level > 100 ? 100 : level);
  }

  /// Inferred rather than reported: register 0x04 says which source the
  /// board is running from, and anything other than the battery means
  /// external power is present. M5Unified's driver returns false here
  /// unconditionally, which is less useful and no more honest.
  TinyM5::Charge isCharging()
  {
    return (_reg.read8(0x04, 2) != 2) ? TinyM5::Charge::Charging
                                      : TinyM5::Charge::Discharging;
  }

  bool isVBUSPresent() { return _reg.read8(0x04, 2) != 2; }

  // ---- the power button ----

  /// Live state of the power button (register 0x48 bit 0).
  bool isKeyPressed() { return (_reg.read8(0x48) & 0x01) != 0; }

  /// Latched "was pressed" (bit 7, cleared by the read). Reported as the
  /// AXP192's short-press bit so that a sketch can treat the two chips
  /// the same.
  uint8_t getKeyState() { return (_reg.read8(0x48) & 0x80) ? 0x02 : 0x00; }

  // ---- settings ----

  void setBatteryCharge(bool enable)
  {
    enable ? _reg.bitOn(0x06, Charge) : _reg.bitOff(0x06, Charge);
  }

  /// Low-voltage cutoff, 2000-4000 mV in steps of 7.81 mV.
  void setBatteryLowCutoff(uint16_t mv)
  {
    if (mv < 2000) mv = 2000;
    if (mv > 4000) mv = 4000;
    _reg.write8(0x08, (uint8_t)(((uint32_t)(mv - 2000) * 100) / 781));
  }

  /// Register 0x0C needs 0xA in its top nibble as a key; 01 is shutdown.
  void powerOff() { _reg.write8(0x0C, 0xA1); }

  // ---- the chip's own GPIOs ----

  /// Function select is two bits per pin in 0x16; 00 is plain GPIO.
  ///
  /// M5GFX clears only one of those two bits for the StickS3 (`1 << 2`
  /// rather than `0b11 << 4`), which works because the register resets to
  /// zero. The other boards that use this chip do it two bits wide, and
  /// that is what is correct.
  void gpioFunctionGpio(Gpio gpio)
  {
    _reg.bitOff(0x16, (uint8_t)(0b11 << ((uint8_t)gpio * 2)));
  }

  void gpioOutput(Gpio gpio) { _reg.bitOn(0x10, gpioBit(gpio)); }
  void gpioInput(Gpio gpio) { _reg.bitOff(0x10, gpioBit(gpio)); }
  void gpioPushPull(Gpio gpio) { _reg.bitOff(0x13, gpioBit(gpio)); }
  void gpioOpenDrain(Gpio gpio) { _reg.bitOn(0x13, gpioBit(gpio)); }

  void gpioWrite(Gpio gpio, bool level)
  {
    level ? _reg.bitOn(0x11, gpioBit(gpio)) : _reg.bitOff(0x11, gpioBit(gpio));
  }

  bool gpioRead(Gpio gpio) { return (_reg.read8(0x12) & gpioBit(gpio)) != 0; }

  /// Configure as a push-pull output and drive it high. What a rail
  /// hanging off one of these pins needs.
  void gpioEnableRail(Gpio gpio)
  {
    gpioFunctionGpio(gpio);
    gpioOutput(gpio);
    gpioPushPull(gpio);
    gpioWrite(gpio, true);
  }

  void gpioResetPulse(Gpio gpio, uint16_t lowMs = 2, uint16_t settleMs = 10)
  {
    gpioWrite(gpio, true);
    delay(1);
    gpioWrite(gpio, false);
    delay(lowMs);
    gpioWrite(gpio, true);
    delay(settleMs);
  }

  // ---- the chip's PWM ----
  //
  // Two channels, and which pin each drives is fixed by the chip: PWM0 is
  // IO3 and PWM1 is IO4. One frequency generator feeds both, so they
  // cannot run at different rates.

  enum class Pwm : uint8_t { Ch0 = 0, Ch1 = 1 };

  /// Hand a pin to the PWM block. Same two bits per pin as
  /// gpioFunctionGpio, set rather than cleared.
  void gpioFunctionPwm(Gpio gpio)
  {
    _reg.bitOn(0x16, (uint8_t)(0b11 << ((uint8_t)gpio * 2)));
  }

  /// Hertz, straight into PWM_FREQ_L/H. Shared by both channels.
  void setPwmFrequency(uint16_t hz)
  {
    const uint8_t buf[2] = {(uint8_t)(hz & 0xFF), (uint8_t)(hz >> 8)};
    _reg.write(0x34, buf, sizeof(buf));
  }

  /// 12-bit duty. The enable bit sits in the same register as the top
  /// nibble, so it goes out in the same write.
  void setPwmDuty(Pwm channel, uint16_t duty12)
  {
    const uint8_t buf[2] = {(uint8_t)(duty12 & 0xFF),
                            (uint8_t)(((duty12 >> 8) & 0x0F) | kPwmEnable)};
    _reg.write(pwmReg(channel), buf, sizeof(buf));
  }

  /// Stop the channel. A duty of zero leaves the block running and the
  /// pin driven, which is not what off means for a backlight.
  void setPwmOff(Pwm channel) { _reg.write8((uint8_t)(pwmReg(channel) + 1), 0); }

  TinyM5::I2cReg &reg() { return _reg; }

 private:
  static constexpr uint8_t kPwmEnable = 0x10;  ///< PWMn_HC bit 4

  static constexpr uint8_t pwmReg(Pwm channel)
  {
    return (uint8_t)(0x30 + (uint8_t)channel * 2);
  }

  // Not called `bit`: Arduino.h defines that as a macro, and a member
  // function of the same name is rewritten by the preprocessor before the
  // compiler ever sees it.
  static constexpr uint8_t gpioBit(Gpio gpio) { return (uint8_t)(1u << (uint8_t)gpio); }

  TinyM5::I2cReg _reg;
  uint8_t _rails;
  bool _ok = false;
};
