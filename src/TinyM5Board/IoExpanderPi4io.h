// TinyM5Board - PI4IOE5V6408 I/O expander.
//
// On the StampPLC, the Tab5 family and the NessoN1, and on some of those
// it holds things that are not obviously expander material: the StampPLC
// puts its three front buttons on it as well as the backlight, so
// `Board.BtnA` there is an I2C read rather than a `digitalRead`.
//
// Eight pins. Direction, pull and output each have their own register,
// and a separate one disables the output driver - a pin has to come out
// of high impedance before it drives anything.
//
// Two of these can share a bus (the Tab5 has one at 0x43 and one at
// 0x44), so the address is a constructor argument.
#pragma once

#include <Arduino.h>
#include <stdint.h>

#include "Common.h"
#include "I2cReg.h"

class TinyM5BoardIoExpanderPi4io {
 public:
  static constexpr uint8_t kAddress = 0x43;
  static constexpr uint8_t kAddressAlt = 0x44;

  enum class Io : uint8_t { P0, P1, P2, P3, P4, P5, P6, P7 };

  constexpr explicit TinyM5BoardIoExpanderPi4io(uint8_t address = kAddress)
      : _address(address)
  {
  }

  void attach(TwoWire &wire) { _reg.attach(wire, _address); }

  bool probe(TwoWire &wire)
  {
    attach(wire);
    // The chip reports an id in 0x01; anything non-zero is one.
    return _reg.read8(0x01, 0x00) != 0;
  }

  bool begin(TwoWire &wire)
  {
    if (!probe(wire)) return false;
    _ok = true;
    return true;
  }

  bool isPresent() const { return _ok; }
  uint8_t address() const { return _address; }

  // ---- pins ----

  void setOutput(Io io) { _reg.bitOn(0x03, mask(io)); }
  void setInput(Io io) { _reg.bitOff(0x03, mask(io)); }

  void setPullUp(Io io)
  {
    _reg.bitOn(0x0D, mask(io));
    _reg.bitOn(0x0B, mask(io));
  }
  void setPullDown(Io io)
  {
    _reg.bitOff(0x0D, mask(io));
    _reg.bitOn(0x0B, mask(io));
  }
  void setPullNone(Io io) { _reg.bitOff(0x0B, mask(io)); }

  /// A pin drives nothing until this is off. Out of reset they are all
  /// high impedance.
  void setHighImpedance(Io io, bool enable)
  {
    enable ? _reg.bitOn(0x07, mask(io)) : _reg.bitOff(0x07, mask(io));
  }

  void write(Io io, bool level)
  {
    level ? _reg.bitOn(0x05, mask(io)) : _reg.bitOff(0x05, mask(io));
  }

  bool read(Io io) { return (_reg.read8(0x0F) & mask(io)) != 0; }

  /// Configure as a driven output at a known level.
  void enableOutput(Io io, bool level, bool pullDown = true)
  {
    setOutput(io);
    pullDown ? setPullDown(io) : setPullUp(io);
    setHighImpedance(io, false);
    write(io, level);
  }

  /// Configure as a pulled-up input, which is how every button wired to
  /// one of these is arranged.
  void enableInput(Io io)
  {
    setInput(io);
    setPullUp(io);
    setHighImpedance(io, false);
  }

  void resetPulse(Io io, uint16_t lowMs = 2, uint16_t settleMs = 10)
  {
    setOutput(io);
    setHighImpedance(io, false);
    write(io, true);
    delay(1);
    write(io, false);
    delay(lowMs);
    write(io, true);
    delay(settleMs);
  }

  TinyM5::I2cReg &reg() { return _reg; }

 private:
  static constexpr uint8_t mask(Io io) { return (uint8_t)(1u << (uint8_t)io); }

  TinyM5::I2cReg _reg;
  uint8_t _address;
  bool _ok = false;
};
