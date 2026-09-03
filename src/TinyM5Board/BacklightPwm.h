// TinyM5Board - backlight wired straight to a PWM pin.
//
// Only eleven of the thirty-five boards with a screen are this simple.
// On the rest the backlight hangs off a PMIC LDO or an IO expander's PWM
// channel, so `Board.Backlight.set()` is what a portable sketch calls and
// this is one of several things behind it.
//
// The brightness curve is M5GFX's (Light_PWM.cpp:120), including the
// 9-bit resolution and the `offset` that lifts the floor on panels that
// never go fully dark. Keeping the arithmetic identical means a board
// looks the same brightness under either library. It is all integer.
//
// `analogWrite` and its two configuration calls are the Arduino spelling
// of what arduino-esp32 drives through LEDC, and host-arduino-core
// implements them for real, so this path is the same on both targets and
// the host trace shows the backlight coming up.
#pragma once

#include <Arduino.h>
#include <stdint.h>

class TinyM5BoardBacklightPwm {
 public:
  static constexpr uint8_t kBits = 9;

  /// `offset` raises the low end: on some panels a small duty is still
  /// visibly lit, and starting from zero wastes most of the range.
  constexpr TinyM5BoardBacklightPwm(int8_t pin, uint32_t freq, uint8_t offset)
      : _pin(pin), _freq(freq), _offset(offset)
  {
  }

  void begin(uint8_t brightness = 128)
  {
    analogWriteResolution(_pin, kBits);
    analogWriteFrequency(_pin, _freq);
    set(brightness);
  }

  void set(uint8_t brightness)
  {
    _brightness = brightness;
    analogWrite(_pin, duty(brightness));
  }

  uint8_t get() const { return _brightness; }
  int8_t getPin() const { return _pin; }

  /// The duty for a brightness, exposed so a test can check the curve
  /// without a PWM peripheral to look at.
  constexpr uint32_t duty(uint8_t brightness) const
  {
    if (!brightness) return 0;
    uint32_t ofs = _offset ? (uint32_t)_offset * 259 >> 8 : 0;
    uint32_t d = (uint32_t)brightness * (257 - ofs);
    d += ofs * 255;
    d += 1u << (15 - kBits);
    return d >> (16 - kBits);
  }

 private:
  int8_t _pin;
  uint32_t _freq;
  uint8_t _offset;
  uint8_t _brightness = 0;
};
