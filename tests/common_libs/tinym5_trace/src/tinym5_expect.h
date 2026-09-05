// Expectations written next to the stimulus that produces them.
//
// The unit sketches check themselves: each one drives a class through a
// scripted timeline and says what it expects at each step. This is the
// reporting half - one line per check, into output/checks.txt and onto
// serial, with FAIL lines that a pytest assertion can quote verbatim.
//
// Deliberately not a golden. Freezing pays off for values transcribed
// from upstream, where the question is "has this moved"; for a state
// machine the expectation is derivable, and it reads better beside the
// input than in a separate file.
#pragma once

#include <Arduino.h>
#include <stdarg.h>
#include <stdio.h>
#include <sys/stat.h>

namespace TinyM5Expect {

inline FILE *&file()
{
  static FILE *f = nullptr;
  return f;
}

inline int &checks()
{
  static int n = 0;
  return n;
}

inline int &failed()
{
  static int n = 0;
  return n;
}

inline const char *&name()
{
  static const char *n = "";
  return n;
}

inline void say(const char *fmt, ...)
{
  char buf[192];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  if (file()) {
    fprintf(file(), "%s\n", buf);
  }
  Serial.println(buf);
}

/// One expectation. Everything is compared as a long so that a bool, a
/// count and a pin number all read the same way in the output.
inline void check(const char *what, long got, long want)
{
  ++checks();
  if (got == want) {
    say("ok   %s = %ld", what, got);
  } else {
    ++failed();
    say("FAIL %s = %ld, want %ld", what, got, want);
  }
}

inline void start(const char *test)
{
  name() = test;
  mkdir("output", 0755);
  file() = fopen("output/checks.txt", "w");
  Serial.printf("TEST start %s\n", test);
}

inline void finish()
{
  say("%d checks, %d failed", checks(), failed());
  if (file()) {
    fclose(file());
    file() = nullptr;
  }
  Serial.printf("TEST done %s\n", name());
}

}  // namespace TinyM5Expect
