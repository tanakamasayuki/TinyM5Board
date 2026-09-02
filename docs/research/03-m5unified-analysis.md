# M5Unified の実態調査

調査対象:

- `~/dev/M5Unified` — 19,702 行 (src 配下 .cpp/.hpp/.h)
- `~/dev/M5GFX` — 663,028 行 (大半はフォントデータ)
- `~/dev/M5PM1` — 9,481 行 (M5Stack 公式 PM1 ドライバ)

M5Unified が何をどうやっているか。**設計方針は含まない。**

---

## 1. M5Unified のボード別処理

`M5Unified.cpp` 内の `board_t::board_` 参照は **409 箇所**、
`Power_Class.cpp` だけで `case board_t::board_` が **148 個**。
ボード別処理は次の 6 系統に分かれている。

### 1-1. ピンテーブル (宣言的データ)

`M5Unified.cpp:85-300` に、ボード ID をキーにした静的テーブルが並んでいる。

```c
static constexpr const uint8_t _pin_table_i2c_ex_in[][5] = {
                            // In SCL,SDA, EX SCL,SDA
{ board_t::board_M5StackCoreS3, GPIO_NUM_11,GPIO_NUM_12 , GPIO_NUM_1 ,GPIO_NUM_2  },
{ board_t::board_M5StickS3    , GPIO_NUM_48,GPIO_NUM_47 , GPIO_NUM_10,GPIO_NUM_9  },
/* ... */
{ board_t::board_unknown      , GPIO_NUM_39,GPIO_NUM_38 , GPIO_NUM_1 ,GPIO_NUM_2  }, // 既定値
};
```

テーブルの種類:

| テーブル | 内容 |
|---|---|
| `_pin_table_i2c_ex_in` | 内部 I2C / 外部 (PortA) I2C の SCL・SDA |
| `_pin_table_port_bc` | PortB / PortC のピン |
| `_pin_table_port_de` | PortD / PortE のピン |
| `_pin_table_sd` | SD の CLK/CMD/D0/D1/D2/D3 |
| `_pin_table_other0` | RGB LED |
| `_pin_table_other1` | **POWER_HOLD** |

**ボード表をデータとして持つ形が、ここに既に実装されている。**
照会 API は `M5.getPin(pin_name_t::rgb_led)` の 1 本。

### 1-2. PMIC の選択と初期化 — `Power_Class::begin()`

ボード → `pmic_t` の 7 分類 + ボード固有の初期化。

```c
enum pmic_t
{ pmic_unknown
, pmic_adc      // PMIC 無し。ADC で電池電圧を直読み
, pmic_axp192
, pmic_ip5306
, pmic_axp2101
, pmic_aw32001
, pmic_m5pm1
};
```

**`pmic_adc` の存在が重要。** PMIC を持たないボードは ADC 直読みで、
ピンと分圧比がここに書いてある:

```c
case board_t::board_M5StickCPlus2:
  _wakeupPin  = GPIO_NUM_35;      // 電源ボタン
  _batAdcCh   = ADC1_GPIO38_CHANNEL;
  _batAdcUnit = 1;
  _batAdcPin  = 38;               // ← GPIO38
  _pmic       = pmic_t::pmic_adc;
  _adc_ratio  = 2.0f;             // 分圧比 1/2
  break;
```

`pmic_adc` を使うボード: StickCPlus2 / Capsule / AirQ / DinMeter / Cardputer / CardputerADV /
TimerCam / CoreInk / Paper / PaperS3。**10 機種が「PMIC 無しで ADC 直読み」**。

### 1-3. IO エキスパンダの選択 — `_setup_i2c()`

ボード → `M5IOE1_Class` / `PI4IOE5V6408_Class` を生成して `_io_expander[]` に保持。
`IOExpander_Base` という抽象基底があり、`setDirection` / `setPullMode` /
`setHighImpedance` / `getWriteValue` などの純粋仮想を持つ。

| チップ | 使用ボード |
|---|---|
| `M5IOE1_Class` | CoreP4X / ChainCaptain / PaperMono / StopWatch / ToughC5 / CoreMatrix |
| `PI4IOE5V6408_Class` | Tab5 / Tab5X / UnitC6L / NessoN1 / StampPLC |

### 1-4. LED

ボード → `LED_PowerHub_Class` / `LED_PMIC_Class` / `LED_PaperMono_Class` / `LED_Strip_Class`。
`LED_Base` 抽象 + `LedBus_RMT`。AtomMatrix は `led_count = 25`、PaperColor は 2。

### 1-5. スピーカー / マイクの enable コールバック

**ボードごとに関数が 1 つずつ生えている。** 発見できたものだけで:

```
_speaker_enabled_cb_core2 / _cores3 / _sticks3 / _papercolor / _stopwatch /
_chain_captain / _tab5 / _corep4x / _hat_spk / _atomic_echo / _cardputer_adv /
_atom_echos3r
_microphone_enabled_cb_stickc / _cores3 / _atomic_echo / _atom_echos3r /
_sticks3 / _papercolor / _papermono / _stopwatch / _chain_captain / _tab5 /
_corep4x / _cardputer_adv
```

中身は「codec の EN ピンを叩く」「PA の電源を入れる」「I2C を一時的に切り替えて
アンプのレジスタを書く」といったもの。**ここが最もボード固有性が高く、最も肥大化している。**

### 1-6. 個別ワークアラウンド

`_begin()` の中にボードごとの一点ものが入っている。例:

- **M5Stack**: `GPIO15` を LOW に固定 (M5GO ボトム接続時に WiFi 感度が落ちる問題)
- **M5Stack Core v2.6**: SPI 通信速度を上げられない個体への対応
- **CoreInk**: スピーカー EN ピンが `GPIO25`、他は `GPIO0`

### 1-7. チップドライバの規模

```
power/AXP2101   608 + 208 行
power/AXP192    361 + 114 行
power/M5PM1     352 + 250 行
power/IP5306    142 +  49 行
power/AW32001   120 +  59 行
power/INA226     77 + 126 行
power/BQ27220    94 +  33 行
power/INA3221    75 +  53 行
power/PY32PMIC         14 行
                ------------
                    2,735 行
```

**電源関連だけを切り出すと** `Power_Class` (2,971 + 301) + `power/*` (2,735) +
IOExpander 3 ファイル + `I2C_Class` ≈ **6,500〜7,000 行**。M5Unified 全体の約 1/3。

---

## 2. なぜ M5Unified は重いのか — 構造的な理由

`M5Unified.hpp:229-256`:

```cpp
M5GFX Display;              // ← M5GFX 全体をリンク
M5GFX &Lcd = Display;
IMU_Class Imu;
Log_Class Log;
Power_Class Power;
RTC_Class Rtc;
Touch_Class Touch;
Speaker_Class Speaker;
Mic_Class Mic;
LED_Class Led;
Button_Class _buttons[5];
```

**すべてが具体メンバとして宣言されている。**
`config_t` の `internal_imu` / `internal_rtc` / `internal_mic` / `internal_spk` といったフラグは
**実行時の初期化をスキップするだけ**で、コンパイルとリンクは常に行われる。

つまり「使わない機能を切ってビルドを軽くする」ことが**設計上できない**。
機能を削れば直る問題ではなく、god オブジェクト設計の帰結。

---

## 3. ペリフェラル直叩きの実態

### 3-1. I2C — 完全に直叩き

M5GFX の `lgfx::i2c` (`src/lgfx/v1/platforms/esp32/common.cpp`) は
**ESP32 の I2C ペリフェラルレジスタを直接読み書きしている**。

```c
periph_module_enable(mod);
static i2c_dev_t* getDev(int num);
dev->command[index].val = cmd.val;
dev->int_clr.val = int_raw.val;
auto fifo_reg = (volatile uint32_t*)(&dev->fifo_data);
```

ESP-IDF の `i2c_driver_install()` も Arduino の `Wire` も使わない。
**同じ I2C ポートで `Wire` を使うと衝突する。**

回避策として `i2c_temporary_switcher_t` (「一時的にピンを奪って元に戻す」仕組み) が
用意されているが、これは共存が構造的に難しいことの裏返し。

### 3-2. SPI — ハイブリッド

```c
spi_bus_initialize(host, &buscfg, dma_channel);
spi_device_acquire_bus(_spi_dev_handle[spi_host], portMAX_DELAY);
/* ...ただし転送は... */
writereg(SPI_CMD_REG(spi_port), SPI_EXECUTE);
while (*reg(SPI_CMD_REG(spi_port)) & SPI_USR);
```

IDF ドライバに登録はするのでバスレベルの排他は効くが、転送自体はレジスタ直叩き。
Arduino の `SPI` クラスとは依然として共存しづらい。

### 3-3. 対照 — M5Stack 公式 M5PM1 ライブラリは正解の形

`~/dev/M5PM1/src/M5PM1_i2c_compat.h` が **4 系統の I2C を吸収**している:

- Arduino `Wire` (`TwoWire*`)
- ESP-IDF `i2c_master` (新 API)
- `i2c_bus` (esp-idf-lib)
- Legacy `driver/i2c.h`

```cpp
m5pm1_err_t begin(TwoWire* wire = &Wire, uint8_t addr = M5PM1_DEFAULT_ADDR, ...);
m5pm1_err_t begin(i2c_bus_handle_t bus, uint8_t addr = M5PM1_DEFAULT_ADDR, ...);
```

4 系統の I2C を 1 つのヘッダで吸収しており、`Wire` を受け取る形も用意されている。

---
