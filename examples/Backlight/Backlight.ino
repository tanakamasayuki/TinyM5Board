// Backlight - a pin, a power rail and an expander channel, dimmed alike.
//
// On more than half the boards with a screen the backlight is not a pin
// at all: the StickC dims by changing an AXP192 rail's voltage, the
// CoreS3 by changing an AXP2101's, the ChainCaptain through a PWM
// channel inside its I/O expander, and the PaperMono through one inside
// its power chip. `Board.Backlight` is the one way to reach all of them,
// which is also why the display specification this library hands out has
// no backlight pin in it - that would give the brightness two owners.
//
// Change the include to move this sketch to another board.

#include <TinyM5BoardCore2.h>
// #include <TinyM5BoardStickC.h>      // Stick: an AXP192 rail's voltage
// #include <TinyM5BoardAtomLite.h>    // Atom:  no screen - prints so
// #include <TinyM5BoardStampPLC.h>    // Stamp: on/off only, through an expander
// #include <TinyM5BoardPaperMono.h>   // Paper: a front light in the power chip
// #include <TinyM5BoardDial.h>        // Other: a plain PWM pin

void setup()
{
  Board.begin();
  Serial.printf("board : %s\n", Board.getBoardName());

#if TINYM5_HAS_BACKLIGHT
  // Not every backlight can be dimmed. The StampPLC's is a switch on an
  // expander pin, so it answers false here and set() lands on off or on.
  Serial.printf("dimming: %s\n",
                Board.Backlight.dimmable() ? "yes" : "no - on and off only");
#else
  Serial.println("backlight: this board has none");
#endif
}

void loop()
{
#if TINYM5_HAS_BACKLIGHT
  // A slow ramp, so a wrong brightness curve is visible rather than
  // merely plausible. 0 is off and 255 is full on whichever hardware is
  // behind it; what differs is the arithmetic in between, and each
  // driver uses the curve M5GFX uses for that chip.
  for (int i = 0; i <= 255; i += 15) {
    Board.Backlight.set((uint8_t)i);
    delay(60);
  }
  for (int i = 255; i >= 0; i -= 15) {
    Board.Backlight.set((uint8_t)i);
    delay(60);
  }
#else
  delay(1000);
#endif
}
