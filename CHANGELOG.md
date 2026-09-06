# Changelog / 変更履歴

> **(EN) Nothing has been released yet, and nothing below has been run on
> real hardware.** Every board is transcribed from the schematics
> M5Stack's own libraries carry, frozen against a host-side golden of
> what `begin()` does to the bus, and compiled for its own SoC. Until a
> board has been through the manual check, treat its pinout as a
> transcription rather than a measurement.
>
> **(JA) まだリリースしていない。実機で動かしてもいない。** 各ボードは
> M5Stack 自身のライブラリが持つ配線からの転記で、`begin()` がバスに
> 何をするかをホスト実行のゴールデンで凍結し、各 SoC 向けに
> コンパイルまで通してある。手動確認を通るまで、ピン表は「実測」ではなく
> 「転記」として読むこと。

## Unreleased
- (EN) 34 boards, chosen at build time by the header you include. Atom,
  Core, Paper, Stamp, Stick and the ones that are their own thing.
- (EN) Power: a divider on an ADC pin, AXP192, AXP2101 and M5PM1, all
  answering the same questions. The Core2 asks its chip which it is.
- (EN) I/O expanders where the panel needs one: M5IOE1, AW9523B,
  PI4IOE5V6408.
- (EN) Backlight through whatever the board has - a PWM pin, a PMIC rail,
  a channel inside an expander or inside the power chip, or a plain
  switch - behind one `Board.Backlight`.
- (EN) Buttons with debounce, hold and click counting, whether the button
  is a pin, a power chip's key or an expander's line.
- (EN) The display's pins and particulars are handed out rather than
  drawn on: SPI, QSPI and the electrophoretic panels' BUSY line. No
  graphics library is pulled in.
- (EN) On the boards where the TF card shares the panel's SPI bus,
  `begin()` puts the card into SPI mode so it stops answering.
- (EN) Examples by feature - Hello, Buttons, Battery, Backlight - with the
  board as one line to change.
- (JA) 未リリース。**実機での確認はまだ**。以下のボードはすべて M5Stack 自身の
  ライブラリが持つ配線から起こし、`begin()` の動作をホスト実行のゴールデンで
  凍結し、各 SoC 向けにコンパイルまで通してある。手動確認を通るまでは
  ピン表は「転記」として扱うこと。
- (JA) 34 機種。include したヘッダでビルド時に決まる。
- (JA) 電源: ADC 直結 / AXP192 / AXP2101 / M5PM1 を同じ API で。
  Core2 は実行時にチップに名乗らせる。
- (JA) IO エキスパンダ: M5IOE1 / AW9523B / PI4IOE5V6408。
- (JA) バックライト: PWM ピン / PMIC のレール / エキスパンダや電源チップの
  中の PWM / 単なるスイッチを、すべて `Board.Backlight` の後ろに。
- (JA) ボタン: デバウンス・長押し・クリック回数。ピンでも、電源チップの
  キーでも、エキスパンダのピンでも同じ書き方。
- (JA) 表示は描かずに諸元を渡す。SPI / QSPI と電子ペーパーの BUSY まで。
  グラフィックスライブラリは引き込まない。
- (JA) TF カードがパネルと SPI バスを共有する機種では、`begin()` が
  カードを SPI モードに移して黙らせる。
- (JA) サンプルは機能軸。Hello / Buttons / Battery / Backlight。
