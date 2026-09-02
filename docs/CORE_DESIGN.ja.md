# コア設計

内部の記録。日本語のみ。**API の形と内部構造。**

**なぜそうしたか**は [DECISIONS.ja.md](DECISIONS.ja.md) にある。ここには
**何がどうなっているか**だけを書く。

## 1. 層構造

```text
スケッチ
  |
  v
Board                      ボード実体。ビルド時に 1 つだけ実体化される
  |                        グローバル実体 `Board` をライブラリが宣言する
  +-- Board.Power          電源チップ（AXP192 / AXP2101 / M5PM1 / ADC / なし）
  +-- Board.Backlight      バックライト（PWM / PMIC LDO / エキスパンダ PWM / なし）
  +-- Board.BtnA .. BtnPwr ボタン（GPIO / PMIC の PEK）
  +-- Board.display()      表示諸元（データのみ。ドライバは持たない）
  +-- Board.getPin(...)    ピン照会（すべてコンパイル時定数）
```

**仮想関数を置かない。** ボードが決まればチップも決まるので、すべて具象メンバとして持てる。
「複数ボードを 1 バイナリで扱いたい」という要件が出てから opt-in で足せばよい。今は入れない。

**GFX を知らない。** 連携は `TinyM5Board/gfx/*.h` に閉じ、include しなければ存在しない。

## 2. ユーザーが書くコード

### 2.1 最小構成

```cpp
#include <TinyM5BoardAtomLite.h>

void setup() {
  Board.begin();
}

void loop() {
  Board.update();
  if (Board.BtnA.wasPressed()) {
    Serial.println("pressed");
  }
}
```

`Serial.begin()` も `Wire.begin()` も書いていない。`Board.begin()` がやる（§5）。

### 2.2 Hello サンプルの形

```cpp
// 自分のボードの行だけ有効にする（全一覧は README / IDE の補完でも出る）
#include <TinyM5BoardStickCPlus2.h>
// #include <TinyM5BoardCore2.h>
// #include <TinyM5BoardCoreS3.h>
// #include <TinyM5BoardAtomS3.h>
// #include <TinyM5BoardAtomLite.h>
// #include <TinyM5BoardStampS3.h>
// #include <TinyM5BoardPaperS3.h>

void setup() {
  Board.begin();
  Serial.printf("%s\n", Board.getBoardName());
}

void loop() {
  Board.update();

  if (Board.BtnA.wasPressed()) {
    Serial.printf("%u mV / %d %%\n",
                  Board.Power.getBatteryVoltage(),
                  Board.Power.getBatteryLevel());
  }
}
```

**ボードを替えるときに変わるのは `#include` の 1 行だけ。**

## 3. 入口の形

### 3.1 実測 — ライブラリ解決の条件

arduino-cli 1.5.0 で確認した（2026-09-02）。

| スケッチが書く include | ライブラリが見つかるか |
| --- | --- |
| `#include <TinyM5Board.h>` | ✅ |
| `#include <TinyM5Board/StickCPlus2.h>` **のみ** | ❌ ファイルが見つからない |
| `#include <TinyM5Board/boards/StickCPlus2.h>` **のみ** | ❌ 同上 |
| ルートヘッダを先に書けばネストも通る | ✅ |
| **`src/` 直下の `TinyM5BoardStickCPlus2.h` のみ** | ✅ |
| `#define` してから `<TinyM5Board.h>` | ✅ |

**ライブラリ解決は `src/` 直下のヘッダ名でしか効かない。**
サブディレクトリのヘッダは、ライブラリが既にビルドに入ってからでないと見えない。
TinyGFX が `<TinyGFX.h>` を先に書かせているのはこの制約による。

### 3.2 入口は 2 つ。どちらも同じボードヘッダに落ちる

**正の入口 — ボードヘッダを直接 include する**

```cpp
#include <TinyM5BoardStickCPlus2.h>
```

1 行で完結し、`boards/` の階層も `#define` も表に出ない。
`#include <TinyM5Board` まで打てば **IDE の補完が 64 機種を出す**。
サンプル・README・ドキュメントはすべてこの形で書く。

**併設 — ビルドフラグから指定する**

```cpp
#define TINYM5_STICKCPLUS2
#include <TinyM5Board.h>
```

`-DTINYM5_STICKCPLUS2` でも指定できるので、**CI のボード別マトリクス**と
PlatformIO の env 分けがそのまま書ける。サンプルの include を書き換えずに
全機種ビルドできるのはこちらの経路。

マクロが未定義なら `#error` で止める。Arduino のボードマクロは**見ない**。

### 3.3 `src/` の規約

```text
src/TinyM5BoardStickCPlus2.h    入口（スケッチが書くのはここだけ。64 本）
src/TinyM5Board.h               入口（define 経由）＋ 共通型
src/TinyM5Board/                内部（スケッチが直接 include しない）
```

**`src/` 直下にあるものが入口、`src/TinyM5Board/` の中が内部**、という一本の規則になる。

IDE の「ライブラリをインクルード」メニューに出るのは `library.properties` の
`includes=` で指定した 1 本だけなので、直下に 64 本並んでも実害はない。

## 4. ファイル構成

```text
src/TinyM5Board<Board>.h            ボードヘッダ 64 本（tools/gen_boards.py が生成）
src/TinyM5Board.h                   共通型・enum・ボード ID・define 経由の入口
src/TinyM5Board/
    Board.h                         ボード実体の共通部分
    Button.h                        デバウンス + エッジ検出
    PowerAxp192.h                   AXP192
    PowerAxp2101.h                  AXP2101
    PowerM5pm1.h                    M5PM1
    PowerAdc.h                      PMIC なし機（ADC + 分圧比）
    PowerNone.h                     電源ハードを持たないボード
    BacklightPwm.h                  PWM 直結
    BacklightAxp192.h               AXP192 の LDO 電圧
    BacklightM5ioe1.h               M5IOE1 の PWM チャネル
    BacklightNone.h                 バックライトを持たないボード
    IoExpanderM5ioe1.h              M5IOE1
    IoExpanderPi4io.h               PI4IOE5V6408
    gfx/TinyGFX.h                   opt-in。TinyGFX と繋ぐ
    gfx/LovyanGFX.h                 opt-in
tools/gen_boards.py                 カタログ → ボードヘッダ / README の表 / keywords.txt
```

**ボードヘッダがそのボードに必要なものだけを include する。**
StickC Plus2 のスケッチに AXP192 のコードは 1 バイトも入らないし、コンパイルもされない。

`.cpp` は 1 本も置かない。

## 5. `Board.begin()`

### 5.1 できるだけ初期化する

最初に呼ばれるものなので、既存の設定を壊しても実害が小さい。壊れて困る人は
`begin()` の後で自分で初期化し直せる。**既定は全部やる。**

やること:

1. **POWER_HOLD を HIGH** — 最優先。StickC Plus2 は電源ボタンから指を離した瞬間に落ちる
2. `Serial.begin()`
3. `Wire.begin()` / `Wire1.begin()` を**そのボードの正しいピンで**
4. ボタンのピンを `INPUT_PULLUP`
5. 電源チップの検出と初期化（個体差がある機種はここで名乗らせる）
6. 電源レール投入
7. LCD のリセットパルス
8. バックライトを既定輝度で点灯

**`Wire.begin()` を呼ぶことは、M5GFX の罪とは別物。**
M5GFX が問題なのは `Wire` をバイパスして I2C ペリフェラルのレジスタを直叩きすることで
（`periph_module_enable` + `dev->command[]`）、そちらは同じポートで `Wire` を使うと衝突する。
**標準 API を正しいピンで呼ぶのは共存を壊さない。**

### 5.2 降り口

```cpp
Board.begin();                       // 既定。全部やる
Board.begin(TinyM5::KeepSerial);     // Serial は自分で開いた
Board.begin(TinyM5::KeepI2c);        // I2C は自分で開いた
```

**暫定** — フラグの形（enum のビット和か、`config_t` か）は未確定。

### 5.3 戻り値

`bool` を返す。意味は **「期待した電源チップが応答したか」**。

TinyGFX は `bool` を「設定が使えるか」に固定して「線の向こうにデバイスが居るか」を
意図的に除外したが、ここは逆にする。**チップは基板に半田付けされているので、
応答しない＝実害のある異常。**

最小構成のサンプルは戻り値を見ない。**見なくても動く**のが正しい。

## 6. `Board.update()`

ボタンのデバウンスとエッジ検出のために持つ。`M5.update()` 相当。

**PEK のボードではレート制限する。** StickC / StickC Plus は電源ボタンが PMIC の
PEK なので、`update()` が I2C トランザクションを発生させる。毎ループ叩くのは無駄なので、
デバウンス間隔（既定 10 ms）と同じ周期に制限する。GPIO のボードでは `digitalRead` なので
制限しない。

電池電圧のような読み出しは `update()` に載せない。呼ばれたときに読む。

## 7. 命名 — M5Unified に合わせる範囲

**基準: どんな名前でもいいものは合わせる。構造が違うものは合わせない。**

### 7.1 そのまま合わせる

戻り値の型も、合わせない理由がないものは合わせる。

| M5Unified | TinyM5Board |
| --- | --- |
| `M5.begin()` / `M5.update()` | `Board.begin()` / `Board.update()` |
| `M5.getBoard()` → `board_t` | `Board.getBoard()`（**数値も m5stack-board-id に合わせる**） |
| `M5.Power.getBatteryVoltage()` → mV | 同じ |
| `M5.Power.getBatteryLevel()` | 同じ |
| `M5.Power.getBatteryCurrent()` / `getVBUSVoltage()` | 同じ |
| `M5.Power.isCharging()` → enum | 同じ（enum の形も揃える） |
| `M5.Power.setChargeCurrent(mA)` / `setChargeVoltage(mV)` | 同じ |
| `M5.Power.setBatteryCharge(bool)` / `powerOff()` | 同じ |
| `M5.Power.getType()` → `pmic_t` | 同じ |
| `M5.BtnA.wasPressed()` / `isPressed()` / `wasReleased()` | 同じ |
| `M5.BtnA.wasClicked()` / `wasHold()` / `pressedFor()` | 同じ |
| `M5.BtnA.setDebounceThresh()` / `setHoldThresh()` | 同じ |
| `M5.getPin(pin_name_t::...)` | `Board.getPin(...)`（**コンパイル時定数**に畳まれる） |

### 7.2 合わせない

| M5Unified | TinyM5Board | 理由 |
| --- | --- | --- |
| `M5.Power.getExtVoltage()` → **float** | 整数（mV） | RISC-V 機に FPU が無い |
| `M5.Display.setBrightness()` | **`Board.Backlight.set()`** | Display を持たないので、その上に置けない |
| `M5.Display` / `M5.Imu` / `M5.Speaker` / `M5.Rtc` / `M5.Lcd` | **持たない** | 持たないものに no-op を置かない |

`Board.Display` を作れば綴りは一致するが、**`fillScreen()` が期待される名前になる。**
諸元と明るさしか持たないので、名前が嘘をつく。README の対応表 1 行で埋まる問題と、
README では埋まらない問題を比べて後者を避けた。

### 7.3 追加するもの

| | 内容 |
| --- | --- |
| `Board.getBoardName()` → `const char*` | コンパイル時定数の文字列。**サンプルを雛形に使う方針で効く**（今どのボードとしてビルドされているかが見える） |

### 7.4 グローバル実体

```cpp
extern TinyM5BoardStickCPlus2 Board;   // ボードヘッダが宣言する
```

**`M5` という名前にはしない。** M5Unified が `M5Unified.cpp:58` で
`m5::M5Unified M5;` を実体として定義しているので、同名にすると
**M5Unified に依存する公式 Unit ライブラリを 1 つ入れただけで衝突**する。
ユーザーには直せないし、原因にもたどり着けない。

`TINYM5_NO_GLOBAL_BOARD` を定義すればグローバル実体を作らない。
`Board` は `M5` ほどではないにせよ一般的な語なので、衝突したときの逃げ道を残す。

## 8. 群と機能フラグ

### 8.1 群 — 探すための軸

```cpp
static constexpr TinyM5::Family kFamily = TinyM5::Family::Stick;
```

`Core` / `Stick` / `Atom` / `Stamp` / `Paper` / `Unit` / `Other`。**製品名で切る。**

README の表・サンプルの一覧・CI のマトリクスをこの単位で並べる。

### 8.2 機能フラグ — 動く / 動かないの軸

```cpp
static constexpr bool kHasDisplay     = true;
static constexpr bool kHasBacklight   = true;
static constexpr bool kHasBattery     = true;
static constexpr bool kHasExternalI2c = true;   // Grove などの別バスがあるか
static constexpr bool kSharesI2cBus   = false;  // 内部と外部が物理的に同一か
```

**群と混ぜない。** Atom 系には画面ありの AtomS3 と画面なしの AtomLite が両方いる。

無い機能は**メンバごと存在しない**。no-op を置かないので、
`Board.Backlight` を画面なしボードで書けばコンパイルエラーになる。
サンプルは `kHas*` を見て `#error` で親切に止められる。

## 8.3 照会できるピン

**4 つだけ**（D27）。

```cpp
Board.kI2cSda / kI2cScl        // 内部 I2C
Board.kI2cExtSda / kI2cExtScl  // Port A（外部 Grove）。無ければ -1
Board.kRgbLed / kRgbLedCount   // 無ければ -1 / 0
Board.kPowerHold               // 無ければ -1
```

`constexpr` 定数が正で、`Board.getPin(TinyM5::Pin::RgbLed)` を
M5Unified からの移行用に併設する（D28）。対象が 4 つしかないので
`switch` 1 本で定数に畳まれ、実行時コストはゼロ。

**IMU / RTC / Speaker / Mic のピンは出さない。** M5Unified の `getPin()` にも無く、
転記元が構造化データとして存在しないため（D27）。

## 9. 個体差の扱い

Core2 の PMIC は AXP192 / AXP2101 で割れる。**ファイルは 1 本のまま。**

```cpp
#include <TinyM5BoardCore2.h>                 // 既定。起動時に名乗らせる

#define TINYM5_CORE2_PMIC_AXP2101             // 分かっている人はこう書くと
#include <TinyM5BoardCore2.h>                 // AXP192 のコードは 1 バイトも載らない
```

**名前に版数もチップ名も出さない。** IMU を持たない以上 Core2 v1.1 と v1.3 は
完全に同じ内容になるので、版数で分けると「中身が同一のファイルが 2 本ある」状態を作り、
かえって「どっちを選べばいいのか」を生む。

判別の条件は [REQUIREMENTS.ja.md](REQUIREMENTS.ja.md) §4.4 に定めた 3 つを満たすときだけ。

## 10. 表示諸元

**データだけを返す。ドライバは持たない。**

```cpp
struct Display {
  int8_t   mosi, miso, sclk, dc, cs;
  int8_t   rst;          ///< -1 = begin() がリセット済み。GFX 側は触らない
  int8_t   backlight;    ///< -1 = PWM ではない。Board.Backlight を使う
  uint32_t freqWrite, freqRead;
  uint16_t width, height, offsetX, offsetY;
  uint8_t  rotation;
  bool     invert;
};
```

`rst` と `backlight` の **`-1` は「こちらで処理済み」の意味**を持つ。
ボードによって GPIO だったり I2C 越しだったりする差を、GFX 側に一切知らせずに畳める。

**パネルの型番が割れる機種（AtomS3 / Tab5 / M5Stack のロット差）では型番を返さない。**
そこは GFX の仕事（[REQUIREMENTS.ja.md](REQUIREMENTS.ja.md) §4.4）。

## 11. GFX 連携

```text
src/TinyM5Board.h              GFX を一切知らない
src/TinyM5Board/gfx/TinyGFX.h  opt-in。両方を include して繋ぐ
```

adapter は **TinyM5Board 側に置く。** GFX 側に置くと、その GFX が全ボードを
知る必要が出てしまう。ボードが増えたとき同じカタログから adapter も生成できる。

**画面なしボードでは adapter を include しないので何も起きない。**

`library.properties` の `depends` に GFX を書かない。書くと Library Manager 経由で
入れた全員に GFX が付いてきて、**GFX 非依存という主張がそこで崩れる。**
表示サンプルだけが `sketch.yaml` の `libraries` で GFX を要求する。

## 12. カタログ生成

`tools/gen_boards.py` がカタログ表から、ボードヘッダ 64 本 / `README` の表 /
`keywords.txt` / `TinyM5Board.h` の `#define` 分岐を生成する。

**列の定義と「持たないもの」の一覧は [BOARD_CATALOG.ja.md](BOARD_CATALOG.ja.md)。**

要点だけ:

- **データは表、手順はコード。** 表を DSL にしない（D26）
- **手順は省略可。** POWER_HOLD・レール投入・LCD リセット・ボタン・バックライトは
  列から生成する。書くのは収まらないボードだけ
- **手順にレジスタ番号を書かない。** ボード側は役割名で言い、`0x12` はチップドライバに閉じ込める
- **機能フラグは列に持たない。** 対応する列が `None` かどうかで導出する。
  `kHasBacklight = true` なのに `backlight` が空、という食い違いを起こせなくする

手で 64 機種を並べると、追加のたびに漏れる。
