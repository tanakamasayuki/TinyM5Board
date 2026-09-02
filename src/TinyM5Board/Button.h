// TinyM5Board - button with debounce and edge detection.
//
// A button is board knowledge in the way that matters here: the pin, the
// polarity, and - on the Stick - whether there is a pin at all. The
// StickC's power button is the AXP192's PEK register and never reaches a
// GPIO, while the StickC Plus2 sitting next to it wires the same button
// to GPIO 35. Reading through a function pointer lets both spell the same
// thing:
//
//     if (Board.BtnPwr.wasPressed()) { ... }
//
// The reader is a plain function pointer, not std::function: it is four
// bytes and no allocation.
//
// Names follow M5Unified's Button_Class so that a sketch moving over does
// not have to be re-learned. The click-count part of that state machine
// (wasClicked / wasDoubleClicked / getClickCount) is not implemented yet.
#pragma once

#include <Arduino.h>
#include <stdint.h>

class TinyM5BoardButton {
 public:
  /// Two shapes of reader. The plain one suits a GPIO button, where a
  /// capture-less lambda around digitalRead is four bytes and no
  /// allocation. The second takes a context pointer, which is what a PMIC
  /// power key needs: it has to reach the chip driver, and that driver is
  /// a sibling member of the board rather than a global.
  using Reader = bool (*)();
  using ReaderCtx = bool (*)(void *);

  /// `rateLimit` is for buttons that cost an I2C transaction to read (a
  /// PMIC power key). Those are sampled once per debounce interval
  /// instead of on every update(), which is safe because the chip latches
  /// the press until it is read.
  constexpr explicit TinyM5BoardButton(Reader reader, bool rateLimit = false)
      : _read(reader), _rateLimit(rateLimit)
  {
  }

  constexpr TinyM5BoardButton(ReaderCtx reader, void *ctx, bool rateLimit = false)
      : _readCtx(reader), _ctx(ctx), _rateLimit(rateLimit)
  {
  }

  void update() { update(millis()); }

  void update(uint32_t msec)
  {
    _wasHold = false;
    if (_rateLimit && _sampled && (uint32_t)(msec - _lastSample) < _msecDebounce) {
      return;
    }
    _lastSample = msec;
    _sampled = true;

    const bool raw = _read ? _read() : _readCtx(_ctx);
    if (raw != _rawState) {
      _rawState = raw;
      _lastRawChange = msec;
    }

    _oldPress = _press;
    if ((uint32_t)(msec - _lastRawChange) >= _msecDebounce) {
      const uint8_t settled = raw ? 1 : 0;
      if (settled != (_press ? 1 : 0)) {
        _press = settled;
        _lastChange = msec;
      } else if (_press == 1 && (uint32_t)(msec - _lastChange) >= _msecHold) {
        _press = 2;
        _wasHold = true;
      }
    }
    _lastMsec = msec;
  }

  bool isPressed() const { return _press != 0; }
  bool isReleased() const { return _press == 0; }
  bool isHolding() const { return _press == 2; }

  bool wasPressed() const { return !_oldPress && _press; }
  bool wasReleased() const { return _oldPress && !_press; }
  bool wasChangePressed() const { return (bool)_press != (bool)_oldPress; }
  bool wasHold() const { return _wasHold; }

  bool pressedFor(uint32_t ms) const
  {
    return _press && (uint32_t)(_lastMsec - _lastChange) >= ms;
  }
  bool releasedFor(uint32_t ms) const
  {
    return !_press && (uint32_t)(_lastMsec - _lastChange) >= ms;
  }

  void setDebounceThresh(uint32_t msec) { _msecDebounce = msec; }
  void setHoldThresh(uint32_t msec) { _msecHold = msec; }
  uint32_t getDebounceThresh() const { return _msecDebounce; }
  uint32_t getHoldThresh() const { return _msecHold; }
  uint32_t lastChange() const { return _lastChange; }
  uint32_t getUpdateMsec() const { return _lastMsec; }

 private:
  Reader _read = nullptr;
  ReaderCtx _readCtx = nullptr;
  void *_ctx = nullptr;
  bool _rateLimit;
  uint32_t _msecDebounce = 10;
  uint32_t _msecHold = 500;
  uint32_t _lastMsec = 0;
  uint32_t _lastChange = 0;
  uint32_t _lastRawChange = 0;
  uint32_t _lastSample = 0;
  bool _sampled = false;
  bool _rawState = false;
  uint8_t _press = 0;     ///< 0 released, 1 pressed, 2 held
  uint8_t _oldPress = 0;
  bool _wasHold = false;
};
