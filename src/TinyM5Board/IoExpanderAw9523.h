// TinyM5Board - AW9523B I/O expander.
//
// On the CoreS3 family. Sixteen pins across two ports, and on that board
// one of them - P1_1 - is the panel's reset line, so a graphics library
// never gets a pin for it.
//
// Each pin can be a GPIO or an LED driver, and the two are selected in a
// separate register from the direction. A board that wants plain GPIOs
// has to say so for all sixteen; leaving them in LED mode is a quiet way
// to have nothing work.
//
// Register map from M5GFX's CoreS3 bring-up.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"
#include "I2cReg.h"

class TinyM5BoardIoExpanderAw9523 {
 public:
  static constexpr uint8_t kAddress = 0x58;
  static constexpr uint8_t kChipId = 0x23;

  /// P0_0..P0_7 then P1_0..P1_7, in the order the registers pair them.
  enum class Io : uint8_t {
    P0_0, P0_1, P0_2, P0_3, P0_4, P0_5, P0_6, P0_7,
    P1_0, P1_1, P1_2, P1_3, P1_4, P1_5, P1_6, P1_7,
  };

  void attach(TwoWire &wire) { _reg.attach(wire, kAddress); }

  bool probe(TwoWire &wire)
  {
    attach(wire);
    return _reg.read8(0x10, 0xFF) == kChipId;
  }

  bool begin(TwoWire &wire)
  {
    if (!probe(wire)) return false;
    _ok = true;
    return true;
  }

  bool isPresent() const { return _ok; }

  // ---- whole-port configuration ----
  //
  // The bring-up sequences for this chip set whole bytes rather than
  // walking pins, so these take the port pattern the schematic implies.
  // Register addresses stay in here; a board header says what, not where.

  /// 1 = input, 0 = output. The chip's own convention.
  void setDirections(uint8_t p0, uint8_t p1)
  {
    _reg.write8(0x04, p0);
    _reg.write8(0x05, p1);
  }

  /// 1 = plain GPIO, 0 = LED driver. Out of reset these are LED mode, so
  /// a board using them as GPIOs has to say so.
  void setGpioMode(uint8_t p0, uint8_t p1)
  {
    _reg.write8(0x12, p0);
    _reg.write8(0x13, p1);
  }

  /// P0's outputs are open-drain out of reset; P1's are always push-pull.
  void setPushPullP0() { _reg.write8(0x11, 0b00010000); }

  /// Drive the given bits high, leaving the rest alone.
  void setOutputs(uint8_t p0, uint8_t p1)
  {
    _reg.bitOn(0x02, p0);
    _reg.bitOn(0x03, p1);
  }

  // ---- single pins ----

  void write(Io io, bool level)
  {
    const uint8_t r = port(io) ? 0x03 : 0x02;
    level ? _reg.bitOn(r, mask(io)) : _reg.bitOff(r, mask(io));
  }

  bool read(Io io)
  {
    return (_reg.read8(port(io) ? 0x01 : 0x00) & mask(io)) != 0;
  }

  /// Pulse a reset line that lands on this chip.
  void resetPulse(Io io, uint16_t lowMs = 2, uint16_t settleMs = 10)
  {
    write(io, true);
    delay(1);
    write(io, false);
    delay(lowMs);
    write(io, true);
    delay(settleMs);
  }

  TinyM5::I2cReg &reg() { return _reg; }

 private:
  static constexpr uint8_t port(Io io) { return (uint8_t)io >= 8 ? 1 : 0; }
  static constexpr uint8_t mask(Io io) { return (uint8_t)(1u << ((uint8_t)io & 7)); }

  TinyM5::I2cReg _reg;
  bool _ok = false;
};
