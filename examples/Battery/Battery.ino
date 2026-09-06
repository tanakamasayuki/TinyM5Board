// Battery - four different power chips, one set of questions.
//
// The StickC has an AXP192, the CoreS3 an AXP2101, the StickS3 an M5PM1,
// and the Capsule has no chip at all - just a divider onto an ADC pin.
// A sketch that wants to know how full the battery is asks the same way
// on all four, and a board with no battery does not have a Power member
// to ask at all, which is why the #if is there.
//
// Change the include to move this sketch to another board.

#include <TinyM5BoardStickC.h>
// #include <TinyM5BoardCore2.h>       // Core:  AXP192 or AXP2101, decided at run time
// #include <TinyM5BoardAtomLite.h>    // Atom:  no battery - prints so
// #include <TinyM5BoardStampPLC.h>    // Stamp: no battery either
// #include <TinyM5BoardPaperMono.h>   // Paper: M5PM1
// #include <TinyM5BoardCapsule.h>     // Other: a divider onto an ADC pin

void setup()
{
  Board.begin();
  Serial.printf("board : %s\n", Board.getBoardName());

#if TINYM5_HAS_BATTERY
  // Which chip answered. Not something to branch on - every reading
  // below works the same on all of them - but worth printing once,
  // because on the Core2 it is only known at run time.
  const char *chip = "?";
  switch (Board.Power.getType()) {
    case TinyM5::Pmic::Adc: chip = "divider on an ADC pin"; break;
    case TinyM5::Pmic::Axp192: chip = "AXP192"; break;
    case TinyM5::Pmic::Axp2101: chip = "AXP2101"; break;
    case TinyM5::Pmic::M5pm1: chip = "M5PM1"; break;
    default: break;
  }
  Serial.printf("power : %s\n", chip);
#else
  Serial.println("power : this board has no battery");
#endif
}

void loop()
{
  Board.update();

#if TINYM5_HAS_BATTERY
  // Millivolts as measured, and a percentage. The chips that have a fuel
  // gauge report it; the ones that do not have their voltage turned into
  // an estimate, so the number means the same thing either way.
  Serial.printf("%d mV, %d%%", (int)Board.Power.getBatteryVoltage(),
                (int)Board.Power.getBatteryLevel());
  switch (Board.Power.isCharging()) {
    case TinyM5::Charge::Charging: Serial.print(", charging"); break;
    case TinyM5::Charge::Discharging: Serial.print(", on battery"); break;
    default: break;
  }
  Serial.println();
#endif
  delay(2000);
}
