# 開発計画

内部の記録。日本語のみ。**現在地と残作業。**

## 1. 現在地

**AtomLite が 1 機種、ホストのゴールデンテストまで通っている。**

| 項目 | 状況 |
| --- | --- |
| 責務・設計・決定の文書化 | **一巡した**（[README.ja.md](README.ja.md) の一覧） |
| 調査記録 | **あり。** [research/](research/) に事実のみ |
| ライブラリ解決の条件 | **実測で確定**（arduino-cli 1.5.0） |
| ボードカタログのスキーマ | **決まった**（[BOARD_CATALOG.ja.md](BOARD_CATALOG.ja.md)） |
| テスト戦略 | **決まった**（[TEST_PLAN.ja.md](TEST_PLAN.ja.md)） |
| `tools/gen_boards.py` | **あり。** ボードヘッダ / `TinyM5Board.h` / `BoardId.h` を生成、`--check` つき |
| `src/TinyM5Board/Common.h` | **あり。** 型・enum・`resetPulse` |
| `src/TinyM5Board/Button.h` | **あり。** デバウンス + エッジ。click カウントは未実装 |
| ボード定義 | **AtomLite のみ**（[BOARD_CATALOG.ja.md](BOARD_CATALOG.ja.md) の全列を使う最小例） |
| `tests/begin/` | **通っている。** ホストで `begin()` の I2C / GPIO 列を記録しゴールデン比較 |
| `tests/common_libs/tinym5_trace/` | **あり。** バス観測ポートの記録ヘルパ |
| `examples/Hello` | **あり。** 実機コア（`esp32:esp32:m5stack_atom`）でビルド確認済み |
| `.github/workflows/tests.yml` | **あり。** `core install` を使わない構成 |
| 利用者向け README | **無い。** 機種が揃ってから |
| 電源チップのドライバ | **無い。** AXP192 / AXP2101 / M5PM1 とも未着手 |

### 1.1 実装して分かったこと

**`if constexpr` では機能の有無を分岐できない**（D31）。テンプレートの外では
捨てられた枝も名前解決されるので、`Board.Power` が無いボードでは
実行されない側に書いてもコンパイルが通らない。`TINYM5_HAS_*` マクロを追加した。

**ビルドフラグからは文字列しか渡せない。** pytest-embedded の
`build_config.toml` は `-DNAME="value"` の形でしか注入できないため、
`TINYM5_BOARD_HEADER` という computed include の入口を足した。
結果として**入口が 3 通り**になった（直接 include / マクロ / ヘッダ名の文字列）。

**AtomLite の実測**: ESP32 でフラッシュ 294,272 B / RAM 23,548 B。
大半は Arduino のベースラインと `Wire`。

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

### 2-4. AtomLite を通しで作る（D30）

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

1. **電源ハードを持たない画面なしボード** — ピン表だけで済む
2. **POWER_HOLD 1 本のボード** — CoreInk / AirQ / Paper / TimerCam
3. **AXP192 / M5PM1 を共有する機種** — チップドライバは共通、ピン割当だけ

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
