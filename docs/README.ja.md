# ドキュメント案内

> **この下の文書はすべて日本語のみ。** 開発中の内部記録であって、
> 利用者が読むものではないため（[DECISIONS.ja.md](DECISIONS.ja.md) D23）。
> 利用者向けの文書は英語と日本語の両方を用意する。

TinyM5Board の設計文書。**まだ実装は無い。** 確定していない項目には「**暫定**」と書いてある。

**言語方針は 3 段。正本は日本語版。** 兄弟プロジェクト（TinyGFX / PaperCanvas / BarcodeKit）と同じ。

| 区分 | 言語 | 対象 |
| --- | --- | --- |
| 使う人が読むもの | 日英 | `../README.ja.md`、`API.ja.md`、`../examples/README.ja.md` |
| 内部の記録・作業メモ | 日本語のみ | [REQUIREMENTS.ja.md](REQUIREMENTS.ja.md)、[CORE_DESIGN.ja.md](CORE_DESIGN.ja.md)、[DECISIONS.ja.md](DECISIONS.ja.md)、[BOARD_CATALOG.ja.md](BOARD_CATALOG.ja.md)、[TEST_PLAN.ja.md](TEST_PLAN.ja.md)、[research/](research/) |
| **コード中のコメント** | **英語のみ** | `../src/`、`../examples/`、`../tests/`、`../tools/` |

## 読む順

| やりたいこと | 読む文書 |
| --- | --- |
| **何を作るライブラリで、どこまでが責務なのか知る** | **[REQUIREMENTS.ja.md](REQUIREMENTS.ja.md)** |
| **API の形と内部構造を知る** | **[CORE_DESIGN.ja.md](CORE_DESIGN.ja.md)** |
| **なぜそう設計したのかを知る／論点を潰す** | **[DECISIONS.ja.md](DECISIONS.ja.md)** |
| **カタログが何を持ち、何を持たないか** | **[BOARD_CATALOG.ja.md](BOARD_CATALOG.ja.md)** |
| **何をどう検証するか** | **[TEST_PLAN.ja.md](TEST_PLAN.ja.md)** |
| 現在地と残作業を知る | [DEVELOPMENT_PLAN.ja.md](DEVELOPMENT_PLAN.ja.md) |
| **M5GFX / M5Unified が実際に何をしているか**（事実のみ） | [research/](research/) |

## 三行まとめ

1. **M5 のボードを、GFX ライブラリを引き込まずに立ち上げる。** 電源を入れ、
   リセットを解き、ピン表を公開するところまで。画面には描かない
2. **ボードはビルド時に決め打ち。** 重さを決めるのは「やる量」ではなく
   「実行時に選ぶかどうか」なので、決め打ちなら全部やってよい
3. **停止則は「ビルド時に確定できることだけを持つ」。**
   IMU のチップ種別は世代で変わるので持たない。ピンとバスまで渡す

## 出発点

M5GFX リポジトリの `docs/board-init-research/` にあった調査メモ 4 本。
**あれは確定事項ではない**ので、この docs はゼロベースで決め直したもの。

移設にあたって**提案部分を削り、事実だけを [research/](research/) に残した。**
古い方針が残っていると、どちらが正なのか分からなくなるため。
メモから変えた点は [DECISIONS.ja.md](DECISIONS.ja.md) §2 にある。
