# チップ別レジスタマップと Stick 系の初期化手順

M5GFX `d91077b` (v0.2.28) から復元した事実。**設計方針は含まない。**

Stick 系 4 機種の全手順と、AXP192 / M5PM1 のレジスタマップ。

---

## 1. Stick 系 4 機種の初期化手順

4 機種で**電源チップは AXP192 と M5PM1 の 2 種類、触るレジスタは各 2〜5 本だけ**。
Plus2 に至っては GPIO 1 本。

### M5StickC — ESP32 PICO-D4 / AXP192

**AXP192 の `reg 0x12` に `0x4D` を OR しないと画面が真っ黒のまま。**
LDO2 (バックライト)・LDO3・DCDC1・EXTEN が全部落ちているため。
Stick 系で一番よく踏まれる罠。

| | ピン |
|---|---|
| SPI | SPI2 |
| MOSI / MISO / SCLK | `G15` / `G14` / `G13` |
| DC / CS / RST | `G23` / `G5` / `G18` |
| I2C SDA / SCL | `G21` / `G22` |

パネル: ST7735S / 80×240 のうち 80×160 / offset 26,1 / offset_rotation 2 / invert /
27 MHz (read 14 MHz)

```c
/* 電源投入 — I2C1 400kHz, AXP192 = 0x34 */
i2c_init(21, 22);
reg_or(0x34, 0x12, 0x4D);   /* EXTEN | LDO3 | LDO2 | DCDC1 */
gpio_reset(18);             /* LCD RST: HIGH -> LOW 2ms -> HIGH 10ms */

/* バックライト = AXP192 LDO2 (reg 0x28 上位ニブル / 1.8V + 0.1V×n) */
void set_brightness(uint8_t b) {
    uint8_t v = (((b >> 1) + 8) / 13) + 5;      /* 0-255 -> 5..15 */
    if (b) reg_or (0x34, 0x12, 1 << 2);         /* LDO2 ON  */
    else   reg_and(0x34, 0x12, ~(1 << 2));      /* LDO2 OFF */
    reg_masked(0x34, 0x28, v << 4, 0x0F);       /* 下位ニブル(LDO3)は保持 */
}

/* ST7735S 初期化後にガンマ設定を追加送出: CMD_GAMMASET(0x26), 1 byte, 0x08 */
```

### M5StickC Plus — ESP32 PICO-D4 / AXP192 / StickC と共通

**電源シーケンスもピンも StickC と完全に同一。** 違いはパネルだけ (ST7735S → ST7789)。
`AXP192` の処理は 1 本にまとめられる。

パネル: ST7789 / 135×240 / offset 52,40 / invert / 40 MHz (read 15 MHz)

### M5StickC Plus2 — ESP32 PICO-V3-02 / PMIC なし

**PMIC なし。`G4` (POWER_HOLD) を HIGH にするだけ。**
ただしこれを `setup()` のできるだけ冒頭でやらないと、
**電源ボタンから指を離した瞬間に電源が落ちる**。

Plus からピン配置が変わっている点に注意 (**DC が `G23`→`G14`、RST が `G18`→`G12`**)。

| | ピン |
|---|---|
| SPI | SPI2 |
| MOSI / MISO / SCLK | `G15` / なし / `G13` |
| DC / CS / RST | `G14` / `G5` / `G12` |
| POWER_HOLD | `G4` |
| BL (PWM) | `G27` |

パネル: ST7789 / 135×240 / offset 52,40 / invert / 40 MHz (read 15 MHz)

```c
gpio_high(4);        /* POWER_HOLD — 最優先。落とすと即電源断 */
gpio_reset(12);      /* LCD RST */

/* バックライト = PWM G27 / 256 Hz / duty offset 40 */
/* offset 40 は「消灯しきらない下限」を持ち上げる補正 */
```

> **電池電圧**: PMIC が無いので **ADC 直読み**。M5Unified で確定済み
> (`Power_Class.cpp:658`): **`GPIO38` / ADC1 / 分圧比 2.0**。
> 電源ボタンは `GPIO35` (wakeup pin)。

### M5StickS3 — ESP32-S3 LGA56 / M5PM1

**M5PM1 の `GPIO2` を出力 HIGH にすると L3B が有効になり LCD に電源が来る。**
あわせて `0x09` (I2C アイドルスリープ) を無効化するのが必須。
電源を切ってもこのレジスタは保持されるので、
**他のコードが変更していると通信不能になる**。

| | ピン |
|---|---|
| SPI | SPI3 |
| MOSI / MISO / SCLK | `G39` / なし / `G40` |
| DC / CS / RST | `G45` / `G41` / `G21` |
| I2C SDA / SCL | `G47` / `G48` |
| BL (PWM) | `G38` |

パネル: ST7789 / 135×240 / offset 52,40 / invert / 40 MHz (read 16 MHz)

```c
/* M5PM1 = 0x6E / 100kHz */
i2c_init(47, 48);
reg_and(0x6E, 0x16, ~(0b11 << (2*2)));  /* GPIO2 を GPIO 機能に (2bit/pin) */
reg_or (0x6E, 0x10, 1 << 2);            /* GPIO2 出力 */
reg_and(0x6E, 0x13, ~(1 << 2));         /* GPIO2 push-pull */
reg_or (0x6E, 0x11, 1 << 2);            /* GPIO2 HIGH = L3B / LCD 電源 */
reg_write(0x6E, 0x09, 0x00);            /* I2C アイドルスリープ無効 */
delay(100);                             /* レール安定待ち */
gpio_reset(21);                         /* LCD RST */

/* バックライト = PWM G38 / 256 Hz / duty offset 16 */
```

> **M5GFX の記述ゆれ**: M5GFX の StickS3 のコードは `0x16` のビットを `1 << 2` で操作しているが、
> 同じ M5PM1 を使う PaperColor / ToughC5 側は **`0b11 << (pin*2)` (2 ビット／ピン)** で操作している。
> レジスタ `0x16` は 2 ビット／ピンの機能選択なので後者が正で、StickS3 側は
> 「GPIO2 の機能ビットの下位 1 本しかクリアしていない」形。
> 実機ではリセット直後の値が 00 なので動いているが、**新規実装では 2 ビット幅で書くべき**。

---

## 2. チップ別レジスタマップ

### AXP192 @0x34 — 表示系

| レジスタ | 内容 | Stick 系での用途 |
|---|---|---|
| `0x03` | IC タイプ (`0x03`=AXP192 / `0x4A`=AXP2101) | 存在確認・世代判別 |
| `0x12` | DC/LDO 出力有効<br>bit0 DCDC1 / bit1 DCDC3 / **bit2 LDO2** / bit3 LDO3 / bit4 DCDC2 / bit6 EXTEN | **`\|= 0x4D` が起動の要** |
| `0x28` | LDO2/LDO3 電圧<br>bit7-4 = LDO2、bit3-0 = LDO3 (1.8 V + 0.1 V × n) | バックライト輝度 (上位ニブル、5..15) |

### AXP192 @0x34 — 電源系 (M5GFX は未使用)

**ADC は既定で全部有効ではない。`0x82` で電池電圧 ADC を有効にしないと 0 が返る。**
`begin()` で必ず設定すること。

| レジスタ | 内容 |
|---|---|
| `0x00` | 電源状態<br>bit7 ACIN あり / bit6 ACIN 使用可 / **bit5 VBUS あり** / bit4 VBUS 使用可 / bit3 VBUS が VHOLD 超 / **bit2 電池電流方向 (1=充電)** / bit0 起動要因 |
| `0x01` | 充電状態<br>bit7 過温度 / **bit6 充電中 (0=完了 or 非充電)** / **bit5 電池あり** / bit3 電池活性化モード / bit2 充電電流が設定値未満 |
| `0x32` | シャットダウン / 電池検出 / CHGLED<br>**bit7 = 1 で電源 OFF** / bit6 電池モニタ有効 / bit5-4 CHGLED モード / bit3 CHGLED 制御元 |
| `0x33` | 充電制御 1<br>bit7 充電有効 / bit6-5 目標電圧 (00=4.1V, 01=4.15V, 10=4.2V, 11=4.36V) / bit4 終止電流 (0=10%, 1=15%) / bit3-0 充電電流 (0=100mA 〜 15=1320mA、**ステップ非線形**。正確な値はデータシート参照) |
| `0x35` | コイン電池 (RTC バックアップ) 充電<br>bit7 有効 / bit6-5 電圧 (00=3.1V, 01=3.0V, 10=3.0V, 11=2.5V) / bit1-0 電流 (00=50µA, 01=100µA, 10=200µA, 11=400µA) |
| `0x36` | PEK (電源キー) 設定<br>bit7-6 起動押下時間 / bit5-4 長押し判定時間 / bit3 長押しで自動 OFF / bit1-0 電源 OFF 押下時間 |
| `0x40`-`0x44` | IRQ 有効化 / `0x44`-`0x4A` IRQ ステータス (PEK 短押し・長押しはここ) |
| `0x56`/`0x57` | ACIN 電圧 — 12 bit / 1.7 mV per LSB |
| `0x58`/`0x59` | ACIN 電流 — 12 bit / 0.625 mA per LSB |
| `0x5A`/`0x5B` | **VBUS 電圧** — 12 bit / 1.7 mV per LSB |
| `0x5C`/`0x5D` | VBUS 電流 — 12 bit / 0.375 mA per LSB |
| `0x5E`/`0x5F` | 内部温度 — 12 bit / 0.1 °C per LSB / オフセット -144.7 °C |
| `0x70`-`0x72` | 電池瞬時電力 — 24 bit |
| `0x78`/`0x79` | **電池電圧** — 12 bit / **1.1 mV per LSB** |
| `0x7A`/`0x7B` | **電池充電電流** — 13 bit / 0.5 mA per LSB |
| `0x7C`/`0x7D` | **電池放電電流** — 13 bit / 0.5 mA per LSB |
| `0x7E`/`0x7F` | APS 電圧 — 12 bit / 1.4 mV per LSB |
| `0x82` | **ADC 有効化 1**<br>bit7 電池電圧 / bit6 電池電流 / bit5 ACIN 電圧 / bit4 ACIN 電流 / bit3 VBUS 電圧 / bit2 VBUS 電流 / bit1 APS 電圧 / bit0 TS ピン |
| `0x83` | ADC 有効化 2 — bit7 内部温度 |
| `0x84` | ADC サンプリングレート — bit7-6 (00=25Hz, 01=50, 10=100, 11=200) |
| `0xB0`-`0xB8` | クーロンカウンタ (充電 `0xB0`-`0xB3` / 放電 `0xB4`-`0xB7` / 制御 `0xB8`) |

ADC 値のフォーマット: 上位レジスタが上位 8 bit、下位レジスタの下位ニブル (13 bit のものは下位 5 bit) が残り。

> **AXP192 には残量計が無い。** % は電圧からの推定になる。AXP2101 は `0xA4` に残量レジスタを持つ。

### M5PM1 @0x6E — 表示系 (M5GFX の全用例から復元)

M5PM1 は Stick 系だけでなく StopWatch / PaperMono / ChainCaptain / PaperColor /
PaperDIY / CoreP4X / ToughC5 / CoreMatrix でも同じマップ。**計 9 機種。**

| レジスタ | 内容 | Stick 系での用途 |
|---|---|---|
| `0x00`-`0x01` | DEVICE_ID (16 bit LE = `0x2050`) | 存在確認 |
| `0x06` | PWR_CFG — bit2 = 3.3V LDO EN ほか (`0x17` で LED/LDO/DCDC/CHG 一括) | StickS3 では未使用 |
| `0x09` | I2C_CFG — `0x00` でアイドルスリープ無効 | **必須** / 電源断後も値が残る |
| `0x0A` | WDT_CNT — `0x00` でウォッチドッグ無効 | 推奨 |
| `0x10` | GPIO 方向 (1 bit/pin、1 = 出力) | GPIO2 を出力に |
| `0x11` | GPIO 出力レベル (1 bit/pin) | GPIO2 を HIGH に |
| `0x13` | GPIO ドライブ (0 = push-pull / 1 = open-drain) | GPIO2 を push-pull に |
| `0x16` | GPIO 機能選択 (**2 bit/pin**、00 = GPIO) | GPIO2 を GPIO 機能に |
| `0x30`-`0x31` | PWM0 duty L/H (H の bit4 = enable) | PaperMono のフロントライト |
| `0x34`-`0x35` | PWM 周波数 L/H (Hz、16 bit LE) | 同上 |

### M5PM1 — 電源系

**M5GFX からは分からない。** M5GFX が触っているのは上表の表示系レジスタだけで
(`0x00`,`0x06`,`0x09`,`0x0A`,`0x10`,`0x11`,`0x13`,`0x16`,`0x30`-`0x31`,`0x34`-`0x35`)、
電池・充電系のレジスタは一度も出てこない。

以下は M5Stack 公式ドライバ (`~/dev/M5PM1/src/M5PM1.h`、MIT) から。

| レジスタ | 内容 |
|---|---|
| `0x00`-`0x03` | DEVICE_ID / DEVICE_MODEL / HW_REV / SW_REV |
| `0x04` | PWR_SRC — 現在の給電源。**0=5VIN / 1=5VINOUT / 2=電池** |
| `0x05` | WAKE_SRC — 起動要因 (bit2 電源ボタン / bit1 VIN 挿入 / bit0 タイマ ほか)。**0 を書いてクリア** |
| `0x06` | PWR_CFG — bit0 CHG_EN / bit1 DCDC_EN (5V) / **bit2 LDO_EN (3.3V)** / bit3 BOOST_EN (5VINOUT) / bit4 LED_EN |
| `0x07` | HOLD_CFG — 電源保持。bit5 LDO / bit0-4 GPIO0-4 の出力状態。**リセット/シャットダウンで 0 に戻る** |
| `0x08` | BATT_LVP — 低電圧保護。**mV = 2000 + n × 7.81** (2000〜4000 mV) |
| `0x09` | I2C_CFG — bit4 速度 (0=100k/1=400k) / bit3-0 **アイドルスリープ秒 (0=無効)** |
| `0x0A` | WDT_CNT — ウォッチドッグ秒 (0=無効) / `0x0B` WDT_KEY に `0xA5` で餌やり |
| `0x0C` | SYS_CMD — **上位ニブルに `0xA` が鍵**。下位 2 bit: 01=シャットダウン / 10=再起動 / 11=ダウンロードモード |
| `0x22`/`0x23` | **VBAT — mV そのまま、リトルエンディアン** |
| `0x24`/`0x25` | VIN 電圧 (mV) / `0x26`/`0x27` 5VINOUT 電圧 (mV) |
| `0x28`/`0x29` | ADC 結果 (mV) / `0x2A` ADC_CTRL |
| `0x40`-`0x42` | IRQ ステータス 1〜3 / `0x43`-`0x45` IRQ マスク |
| `0x48` | BTN_STATUS — **bit7 押された履歴 (読むと自動クリア) / bit0 現在の状態** |
| `0x49`/`0x4A` | BTN_CFG |
| `0x60`- | NeoPixel データ / `0xA0`- RTC RAM (32 バイト) |

**残量計は無い。** `0x22`/`0x23` の電圧から推定するしかない (AXP192 と同じ)。

**充電中かどうかを直接返すレジスタも無い。** `0x04` (PWR_SRC) が電池以外を指していれば
外部電源が来ている、という推定になる (M5Unified の `isCharging()` は無条件で false を返す)。

---

