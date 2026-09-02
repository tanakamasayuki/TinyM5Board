# テスト計画

内部の記録。日本語のみ。**何をどう検証するか。**

## 1. 方針 —— 凍結モデル

> **上流はボードを追加するときの資料。取り込んだら凍結し、以後は追わない。**

`tests/` は**完全に自己完結**させる。M5GFX / M5Unified / Arduino Core /
[variants_collector](https://github.com/tanakamasayuki/variants_collector) を
CI から参照しない。

理由は実地の経験による。variants_collector は定期取得で上流と突き合わせているが、
**上流の列が増えるたびに壊れる。** 検証したいのは自分のコードであって上流の形ではないので、
壊れる原因を外部に置くのは割に合わない。

代わりにこうする。

| 場面 | 上流の扱い |
| --- | --- |
| **ボードを新規に追加するとき** | M5GFX / M5Unified / variants_collector を読んで値を起こす |
| **その値が通ったとき** | ゴールデンとして**凍結** |
| **以後** | **見ない。** 上流が変わっても追わない |
| **動かない報告が来たとき** | そのボードだけ直す |

過去のボードは基本的に更新しない。**「今の M5GFX と一致しているか」ではなく
「一度通った状態から変わっていないか」**を守る。

### やらないこと

| | 理由 |
| --- | --- |
| M5GFX / M5Unified のソースを CI から参照する | 上流の変更で壊れる。検証対象は自分のコード |
| 期待値に M5GFX のソース行ハッシュを埋める | 同じ。**M5GFX への依存を作らない** |
| ホストで M5GFX を走らせて初期化列を取る | **構造的に不可能**（§5） |
| チップシミュレータを書いて M5GFX の autodetect を回す | 可能だが、それ自体が 1 プロジェクト。費用対効果が合わない |

## 2. Tier 0 —— 土台

**ヘッダが単体で成立するか。** 全 64 機種分。

- ボードヘッダを 1 本だけ include した空スケッチがコンパイルできる
- `#define` 経由の入口（`-DTINYM5_xxx` + `<TinyM5Board.h>`）でも同じ結果になる
- 2 つのボードヘッダを同時に include したら `#error` で止まる
- `TINYM5_NO_GLOBAL_BOARD` を定義するとグローバル実体が作られない
- `kHasDisplay` などの機能フラグが全機種で定義されている

安いのに、ヘッダの取り違え・マクロ衝突・フラグの付け忘れを確実に拾う。
**サンプルの include を書き換えず `-D` を注入すれば、1 スケッチで全機種を回せる。**

## 3. Tier 1 —— 初期化列のゴールデン（ホスト実行）

**このライブラリの正しさの中心。**

host-arduino-core 1.5.0 の**バス観測ポート**を使う。3 つ揃っていて、
`Board.begin()` が触るものは全部見える。

| 半分 | 場所 | 見えるもの |
| --- | --- | --- |
| GPIO | `cores/host/HostBus.h` | `setPinWriteHook` / `setPinModeHook` / `setPinReadHook`。`digitalWrite` が全部通知され、`digitalRead` は書いた値を返す |
| I2C | `libraries/Wire/src/Wire.h` | `setWriteHook` / `setReadHook`。**トランザクション単位**（アドレス + ペイロード + stop）。`sda()` / `scl()` / `getClock()` も読める |
| SPI | `libraries/SPI` | `setTransferHook` |

### 3.1 何を固定するか

`Board.begin()` を呼び、観測ポートに流れたものを 1 本のログにして
ゴールデンファイルと突き合わせる。

```text
pinMode(4, OUTPUT)              POWER_HOLD
digitalWrite(4, 1)              ← 最優先。Plus2 はこれが遅いと電源が落ちる
Wire.begin(sda=21, scl=22, 400000)
i2c write 0x34 [0x12, 0x4D]     AXP192 レール投入
pinMode(37, INPUT_PULLUP)       BtnA
pinMode(18, OUTPUT)             LCD RST
digitalWrite(18, 0)
digitalWrite(18, 1)
```

**順序も含めて固定する。** POWER_HOLD が最初でないと実機で電源が落ちるので、
順序は結果と同じくらい重要。

### 3.2 応答を返す device model

読み出しがある経路（Core2 の PMIC 判別、電池電圧）は、`setReadHook` に
チップの応答を差し込んで分岐を両方通す。

```
AXP192  を返す設定 → reg 0x03 = 0x03 → AXP192 側の列になること
AXP2101 を返す設定 → reg 0x03 = 0x4A → AXP2101 側の列になること
```

**個体差を実行時に確かめる設計（[DECISIONS.ja.md](DECISIONS.ja.md) D5）は、
ここでしか検証できない。** 実機は片方しか持っていないため。

### 3.3 ホスト側で見えないもの

観測ポートで見えない経路が 2 つある。**どちらも host-arduino-core 側に
フックが増えれば埋まる**ので、ライブラリ側の設計課題ではない。

| 見えないもの | 影響 | 状況 |
| --- | --- | --- |
| `Wire.begin()` | 順序を持つ部分に現れない。開いたピンとクロックは `--- state ---` に記録するので、**値は取れている**。I2C の**トランザクション**はすべて正しい順序で並ぶ | フックが無い |
| **PWM / analog** | `analogWrite` 系にフックが無く、**バックライトの初期化がゴールデンに出ない**。輝度カーブ自体は `Backlight.duty()` が整数関数なので単体で検査できる | `ledcWrite` / `analogWriteFrequency` は host core の TODO に「no-op stub で足りる」とある |

### 3.4 pytest-embedded の落とし穴 (実測)

**ボードごとにディレクトリを分ける。** `dut` フィクスチャは**モジュールスコープ**で、
ビルドパスはスケッチディレクトリに従う。1 つのスケッチを共有すると
2 つ目のモジュールが 1 つ目のプロセスに繋がる。

**`expect` の文字列にボード名を入れる。** バッファが**セッション全体で共有**されているため、
素の `TEST done` は前のボードの実行にマッチしてしまい、
まだ書かれていないトレースを読みに行く。

どちらも `tools/gen_boards.py` が生成側で守っているので、
ボードを足すときに踏み直すことはない。

### 3.5 ゴールデンの作り方

初回は実行結果をそのまま書き出し、**人が M5GFX の該当箇所と読み合わせて承認する。**
以後は差分が出たら失敗。更新は明示的な操作（`--update-golden`）でのみ。

ゴールデンには**いつ・何を根拠に承認したか**をコメントで書く。

```text
# M5StickCPlus2 / blessed 2026-09-05
#   source : M5GFX.cpp の StickCPlus2 節を読んで起こした
#   hardware: 実機で確認済み (2026-09-06)
```

これは**テスト側のメタデータ**であって、ライブラリが持つフラグではない
（[DECISIONS.ja.md](DECISIONS.ja.md) D9 で否定したのは後者）。

## 4. Tier 2 —— サンプルのビルド網羅

examples が実機コアでビルドできること。ESP32 / S3 / C3 / C6 / P4 と、
各群の代表ボード。`kHas*` を見て `#error` で止まるサンプルが、
**止まるべきボードで止まり、止まらないボードで通る**ことも見る。

## 5. Tier 3 —— 実機ベースライン

**機種ごとに 1 回。日常的には回さない。**

手順は `MANUAL_TEST.ja.md`（未作成）。通ったら Tier 1 のゴールデンに
`hardware:` 行を足して凍結する。

見るのは 4 点だけ。

1. 電源が落ちない（POWER_HOLD / PMIC のレール）
2. 画面に電源が来ている（バックライトが点く。絵は GFX の仕事）
3. 電池電圧が妥当な値で読める
4. ボタンが押せる

## 6. 補足 —— ホストで M5GFX を走らせられない理由

調べた結果を記録しておく（同じ検討を繰り返さないため）。

**`M5GFX.cpp:80` の `#if defined(ESP_PLATFORM)` が、ボード別処理を丸ごと囲んでいる**
（80〜3793 行）。ホストビルドでは `#else` 側に切り替わり、`autodetect()` は
別の関数になる。

```cpp
// M5GFX.cpp:3808 —— ホスト側の autodetect
board_t M5GFX::autodetect(bool use_reset, board_t board) {
  auto p = new Panel_sdl();
  // ... switch (board) { case board_M5Stack: title = "M5Stack"; ...
```

**ウィンドウのサイズとタイトルを決めるだけで、I2C も GPIO も 1 バイトも出ない。**

M5Unified も同じ。`I2C_Class` は `m5gfx::i2c::*` を呼ぶが、SDL 実装
（`lgfx/v1/platforms/sdl/common.cpp:96-111`）は**全関数が
`cpp::fail(error_t::unknown_err)` を返すスタブ**。`Power_Class.cpp:8` も
`#if !defined(M5UNIFIED_PC_BUILD)` で無効化されている。

`M5GFX_BOARD` マクロでボードを指定することはできる（`M5GFX.cpp:1065` と `3800`）が、
**ESP ビルドでは「最初の候補」にするだけで判別は飛ばさず**、
SDL ビルドでは上記のとおり別関数なので寸法が決まるだけ。

## 7. CI

`tests/` に pytest + uv。`.github/workflows/tests.yml`。

**コアは `arduino-cli core install` で入れない。`sketch.yaml` の profile で入れる**
（[DECISIONS.ja.md](DECISIONS.ja.md) D29）。バージョンを固定できるのが profile だけなので、
CI もローカルも同じコアが入り、**コアが上がって黙って結果が変わることがない。**
テストが生成するスケッチにも profile を付ける。

| Tier | 必要なコア | CI で回すか |
| --- | --- | --- |
| 0 | `esp32:esp32`（profile 固定） | ✅ |
| 1 | `lang-ship:host`（profile 固定） | ✅ |
| 2 | `esp32:esp32`（profile 固定） | ✅（重いので代表ボードのみ） |
| 3 | 実機 | ❌ 手動 |

結果は**群単位**で出す（[DECISIONS.ja.md](DECISIONS.ja.md) D19）。
64 機種の緑ランプより「Stick 系 全機種通過」のほうが読める。
