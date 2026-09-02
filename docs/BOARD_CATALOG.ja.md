# ボードカタログのスキーマ

内部の記録。日本語のみ。**カタログが何を持ち、何を持たないか。**

`tools/gen_boards.py` の中に Python の表として置く。TinyGFX の
`tools/gen_panels.py` と同じ形（カタログとツールを同じファイルに置く）。

## 1. 方針

### 1.1 データは表、手順はコード

ピンや群はデータなので表に入る。問題はレール投入の**手順**で、
StickC は AXP192 の 1 レジスタだが、StopWatch は M5IOE1 の 5 ピンを個別に設定して
リセットパルスを打ち、Tab5 は PI4IO 2 個に 5〜7 レジスタずつ書く。

これを表で表現しようとすると、任意のレジスタ列・待ち時間・パルスを書ける記述形式が要る。
**表が DSL になり、読めなくなる。**

上流も同じ結論に達している。M5Unified は `_pin_table_*`（データ）と
ボードごとの `switch`（手書きコード）に分かれていて、表に押し込もうとした形跡がない。

→ **データは表、手順はコード。**

### 1.2 ただし、大半のボードは手順を書かなくていい

手順の中身は列から導出できるものが多い。

| やること | どの列から出るか |
| --- | --- |
| POWER_HOLD を HIGH | `power_hold` |
| PMIC のレール投入 | `pmic` + `rails` |
| LCD リセットパルス | `display.rst` |
| ボタンピンを `INPUT_PULLUP` | `buttons` |
| バックライト初期化 | `backlight` |

→ **`power_on` は省略可。書かなければ列から生成する。**
収まらないボード（StopWatch / Tab5 / CoreP4X など）だけが書く。

### 1.3 手順にレジスタ番号を書かない

```cpp
// ✅ ボード側はどのレールを使うかだけを言う
Axp192::enable(w, Axp192::Ldo2 | Axp192::Ldo3 | Axp192::Dcdc1 | Axp192::Exten);

// ❌ ボード側にレジスタが漏れている
i2cWrite(w, 0x34, 0x12, 0x4D);
```

`0x12` も `0x4D` もチップドライバ側に閉じ込める。こうすると
手順がボードごとに 2〜5 行に収まり、**表を DSL にしないまま逃げ道が成立する。**

### 1.4 エントリが持つのは「回路図を見ないと分からないこと」だけ

TinyGFX の `panels/` と同じ規律（[DECISIONS.ja.md](DECISIONS.ja.md) 参照）。
導出できるものは 1 つも持たない。§4 に一覧がある。

## 2. 列

### 2.1 識別

| 列 | 例 | 生成されるもの |
| --- | --- | --- |
| `id` | `StickCPlus2` | ヘッダ名 `TinyM5BoardStickCPlus2.h` / クラス名 / `TINYM5_STICKCPLUS2` |
| `name` | `M5StickC Plus2` | `getBoardName()` / README の表 |
| `board_id` | m5stack-board-id の数値 | `getBoard()` |
| `family` | `Stick` | 群。README・サンプル・CI の並び順 |
| `soc` | `esp32` | **FPU の有無・I2C の数・`Wire1` の有無がここから導出される** |
| `note` | 短い説明 | README の表とヘッダ先頭のコメント |

### 2.2 ピン —— 出すのはこの 4 つだけ

照会できるピンは**最小限**にする。理由は §3。

| 列 | 例 | 意味 |
| --- | --- | --- |
| `i2c_int` | `(21, 22)` | 内部 I2C の `(sda, scl)`。`begin()` が `Wire` を開くのに使う |
| `i2c_ext` | `(32, 33)` / `None` | Port A（外部 Grove）。`None` なら外部バス無し |
| `power_hold` | `4` / `None` | POWER_HOLD |
| `rgb_led` | `(27, 1)` / `None` | `(ピン, 個数)` |

`buttons` はピン照会ではなく `Board.BtnA` の実体になるので別枠。

| 列 | 例 |
| --- | --- |
| `buttons` | `{A: (37, low), B: (39, low), Pwr: (35, low)}` / `Pwr: pek` |

### 2.3 電源

| 列 | 例 | 備考 |
| --- | --- | --- |
| `pmic` | `adc` / `axp192` / `axp2101` / `m5pm1` / `none` | `(axp192, axp2101)` と書くと**実行時に名乗らせる**（D5） |
| `bat_adc` | `(38, 2000)` | `pmic == adc` のときだけ。`(ピン, 分圧比 ×1000)` |
| `rails` | `(ldo2, ldo3, dcdc1, exten)` | `begin()` で投入するレール。**役割名で書く** |

### 2.4 バックライト

| 例 | 意味 |
| --- | --- |
| `(pwm, 27, 256, 40)` | `(方式, ピン, Hz, duty offset)` |
| `(axp192_ldo2,)` | AXP192 の LDO2 電圧 |
| `(m5ioe1_pwm, ch, pin)` | M5IOE1 の PWM チャネル |
| `None` | バックライトを持たない（EPD / OLED / LED / 画面なし） |

### 2.5 表示

| 例 |
| --- |
| `bus=spi2, mosi=15, miso=-1, sclk=13, dc=14, cs=5, rst=12,`<br>`freq_write=40M, freq_read=15M, w=135, h=240, ox=52, oy=40, invert` |
| `None`（画面なしボード） |

**パネルの型番は持たない。** AtomS3 / Tab5 / M5Stack 初代のように
同じ機種名で載っているガラスが違うことがあり、判別には SPI バスが要る
（[REQUIREMENTS.ja.md](REQUIREMENTS.ja.md) §4.4）。そこは GFX の仕事。

### 2.6 逃げ道

| 列 | 内容 |
| --- | --- |
| `power_on` | 省略可。列から生成できない手順だけを C++ で書く（§1.2 / §1.3） |

## 3. 照会ピンをこの 4 つに絞る理由

M5Unified の `getPin()` は内部 I2C / Port A〜E / SD 6 本 / RGB LED /
POWER_HOLD / MBUS 30 本を持つ（`M5Unified.hpp:26`）。
**IMU / RTC / Speaker / Mic は入っていない** —— ドライバ側に焼き込まれている。

| | 範囲 | 転記元 |
| --- | --- | --- |
| **採用** | 内部 I2C / Port A / RGB LED / POWER_HOLD | `_pin_table_i2c_ex_in` / `_pin_table_other0` / `_pin_table_other1` |
| 見送り | Port B〜E / SD 6 本 | `_pin_table_port_bc` / `_pin_table_port_de` / `_pin_table_sd`。**後から列を足せる** |
| 却下 | IMU / RTC / SPK / MIC | **構造化された転記元が無い。** 64 機種を回路図から起こすことになる |

判断基準は作業量ではなく**間違ったときの被害**。ピン表は「調べる手間を省く」ための
情報なので、間違っていると調べるより悪い。一度に多数のピンを埋めると、
検証できない値が大量に入る。

IMU については、そもそも**チップ種別が確定しない**（D6）ので、
ピンだけ出しても使う側はプローブが要る。出す価値が最初から薄い。

採用した 4 つはそれぞれ理由がある。

- **内部 I2C / POWER_HOLD** —— `begin()` が自分で使う。照会として出るのは副産物
- **Port A** —— Grove に何か挿すなら必ず要る。M5 の基本的な使い方
- **RGB LED** —— Atom 系では唯一の出力。例外として持つと決めた（D18）ものと対応する

## 4. 持たない —— ここが本体

| 持たないもの | どこから出るか |
| --- | --- |
| FPU の有無 / `Wire1` の有無 / I2C の数 | **`soc` から** |
| `kHasExternalI2c` | `i2c_ext` が `None` か |
| `kSharesI2cBus` | `i2c_int == i2c_ext` か |
| `kHasDisplay` / `kHasBattery` / `kHasBacklight` | 対応する列が `None` か |
| PMIC の I2C アドレス | **チップ固有**（AXP192 は常に `0x34`） |
| レジスタマップ | チップドライバ |
| リセットパルスの幅と待ち時間 | チップドライバ |
| 輝度カーブの式 | バックライト方式ごとに決まる |
| I2C 周波数の既定値 | チップドライバ |
| パネルの初期化コマンド列 | GFX |

**機能フラグを列として持たないのが効く。**
`kHasBacklight = true` と書いたのに `backlight` が空、という食い違いが
起こせなくなる。

## 5. 生成物

| | 内容 |
| --- | --- |
| `src/TinyM5Board<Id>.h` | ボードヘッダ 64 本 |
| `src/TinyM5Board.h` の `#define` 分岐 | `-DTINYM5_<ID>` からボードヘッダを引く |
| `README.md` / `README.ja.md` の表 | 群ごとに並べる |
| `keywords.txt` | ボード名・クラス名 |

`--check` で「生成物が最新か」を確かめられるようにする（TinyGFX の `gen_panels.py` と同じ）。

## 6. 上流の扱い

**カタログを埋めるときだけ上流を読む。取り込んだら凍結し、CI からは参照しない**
（[DECISIONS.ja.md](DECISIONS.ja.md) D24）。

| 欲しいもの | 参照先 |
| --- | --- |
| 内部/外部 I2C・RGB LED・POWER_HOLD | `M5Unified/src/M5Unified.cpp:85-300` |
| PMIC 種別・ADC ピンと分圧比 | `M5Unified/src/utility/Power_Class.cpp:109-876` |
| レール割り当て・表示のピンと諸元・バックライト方式 | `M5GFX/src/M5GFX.cpp`（[research/](research/) 01・02 に整理済み） |
| ボード ID の数値 | [m5stack-board-id](https://github.com/m5stack/m5stack-board-id) |
| Arduino Core が宣言するピン | [variants_collector](https://github.com/tanakamasayuki/variants_collector) |
