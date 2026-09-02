// A plain register file on the I2C bus, for host tests.
//
// Enough of a chip to make a driver's detection succeed and its
// read-modify-writes behave: an address, 256 registers, and a pointer
// that a write sets and a read continues from. That is the whole of what
// the AXP192 / AXP2101 / M5PM1 drivers need from the far side.
//
// The point is not to emulate a PMIC. It is to let the *branch* run: a
// driver that identifies its chip by a register cannot be exercised on
// the host unless something answers. Setting the id register to 0x03 or
// 0x4A is what makes the Core2's two power chips both testable on a
// machine that has neither.
#pragma once

#include <stdint.h>
#include <string.h>

#include "tinym5_trace.h"

namespace TinyM5Trace {

class RegFile {
 public:
  void reset(uint8_t bus, uint8_t addr)
  {
    _bus = bus;
    _addr = addr;
    memset(_reg, 0, sizeof(_reg));
    _pointer = 0;
  }

  void set(uint8_t reg, uint8_t value) { _reg[reg] = value; }
  uint8_t get(uint8_t reg) const { return _reg[reg]; }

  uint8_t onWrite(uint8_t bus, uint8_t addr, const uint8_t *data, size_t len)
  {
    if (bus != _bus || addr != _addr || len == 0) return 2;  // nobody home
    _pointer = data[0];
    for (size_t i = 1; i < len; ++i) {
      _reg[(uint8_t)(_pointer + i - 1)] = data[i];
    }
    return 0;  // ACK
  }

  size_t onRead(uint8_t bus, uint8_t addr, uint8_t *data, size_t len)
  {
    if (bus != _bus || addr != _addr) return 0;
    for (size_t i = 0; i < len; ++i) {
      data[i] = _reg[(uint8_t)(_pointer + i)];
    }
    return len;
  }

 private:
  uint8_t _bus = 0xFF;
  uint8_t _addr = 0xFF;
  uint8_t _reg[256] = {0};
  uint8_t _pointer = 0;
};

/// The one model on the bus for this sketch. One is enough so far; a
/// board with two chips will need this to become a small list.
inline RegFile &model()
{
  static RegFile m;
  return m;
}

inline uint8_t modelWrite(uint8_t bus, uint8_t addr, const uint8_t *data, size_t len)
{
  return model().onWrite(bus, addr, data, len);
}

inline size_t modelRead(uint8_t bus, uint8_t addr, uint8_t *data, size_t len)
{
  return model().onRead(bus, addr, data, len);
}

/// Put a chip on the bus that identifies itself through `idReg`.
inline void useChip(uint8_t bus, uint8_t addr, uint8_t idReg, uint8_t idValue)
{
  model().reset(bus, addr);
  model().set(idReg, idValue);
  device().onWrite = modelWrite;
  device().onRead = modelRead;
}

}  // namespace TinyM5Trace
