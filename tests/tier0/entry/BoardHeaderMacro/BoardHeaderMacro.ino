// The third way in: the header named as a string.
//
// Some build systems can only pass a string, so <TinyM5Board.h> takes
// one. The mechanism is the same for every board, so one board is
// enough to prove it - what is board specific is covered per board in
// tier0/boards/.
//
// The global instance is left alone here on purpose. The per-board
// sketches all switch it off, so this is the one place the default -
// `Board` exists without being asked for - is compiled.
#define TINYM5_BOARD_HEADER "TinyM5BoardAtomLite.h"
#include <TinyM5Board.h>

static_assert(TINYM5_BOARD::kBoardId == TinyM5::BoardId::AtomLite,
              "the string spelling of the entry point picked another board");

void setup()
{
  Board.begin();
  Serial.println(Board.getBoardName());
}

void loop() { Board.update(); }
