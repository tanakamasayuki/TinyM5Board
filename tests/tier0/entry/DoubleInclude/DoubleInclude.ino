// Two boards in one sketch has to stop the build.
//
// Without the guard this compiles and quietly drives the wrong pinout:
// only the first header takes effect, because `Board` is already an
// instance of that board by the time the second one is read. A wrong
// pinout on a bring-up means rails going to the wrong place, so it is
// worth an error rather than a warning.
//
// This sketch is EXPECTED TO FAIL. test_tier0.py reads the message.
#include <TinyM5BoardAtomLite.h>
#include <TinyM5BoardStickC.h>

void setup() {}
void loop() {}
