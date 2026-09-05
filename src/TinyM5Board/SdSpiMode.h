// TinyM5Board - take the TF card off the panel's SPI bus.
//
// On the Core2, the Tough, the CoreS3 family and the StampPLC the card
// shares the panel's SPI wires. A card that has just been powered up is
// in its native SD mode, where it answers commands addressed to nobody
// in particular - and the first thing a graphics library does on these
// boards is read the panel's id, which then comes back as whatever the
// card happened to say. The panel is then mistaken for another one, or
// for none.
//
// A card that has been told to speak SPI stays quiet until its CS goes
// low, so one CMD0 with CS asserted settles it for the rest of the run.
// That command is the whole of this file.
//
// This is bring-up, not a driver: nothing here reads a block or knows
// what a filesystem is. It releases the bus on the way out, so whatever
// opens the panel afterwards finds the host free.
//
// Transcribed from M5GFX's `_set_sd_spimode` (M5GFX.cpp:989).
#pragma once

#include <Arduino.h>
#include <SPI.h>
#include <stdint.h>

namespace TinyM5 {

/// 128 clocks with the card deselected. A card will not look at CS until
/// it has seen at least 74 of them, so this is what makes the command
/// that follows arrive at something that is listening.
inline void sdDummyClock(int8_t cs)
{
  digitalWrite(cs, HIGH);
  for (int i = 0; i < 16; ++i) {
    SPI.transfer(0xFF);
  }
  digitalWrite(cs, LOW);
}

/// Put the card on this bus into SPI mode, if it is not there already.
///
/// The pins are the panel's: on these boards they are the card's too,
/// which is the entire reason this has to happen during bring-up rather
/// than when someone gets around to mounting the card.
inline void sdToSpiMode(int8_t sclk, int8_t miso, int8_t mosi, int8_t cs)
{
  if (cs < 0) return;

  pinMode(cs, OUTPUT);
  SPI.begin(sclk, miso, mosi, -1);
  // 400 kHz is the speed a card is required to accept before it has been
  // configured. Mode 0 is the only one SPI-mode cards answer.
  SPI.beginTransaction(SPISettings(400000, MSBFIRST, SPI_MODE0));

  sdDummyClock(cs);

  // READ_OCR (CMD58), sent with its CRC and two bytes of room for the
  // reply. A card that is in SPI mode answers in those two; one that is
  // not leaves the line as it found it, so the two bytes coming back the
  // same is the "still in SD mode" case.
  uint8_t cmd58[] = {0x7A, 0, 0, 0, 0, 0xFD, 0xFF, 0xFF};
  SPI.transfer(cmd58, sizeof(cmd58));

  if (cmd58[6] == cmd58[7]) {
    sdDummyClock(cs);
    // GO_IDLE_STATE (CMD0) with CS low. A card that sees this while
    // selected switches to SPI for good, until it is powered down.
    static constexpr uint8_t cmd0[] = {0x40, 0, 0, 0, 0, 0x95, 0xFF, 0xFF};
    for (uint8_t b : cmd0) {
      SPI.transfer(b);
    }
  }

  digitalWrite(cs, HIGH);
  SPI.endTransaction();
  // Hand the host back. A graphics library initialising this same bus
  // afterwards would otherwise find it already claimed.
  SPI.end();
}

}  // namespace TinyM5
