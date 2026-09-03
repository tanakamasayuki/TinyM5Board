// TinyM5Board - backlight switched by a PI4IOE5V6408 pin.
//
// The one kind that does not dim: the pin is a plain output, so the
// screen is on or off and nothing between. `set(0)` is off and anything
// else is on.
//
// `Board.Backlight.set(128)` still means what it means everywhere else,
// which is the point of putting all of these behind one name - a sketch
// that dims does not have to know which boards can.
//
// The StampPLC drives this pin low to light the panel, hence the
// polarity argument.
#pragma once

#include <stdint.h>

#include "IoExpanderPi4io.h"

class TinyM5BoardBacklightPi4io {
 public:
  using Io = TinyM5BoardIoExpanderPi4io::Io;

  constexpr TinyM5BoardBacklightPi4io(TinyM5BoardIoExpanderPi4io &ioe, Io pin,
                                      bool activeLow)
      : _ioe(ioe), _pin(pin), _activeLow(activeLow)
  {
  }

  void begin(uint8_t brightness = 128)
  {
    _ioe.setOutput(_pin);
    _ioe.setPullDown(_pin);
    _ioe.setHighImpedance(_pin, false);
    set(brightness);
  }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    const bool on = brightness != 0;
    _ioe.write(_pin, _activeLow ? !on : on);
  }

  uint8_t get() const { return _brightness; }

  /// This board cannot dim. Worth asking before offering a slider.
  static constexpr bool dimmable() { return false; }

 private:
  TinyM5BoardIoExpanderPi4io &_ioe;
  Io _pin;
  bool _activeLow;
  uint8_t _brightness = 0;
};
