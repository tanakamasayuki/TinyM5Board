# 開発計画

内部の記録。日本語のみ。**現在地と残作業。**

## 1. 現在地

**10 機種。ADC / AXP192 / AXP2101 / M5PM1 の 4 系統がホストのゴールデンと実機ビルドまで通っている。**

| 項目 | 状況 |
| --- | --- |
| 責務・設計・決定の文書化 | **一巡した**（[README.ja.md](README.ja.md) の一覧） |
| `tools/gen_boards.py` | ボードヘッダ / 入口 / `BoardId.h` / テスト一式を生成、`--check` と `--families` |
| ボード定義 | **11 機種** —— AtomLite / TimerCam / Capsule / StickC / StickCPlus / StickCPlus2 / StickS3 / Station / Tough / Core2 / **ChainCaptain** |
| 電源 | `PowerAdc` / `PowerAxp192` / `PowerAxp2101` / `PowerM5pm1` / `PowerCore2`（二択の判別） |
| IO エキスパンダ | **`IoExpanderM5ioe1`**。AW9523B / PI4IOE5V6408 は未着手 |
| バックライト | PWM / AXP192 の Ldo2・Ldo3・Dc3 / Core2 / **M5IOE1 の PWM**。**すべて M5GFX と同じカーブ** |
| ボタン | GPIO と PMIC の電源キーを同じ型で。click カウントは未実装 |
| 表示 | `TinyM5::Display`。3 線式と PMIC 越しリセットの表現あり |
| `tests/begin/` | **12 スケッチ通過。群ごとのディレクトリ**で、CI の matrix 軸もこれ。**1 バスに複数チップ**のモデルに対応 |
| `.github/workflows/tests.yml` | **群ごとに並列**。軸はカタログから生成 |
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

### 1.3 テストの所要時間

`tests/begin` は 1 本ごとにスケッチをビルドして実行するので、**機種数に線形**。
11 スケッチで約 8 分。**群ごとに並列化してある**ので CI では最長の群の時間で済み、
ローカルは `pytest begin/Stick` のように絞れる（約 2 分）。

## 2. 次にやること

順序に意味がある。**土台を先に作らないと、機種を増やした分だけ壊れる。**

### 2-1. テスト基盤を作る

方針は [TEST_PLAN.ja.md](TEST_PLAN.ja.md) で決まった。**必要なものは全部揃っている。**

host-arduino-core 1.5.0 のバス観測ポート（GPIO / I2C / SPI の 3 つ）で、
`Board.begin()` が触るものは全部見える。`setReadHook` で応答を差し込めるので、
Core2 の PMIC 判別のような分岐も両方通せる。

作るもの:

- `tests/` の骨格（pytest + uv、`.github/workflows/tests.yml`）
- Tier 0（全機種のヘッダ単体コンパイル）
- 観測ポートのログを 1 本にまとめるヘルパと、ゴールデンの比較・更新

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
8. **CoreS3 系** —— AXP2101 は済んでいるが AW9523B が要る
9. **PI4IOE5V6408** —— StampPLC / Tab5 / Tab5X / NessoN1 / UnitC6L
10. 残りの画面なしボード —— ピン表だけで済むものが多い

### 2-7. 積んである宿題

| | |
| --- | --- |
| **SD の SPI モード落とし** | Core2 / Tough / M5Stack / CoreS3 / StampPLC / PaperColor / Paper は SD が LCD と同じ SPI バスに載る。SD モードのままだとバス上で応答してパネル ID 読みを壊す。**責務としては持つと決めている**（REQUIREMENTS §4.2）が未実装 |
| Button の click カウント | `wasClicked` / `wasDoubleClicked` / `getClickCount` が未実装 |

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
| `keywords.txt` | **無い** | `gen_boards.py` が生成する |
| `.github/workflows/tests.yml` | **無い** | プロジェクト固有。2-1 の後 |
| `src/` 一式 | **無い** | |
| `examples/` | **無い** | |
| `tests/` 一式 | **無い** | |
| `README.md` / `README.ja.md` | **無い** | 実機で動いてから書く |

## 4. リリース方針

**暫定。** TinyGFX と同じく途中リリースをせず、実機で動いた時点で
`1.0.0` として初回リリースする案が有力。ただし対象が 64 機種あるので、
「どこまで動けば 1.0.0 か」は 2-5 と一緒に決める。

**要確認（公開前）**: ライブラリ名 `TinyM5Board` が Arduino Library Registry と
PlatformIO Registry で空いているか（DECISIONS Q6）。GitHub のリポジトリは取得済み。
