// What Board.begin() does to the bus, recorded and compared with a
// golden file. This is the centre of the test suite: the pin table and
// the bring-up order are the whole product, and both are visible here.
//
// The board comes from -DTINYM5_<ID> so that one sketch covers every
// board in the catalogue. That is the reason the build-flag entry point
// exists at all.
#include <TinyM5Board.h>
#include <tinym5_trace.h>

void setup()
{
  Serial.begin(115200);
  TinyM5Trace::start(TINYM5_BOARD::kName);

  Board.begin();

  TinyM5Trace::finish();
}

void loop() { delay(10); }
