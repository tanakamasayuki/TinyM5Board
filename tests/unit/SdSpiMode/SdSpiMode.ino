// Taking the TF card off the panel's bus, with a card on the other end.
//
// The begin() goldens cover this too, but only the branch a silent bus
// produces: with nothing answering, the card looks like it is still in
// SD mode and CMD0 goes out. The other branch - a card that is already
// in SPI mode, which must NOT be reset - needs something to answer, and
// that is what the transfer hook here is for.
//
// The bus is the host core's, so no wire is real and no timing matters.
#include <TinyM5Board/SdSpiMode.h>
#include <tinym5_expect.h>

#include <SPI.h>

// The panel's pins on a Core2, which is also where its card sits.
static constexpr int8_t kSclk = 18;
static constexpr int8_t kMiso = 38;
static constexpr int8_t kMosi = 23;
static constexpr int8_t kCs = 4;

static uint8_t g_mosi[128];
static size_t g_count = 0;
static uint32_t g_clock = 0;
static bool g_answersOcr = false;

// The sequence is 16 dummy clock bytes and then the eight byte READ_OCR,
// so the two bytes the card answers in are transfers 22 and 23.
static constexpr size_t kOcrAnswer = 22;

static uint8_t onByte(uint8_t out, void *)
{
  const size_t i = g_count;
  if (i < sizeof(g_mosi)) {
    g_mosi[i] = out;
  }
  ++g_count;
  // A card in SPI mode answers; one that is not leaves the line high.
  return (g_answersOcr && i == kOcrAnswer) ? 0x00 : 0xFF;
}

static void onTransaction(bool active, const SPISettings &settings, void *)
{
  if (active) {
    g_clock = settings._clock;
  }
}

static uint8_t at(size_t i) { return i < g_count ? g_mosi[i] : 0; }

static void run(bool answersOcr, int8_t cs)
{
  g_count = 0;
  g_clock = 0;
  g_answersOcr = answersOcr;
  TinyM5::sdToSpiMode(kSclk, kMiso, kMosi, cs);
}

static void silentCard()
{
  TinyM5Expect::say("-- a card that does not answer --");
  run(false, kCs);

  // 16 dummy clocks, READ_OCR, 16 more, GO_IDLE_STATE.
  TinyM5Expect::check("bytes transferred", g_count, 48);
  TinyM5Expect::check("clocked at 400 kHz", g_clock, 400000);
  TinyM5Expect::check("dummy clocks are ones", at(0), 0xFF);
  TinyM5Expect::check("READ_OCR after 16 of them", at(16), 0x7A);
  TinyM5Expect::check("its CRC", at(21), 0xFD);
  // The point of the whole exercise: an unanswering card gets reset.
  TinyM5Expect::check("GO_IDLE_STATE", at(40), 0x40);
  TinyM5Expect::check("its CRC - the one a card checks", at(45), 0x95);
  TinyM5Expect::check("card left deselected", digitalRead(kCs), HIGH);
}

static void answeringCard()
{
  TinyM5Expect::say("-- a card already in SPI mode --");
  run(true, kCs);

  // It answered, so there is nothing to fix: the run stops after
  // READ_OCR and the card is never reset. Resetting one that is already
  // up would drop it back to idle for no reason.
  TinyM5Expect::check("bytes transferred", g_count, 24);
  TinyM5Expect::check("READ_OCR still sent", at(16), 0x7A);
  TinyM5Expect::check("no GO_IDLE_STATE", at(24), 0);
  TinyM5Expect::check("card left deselected", digitalRead(kCs), HIGH);
}

static void noCard()
{
  TinyM5Expect::say("-- a board whose card is not on this bus --");
  // kSdSpiCs is -1 on most of the catalogue, and the call is generated
  // for those boards too through the shared header. Nothing may happen.
  run(false, -1);
  TinyM5Expect::check("bus untouched", g_count, 0);
}

void setup()
{
  Serial.begin(115200);
  TinyM5Expect::start("SdSpiMode");
  SPI.setTransferHook(onByte);
  SPI.setTransactionHook(onTransaction);

  silentCard();
  answeringCard();
  noCard();

  SPI.clearHooks();
  TinyM5Expect::finish();
}

void loop() { delay(10); }
