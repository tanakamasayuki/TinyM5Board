// Hello - bring the board up and show that it is alive.
//
// The first example on purpose uses no screen. Twenty-nine of the M5
// boards do not have one, and that is the group this library exists for,
// so the first thing anyone runs has to work there too.
//
// Change the include to move this sketch to another board. Nothing else
// in it is board specific.

#include <TinyM5BoardAtomLite.h>
// The rest of the catalogue is listed in the README, one line per board.
// Typing `#include <TinyM5Board` also makes the IDE offer every one.

void setup()
{
  Board.begin();

  Serial.printf("board : %s\n", Board.getBoardName());
  Serial.printf("i2c   : sda=%d scl=%d\n", Board.kI2cSda, Board.kI2cScl);
  if (Board.kHasExternalI2c) {
    Serial.printf("grove : sda=%d scl=%d\n", Board.kI2cExtSda, Board.kI2cExtScl);
  }
  if (Board.kRgbLedCount) {
    Serial.printf("led   : pin=%d count=%u\n", Board.kRgbLed, Board.kRgbLedCount);
  }

  // Hardware a board does not have is absent rather than stubbed out, so
  // this has to be #if and not `if constexpr`: outside a template, the
  // discarded arm of an `if constexpr` still goes through name lookup, and
  // `Board.Power` does not exist here to look up.
#if TINYM5_HAS_BATTERY
  Serial.printf("batt  : %d mV\n", Board.Power.getBatteryVoltage());
#else
  Serial.println("batt  : this board has none");
#endif
}

void loop()
{
  Board.update();

  if (Board.BtnA.wasPressed()) {
    Serial.println("BtnA pressed");
  }
  if (Board.BtnA.wasHold()) {
    Serial.println("BtnA held");
  }
}
