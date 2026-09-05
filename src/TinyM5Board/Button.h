// TinyM5Board - button with debounce, edge detection and click counting.
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
// Names and state machine follow M5Unified's Button_Class so that a
// sketch moving over does not have to be re-learned.
#pragma once

#include <Arduino.h>
#include <stdint.h>

class TinyM5BoardButton {
 public:
  /// What the last update() decided. Only one of these can be true at a
  /// time, which is why the click predicates are all one comparison.
  /// Same four values as M5Unified's `button_state_t`.
  enum class State : uint8_t {
    Nochange,
    Clicked,           ///< pressed and released before the hold threshold
    Hold,              ///< still pressed at the hold threshold
    DecideClickCount,  ///< the quiet time after a click ran out
  };

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
    if (_rateLimit && _sampled && (uint32_t)(msec - _lastSample) < _msecDebounce) {
      // Between samples nothing was read, so there is no edge to report.
      // Leaving the previous one standing would make one press count
      // several times in a sketch that polls faster than the chip is
      // read - which is every sketch, since the limit exists precisely
      // because reading is expensive.
      expire();
      _oldPress = _press;
      _state = State::Nochange;
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
    State state = State::Nochange;
    if ((uint32_t)(msec - _lastRawChange) >= _msecDebounce) {
      const uint8_t settled = raw ? 1 : 0;
      if (settled != (_press ? 1 : 0)) {
        // A release from a plain press is a click. A release from a hold
        // is not: that press was already reported as State::Hold, and
        // counting it again would make every hold end in a click too.
        if (!settled && _press == 1) {
          state = State::Clicked;
        }
        _press = settled;
        _lastChange = msec;
      } else if (_press == 1 && (uint32_t)(msec - _lastChange) >= _msecHold) {
        _press = 2;
        state = State::Hold;
      }
    }
    _lastMsec = msec;
    decide(msec, state);
  }

  bool isPressed() const { return _press != 0; }
  bool isReleased() const { return _press == 0; }
  bool isHolding() const { return _press == 2; }

  bool wasPressed() const { return !_oldPress && _press; }
  bool wasReleased() const { return _oldPress && !_press; }
  bool wasChangePressed() const { return (bool)_press != (bool)_oldPress; }
  bool wasHold() const { return _state == State::Hold; }

  /// Fires on the update() that saw the release, so a sketch that only
  /// wants "was this tapped" needs nothing else. The count is not known
  /// yet at this point - a second click may still be coming.
  bool wasClicked() const { return _state == State::Clicked; }

  /// Fires once, a hold threshold after the last click in a run, which
  /// is the earliest moment the count is final.
  bool wasDecideClickCount() const { return _state == State::DecideClickCount; }
  bool wasSingleClicked() const { return wasDecideClickCount() && _clickCount == 1; }
  bool wasDoubleClicked() const { return wasDecideClickCount() && _clickCount == 2; }

  /// Clicks in the current run. Meaningful while wasDecideClickCount()
  /// is true; it is cleared on the update() after that.
  uint8_t getClickCount() const { return _clickCount; }
  State getState() const { return _state; }

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
  /// A reported count belongs to the single update() that reported it.
  /// Every path out of update() has to run this, including the one that
  /// skips the read, or the count stays up and is reported again.
  void expire()
  {
    if (_state == State::DecideClickCount) {
      _clickCount = 0;
    }
  }

  /// Turn "a click happened" into "the run of clicks is over and there
  /// were N of them".
  ///
  /// The count cannot be reported when the click happens, because a
  /// second click may still arrive. So the run stays open until the
  /// button has been quiet for a hold threshold - the same threshold, so
  /// that a board with a slow button only has one number to tune.
  void decide(uint32_t msec, State state)
  {
    expire();
    if (state == State::Clicked) {
      ++_clickCount;
      _lastClicked = msec;
    } else if (state == State::Nochange && _clickCount && !_press
               && (uint32_t)(msec - _lastClicked) > _msecHold) {
      if (_oldPress == 0 && _state == State::Nochange) {
        state = State::DecideClickCount;
      } else {
        // The run ended in something other than a settled release - a
        // hold, say. There is no click count to report.
        _clickCount = 0;
      }
    }
    _state = state;
  }

  Reader _read = nullptr;
  ReaderCtx _readCtx = nullptr;
  void *_ctx = nullptr;
  bool _rateLimit;
  uint32_t _msecDebounce = 10;
  uint32_t _msecHold = 500;
  uint32_t _lastMsec = 0;
  uint32_t _lastChange = 0;
  uint32_t _lastRawChange = 0;
  uint32_t _lastClicked = 0;
  uint32_t _lastSample = 0;
  bool _sampled = false;
  bool _rawState = false;
  uint8_t _press = 0;     ///< 0 released, 1 pressed, 2 held
  uint8_t _oldPress = 0;
  uint8_t _clickCount = 0;
  State _state = State::Nochange;
};
