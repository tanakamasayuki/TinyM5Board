// The button state machine, checked against a written-out timeline.
//
// Not generated, and not a golden. Nothing here is board specific -
// every board's buttons are this one class - and what matters is the
// timing, which reads better as an expectation next to the stimulus than
// as a frozen file.
//
// The clock is synthetic. `update(msec)` takes the time as an argument,
// so a 600 ms hold costs no wall clock and no result depends on how
// fast the machine running the test happens to be.
#include <TinyM5Board/Button.h>

#include <stdarg.h>
#include <stdio.h>
#include <sys/stat.h>

// A plain GPIO button: read on every update().
static bool g_raw = false;
static TinyM5BoardButton g_btn([] { return g_raw; });

// A rate limited one, which is what a PMIC power key costs an I2C
// transaction to read. Counting the reads is how the test tells a
// skipped update() from a sampled one.
static bool g_slowRaw = false;
static int g_slowReads = 0;
static TinyM5BoardButton g_slow(
    [] {
      ++g_slowReads;
      return g_slowRaw;
    },
    true);

static FILE *g_out = nullptr;
static int g_checks = 0;
static int g_failed = 0;

static void say(const char *fmt, ...)
{
  char buf[192];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  if (g_out) {
    fprintf(g_out, "%s\n", buf);
  }
  Serial.println(buf);
}

static void check(const char *what, long got, long want)
{
  ++g_checks;
  if (got == want) {
    say("ok   %s = %ld", what, got);
  } else {
    ++g_failed;
    say("FAIL %s = %ld, want %ld", what, got, want);
  }
}

/// One update() at a chosen time, with the button held in a chosen state.
static void at(uint32_t msec, bool raw)
{
  g_raw = raw;
  g_btn.update(msec);
}

static void debounce()
{
  say("-- debounce --");
  at(900, false);
  check("released at rest", g_btn.isReleased(), 1);

  // A bouncing contact is not a press yet. The pin reads high from 1000
  // but the class waits out its debounce interval before believing it.
  at(1000, true);
  check("not pressed at +0ms", g_btn.isPressed(), 0);
  at(1005, true);
  check("not pressed at +5ms", g_btn.isPressed(), 0);
  at(1010, true);
  check("pressed at +10ms", g_btn.isPressed(), 1);
  check("wasPressed once", g_btn.wasPressed(), 1);
  at(1020, true);
  check("wasPressed is an edge", g_btn.wasPressed(), 0);
}

static void singleClick()
{
  say("-- single click --");
  at(1100, false);
  check("still pressed while bouncing", g_btn.isPressed(), 1);
  at(1110, false);
  check("wasReleased", g_btn.wasReleased(), 1);
  check("wasClicked", g_btn.wasClicked(), 1);
  // The count is not final here: a second click may still arrive.
  check("no count yet", g_btn.wasDecideClickCount(), 0);

  at(1300, false);
  check("quiet", g_btn.wasClicked(), 0);
  check("still undecided", g_btn.wasDecideClickCount(), 0);

  // A hold threshold of quiet after the click ends the run.
  at(1611, false);
  check("wasDecideClickCount", g_btn.wasDecideClickCount(), 1);
  check("wasSingleClicked", g_btn.wasSingleClicked(), 1);
  check("getClickCount", g_btn.getClickCount(), 1);

  at(1620, false);
  check("reported once", g_btn.wasDecideClickCount(), 0);
  check("count cleared", g_btn.getClickCount(), 0);
}

static void doubleClick()
{
  say("-- double click --");
  at(2000, true);
  at(2010, true);
  at(2100, false);
  at(2110, false);
  check("first click", g_btn.wasClicked(), 1);

  at(2200, true);
  at(2210, true);
  at(2300, false);
  at(2310, false);
  check("second click", g_btn.wasClicked(), 1);
  check("count still open", g_btn.wasDecideClickCount(), 0);

  at(2500, false);
  check("gap shorter than the hold threshold decides nothing",
        g_btn.wasDecideClickCount(), 0);

  at(2811, false);
  check("wasDoubleClicked", g_btn.wasDoubleClicked(), 1);
  check("not single", g_btn.wasSingleClicked(), 0);
  check("getClickCount", g_btn.getClickCount(), 2);
}

static void hold()
{
  say("-- hold --");
  at(3000, true);
  at(3010, true);
  at(3400, true);
  check("not held before the threshold", g_btn.isHolding(), 0);
  at(3510, true);
  check("isHolding", g_btn.isHolding(), 1);
  check("wasHold", g_btn.wasHold(), 1);
  at(3600, true);
  check("wasHold is an edge", g_btn.wasHold(), 0);
  check("still holding", g_btn.isHolding(), 1);

  // Letting go of a hold is not a click. Reporting one here would make
  // every long press end in a short one as well.
  at(3700, false);
  at(3710, false);
  check("released", g_btn.isReleased(), 1);
  check("no click from a hold", g_btn.wasClicked(), 0);
  at(4300, false);
  check("no count from a hold", g_btn.wasDecideClickCount(), 0);
  check("count is zero", g_btn.getClickCount(), 0);
}

static void rateLimited()
{
  say("-- rate limited --");
  int pressed = 0, released = 0, clicked = 0, decided = 0, count = 0;

  // A sketch polls as fast as its loop runs. The chip behind this button
  // is read once per debounce interval, and the updates in between have
  // read nothing, so they must report nothing rather than repeating the
  // last answer.
  for (uint32_t t = 0; t < 2000; ++t) {
    g_slowRaw = (t >= 500 && t < 600);
    g_slow.update(t);
    pressed += g_slow.wasPressed();
    released += g_slow.wasReleased();
    clicked += g_slow.wasClicked();
    if (g_slow.wasDecideClickCount()) {
      ++decided;
      count = g_slow.getClickCount();
    }
  }
  check("2000 updates, one press", pressed, 1);
  check("one release", released, 1);
  check("one click", clicked, 1);
  check("one decision", decided, 1);
  check("counted one click", count, 1);
  // Once every 10 ms - the debounce interval - and not 2000 times.
  check("reads", g_slowReads, 200);
}

void setup()
{
  Serial.begin(115200);
  mkdir("output", 0755);
  g_out = fopen("output/checks.txt", "w");
  Serial.println("TEST start Button");

  debounce();
  singleClick();
  doubleClick();
  hold();
  rateLimited();

  say("%d checks, %d failed", g_checks, g_failed);
  if (g_out) {
    fclose(g_out);
    g_out = nullptr;
  }
  Serial.println("TEST done Button");
}

void loop() { delay(10); }
