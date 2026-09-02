# 開発計画

内部の記録。日本語のみ。**現在地と残作業。**

## 1. 現在地

**設計の骨格が決まったところ。実装は 1 行も無い。**

| 項目 | 状況 |
| --- | --- |
| 調査メモ（M5GFX / M5Unified の実態調査） | **あり。** [research/](research/) に 4 本。確定事項ではない |
| 責務・設計・決定の文書化 | **一巡した**（[REQUIREMENTS.ja.md](REQUIREMENTS.ja.md) / [CORE_DESIGN.ja.md](CORE_DESIGN.ja.md) / [DECISIONS.ja.md](DECISIONS.ja.md)） |
| ライブラリ解決の条件 | **実測で確定**（arduino-cli 1.5.0、2026-09-02。CORE_DESIGN §3.1） |
| リポジトリ整備 | **途中**（§3） |
| ボードカタログのスキーマ | **決まった**（[BOARD_CATALOG.ja.md](BOARD_CATALOG.ja.md) / DECISIONS D26〜D28） |
| テスト戦略 | **決まった**（[TEST_PLAN.ja.md](TEST_PLAN.ja.md) / DECISIONS D24・D25） |
| `src/` 一式 | **無い** |
| examples | **無い** |
| 利用者向けドキュメント | **無い** |

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

### 2-4. 1 機種を通しで作る

土台の上に最初の 1 機種を載せて、`Board.begin()` から `Board.update()` までを通す。
どの機種にするかは手元の実機で決める。

### 2-5. v1 のスコープを決める（DECISIONS Q3）

調査メモは「Stick 系 4 機種 + AXP192 / M5PM1」を提案しているが、
**価値の源泉はボード表のほう**（メモ 03 自身の結論）なので、
2 段構えにする案がある。

| 段 | 内容 | 対象 |
| --- | --- | --- |
| 全機種 | ピン表・ボード ID・群・機能フラグ | 64 機種 |
| 通しで実装 | `begin()` / 電源 / バックライト / ボタン | 手元で確認できる機種から |

**未決。** 2-4 が終わってから決めたほうが判断材料が揃う。

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
