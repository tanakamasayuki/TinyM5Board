# 調査記録

M5GFX / M5Unified / SoC / Arduino Core を実際に読んで調べた**事実**。

> **方針・設計案は含まない。** 調査時点の提案は
> [../DECISIONS.ja.md](../DECISIONS.ja.md) で決め直したので、
> 混乱を避けるためこのディレクトリからは削除した。
> メモから変えた点は [../DECISIONS.ja.md](../DECISIONS.ja.md) §2 にある。

| ファイル | 内容 |
|---|---|
| [01-m5gfx-board-catalog.md](01-m5gfx-board-catalog.md) | **M5GFX がボード単位でやっていること全部。** 表示ボード 35 種の必要な前処理、初期化では終わらない処理、自動判別のための横断機構 |
| [02-chip-registers.md](02-chip-registers.md) | **AXP192 / M5PM1 のレジスタマップ**と、Stick 系 4 機種の全初期化手順 |
| [03-m5unified-analysis.md](03-m5unified-analysis.md) | **M5Unified のボード別処理**（ピンテーブル・PMIC 選択・IO エキスパンダ・enable コールバック）、重さの構造的原因、ペリフェラル直叩きの実態 |
| [04-platform-facts.md](04-platform-facts.md) | **SoC と Arduino Core の実測。** FPU の有無、I2C の数、内部/外部 I2C、ボード定義のカバー率と曖昧なマクロ |

## 調査対象

| | バージョン | 規模 |
|---|---|---|
| M5GFX | `d91077b` (v0.2.28) | `src/M5GFX.cpp` 4041 行。ボード別処理はほぼ全部ここ |
| M5Unified | — | src 配下 19,702 行。`board_t::board_` の参照が 409 箇所 |
| M5PM1 (M5Stack 公式) | — | 9,481 行 |
| IDF | 5.4 | `soc_caps.h` |
| Arduino Core | m5stack_esp32 3.3.7 / esp32 3.3.11 | |

すべて MIT ライセンス。

## 押さえておくべき数字

- 表示を持つボード **35 種**のうち、**追加処理なしで動くのは 8 種だけ**。
  22 種は I2C の PMIC / IO エキスパンダを叩かないと画面に電源が来ない
- **画面なしボードは 29 種**。M5GFX は判別しないと明記している（`M5GFX.cpp:3318`）
- M5Unified の電源関連だけで **6,500〜7,000 行**（全体の約 1/3）
- Stick 系 4 機種は **AXP192 と M5PM1 の 2 チップ・計 8 レジスタ**で足りる
- **M5PM1 の電源系レジスタは M5GFX からは分からない。** 表示系しか出てこない
