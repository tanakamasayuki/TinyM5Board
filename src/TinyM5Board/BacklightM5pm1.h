// TinyM5Board - front light on one of the M5PM1's PWM channels.
//
// The fifth way these boards dim a screen. The panel here is
// electrophoretic, so this is a front light rather than a backlight, but
// it is the same object to a sketch: Board.Backlight.set(brightness).
//
// The duty is 12-bit and the curve is square law - `duty = brightness^2`
// shifted down four - which is what M5GFX uses for this chip
// (Light_M5PaperMono) and what the M5IOE1 channel next door does too.
//
// Brightness zero stops the channel rather than setting a duty of zero:
// the block keeps driving the pin otherwise.
#pragma once

#include <stdint.h>

#include "PowerM5pm1.h"

class TinyM5BoardBacklightM5pm1 {
 public:
  using Pwm = TinyM5BoardPowerM5pm1::Pwm;
  using Gpio = TinyM5BoardPowerM5pm1::Gpio;

  /// `pin` is the chip GPIO the channel is wired to. The pairing is fixed
  /// by the chip, but naming both keeps the board's schematic readable
  /// from the catalogue entry.
  constexpr TinyM5BoardBacklightM5pm1(TinyM5BoardPowerM5pm1 &pmic, Pwm channel,
                                      Gpio pin, uint16_t freqHz)
      : _pmic(pmic), _channel(channel), _pin(pin), _freq(freqHz)
  {
  }

  void begin(uint8_t brightness = 128)
  {
    _pmic.gpioPushPull(_pin);
    _pmic.gpioFunctionPwm(_pin);
    _pmic.setPwmFrequency(_freq);
    set(brightness);
  }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    if (brightness == 0) {
      _pmic.setPwmOff(_channel);
    } else {
      _pmic.setPwmDuty(_channel, duty(brightness));
    }
  }

  uint8_t get() const { return _brightness; }

  /// The 12-bit duty for a brightness, exposed so the curve can be
  /// checked without a chip to talk to. 255 lands on 4064 rather than
  /// 4095 - the same arithmetic M5GFX does.
  static constexpr uint16_t duty(uint8_t brightness)
  {
    return (uint16_t)(((uint32_t)brightness * brightness) >> 4);
  }

 private:
  TinyM5BoardPowerM5pm1 &_pmic;
  Pwm _channel;
  Gpio _pin;
  uint16_t _freq;
  uint8_t _brightness = 0;
};
