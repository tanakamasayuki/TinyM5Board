// Hello - bring the board up and show that it is alive.
//
// The first example on purpose uses no screen. Twenty-nine of the M5
// boards do not have one, and that is the group this library exists for,
// so the first thing anyone runs has to work there too.
//
// Change the include to move this sketch to another board. Nothing else
// in it is board specific.

#include <TinyM5BoardAtomLite.h>
// #include <TinyM5BoardStickC.h>
// #include <TinyM5BoardStickCPlus2.h>
// #include <TinyM5BoardTough.h>
// #include <TinyM5BoardCapsule.h>
// #include <TinyM5BoardTimerCam.h>
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
#if TINYM5_HAS_RGB_LED
  {
    Serial.printf("led   : pin=%d count=%u\n", Board.kRgbLed, Board.kRgbLedCount);
  }
#endif

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

  // Buttons vary more than anything else on these boards. The Tough has
  // none at all - its A/B/C are touch zones - while the StickC's power
  // key lives inside the PMIC and never reaches a pin. Missing hardware
  // is absent rather than stubbed out, so a portable sketch asks first.
#if TINYM5_HAS_BTN_A
  if (Board.BtnA.wasPressed()) {
    Serial.println("BtnA pressed");
  }
  if (Board.BtnA.wasHold()) {
    Serial.println("BtnA held");
  }
  // A click is a press that was let go of before it became a hold, so
  // this fires on the release rather than on the way down. How many
  // clicks there were cannot be known until the button has been quiet
  // for a moment, which is why the count arrives separately.
  if (Board.BtnA.wasDoubleClicked()) {
    Serial.println("BtnA double click");
  }
#endif
#if TINYM5_HAS_BTN_PWR
  if (Board.BtnPwr.wasPressed()) {
    Serial.println("power key");
  }
#endif
}
