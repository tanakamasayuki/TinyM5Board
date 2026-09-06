# 開発計画

内部の記録。日本語のみ。**現在地と残作業。**

## 1. 現在地

**37 機種。ADC / AXP192 / AXP2101 / M5PM1 / AW32001 の 5 系統が、ホストのゴールデンと
実物のツールチェーンのビルド（Tier 0）まで通っている。SoC は esp32 / S3 /
C3 / C6 / H2 / **P4** の 6 種類。**

| 項目 | 状況 |
| --- | --- |
| 責務・設計・決定の文書化 | **一巡した**（[README.ja.md](README.ja.md) の一覧） |
| `tools/gen_boards.py` | ボードヘッダ / 入口 / `BoardId.h` / テスト一式を生成、`--check` と `--families` |
| ボード定義 | **37 機種** —— Atom: AtomLite / AtomMatrix / AtomU / AtomVoice / AtomS3Lite / AtomS3U、Core: Core2 / Tough / Station / ChainCaptain / CoreS3 / CoreS3SE / StackChan / **CoreP4X**、Stick: StickC / StickCPlus / StickCPlus2 / StickS3、Stamp: StampPico / **StampS3** / **StampC3** / **StampC3U** / StampPLC、Other: TimerCam / Capsule / NanoC6 / NanoH2 / Dial / DinMeter / StopWatch / Cardputer / VAMeter / AirQ / **NessoN1**、Paper: PaperMono / Paper / **CoreInk** |
| 電源 | `PowerAdc` / `PowerAxp192` / `PowerAxp2101` / `PowerM5pm1` / `PowerCore2`（二択の判別） / **`PowerAw32001`**（充電器 + 燃料計の 2 チップ、D42） |
| IO エキスパンダ | `IoExpanderM5ioe1` / `IoExpanderAw9523` / `IoExpanderPi4io`。**主要 3 種**。**1 機種に 2 個**も持てる（D43） |
| バックライト | PWM / AXP192 (Ldo2・Ldo3・Dc3) / AXP2101 (Bldo1・Dldo1) / Core2 / M5IOE1 の PWM / **M5PM1 の PWM**。**すべて M5GFX と同じカーブ** |
| ボタン | GPIO / PMIC の電源キー / **IO エキスパンダのピン**を同じ型で。名前はカタログから導出（CoreInk の `Ext` で 5 つ目）。**click / hold / click カウントまで M5Unified と同じ状態機械**（D36） |
| 表示 | `TinyM5::Display`（SPI / QSPI / EPD の BUSY）と **`DisplayDsi`**（MIPI-DSI、D41） |
| `tests/begin/` | **38 スケッチ通過**（Core2 が二択で 2 本）**。群ごとのディレクトリ**で、CI の matrix 軸もこれ。1 バスに複数チップのモデルに対応 |
| `tests/tier0/` | **全機種のヘッダを実物のコアでビルド**。マクロと定数の一致を `static_assert` で（37 機種 + 入口 2 本 / **6 種類の SoC**） |
| `tests/tier2/` | **サンプルを実機コアで建てる**（D20 の裏取り）。4 本 / 約 28 秒 |
| `tests/unit/` | **ボード非依存のクラス**の検査。Button の状態機械と SD のモード落とし（39 + 13 検査 / 約 16 秒） |
| `.github/workflows/tests.yml` | **群ごとに並列**。軸はカタログから生成。`unit` / `tier0` / `examples` は別ジョブ |
| I2C | 内部 / 外部の 2 本。**内部を持たない module では Grove が `Wire`**（D37） |
| SD | **パネルとバスを共有する 6 機種でモードを落とす**（D38）。バスは `SPI.end()` で返す |
| `keywords.txt` | **あり。** `gen_boards.py` が**ヘッダを読み直して**生成する |
| 利用者向け README | **無い。** 機種が揃ってから |

### 1.1 実測（arduino-esp32 3.3.11 / 同一スケッチ）

| 構成 | フラッシュ |
| --- | --- |
| AtomLite（電源ハードなし） | 312,708 B |
| Core2（両チップをリンク） | 313,524 B |
| Core2（片方に固定） | 312,748〜313,044 B |
| StickC（AXP192） | 314,144 B |
| StickS3（M5PM1 / ESP32-S3） | 332,736 B |
| ChainCaptain（M5PM1 + M5IOE1 / ESP32-S3） | 322,017 B |
| CoreS3（AXP2101 + AW9523B / ESP32-S3） | 320,265 B |
| StampPLC（PI4IO のみ / ESP32-S3） | 321,329 B |

**SD のモード落とし（D38）は +5,324 B。** 中身ではなく Arduino の `SPI` を
引くぶんで、該当するのは 6 機種のみ。

**二択のまま持つ代金は 480〜776 バイト。**

### 1.2 実装して分かったこと

**`if constexpr` では機能の有無を分岐できない**（D31）。`TINYM5_HAS_*` を出す。
ボタンは**ボード間で一番ばらつく**ので `TINYM5_HAS_BTN_*` も要る。

**ゴールデンは順序だけでは足りない**（TEST_PLAN §3.2.2）。カタログの中身も入れる。

**読み出しは差し込んで検算する**（TEST_PLAN §3.2.1）。分圧比も 12 bit の組み立ても、
間違っていても「それらしい電圧」が出るだけで落ちない。

**`power_on` は `Power.begin()` の後**（D32）、**レール電圧はレール投入の前**（D33）。

**二択の判別は上位で 1 回だけ読む。** 各ドライバに順番に `probe()` させると
実機がやらない「失敗した検出」がトレースに残る。

**`bit()` は Arduino のマクロ。** 同名のメンバ関数を書くとプリプロセッサに
書き換えられ、エラーがコアのヘッダの行番号で出る。

**間引いた `update()` は「変化なし」を返さないといけない。** I2C 越しのボタンは
デバウンス間隔に 1 回しか読まないが、読まなかった回で前回のエッジを立てたままに
すると、**1 回の押しが `wasPressed()` で何回も取れる。** 押した回数を数える
サンプルは、これで必ず狂う。読み飛ばす経路にも状態を畳む処理が要る。

### 1.3 テストの所要時間

`tests/begin` は 1 本ごとにスケッチをビルドして実行するので、**機種数に線形**。
**1 スケッチ約 10 秒**（実測）なので 38 本で 6 分。**群ごとに並列化してある**ので
CI では最長の群の時間で済み、ローカルは `pytest begin/Stick` のように絞れる
（4 機種で約 30 秒 / 実測）。

`tests/tier0` は 39 本ビルドして**約 3 分**、`tests/unit` は 2 本で**約 16 秒**。
**全部で 11〜19 分**（35 機種 + サンプル 4 本 / ローカル実測。他のビルドと並走すると倍近く振れる）。
どちらも機種数に線形だが、実行が無い分だけ安い。
ボード非依存の変更は `unit` だけ回せばよい。

**いまの最長は Other 群の 11 スケッチ**（Core 群が 8 で続く）**。** Dial / DinMeter / Cardputer / VAMeter /
StopWatch のように「群に収まらない製品」が全部ここに落ちるので、今後も伸びる。
**軸を群からボード単位に落とす**時期が近い（生成できるので workflow は変わらない）。

## 2. 次にやること

順序に意味がある。**土台を先に作らないと、機種を増やした分だけ壊れる。**

### 2-1. テスト基盤を作る

方針は [TEST_PLAN.ja.md](TEST_PLAN.ja.md) で決まった。**必要なものは全部揃っている。**

host-arduino-core 1.5.0 のバス観測ポート（GPIO / I2C / SPI の 3 つ）で、
`Board.begin()` が触るものは全部見える。`setReadHook` で応答を差し込めるので、
Core2 の PMIC 判別のような分岐も両方通せる。

作るもの —— **すべて済**:

- ~~`tests/` の骨格（pytest + uv、`.github/workflows/tests.yml`）~~
- ~~Tier 0（全機種のヘッダ単体コンパイル）~~ —— `tests/tier0/`。
  **実物のツールチェーンが通る唯一の層**で、マクロと定数の一致まで
  `static_assert` で見る（TEST_PLAN §2）
- ~~観測ポートのログを 1 本にまとめるヘルパと、ゴールデンの比較・更新~~

**ボードを 1 機種も書く前にここを作る。** 逆順にすると、増やした分だけ壊れる。

### 2-2. カタログを埋める

列の定義。「回路図を見ないと分からないことだけ」に絞る
（[CORE_DESIGN.ja.md](CORE_DESIGN.ja.md) §12）。

**上流は取り込み時の資料としてだけ使う**（D24）。CI からは参照しない。

| 欲しいもの | 参照先 |
| --- | --- |
| ボード別ピン | `M5Unified/src/M5Unified.cpp:85-300`（`_pin_table_*`） |
| ボード別 PMIC 選択 | `M5Unified/src/utility/Power_Class.cpp:109-876` |
| AXP192 / AXP2101 / M5PM1 ドライバ | `M5Unified/src/utility/power/` |
| IO エキスパンダ | `M5Unified/src/utility/M5IOE1_Class.*` / `PI4IOE5V6408_Class.*` |
| M5PM1 の完全な仕様 | `M5PM1/README_FUNCTION_EN.md` + `src/M5PM1.h` |
| ディスプレイ側のピンと初期化 | `M5GFX/src/M5GFX.cpp`（[research/](research/) 01 / 02 に整理済み） |
| Arduino Core が宣言するピン | [variants_collector](https://github.com/tanakamasayuki/variants_collector)（`src/variants_collector.h`。M5 向けの override つき） |

すべて MIT。

**取り込んだ時点を書いておく。** 凍結モデル（TEST_PLAN §1）では
「いつの上流から起こした値か」だけが後から効く。

| 取り込み | 対象 | 上流 |
| --- | --- | --- |
| 2026-09-05 | AtomMatrix / AtomU / AtomVoice / AtomS3Lite / AtomS3U / StampPico / CoreS3SE / StackChan | M5Unified・M5GFX の `master`（`_pin_table_*`、ボタンの `switch`、`boards.hpp`、CoreS3 の分岐） |

**M5PM1 の電源系レジスタは M5GFX からは分からない。**
表示系（`0x00` `0x06` `0x09` `0x0A` `0x10` `0x11` `0x13` `0x16` `0x30`-`0x31` `0x34`-`0x35`）しか
出てこないため、電池・充電は `~/dev/M5PM1` を読む必要がある。

### 2-3. `tools/gen_boards.py` を書く

カタログ → ボードヘッダ 64 本 / README の表 / `keywords.txt` /
`TinyM5Board.h` の `#define` 分岐。

**手で 64 機種を並べない。** 追加のたびに漏れる。

### 2-4. AtomLite を通しで作る（D30）—— **済**

起点は **AtomLite**。画面なし・電源ハードなし・ボタン 1 つ・RGB LED 1 つで、
骨格を通すのに最小。しかも**本命の領域**（画面なしボード 29 機種）の代表そのもの。

| 列 | 値 | 出所 |
| --- | --- | --- |
| `board_id` | 128 | `boards.hpp:49` |
| `soc` | esp32 | |
| `i2c_int` | SDA 25 / SCL 21 | `M5Unified.cpp:143` |
| `i2c_ext` | SDA 26 / SCL 32 | 同上（Port A） |
| `rgb_led` | (27, 1) | `M5Unified.cpp:266` |
| `power_hold` | なし | `_pin_table_other1` に無い |
| `buttons` | A = 39 / active-low | `M5Unified.cpp:2336` |
| `pmic` / `backlight` / `display` | なし | |

**「初期化一切なし」ではない。** `M5Unified.cpp:2299` に、CH552 が GPIO0 に 4V を
かけて WiFi 感度が落ちる問題への対策として GPIO0 を出力 HIGH にする処理がある。
役割名で表現できない一点ものなので、**`power_on` の逃げ道が最初から要る。**

なお GPIO39 は ESP32 では入力専用でプルアップを持たないため `INPUT_PULLUP` にできない。
これは SoC の制約なので**列に持たず `soc` とピン番号から導出する**
（[BOARD_CATALOG.ja.md](BOARD_CATALOG.ja.md) §4）。

### 2-5. 広げる

最終的にはなるべく多くの機種を載せる。安い順に:

1. ~~電源ハードを持たない画面なしボード~~ —— AtomLite で通した
2. ~~POWER_HOLD 1 本のボード~~ —— TimerCam / Capsule / StickCPlus2 で通した
3. ~~AXP192~~ —— StickC / StickC Plus で通した。ドライバは Core2 / Tough /
   Station にもそのまま効く
4. ~~Station / Tough~~ —— 通した。**リセットが I2C 越し**の形
   （`display().rst == -1`）はここで実地になった
5. ~~Core2~~ —— 通した。**二択の判別（D5）は両分岐ともホストで検証済み**
6. ~~M5PM1~~ —— ドライバは書けた。StickS3 で通した
7. ~~M5IOE1~~ —— ドライバは書けた。ChainCaptain で通した。
   **同じ 2 チップ構成の StopWatch / PaperMono / CoreP4X / ToughC5 / CoreMatrix は
   ピン割当だけ**（ただし表示バスが AMOLED QSPI / EPD / MIPI-DSI / LED マトリクスと様々）
8. ~~CoreS3~~ —— 通した。**CoreS3SE / StackChan も通した。**
   上流も 3 機種で 1 つの分岐なので、`CORE_S3_POWER_ON` を 3 エントリで共有している
   （違いはカメラと servo 側のエキスパンダで、電源にも表示にも関わらない）
9. ~~PI4IOE5V6408~~ —— 通した。**NessoN1 はエキスパンダ 2 個で同じ形**
10. 画面なしボード —— **AtomMatrix / AtomU / AtomVoice / AtomS3Lite / AtomS3U /
    StampPico / StampS3 / StampC3 / StampC3U / NanoC6 / NanoH2 を通した。**
    どれもピン表と識別子だけで、`power_on` を書いたものは無い
    （CH552 の GPIO0 バイアスは AtomLite と共有する定数にした）。
    **内部 I2C を持たない形は `i2c_int` を省略可にして通した**（D37）。
    C3 / C6 / H2 が入ったので、Tier 0 が RISC-V のツールチェーンも通るようになった

**電源と IO の側は主要なチップが出揃った。**
AXP192 / AXP2101 / M5PM1 / ADC と、M5IOE1 / AW9523B / PI4IO。
残るボードの大半は**カタログにピンを書くだけ**で届く。
届かないのは表示バスが SPI でない機種で、それは §2-7 の宿題。

### 2-7. 積んである宿題

**SD のモード落としは済**（D38）。カタログにいる 6 機種
（Core2 / Tough / CoreS3 / CoreS3SE / StackChan / StampPLC）で通っている。
まだ入っていない M5Stack 初代 / PaperColor / Paper は、機種を足せば列を書くだけ。

| | |
| --- | --- |
| **SPI 以外の表示バス** | 下の §2-8 に分解した。**「大きい設計判断 1 つ」ではなく、小さいのが 3 つと本物が 1 つ** |
| CoreS3 の GPIO35 兼用 | MISO と D/C を共有しており、CS のたびに GPIO マトリクスの書き換えが要る。**SPI トランザクション層の話なので GFX の領分**。諸元では両方の役割を報告し、注記している |

### 2-8. SPI 以外の表示バス —— 上流を読んで分解した

**「`TinyM5::Display` に入らない」と一括りにしていたが、中身は 4 つ別の話だった。**
M5GFX の該当分岐を読んだ結果（2026-09-06 の master）。

| 機種 | バス | いまの構造体に足りないもの |
| --- | --- | --- |
| ~~**PaperMono** (EPD)~~ | **素の SPI** —— mosi 14 / sclk 15 / dc 17 / cs 16 / 3wire | ~~`busy` ピン 1 本~~ **—— 足して通した** |
| ~~M5Paper~~ / PaperS3 / PaperColor (EPD) | 同上 | **M5Paper は通した。** 残り 2 つは §2-9 |
| ~~**StopWatch** (AMOLED)~~ | **QSPI** —— io0 41 / io1 42 / io2 46 / io3 45 / sclk 40 / cs 39 | ~~バスの種別と `io2` `io3`~~ **—— 足して通した** |
| ~~**CoreP4X**~~ | **MIPI-DSI** | ~~レーン数・タイミング一式~~ **—— `DisplayDsi` を隣に置いて通した（D41）** |
| CoreMatrix | LED マトリクス (I2C) | そもそもフレームバッファのパネルではない |

**提案（暫定）**:

1. ~~**EPD は `busy` を 1 列足すだけで届く。**~~ —— **そのとおりだった。**
   `Display::busy` を足し、PaperMono を通した（D39）。M5Paper / PaperS3 /
   PaperColor はピンを書くだけで入る
2. ~~**QSPI は `bus` タグ + `io2` / `io3`。**~~ —— **そのとおりだった。**
   `DisplayBus` と `io2` / `io3` を足し、StopWatch を通した（D40）
3. ~~**DSI は `Display` を広げない。**~~ —— **そのとおりにした。**
   `displayDsi()` と `TINYM5_HAS_DISPLAY_DSI`（D41）。CoreP4X で通した
4. **LED マトリクスは表示として持たない。** ピンを出すだけにする

**残るのは LED マトリクスだけ**で、これは表示として持たない方針のまま
（CoreMatrix はピンを出すだけにする）。**表示バスの宿題はここで終わり。**

### 2-9. いま入れられない機種と、その理由

**「ピンを書くだけ」に見えて入らないものがある。** 保留の理由を残しておく。
どれも「調べれば分かる」ではなく「調べないと嘘になる」ほうの話。

#### AtomS3 —— ロット差が**寸法まで**違う

REQUIREMENTS §4.4 が例に挙げていた「同じ機種名で載っているガラスが違う」の実物。
M5GFX.cpp 2463-2510 で 2 つに分かれる。

| | ST7735S | GC9107 |
| --- | --- | --- |
| offset | x=2, y=1 | x=0, **y=32** |
| offset_rotation | 2 | 0 |
| invert | true | false |

**ピンは同じだが寸法が違う。** `TinyM5::Display` はビルド時の値なので、
どちらかを書けばもう一方で絵がずれる。REQUIREMENTS §4.3 の
「別ボードに分ける（見分けがつく場合のみ）／持たない」でいえば、
**利用者にも見分けがつかない**（開けても分からない）ので**持たない**。

AirQ も 2 つのコントローラが流通しているが、**ピンも寸法も同じ**なので入れた。
違いはドライバが見つける話で、ヘッダが持つ話ではない。

#### ~~Tab5 / Tab5X / NessoN1~~ —— NessoN1 は通した。残り 2 つは表示側

**「PI4IO が 2 個だからスキーマ変更が要る」と書いていたが、そこは詰まりではない。**
`IoExpanderPi4io` はもともとアドレスをコンストラクタ引数に取る（Tab5 の
0x43 / 0x44 を想定した設計）ので、生成側を 2 個対応にするのは小さい変更で、
実際に書いてみたら**生成物は 1 バイトも変わらなかった**（既存 36 機種はどれも 1 個）。

詰まっているのは**電源チップ**のほう。3 機種とも

| チップ | 役割 | いまの状況 |
| --- | --- | --- |
| **AW32001** | 充電制御 | ドライバ無し。`Pmic` 列挙にも無い |
| **BQ27220** | 燃料計 | ドライバ無し |
| INA226 | 電流計（Tab5） | デバイス扱いで対象外 |

→ **`PowerAw32001` を書いて（D42）、エキスパンダ 2 個対応も入れ直し（D43）、
NessoN1 を通した。** 期待どおり、詰まっていたのは電源チップのほうだった。

**Tab5 / Tab5X はもう電源とエキスパンダでは詰まらない。** 残るのは表示で、
MIPI-DSI のパネル諸元（CoreP4X と同じ形で読める）と、**タッチ ID による
パネル分岐**が上流にあるので、そこを読み解く必要がある。

#### PaperS3 / PaperColor —— 上流の諸元に読めない点がある

PaperColor の分岐（M5GFX.cpp 2255-2290）で、

```cpp
bus_cfg.pin_dc  = GPIO_NUM_43;   // D/C
...
_pin_reset(GPIO_NUM_12, use_reset);  // コメントは EPD RST
cfg.pin_rst = GPIO_NUM_43;           // パネル設定では 43 = D/C と同じピン
cfg.pin_cs  = GPIO_NUM_44;
```

**D/C とリセットが同じピン番号**で、しかも別に GPIO12 をリセットとして叩いている。
どちらかが誤りか、ED2208 が D/C をリセットとしても使う配線か、判断がつかない。

**間違ったピン表は調べるより悪い**（BOARD_CATALOG §3）ので、
**回路図か実機で確かめるまで入れない。** PaperS3 も同じ分岐の近くにあり、
同様に読み直しが要る。

**UnitC6L も同じ形**（M5GFX.cpp 3358-3392）。`_pin_reset(GPIO_NUM_6)` の
コメントは「LCD RST」だが、パネル設定は `pin_cs = 6` / `pin_rst = 15`。
3 機種で同じパターンなので、**上流のコメントか設定のどちらかに癖がある**
可能性が高い。1 機種ぶん実機で確かめれば 3 機種とも解ける見込み。

### 2-6. ~~host-arduino-core への要望~~ —— 1.6.0 で解決

`Wire.setLifecycleHook` と `HostArduino::setAnalogWriteHook`、そして
`setAnalogMilliVolts` による読み出しの差し込みが入った。

結果として **`#if defined(ARDUINO_ARCH_ESP32)` のガードを 2 箇所で外せた。**
`BacklightPwm` と `PowerAdc` はホストで中身を実行しない形にしてあったが、
今は**実機と同じコードがそのまま走る。** 迂回した経路が残らない。

## 3. リポジトリ整備

兄弟ライブラリと同じ構造に揃える。雛形は
[`../../arduino-library-release-toolkit`](../../arduino-library-release-toolkit)。

| ファイル | 状況 | 備考 |
| --- | --- | --- |
| `LICENSE` | **あり** | |
| `docs/` | **あり** | |
| `library.properties` | **あり** | `architectures=esp32` / `includes=TinyM5Board.h` / `depends` なし（DECISIONS D21） |
| `CHANGELOG.md` | **あり** | 先頭に `## Unreleased` |
| `.gitignore` | **あり** | TinyGFX からコピー |
| `tools/bump_version.py` | **あり** | toolkit からコピー。**個別編集しない** |
| `.github/workflows/release.yml` | **あり** | toolkit からコピー。**個別編集しない** |
| `keywords.txt` | **あり** | `gen_boards.py` が生成。**ヘッダを読み直す**ので手で並べる箇所が無い |
| `.github/workflows/tests.yml` | **あり** | `catalogue` → 群ごとの `begin` matrix、それと `unit` |
| `src/` 一式 | **あり** | ボードヘッダは生成物 |
| `examples/` | **あり** | `Hello` / `Buttons` / `Battery` / `Backlight`。**機能軸**（D20）。Tier 2 が建てる |
| `tests/` 一式 | **あり** | `tier0/` `begin/`（生成）と `unit/`（手書き） |
| `README.md` / `README.ja.md` | **無い** | 実機で動いてから書く |

## 4. リリース方針

**暫定。** TinyGFX と同じく途中リリースをせず、実機で動いた時点で
`1.0.0` として初回リリースする案が有力。ただし対象が 64 機種あるので、
「どこまで動けば 1.0.0 か」は 2-5 と一緒に決める。

**要確認（公開前）**: ライブラリ名 `TinyM5Board` が Arduino Library Registry と
PlatformIO Registry で空いているか（DECISIONS Q6）。GitHub のリポジトリは取得済み。
