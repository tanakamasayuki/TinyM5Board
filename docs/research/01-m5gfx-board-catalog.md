# M5GFX がボード単位でやっていること全部

対象: M5GFX `d91077b` (v0.2.28) / `src/M5GFX.cpp`

表示ボード 35 種 + 外付けディスプレイ 10 種。パネルドライバの違いを除いた
「そのボードだからやっている処理」を、初期化・ランタイム・横断機構に分けて洗い出したもの。

---

## 1. 全体像

表示を持つボード 35 種の分類:

| 分類 | 種類数 | 内容 |
|---|---|---|
| 追加処理なし | **8** | LCD のピンを繋いで PWM でバックライトを点けるだけ |
| GPIO 1〜2 本 | **5** | POWER_HOLD / MAIN_PWR を HIGH にしないと数百 ms で電源が落ちる |
| I2C デバイス必須 | **22** | PMIC か IO エキスパンダのレジスタを叩かないと LCD に電源もリセット解除も届かない |

重要なのは **「初期化」で片付く処理と、片付かない処理がある**こと。
M5GFX の中身は次の 4 系統に分かれていて、A だけが「起動時に一度実行すれば終わり」。

| | 系統 | 内容 | 実行タイミング |
|---|---|---|---|
| **A** | 電源・レール投入 | PMIC の LDO/DCDC、エキスパンダの EN ピン、POWER_HOLD GPIO | 起動時に 1 回 |
| **B** | RST / CS の経路 | リセット線が GPIO ではなく PMIC / エキスパンダのレジスタビット。CoreS3 は CS ごとに GPIO マトリクスを書き換え | ドライバから随時 |
| **C** | バックライト | PWM ピンなのは 35 種中 11 種だけ。9 種は不要 (EPD/OLED/LED)。残る 15 種は PMIC の LDO 電圧かエキスパンダの PWM | `setBrightness` ごと |
| **D** | 個体差の判別 | 同一ボード名で載っているパネルが違う。Tab5 は DSI レーン速度が変わる | バス設定の前後 |

---

## 2. ボード別・表示に必要な前処理

凡例: 🟢 追加処理なし / 🟡 GPIO のみ / 🟠 I2C デバイス必須

「必要な前処理」は、そのボードで**表示を出すために最低限やらなければならないこと**だけ。
M5GFX が自動判別のためにやっているプローブ処理は 4 章に分離した。

### ESP32 (classic)

| | ボード | パネル・バス | 必要な前処理 | バックライト |
|---|---|---|---|---|
| 🟢 | **M5Stack**<br>Basic/Gray/Fire/Go | ILI9342C · SPI3 | なし。ただし `invert` の値をロット判別で決めている (`G33` をプルダウンして読み、内蔵プルアップの有無を見る)。SD が同一バス上にいるため、パネル ID を読む前に SD を SPI モードへ落とす必要あり | PWM `G32` 44.1 kHz |
| 🟠 | **M5StackCore2**<br>/ M5Tough | ILI9342C / 9342E · SPI3 | 初代は **AXP192**、v1.1 は **AXP2101**。搭載品の判別込みでレジスタ列が別<br>AXP192: `LDO2`=LCD 電源 3.3V、`GPIO4`=LCD RST、`GPIO1`=Tough の TP RST (オープンドレイン)<br>AXP2101: `ALDO4`=LCD/TP/TF 電源、`ALDO2`=LCD+TP RST、`DCDC1/3`=3.3V<br>⚠ **RST が GPIO ではない** → Category B | PMIC<br>Core2 初代 `DC3` / v1.1 `BLDO1` / Tough `LDO3`。輝度カーブもそれぞれ別式 |
| 🟠 | **M5Station** | ST7789 · SPI3 | **AXP192** 前提。LCD RST は `G15` (GPIO) | PMIC AXP192 `LDO3` (Tough と同一) |
| 🟠 | **M5StickC**<br>/ StickC Plus | ST7735S / ST7789 · SPI2 | **AXP192** I2C1 `G21/G22`。`reg 0x12 \|= 0x4D` で LDO2/LDO3/DCDC を投入。**これを書かないと画面が真っ黒のまま**。StickC はガンマ設定コマンドを追加送出 | PMIC AXP192 `LDO2`<br>(`reg 0x28` 上位ニブル、5〜15 の 11 段) |
| 🟡 | **M5StickCPlus2** | ST7789 · SPI2 | `G4`=POWER_HOLD を HIGH。落とすと電源が切れる。PMIC なし | PWM `G27` 256 Hz / offset 40 |
| 🟡 | **M5StackCoreInk** | GDEW0154D67 / M09 · SPI3 | `G12`=POWER_HOLD を HIGH。EPD が DeepSleep 中だと ID を読めないので `G0` のリセットは*常に*実施。パネルは 2 世代あり ID コマンドが異なる | なし (EPD) |
| 🟡 | **M5Paper** | IT8951 · SPI3 | `G2`=MAIN_PWR を HIGH。`G27`=BUSY のハンドシェイク待ち (最大 1 s) が必要。SD を SPI モードへ落とす処理あり。リセット復帰に約 800 ms | なし (EPD) |

### ESP32-S3

| | ボード | パネル・バス | 必要な前処理 | バックライト |
|---|---|---|---|---|
| 🟠 | **M5StackCoreS3**<br>/ CoreS3SE / StackChan | ILI9342C / 9342E · SPI2 | **AXP2101 + AW9523B** 両方必須。I2C1 `G12/G11`<br>AW9523: `0x02/0x03` 出力値、`0x04/0x05` CONFIG、`0x11` push-pull、`0x12/0x13` LEDMODE。`P1_1` が LCD RST<br>AXP2101: `0x90=0xBF`、`ALDO3`/`ALDO4` を 3.3V (カメラ・TF)<br>⚠ **G35 が MISO と LCD D/C の兼用** → CS の上げ下げごとに GPIO マトリクスを書き換え (Category B) | PMIC AXP2101 `DLDO1` (`reg 0x99`) |
| 🟢 | **M5Dial** | GC9A01 · SPI2 | なし。`G8`=RST は素の GPIO | PWM `G9` 44.1 kHz |
| 🟢 | **M5AtomS3** | ST7735S **または** GC9107 · SPI3 | なし。ただし同名ボードで**パネルが 2 種類**あり、ID を読んで分岐が必要 (Category D) | PWM `G16` 256 Hz / offset 48 |
| 🟠 | **M5AtomS3R** | ST7735S / GC9107 · SPI3 | **LED ドライバ @0x30** I2C `G45/G0`。`0x00=0x40` → 1 ms → `0x08=0x01`、`0x70=0x00` で有効化<br>一部ロットの GC9107 は 8 MHz で ID を返さないので **100 kHz で再プローブ**するフォールバックあり | I2C LED ドライバ `reg 0x0E` |
| 🟢 | **M5DinMeter** | ST7789 · SPI2 | なし | PWM `G9` 256 Hz / offset 16 |
| 🟢 | **M5Cardputer**<br>/ CardputerADV / VAMeter | ST7789 · SPI3 | なし。3 機種で LCD ピンは完全に同一、**解像度・オフセット・回転・BL 周波数だけが違う**。`G5/G6/G8/G9` のプルダウン読みと I2C 0x40/0x41 の応答で判別 (Category D) | PWM `G38`<br>Cardputer 256 Hz off 16 / VAMeter 512 Hz off 64 |
| 🟡 | **M5AirQ** | GDEW0154D67 / M09 · SPI2 | `G46`=POWER_HOLD を HIGH。CoreInk と同じ EPD 2 世代分岐 | なし (EPD) |
| 🟠 | **M5StampPLC** | ST7789 · SPI2 | **PI4IO @0x43** I2C `G13/G15`。`0x03` bit7 を出力、`0x0D` プルダウン、`0x07` Hi-Z 解除。SD が同一バスなので SPI モード落としが必要 | I2C PI4IO bit7 の **ON/OFF のみ** (調光不可) |
| 🟠 | **M5StickS3** | ST7789 · SPI3 | **M5PM1 @0x6E** I2C `G47/G48`。`GPIO2` を GPIO 機能→出力→push-pull→HIGH で L3B / LCD 電源。`0x09=0x00` で I2C アイドルスリープ無効化。投入後 100 ms 待ち | PWM `G38` 256 Hz / offset 16 |
| 🟠 | **M5StopWatch** | CO5300 AMOLED · QSPI | **M5PM1 + M5IOE1** I2C `G47/G48` 両方必須<br>PM1: `0x09=0` スリープ無効、`0x0A=0` WDT 無効、`0x06 \|= 0x17` (LDO/DCDC/CHG/LED)<br>IOE1: `0x23=0`、IO1/3/4/5/8 を push-pull 出力に、IO4=TP RST・IO5=OLED RST をリセットパルス、オーディオ PA を OFF<br>⚠ OPI-PSRAM 推奨 (無いと奇数座標の描画が崩れる) | なし (AMOLED / `0x51` で階調) |
| 🟠 | **M5PaperMono**<br>/ PaperMono Pro | SSD1677 4-Gray · SPI2 | **M5PM1 + M5IOE1** StopWatch と同じ I2C バス上。アドレス構成 (CST820 の有無 / NFC 0x50 の有無) で識別<br>IOE1: IO3=EPD EN、IO5=EPD RST、IO6=TP RST、IO13=TP EN、IO14=TF EN。EPD と TP のリセットパルス必須<br>⚠ **OPI-PSRAM 必須** (無い場合は表示機能ごと無効化) | I2C M5PM1 の PWM<br>(IO3 / `0x30`,`0x34` / 5 kHz、2 乗カーブ) |
| 🟠 | **M5ChainCaptain** | ST7789 · SPI2 | **M5PM1 + M5IOE1** I2C `G3/G2`。IOE1 IO12=LCD 電源、IO1=LCD RST。PM1/IOE1 とも I2C スリープと WDT を無効化<br>⚠ OPI-PSRAM 必須 | I2C M5IOE1 PWM_CH3 (IO11 / `0x1F`) |
| 🟠 | **M5PaperColor** | ED2208 · SPI2 | **M5PM1** I2C `G3/G2`。PM1 `GPIO0`=EPD 電源、`GPIO3`=SD 電源。投入後 100 ms 待ち。SD の SPI モード落としあり<br>⚠ OPI-PSRAM 必須 | なし (EPD) |
| 🟠🟡 | **M5PaperS3**<br>/ M5PaperDIY | パラレル EPD · Bus_EPD 8bit | PaperS3 🟡: `G44`=PWROFF_PULSE を LOW に固定<br>PaperDIY 🟠: **M5PM1** `GPIO2`=EPD_PWR を出力 HIGH<br>バスが SPI ではなく `spv/ckv/sph/oe/le/cl` + 8 bit データの EPD 専用パラレル<br>⚠ OPI-PSRAM 必須 | なし (EPD) |

### ESP32-P4 (MIPI-DSI)

| | ボード | パネル・バス | 必要な前処理 | バックライト |
|---|---|---|---|---|
| 🟠 | **M5CoreP4X** | ST7102 · MIPI-DSI 2 lane | **M5PM1 + M5IOE1** I2C `G11/G9`<br>IOE1 G8=TP RST、G9/G10/G11=BL / LCD 電源 / LCD RST、**G12=MBUS・TF・IMU・IR・Ethernet 共用の 3V3 レール**<br>DSI は `ldo_chan_id=3` / 2500 mV を確保してから init。投入後 150 ms 待ち<br>⚠ PSRAM 必須 | I2C M5IOE1 PWM (`0x1B`/`0x25`、1 kHz) |
| 🟠 | **M5Tab5**<br>/ Tab5X | ILI9881C / ST7121 / ST7123 · MIPI-DSI | **PI4IO @0x43 + @0x44** I2C `G31/G32`。両エキスパンダに 5〜7 レジスタずつ書き込み、LCD RST と GT911 RST を LOW→HIGH。`G23`(TP INT) を HIGH にして GT911 の I2C アドレスを選択してから開始<br>⚠ **パネル 3 種の判別が先**: タッチ IC の FW 版数 (1→ST7121 / 3→ST7123) か GT911 の ACK で判定。**DSI レーン速度が 900 / 1040 Mbps と変わる**ためバス init より前に確定が必要。ポーチ値もパネルごとに別<br>⚠ PSRAM 200 MHz 必須 | PWM `G22` 44.1 kHz |

### ESP32-C6 / C5 / C61

| | ボード | パネル・バス | 必要な前処理 | バックライト |
|---|---|---|---|---|
| 🟠 | **ArduinoNessoN1** (C6) | ST7789 · SPI2 | **PI4IO @0x43 + @0x44** I2C `G10/G8`。E1 の `P1`=LCD_RST、`P2`=EXT_PWR_EN、`P6`=LCD_BL、`P0`=システム電源断。E0 はボタン / LoRa<br>UnitC6L との区別は `G18` のプル状態 (GND 直結か否か) | I2C PI4IO `0x05` bit6 の **ON/OFF のみ** |
| 🟢 | **M5UnitC6L** (C6) | SSD1306 · SPI2 | なし。`G6`=CS、`G15`=RST は素の GPIO | なし (OLED) |
| 🟠 | **M5ToughC5** (C5) | ILI9342C · SPI2 | **M5PM1 + M5IOE1** I2C `G2/G3` (LP_I2C ポートを使用)<br>IOE1 PIN4=LCD_RST、PIN5=LCD_EN、PIN10=LCD_BL。**リセット線に基板プルアップが無い**ので、出力ラッチへ HIGH を書いてから push-pull / 出力化する順序が必須<br>PM1 `0x06 \|= 0x04` (LDO) → 10 ms → パネル ID 読み。`GPIO2`=TP_RST<br>起動時に **eFuse の flash/psram 容量**を見て、ディスプレイ無しの StampC5 なら一切ピンを触らずに抜ける | I2C M5IOE1 PWM_CH4 (`0x21`/`0x25`、ガンマ 2.0) |
| 🟠 | **M5CoreMatrix** (C61) | TM1680 LED matrix · **I2C** | **M5PM1 + M5IOE1** I2C `G0/G1`。IOE1 PIN4=LEDS_EN で LED レールを投入しないと **TM1680 が I2C に応答しない**。投入後 20 ms 待ち<br>表示デバイスが SPI ではなく I2C バス (`prefix_len=0`、コマンド/データ前置き無し) | なし (LED) |

---

## 3. 初期化では終わらないボード別処理

M5GFX の中では描画ドライバの内部から呼ばれている処理。

| 処理 | 対象 | 内容 |
|---|---|---|
| `rst_control()` | Core2 / CoreS3 / ChainCaptain / ToughC5 / CoreP4X / Tab5 ほか 13 種 | Core2 は **AXP192 `reg 0x96` bit1**、CoreS3 は **AW9523 `reg 0x03` bit1** が LCD RST。パネルクラスの `pin_rst` は `GPIO_NC` にして、リセット関数ごと差し替えている |
| `cs_control()` | **CoreS3 のみ** | **G35 が SPI MISO と LCD D/C の兼用**。CS を下げるたびに `GPIO_FUNC35_OUT_SEL_CFG_REG` を書き換えて「GPIO 出力 (D/C)」と「FSPI MISO 入力」を切り替える。**1 トランザクションごとにレジスタ 2 本を書く** |
| `ILight::setBrightness()` | 15 種 | PMIC の LDO 電圧 (Core2/Tough/StickC/CoreS3)、エキスパンダの PWM チャネル (ToughC5/ChainCaptain/CoreP4X/PaperMono)、ただの ON/OFF (StampPLC/NessoN1)。**輝度カーブもボードごとに別式**で `(b>>3)+72`、`(b+641)>>5`、`((b>>1)+8)/13+5`、2 乗ガンマ … と揃っていない |
| `initPanelByTouchVersion()` | Core2 / CoreS3 / StackChan | **タッチ IC FT5x06 の FIRMID を読んで LCD が ILI9342C か 9342E かを判定**し、9342E なら 15 バイトのガンマテーブルを含む追加初期化コマンド列を送る。パネル init の*後*に実行する必要があり `init_impl()` の末尾に置かれている |
| `initPanelFb()` | StopWatch | PSRAM 上にフレームバッファを確保し、**アクティブなパネルオブジェクトを差し替える**。確保に失敗したら直接描画にフォールバック |
| Touch `getTouchRaw()` | CoreS3 | タッチ座標が取れなかったとき、**AW9523 の `reg 0x00` と `0x01` を読んで INT をクリア**しないと以降割り込みが上がらない |
| `Panel_M5Stack::init()` | M5Stack 初代 | `invert` を **`G33` を出力 LOW → 入力プルダウン → HIGH 書き → read** という手順で内蔵プルアップの有無を調べて決定。パネル init の中に混ざっているボード判別 |
| `picture_frame` | SDL ビルド 8 種 | PC エミュレータ用の**筐体ベゼル画像**を `board_t` から選択して枠を描く。M5Stack / Core2 / CoreS3 / CoreInk / StickCPlus / StickCPlus2 / Dial / Tab5 |
| 外付けディスプレイ | AtomDisplay / ModuleDisplay | 同じ HDMI モジュールでも**母艦ボードによって配線が違う**。ModuleDisplay は AXP の有無で Core2/Tough か Basic/Fire かを判定して `i2c_port`・`spi_cs`・`spi_miso` を切り替え、AtomDisplay は **eFuse のパッケージ版数**で ATOM Lite/Matrix と ATOM PSRAM の SCLK ピンを切り替える |

---

## 4. 横断的な仕組み

「M5GFX が自動判別をやるから必要」なもの。**ボード決め打ちなら大半は不要**。

| 仕組み | 内容 | ボードを決め打ちにした場合 |
|---|---|---|
| `_set_sd_spimode()` | LCD と SD が SPI バスを共有するボード (M5Stack / Core2 / CoreS3 / StampPLC / PaperColor / Paper) では、**SD カードが SD モードのままだとバス上で応答してパネル ID 読みを壊す**。ダミークロック 128 発 → CMD58 で判定 → 必要なら CMD0 で SPI モードへ | **必要** |
| `_detect_i2c_device()` | SDA/SCL を入力プルダウンにして**外部プルアップの有無を確認**してから、ソフトウェア I2C でアドレス ACK を取る。アドレスの組み合わせを*シグネチャ*としてボードを識別 | 不要 |
| `probe_i2c_port = -1` | ボード確定までは**ハードウェア I2C ペリフェラルを一切確保せず**ビットバンで通信し、確定後に本番ポートへ引き継ぐ | 不要 |
| `gpio::pin_backup_t` | 各ボードの試行前に触るピンの状態を保存し、外れたら `restore()`。ToughC5 は **I2C デバイスのレジスタ値まで読んで保存し、不成立なら書き戻す** | 不要 |
| NVS キャッシュ | 判別結果を NVS の `M5GFX/AUTODETECT` に保存し、次回はそれを最初の候補にする。失敗時は最大 4 回リトライ、3 回目以降は `use_reset=true` を強制 | 不要 |
| ビルド時マクロ | `M5GFX_BOARD` か Arduino の `ARDUINO_M5STACK_*` が定義されていればそのボードを最初に試す。**判別を完全に飛ばすわけではない** (候補を絞るだけ) | — |

---

## 参照

- `src/M5GFX.cpp:1176-3790` — `M5GFX::autodetect()`
- `src/M5GFX.cpp:1046-1176` — `M5GFX::init_impl()` (NVS・post-init フック)
- `src/M5GFX.cpp:214-956` — Panel / Light サブクラス
- `src/lgfx/boards.hpp` — `board_t`
- `src/lgfx/v1/platforms/common.hpp:257-271` — I2C ヘルパの意味論
