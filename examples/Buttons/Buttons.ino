// Buttons - the same six lines on every board that has one.
//
// This is the example that shows what the library is for. The StickC's
// power key lives inside its AXP192 and never reaches a pin. The
// StampPLC's three front buttons are on an I/O expander. The AtomLite's
// is a plain GPIO that cannot even have a pull-up, because GPIO 39 on
// the classic ESP32 has none. All three are read the same way here.
//
// Change the include to move this sketch to another board. Nothing else
// in it is board specific.

#include <TinyM5BoardAtomLite.h>
// #include <TinyM5BoardCore2.h>       // Core:  its A/B/C are touch zones
// #include <TinyM5BoardStickC.h>      // Stick: the power key is in the PMIC
// #include <TinyM5BoardStampPLC.h>    // Stamp: three buttons on an expander
// #include <TinyM5BoardPaperMono.h>   // Paper
// #include <TinyM5BoardDial.h>        // Other
// The rest of the catalogue is one line each; typing `#include <TinyM5Board`
// makes the IDE offer every board.

void setup()
{
  Board.begin();
  Serial.printf("board : %s\n", Board.getBoardName());

  // Buttons vary more than anything else on these boards, so a portable
  // sketch asks before it reaches for one. Missing hardware is absent
  // rather than stubbed out: this has to be #if, not `if constexpr`.
#if !TINYM5_HAS_BTN_A && !TINYM5_HAS_BTN_B && !TINYM5_HAS_BTN_C && !TINYM5_HAS_BTN_PWR
  Serial.println("buttons: this board has none");
#endif
}

/// One button's traffic, printed. Every board's buttons are this one
/// class, so this takes a reference and does not care where the button
/// is wired - a pin, a power chip or an expander.
static void report(const char *name, TinyM5BoardButton &btn)
{
  if (btn.wasPressed()) {
    Serial.printf("%s pressed\n", name);
  }
  if (btn.wasReleased()) {
    Serial.printf("%s released\n", name);
  }
  // A hold is reported once, when the button has been down for the hold
  // threshold - not repeatedly while it stays down.
  if (btn.wasHold()) {
    Serial.printf("%s held\n", name);
  }
  // A click is a press let go of before it became a hold, so it arrives
  // on the release. How many clicks there were cannot be known yet: a
  // second one may still be coming.
  if (btn.wasClicked()) {
    Serial.printf("%s clicked\n", name);
  }
  // ...and this is where the run of clicks ends and the count is final.
  if (btn.wasDecideClickCount()) {
    Serial.printf("%s click count = %u\n", name, btn.getClickCount());
  }
}

void loop()
{
  // One update() per loop feeds every button on the board. Reading a
  // power key costs an I2C transaction, so that one is sampled once per
  // debounce interval rather than on every call.
  Board.update();

#if TINYM5_HAS_BTN_A
  report("BtnA", Board.BtnA);
#endif
#if TINYM5_HAS_BTN_B
  report("BtnB", Board.BtnB);
#endif
#if TINYM5_HAS_BTN_C
  report("BtnC", Board.BtnC);
#endif
#if TINYM5_HAS_BTN_PWR
  report("BtnPwr", Board.BtnPwr);
#endif
}
