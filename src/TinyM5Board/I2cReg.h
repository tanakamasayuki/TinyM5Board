// TinyM5Board - register access shared by the power chips.
//
// The semantics match M5GFX's lgfx::i2c helpers so that a sequence read
// out of M5GFX.cpp transcribes without having to be re-reasoned:
//
//     write(reg, data, mask)  ->  (current & mask) | data
//     bitOn (reg, bits)       ->  write(reg, bits, 0xFF)
//     bitOff(reg, bits)       ->  write(reg, 0, ~bits)
//
// A read-modify-write costs a read, so a chip driver that knows the whole
// byte should write it outright with mask 0.
#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <stdint.h>

namespace TinyM5 {

class I2cReg {
 public:
  constexpr I2cReg() = default;

  void attach(TwoWire &wire, uint8_t addr)
  {
    _wire = &wire;
    _addr = addr;
  }

  bool present() const { return _wire != nullptr; }

  bool read(uint8_t reg, uint8_t *data, size_t len)
  {
    if (!_wire) return false;
    _wire->beginTransmission(_addr);
    _wire->write(reg);
    if (_wire->endTransmission(false) != 0) return false;
    if (_wire->requestFrom(_addr, (uint8_t)len) != len) return false;
    for (size_t i = 0; i < len; ++i) {
      data[i] = (uint8_t)_wire->read();
    }
    return true;
  }

  uint8_t read8(uint8_t reg, uint8_t fallback = 0)
  {
    uint8_t v = fallback;
    return read(reg, &v, 1) ? v : fallback;
  }

  /// 12-bit reading: high byte, then the low nibble of the next register.
  uint16_t read12(uint8_t reg)
  {
    uint8_t v[2] = {0, 0};
    if (!read(reg, v, 2)) return 0;
    return ((uint16_t)v[0] << 4) | (v[1] & 0x0F);
  }

  /// 13-bit reading: high byte, then the low five bits of the next.
  uint16_t read13(uint8_t reg)
  {
    uint8_t v[2] = {0, 0};
    if (!read(reg, v, 2)) return 0;
    return ((uint16_t)v[0] << 5) | (v[1] & 0x1F);
  }

  bool write8(uint8_t reg, uint8_t data)
  {
    if (!_wire) return false;
    _wire->beginTransmission(_addr);
    _wire->write(reg);
    _wire->write(data);
    return _wire->endTransmission() == 0;
  }

  /// (current & mask) | data. Costs a read; prefer write8 when the whole
  /// byte is known.
  bool write8(uint8_t reg, uint8_t data, uint8_t mask)
  {
    uint8_t current = 0;
    if (!read(reg, &current, 1)) return false;
    return write8(reg, (uint8_t)((current & mask) | data));
  }

  bool bitOn(uint8_t reg, uint8_t bits) { return write8(reg, bits, 0xFF); }
  bool bitOff(uint8_t reg, uint8_t bits) { return write8(reg, 0, (uint8_t)~bits); }

 private:
  TwoWire *_wire = nullptr;
  uint8_t _addr = 0;
};

}  // namespace TinyM5
