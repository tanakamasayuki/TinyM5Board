// TinyM5Board - backlight on an M5IOE1 PWM channel.
//
// The fourth way these boards dim a screen, after a plain PWM pin, an
// AXP192 rail and an AXP2101 rail. Here the duty is 12-bit and lives in
// an expander register, and the pin the channel drives is fixed by the
// chip rather than by the board.
//
// The curve is square law - `duty = brightness^2` scaled to 12 bits -
// which is what M5GFX uses for this expander (Light_M5ChainCaptain) and
// roughly what an eye expects from a linear slider. Other boards on this
// chip may want a different one; when the second curve turns up it
// becomes a template parameter the way the AXP192's channel did.
#pragma once

#include <stdint.h>

#include "IoExpanderM5ioe1.h"

class TinyM5BoardBacklightM5ioe1 {
 public:
  using Io = TinyM5BoardIoExpanderM5ioe1::Io;
  using Pwm = TinyM5BoardIoExpanderM5ioe1::Pwm;

  /// `pin` is the expander IO the channel drives; it has to be an output
  /// before the PWM reaches it.
  constexpr TinyM5BoardBacklightM5ioe1(TinyM5BoardIoExpanderM5ioe1 &ioe, Pwm channel,
                                       Io pin, uint16_t freqHz)
      : _ioe(ioe), _channel(channel), _pin(pin), _freq(freqHz)
  {
  }

  void begin(uint8_t brightness = 128)
  {
    _ioe.setPushPull(_pin);
    _ioe.setOutput(_pin);
    _ioe.setPwmFrequency(_freq);
    set(brightness);
  }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    _ioe.setPwmDuty(_channel, duty(brightness));
  }

  uint8_t get() const { return _brightness; }

  /// Every backlight answers this, so a sketch can ask without knowing
  /// what is behind it. Only the ones wired to a plain switch say no.
  static constexpr bool dimmable() { return true; }

  /// The 12-bit duty for a brightness, exposed so the curve can be
  /// checked without a chip to talk to. Integer throughout: the rounding
  /// term is half of 255^2.
  static constexpr uint16_t duty(uint8_t brightness)
  {
    return (uint16_t)(((uint32_t)brightness * brightness * 4095u + 32512u) / 65025u);
  }

 private:
  TinyM5BoardIoExpanderM5ioe1 &_ioe;
  Pwm _channel;
  Io _pin;
  uint16_t _freq;
  uint8_t _brightness = 0;
};
