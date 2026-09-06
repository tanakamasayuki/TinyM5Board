# API リファレンス

> English: [API.md](API.md) ／ はじめての人は [ガイド](GUIDE.ja.md)

**上級者向け。** ヘッダが出すものを全部並べます。実装の理由が知りたいときは
[DECISIONS.ja.md](DECISIONS.ja.md)（日本語の内部記録）へ。

## 1. 入口

### 1.1 直接 include（推奨）

```cpp
#include <TinyM5BoardStickC.h>
```

`Board` というグローバルが 1 つ生えます。**`M5` ではありません** ——
M5Unified が同名のグローバルを持っているので、両方を使うスケッチが壊れないように。

### 1.2 ビルドフラグから

CI の matrix や PlatformIO の env のように、**ボードをビルド側で決めたい**とき。

```cpp
#define TINYM5_STICKC          // または -DTINYM5_STICKC
#include <TinyM5Board.h>
```

マクロ名は `TINYM5_` + `id` の大文字（`TINYM5_ATOMLITE` / `TINYM5_CORES3SE` …）。

### 1.3 文字列で

文字列しか渡せないビルドシステム向け。

```cpp
#define TINYM5_BOARD_HEADER "TinyM5BoardAtomLite.h"
#include <TinyM5Board.h>
```

### 1.4 グローバルを作らせない

```cpp
#define TINYM5_NO_GLOBAL_BOARD
#include <TinyM5BoardStickC.h>

TINYM5_BOARD Board;     // 自分で置く。static でもメンバでもよい
```

`TINYM5_BOARD` は**そのボードのクラス名**に展開されます。
`TINYM5_BOARD::display()` のように、インスタンス無しで静的に聞くこともできます。

**ボードヘッダを 2 つ include すると `#error` で止まります。**
最初の 1 つしか効かないので、黙って通すより止めるほうが安全なためです。

## 2. 機能マクロ

**全機種で定義されます**（無い機能は `0`）。`if constexpr` では代用できません
—— 捨てる側も名前解決されるので、無いメンバを書くとコンパイルが通りません。

| マクロ | |
| --- | --- |
| `TINYM5_HAS_DISPLAY` | 画面がある |
| `TINYM5_HAS_DISPLAY_DSI` | その画面が MIPI-DSI（`displayDsi()` がある） |
| `TINYM5_HAS_BACKLIGHT` | `Board.Backlight` がある |
| `TINYM5_HAS_BATTERY` | `Board.Power` がある |
| `TINYM5_HAS_INTERNAL_I2C` | 内部 I2C バスがある |
| `TINYM5_HAS_EXTERNAL_I2C` | Grove（Port A）がある |
| `TINYM5_HAS_RGB_LED` | RGB LED がある |
| `TINYM5_HAS_BTN_A` `_B` `_C` `_EXT` `_PWR` | そのボタンがある |
| `TINYM5_BOARD` | そのボードのクラス名 |
| `TINYM5_CORE2_HAS_AXP192` / `_AXP2101` | Core2 のみ。両方 `1`（実行時に決まる） |

## 3. `Board`

### 3.1 定数

すべて `static constexpr`。**無いものは `-1`**（`kRgbLedCount` だけ `0`）。

| | |
| --- | --- |
| `kBoardId` | `TinyM5::BoardId`。数値は m5stack-board-id と同じ |
| `kFamily` | `TinyM5::Family` |
| `kName` | `const char*` |
| `kI2cSda` `kI2cScl` | 内部 I2C |
| `kI2cExtSda` `kI2cExtScl` | Grove（Port A） |
| `kPowerHold` | 電源保持ピン |
| `kSdSpiCs` | **パネルと SPI を共有する TF カード**の CS。共有しないなら `-1` |
| `kRgbLed` `kRgbLedCount` | RGB LED のピンと個数 |
| `kBtnA` `kBtnB` `kBtnC` `kBtnExt` `kBtnPwr` | ボタンのピン。**そのボタンがある機種にだけ存在します**（マクロのほうは全機種にあります）。電源チップやエキスパンダの中にあるボタンは `-1` |
| `kHasDisplay` `kHasBacklight` `kHasBattery` | 上のマクロと同じ値の `bool` |
| `kHasInternalI2c` `kHasExternalI2c` `kSharesI2cBus` | I2C の構成 |

### 3.2 メソッド

```cpp
bool begin(uint8_t flags = TinyM5::InitDefault);
void update();                                  // ボタンのため。loop で 1 回
static constexpr const char *getBoardName();
static constexpr TinyM5::BoardId getBoard();
static constexpr int8_t getPin(TinyM5::Pin);    // 定数と同じ答えを実行時に
static void holdPower();                        // POWER_HOLD のある機種のみ
static constexpr TinyM5::Display display();     // 画面のある機種のみ
static constexpr TinyM5::DisplayDsi displayDsi();  // DSI の機種のみ
```

`begin()` の戻り値は**チップが応答したか**。チップの無いボードは常に `true`。

`flags` は `TinyM5::Init` のビット和:

| | |
| --- | --- |
| `TinyM5::InitDefault` | 全部やる |
| `TinyM5::KeepSerial` | `Serial.begin()` を呼ばない（自分で開いている） |
| `TinyM5::KeepI2c` | `Wire` / `Wire1` を開かない |

**`holdPower()` は `begin()` より前に呼べます。** `setup()` の先頭で
どうしても他の処理が要るときは、これだけ先に呼んで電源を保持できます。

### 3.3 `begin()` の順序

順序に意味があります（実機で電源が落ちる／画面が映らない差になります）。

1. `holdPower()`
2. `Serial` / `Wire` / `Wire1`
3. ボタンピンの `pinMode`
4. 電源チップ（レール電圧 → レール投入）
5. IO エキスパンダ
6. ボード固有の手順（`power_on`）
7. パネルのリセット
8. EPD の BUSY を入力に
9. **TF カードを SPI モードへ**（パネルとバスを共有する機種）
10. バックライト

## 4. `Board.BtnX`

`TinyM5BoardButton`。**ピンでも、電源チップの中のキーでも、IO エキスパンダの
先でも同じ型**です。I2C を要するボタンはデバウンス間隔に 1 回だけ読みます。

```cpp
void update();  void update(uint32_t msec);   // Board.update() が呼ぶ

bool isPressed();   bool isReleased();   bool isHolding();
bool wasPressed();  bool wasReleased();  bool wasChangePressed();
bool wasHold();

bool wasClicked();              // 離した瞬間（長押しになったものは含まない）
bool wasDecideClickCount();     // クリックの連なりが確定した瞬間
bool wasSingleClicked();        // 上 && 回数 1
bool wasDoubleClicked();        // 上 && 回数 2
uint8_t getClickCount();
State getState();               // Nochange / Clicked / Hold / DecideClickCount

bool pressedFor(uint32_t ms);   bool releasedFor(uint32_t ms);
void setDebounceThresh(uint32_t ms);   // 既定 10
void setHoldThresh(uint32_t ms);       // 既定 500
uint32_t getDebounceThresh();  uint32_t getHoldThresh();
uint32_t lastChange();  uint32_t getUpdateMsec();
```

**`was*` はすべて「その `update()` が見つけた変化」**です。1 回の `update()` で
1 回だけ真になります。

**クリック回数は押した瞬間には決まりません。** 2 回目が来るかもしれないので、
最後のクリックから hold 閾値だけ静かになって初めて `wasDecideClickCount()` が
立ちます。M5Unified の `Button_Class` と同じ状態機械です。

## 5. `Board.Power`

**チップが何でも共通**:

```cpp
bool begin(TwoWire &wire);          // Board.begin() が呼ぶ
bool isPresent();
TinyM5::Pmic getType();             // Adc / Axp192 / Axp2101 / M5pm1 / Aw32001
int16_t getBatteryVoltage();        // mV
int32_t getBatteryLevel();          // 0-100、不明なら -1
TinyM5::Charge isCharging();        // Charging / Discharging / Unknown
```

チップ固有のものは、そのヘッダにあります。

| チップ | 追加で持つもの | ヘッダ |
| --- | --- | --- |
| ADC 直結 | `getAdcPin` `getAdcRatioX1000` | `PowerAdc.h` |
| AXP192 | VBUS / 充電電流・電圧 / LDO 電圧 / RTC バックアップ / `powerOff` / PEK / チップ GPIO | `PowerAxp192.h` |
| AXP2101 | VBUS / 充電 / `setLdoEnables` / ALDO 電圧 / `powerOff` / PEK | `PowerAxp2101.h` |
| M5PM1 | チップ GPIO と PWM / 低電圧カットオフ / `powerOff` / PEK | `PowerM5pm1.h` |
| AW32001 + BQ27220 | 充電電流・電圧 / `getBatteryCurrent` | `PowerAw32001.h` |
| Core2 の二択 | 上 2 つのどちらかへ委譲 | `PowerCore2.h` |

**`Board.BtnPwr` が電源チップの中のキー**になっている機種では、
`Power.isKeyPressed()` を `BtnPwr` が呼んでいます。直接呼ぶ必要はありません。

## 6. `Board.Backlight`

```cpp
void begin(uint8_t brightness = 128);   // Board.begin() が呼ぶ
void set(uint8_t brightness);           // 0 = 消灯
uint8_t get();
static constexpr bool dimmable();       // 段階調光できるか
```

方式は 6 つ（PWM ピン / AXP192 のレール / AXP2101 のレール / Core2 / M5IOE1 の
PWM / M5PM1 の PWM / PI4IO のスイッチ）。**輝度カーブはどれも M5GFX と同じ数字**に
なります。`dimmable()` が `false` を返すのはスイッチだけです。

## 7. `Board.Io` / `Board.Io2`

IO エキスパンダのある機種だけ。**「余ったピン」ではありません** ——
パネルの電源やリセット、ボタンがこの先にあります。

**チップごとに形が違います。** 共通なのは立ち上げと読み書きだけです。

```cpp
bool begin(TwoWire &wire);   bool isPresent();
void write(Io, bool level);  bool read(Io);
void resetPulse(Io);
```

| チップ | 形 |
| --- | --- |
| `IoExpanderM5ioe1` | ピン単位（`setInput` / `setOutput` / `setPushPull` / プル / `enableRail`）+ PWM 4 チャネル |
| `IoExpanderPi4io` | ピン単位 + 高インピーダンス（`enableInput` / `enableOutput`）+ 割り込みマスク |
| `IoExpanderAw9523` | **ポート単位**（`setDirections` / `setOutputs` / `setGpioMode`）。16 ピンを 2 バイトで |

**2 個持つ機種では `Io` と `Io2`。** 2 個目はチップのもう一方のアドレスに居ます。

## 8. `TinyM5::Display`

```cpp
struct Display {
  DisplayBus bus;                       // Spi / QSpi / Dsi
  int8_t mosi, miso, sclk, dc, cs;
  int8_t io2, io3;                      // QSpi のときだけ。他は -1
  int8_t rst;                           // 常に -1（begin() が済ませた）
  int8_t busy;                          // EPD だけ。他は -1
  uint32_t freqWrite, freqRead;
  uint16_t width, height, offsetX, offsetY;
  uint8_t rotation;                     // = M5GFX の offset_rotation
  bool invert;
  bool threeWire;                       // 読み書きが 1 本の線を共有する
};

struct DisplayDsi {                     // TINYM5_HAS_DISPLAY_DSI のときだけ
  uint8_t busId, laneCount;   uint16_t laneMbps;
  uint8_t ldoChannel;         uint16_t ldoMillivolt;
  uint8_t dpiFreqMhz;
  uint16_t hsyncBackPorch, hsyncPulseWidth, hsyncFrontPorch;
  uint16_t vsyncBackPorch, vsyncPulseWidth, vsyncFrontPorch;
};
```

**パネルの型番は持ちません。** 同じ機種名で載っているガラスが違うことがあり、
判別には SPI バスが要ります。そこは GFX の仕事です。

## 9. 型

| | |
| --- | --- |
| `TinyM5::BoardId` | m5stack-board-id と同じ数値 |
| `TinyM5::Family` | `Core` `Stick` `Atom` `Stamp` `Paper` `Unit` `Other` |
| `TinyM5::Pmic` | `Unknown` `Adc` `Axp192` `Axp2101` `M5pm1` `Aw32001` |
| `TinyM5::Charge` | `Unknown` `Discharging` `Charging` |
| `TinyM5::Pin` | `getPin()` の引数 |
| `TinyM5::Init` | `begin()` のフラグ |
| `TinyM5::DisplayBus` | `Spi` `QSpi` `Dsi` |

## 10. 持たないもの

**足りないのではなく、持たないと決めたものです**（[REQUIREMENTS.ja.md](REQUIREMENTS.ja.md) §4）。

| | なぜ |
| --- | --- |
| IMU / RTC / スピーカー / マイク / タッチ / SD のドライバ | ボードに依らないので、ボード層が持つ理由が無い。**ピンとバスまで渡す** |
| IMU や RTC のチップ**種別** | **世代で変わる。** ユーザー自身も開けないと分からない |
| パネルの型番 | 同上。判別には SPI バスが要る |
| 実行時のボード判別 | 間違った判別は「判別しない」より悪い |
| Port B〜E / SD の 6 本 | いまは見送り。**後から列を足せる** |

**同じ製品名で中身が違い、利用者にも見分けがつかない機種**は、ライブラリに
入っていません。一覧と理由は [DEVELOPMENT_PLAN.ja.md](DEVELOPMENT_PLAN.ja.md) §2-9 に。
