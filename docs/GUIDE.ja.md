# ガイド

> English: [GUIDE.md](GUIDE.md) ／ 一覧: [../README.ja.md](../README.ja.md)

**はじめて使う人向け。** 30 分あれば、自分のボードが立ち上がって、
ボタンと電池が読めるところまで行きます。

## 1. 用意するもの

- M5Stack のボード 1 台（[対応表](../README.ja.md#対応ボード)）
- Arduino IDE 2.x か arduino-cli
- **arduino-esp32 3.x**（ボードマネージャで「esp32 by Espressif Systems」）

ライブラリマネージャで `TinyM5Board` を検索して入れます。

## 2. 自分のボードの 1 行を書く

**このライブラリはボードを自動判別しません。** 使う機種を include で名指しします。

```cpp
#include <TinyM5BoardStickC.h>
```

`#include <TinyM5Board` まで打つと、IDE が候補を出します。
どれが自分のボードか分からないときは [対応表](../README.ja.md#対応ボード)を見てください。

> **なぜ自動判別しないのか**
> 判別は間違えます。同じ製品名で中身が違う機種があり、間違ったピン表は
> 「ピン表が無い」より悪いからです（[REQUIREMENTS.ja.md](REQUIREMENTS.ja.md) §4）。

## 3. `Board.begin()` を呼ぶ

```cpp
#include <TinyM5BoardStickC.h>

void setup()
{
  Board.begin();
}

void loop()
{
  Board.update();
}
```

`Board` は include したヘッダが用意するグローバルです。**`begin()` がやること**:

1. **電源を保持する**（POWER_HOLD のあるボード）——ここが遅いと**電源が落ちます**
2. Serial と I2C を開く
3. 電源チップを立ち上げ、レールを投入する
4. IO エキスパンダを立ち上げる
5. 画面のリセットを解く
6. カードがパネルとバスを共有するボードでは、カードを黙らせる
7. バックライトを点ける

**`update()` はボタンのためだけ**にあります。`loop()` の先頭で 1 回呼びます。

## 4. 聞けること

### ピン

```cpp
Board.kI2cSda      // 内部 I2C
Board.kI2cScl
Board.kI2cExtSda   // Grove（Port A）。無ければ -1
Board.kI2cExtScl
Board.kRgbLed      // RGB LED。無ければ -1
Board.kPowerHold
```

**`Wire` は「そのボードが持っている最初のバス」**です。内部バスがあれば内部、
Stamp や Nano のように内部が無い機種では Grove が `Wire` に載ります。

### ボタン

```cpp
Board.update();                    // loop の先頭で 1 回

Board.BtnA.wasPressed()            // 押された瞬間
Board.BtnA.wasReleased()           // 離された瞬間
Board.BtnA.wasHold()               // 長押しになった瞬間（既定 500 ms）
Board.BtnA.wasClicked()            // 短く押して離した（離した瞬間）
Board.BtnA.wasDoubleClicked()      // 2 回クリックが確定した瞬間
Board.BtnA.isPressed()             // いま押されているか
```

**ボタンはボードによって数も名前も違います。** 無いボタンは**メンバごと存在しない**ので、
機種を変えても動くコードにするには `#if` で囲みます。

```cpp
#if TINYM5_HAS_BTN_A
  if (Board.BtnA.wasClicked()) { ... }
#endif
```

`TINYM5_HAS_BTN_A` / `_B` / `_C` / `_EXT` / `_PWR` が**全機種で定義されて**いて、
無いボードでは `0` になります。

### 電池

```cpp
#if TINYM5_HAS_BATTERY
  Board.Power.getBatteryVoltage();   // mV
  Board.Power.getBatteryLevel();     // 0-100（%）
  Board.Power.isCharging();          // TinyM5::Charge::Charging など
#endif
```

**チップが何であっても同じ書き方**です（ADC 直結 / AXP192 / AXP2101 / M5PM1 /
AW32001）。Core2 のように 2 種類の電源チップが流通している機種では、
`begin()` が実行時にチップに名乗らせます。

### バックライト

```cpp
#if TINYM5_HAS_BACKLIGHT
  Board.Backlight.set(128);          // 0 = 消灯、255 = 全開
  Board.Backlight.dimmable();        // 段階調光できるか
#endif
```

ピンの PWM でも、電源チップのレール電圧でも、エキスパンダの中の PWM でも
同じ `set()` です。StampPLC のように**スイッチしか無い**機種では
`dimmable()` が `false` を返し、`set()` は消灯か点灯になります。

## 5. 画面に描く

**このライブラリは描きません。** 代わりに**諸元を渡します**。

```cpp
#if TINYM5_HAS_DISPLAY
  const auto d = Board.display();
  d.mosi, d.miso, d.sclk, d.dc, d.cs;   // バスのピン
  d.freqWrite, d.freqRead;
  d.width, d.height, d.offsetX, d.offsetY, d.rotation, d.invert;
  d.threeWire;                          // 読み書きが 1 本の線を共有する配線
#endif
```

これを M5GFX / TinyGFX / LovyanGFX などのバス設定にそのまま渡します。

**注意が 3 つ**:

- **`d.rst` は必ず `-1`** です。リセットは `begin()` が済ませているので、
  GFX 側にもう一度打たせないための合図です
- **`d.threeWire` が `true` のボード**（Stick 系など）は、4 線前提の設定では
  **読み戻しができません**
- **`d.bus`** が `Spi` 以外のことがあります。`QSpi` なら `mosi` / `miso` は
  4 本のデータ線のうちの 2 本（残りは `io2` / `io3`）、`Dsi` なら**ピンは全部 -1** で、
  レーンやタイミングは `Board.displayDsi()` にあります

## 6. 別のボードに移す

**include の 1 行を変えるだけ**です。`#if` で囲んであれば、無い機能は
自動的に落ちます。[examples/](../examples/README.ja.md) の 4 本は
どれもそう書いてあるので、そのまま試せます。

## 7. うまくいかないとき

| 症状 | たぶんこれ |
| --- | --- |
| **電源がすぐ落ちる** | `Board.begin()` を `setup()` の**先頭**で呼んでいますか。POWER_HOLD のあるボードは、ここが遅いと落ちます |
| **`no board selected` でコンパイルが止まる** | `<TinyM5Board.h>` を直接 include しています。**自分のボードのヘッダ**（`<TinyM5BoardStickC.h>` など）を include してください |
| **`one board per sketch` で止まる** | ボードヘッダを 2 つ include しています。**最初の 1 つしか効かない**ので、意図した方だけ残してください |
| **`Board.Power` が無いと言われる** | そのボードに電池がありません。`#if TINYM5_HAS_BATTERY` で囲んでください |
| **`if constexpr` では消えない** | `if constexpr` の捨てる側も名前解決されます。**`#if` を使ってください** |
| **画面が真っ暗** | `Board.Backlight.set(...)` を呼びましたか。`begin()` は 128 で点けますが、GFX 側が別に消していることがあります |
| **画面の絵がずれる** | `d.offsetX` / `offsetY` / `rotation` を GFX に渡していますか |
| **電池電圧が変** | 分圧比は機種ごとに違います（2.0 だけではありません）。それでもおかしければ Issue へ |

## 次に読むもの

- [API リファレンス](API.ja.md) —— 定数・関数・マクロの全部
- [examples/](../examples/README.ja.md) —— 動くコード 4 本
