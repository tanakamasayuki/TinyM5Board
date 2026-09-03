// TinyM5Board - AXP2101 power management chip.
//
// What replaced the AXP192 in the Core2 v1.1. The rails are named
// differently (ALDO / BLDO / DLDO rather than LDO / DCDC / EXTEN) and so
// are the registers, so the two are not interchangeable behind one
// driver - which is exactly why a board that could have either has to ask
// (docs/DECISIONS.ja.md D5).
//
// One difference reaches the API. The AXP2101 has a real fuel gauge in
// register 0xA4, where the AXP192 only offers a voltage to guess from. A
// percentage means something here and is an estimate there, and
// getBatteryVoltage() stays the primary reading on both so that a sketch
// written against one is not misled by the other.
//
// Integer arithmetic throughout.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"
#include "I2cReg.h"

class TinyM5BoardPowerAxp2101 {
 public:
  static constexpr uint8_t kAddress = 0x34;  ///< same address as the AXP192
  static constexpr uint8_t kChipId = 0x4A;

  constexpr TinyM5BoardPowerAxp2101() = default;

  /// Attach without touching anything. A board with two possible chips
  /// asks first and only initializes the one that answered.
  bool probe(TwoWire &wire)
  {
    attach(wire);
    return _reg.read8(0x03, 0xFF) == kChipId;
  }

  /// Point at the bus without reading anything. For a caller that has
  /// already identified the chip and does not want a second read of the
  /// same register showing up in the trace.
  void attach(TwoWire &wire) { _reg.attach(wire, kAddress); }

  bool begin(TwoWire &wire)
  {
    if (!probe(wire)) return false;
    init();
    return true;
  }

  /// The setup that follows a successful probe. Split out so a board that
  /// had to ask which chip it has does not pay for a second detection
  /// read.
  void init()
  {
    // Every ADC channel on. Without this the battery reads back 0.
    _reg.write8(0x30, 0b111111);
    _ok = true;
  }

  bool isPresent() const { return _ok; }
  TinyM5::Pmic getType() const { return TinyM5::Pmic::Axp2101; }

  // ---- readings ----

  /// Battery voltage in mV, reported directly by the chip.
  int16_t getBatteryVoltage() { return (int16_t)_reg.read14(0x34); }

  /// 0-100 from the chip's own fuel gauge - not a guess from the voltage.
  int32_t getBatteryLevel() { return (int32_t)_reg.read8(0xA4); }

  int16_t getVBUSVoltage()
  {
    return isVBUSPresent() ? (int16_t)_reg.read14(0x38) : 0;
  }

  TinyM5::Charge isCharging()
  {
    return ((_reg.read8(0x01) & 0x60) == 0x20) ? TinyM5::Charge::Charging
                                               : TinyM5::Charge::Discharging;
  }

  bool isVBUSPresent() { return (_reg.read8(0x00) & 0x20) != 0; }

  // ---- settings ----

  void setBatteryCharge(bool enable)
  {
    _reg.write8(0x18, (uint8_t)(enable ? 0x02 : 0x00), 0xFD);
  }

  void powerOff() { _reg.bitOn(0x10, 0x01); }

  /// The power key. Latched in 0x49 and cleared by writing the bits back.
  /// bit0 short press, bit1 long press, matching the AXP192's ordering
  /// after the shift.
  uint8_t getKeyState()
  {
    const uint8_t val = _reg.read8(0x49) & 0x0C;
    if (val) _reg.write8(0x49, val);
    return (uint8_t)(val >> 2);
  }

  /// Whether the power button is down. The AXP chips only latch that it
  /// was pressed, so this is the latched flag rather than a live level -
  /// enough for a debounced button, and the same call the M5PM1 answers
  /// from its live state.
  bool isKeyPressed() { return getKeyState() != 0; }

  // ---- rails ----
  //
  // Register 0x90 switches the A/B/D LDOs, one bit each. Which of them
  // feeds what is board knowledge, so a board header names the pattern
  // its schematic implies rather than the bits.

  void setLdoEnables(uint8_t mask) { _reg.write8(0x90, mask); }

  /// 500-3500 mV in 100 mV steps. The chip counts from 500 mV as zero.
  void setAldo3Millivolt(uint16_t mv) { _reg.write8(0x94, step(mv)); }
  void setAldo4Millivolt(uint16_t mv) { _reg.write8(0x95, step(mv)); }

  static constexpr uint8_t step(uint16_t mv)
  {
    return mv <= 500 ? 0 : (uint8_t)((mv - 500) / 100);
  }

  TinyM5::I2cReg &reg() { return _reg; }

 private:
  TinyM5::I2cReg _reg;
  bool _ok = false;
};
