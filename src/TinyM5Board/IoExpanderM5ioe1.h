// TinyM5Board - M5IOE1, M5Stack's own I/O expander.
//
// Sits next to the M5PM1 on six boards: StopWatch, PaperMono,
// ChainCaptain, CoreP4X, ToughC5 and CoreMatrix. On those, pins that look
// like ordinary board features - the panel's supply, its reset line, the
// backlight - are not pins at all but bits in this chip.
//
// Fourteen GPIOs across sixteen-bit register pairs: the low register
// covers IO1-IO8 and the high one IO9-IO14, so every operation is
// "pick the register, pick the bit". Four PWM channels share one
// frequency and are wired to fixed pins.
//
// Like the M5PM1 it sleeps on an idle bus and keeps that setting across a
// power cycle, so begin() clears register 0x23 every time.
//
// Register map from M5Unified's M5IOE1_Class (MIT).
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"
#include "I2cReg.h"

class TinyM5BoardIoExpanderM5ioe1 {
 public:
  static constexpr uint8_t kAddress = 0x4F;

  /// IO1..IO14 as the silkscreen and M5Unified number them.
  enum class Io : uint8_t {
    Io1, Io2, Io3, Io4, Io5, Io6, Io7,
    Io8, Io9, Io10, Io11, Io12, Io13, Io14,
  };

  /// The four PWM channels and the pin each is wired to. They are not
  /// interchangeable: a board's backlight is on whichever channel its
  /// schematic chose.
  enum class Pwm : uint8_t {
    Ch1 = 0,  ///< IO9
    Ch2 = 1,  ///< IO8
    Ch3 = 2,  ///< IO11
    Ch4 = 3,  ///< IO10
  };

  void attach(TwoWire &wire) { _reg.attach(wire, kAddress); }

  bool probe(TwoWire &wire)
  {
    attach(wire);
    uint8_t uid[2] = {0, 0};
    return _reg.read(0x00, uid, sizeof(uid));
  }

  bool begin(TwoWire &wire)
  {
    if (!probe(wire)) return false;
    init();
    return true;
  }

  void init()
  {
    _reg.write8(0x23, 0x00);  // I2C_CFG: no idle sleep
    _ok = true;
  }

  bool isPresent() const { return _ok; }

  // ---- GPIO ----

  void setOutput(Io io) { _reg.bitOn(reg(0x03, io), mask(io)); }
  void setInput(Io io) { _reg.bitOff(reg(0x03, io), mask(io)); }
  void setPushPull(Io io) { _reg.bitOff(reg(0x13, io), mask(io)); }
  void setOpenDrain(Io io) { _reg.bitOn(reg(0x13, io), mask(io)); }
  void setPullUp(Io io)
  {
    _reg.bitOff(reg(0x0B, io), mask(io));
    _reg.bitOn(reg(0x09, io), mask(io));
  }
  void setPullDown(Io io)
  {
    _reg.bitOff(reg(0x09, io), mask(io));
    _reg.bitOn(reg(0x0B, io), mask(io));
  }
  void setPullNone(Io io)
  {
    _reg.bitOff(reg(0x09, io), mask(io));
    _reg.bitOff(reg(0x0B, io), mask(io));
  }

  void write(Io io, bool level)
  {
    level ? _reg.bitOn(reg(0x05, io), mask(io)) : _reg.bitOff(reg(0x05, io), mask(io));
  }

  bool read(Io io) { return (_reg.read8(reg(0x07, io)) & mask(io)) != 0; }

  /// Configure as a push-pull output and drive it high - what a rail
  /// hanging off one of these pins needs.
  void enableRail(Io io)
  {
    setPushPull(io);
    setOutput(io);
    write(io, true);
  }

  /// Configure as a push-pull output and pulse it low. What a panel or a
  /// touch controller whose reset line lands here needs.
  void resetPulse(Io io, uint16_t lowMs = 10, uint16_t settleMs = 20)
  {
    setPushPull(io);
    setOutput(io);
    write(io, false);
    delay(lowMs);
    write(io, true);
    delay(settleMs);
  }

  // ---- PWM ----

  /// One frequency for all four channels, in Hz.
  void setPwmFrequency(uint16_t hz)
  {
    const uint8_t data[2] = {(uint8_t)(hz & 0xFF), (uint8_t)(hz >> 8)};
    _reg.write(0x25, data, sizeof(data));
  }

  /// 12-bit duty. Bit 15 of the pair enables the channel; bit 14 inverts.
  void setPwmDuty(Pwm channel, uint16_t duty12, bool enable = true, bool inverted = false)
  {
    if (duty12 > 0x0FFF) duty12 = 0x0FFF;
    uint8_t high = (uint8_t)(duty12 >> 8);
    if (enable) high |= 0x80;
    if (inverted) high |= 0x40;
    const uint8_t data[2] = {(uint8_t)(duty12 & 0xFF), high};
    _reg.write((uint8_t)(0x1B + (uint8_t)channel * 2), data, sizeof(data));
  }

  TinyM5::I2cReg &reg() { return _reg; }

 private:
  // IO1-IO8 live in the low register of each pair, IO9-IO14 in the high
  // one, so the pin picks both the register and the bit.
  static constexpr uint8_t reg(uint8_t base, Io io)
  {
    return (uint8_t)(base + ((uint8_t)io >= 8 ? 1 : 0));
  }
  static constexpr uint8_t mask(Io io) { return (uint8_t)(1u << ((uint8_t)io & 7)); }

  TinyM5::I2cReg _reg;
  bool _ok = false;
};
