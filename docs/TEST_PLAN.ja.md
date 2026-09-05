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

## 2. Tier 0 —— 土台（`tests/tier0/`）

**ヘッダが単体で成立するか。** 全機種分。**何も実行しない。**
`arduino-cli compile` が 0 で返ることが結果のすべて。

Tier 1 のゴールデンはホストコアで走る。**ホストコアは製品を出すコンパイラではない。**
ここが**実物のツールチェーンが通る唯一の層**で、しかも
**そのボードの SoC 向けに**通す。

| 見るもの | どう見るか |
| --- | --- |
| ボードヘッダが単体でコンパイルできる | 生成された `tier0/boards/<Id>/` を各 SoC の Dev Module でビルド |
| `#define` 経由の入口が同じ結果になる | 各スケッチが `#define TINYM5_<ID>` + `<TinyM5Board.h>` で入る |
| 文字列指定の入口（`TINYM5_BOARD_HEADER`） | `tier0/entry/BoardHeaderMacro/`。**ここだけ既定のグローバルも通る** |
| 2 つのボードヘッダで `#error` | `tier0/entry/DoubleInclude/`。**失敗することで通る**唯一のテスト |
| `TINYM5_NO_GLOBAL_BOARD` | 各スケッチが自分で `TINYM5_BOARD Board;` を定義する。効いていなければ二重定義で落ちる |
| 機能マクロが全機種で定義されている | `#if !defined(...)` の連鎖 + `#error` |
| **マクロと定数が食い違わない** | `static_assert(TINYM5_HAS_DISPLAY == kHasDisplay)` ほか |
| **`getPin()` と定数が食い違わない**（D28） | 6 つの照会を `static_assert` で突き合わせ |

**期待値はスケッチの中に置く。** `static_assert` と `#error` なので、
外れたときはコンパイルエラーになり、pytest 側が判定を持たなくて済む。

FQBN は**そのボードの機種名ではなく SoC の Dev Module**（`esp32:esp32:esp32s3` など）。
ボード variant が持つのはピン別名とフラッシュ配置で、このライブラリは
**どちらも読まない**（D11）。IDE のボード選択を信用しないと決めた以上、
テストで信用するのは筋が通らない。**落とすコアも 1 つで済む。**

`-D` でボードを注入する形は取らなかった。マクロはスケッチに書いてある。
生成するので手間は同じで、**ビルドプロパティ経由の引用符に依存しない。**

13 機種 + 入口 2 本で**約 90 秒**。

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

`tests/common_libs/tinym5_trace/src/tinym5_model_i2c.h` に**レジスタファイル**を置く。
アドレスと 256 バイトのレジスタ、書き込みが立てて読み出しが辿るポインタ —— それだけ。

**PMIC を模倣するのが目的ではない。** チップに名乗らせないと
ドライバが検出で止まり、その先のトレースが 1 行も出ないので、
**分岐を走らせるために**置いている。

```cpp
TinyM5Trace::useChip(0, 0x34, 0x03, 0x03);   // AXP192 が居ることにする
```

読み出しがある経路はこれで両方通せる。

```
reg 0x03 = 0x03 → AXP192 側の列になること
reg 0x03 = 0x4A → AXP2101 側の列になること
```

**個体差を実行時に確かめる設計（[DECISIONS.ja.md](DECISIONS.ja.md) D5）は、
ここでしか検証できない。** 実機は片方しか持っていないため。

### 3.2.1 読み出しは差し込んで検算する

電池の値は**ゴールデンの中で計算結果まで確かめる**。

| 差し込み | 期待 |
| --- | --- |
| ADC ピンに 2000 mV | 分圧比 2000 の機種 → `mV=4000 level=87` |
| 同上 | **分圧比 1513 の TimerCam → `mV=3026 level=0`** |
| AXP192 の `0x78/0x79` に 0xE34 | 12 bit × 1.1 mV → `mV=3999` |

分圧比も 12 bit の組み立ても、**間違っていても「それらしい電圧」が出る**だけで
落ちない。差し込んだ値からの検算でしか捕まらない。

### 3.2.2 ゴールデンにはボード定義も入れる

バス上のやりとりだけでなく、`--- board ---` と `--- display ---` として
**カタログの中身そのもの**を記録する。

```
--- board ---
name=M5StickC id=6
pins i2c=21/22 ext=32/33 led=-1/0 hold=-1
has display=1 backlight=1 battery=1 extI2c=1 shared=0
--- display ---
spi mosi=15 miso=14 sclk=13 dc=23 cs=5 rst=-1 3wire=1
panel 80x160 offset=26,1 rotation=2 invert=1
```

**パネルのオフセットや I2C のピンが違っていても、クラッシュはしない。**
黙って絵がずれるだけなので、順序の検査だけでは落とせない。
カタログが製品である以上、ゴールデンはカタログを覆う必要がある。

実例: StickC と StickC Plus は**電源手順もピンも完全に同一**で、
違うのは識別子とパネルだけ。この節が無いと 2 機種の区別がつかない。

### 3.3 観測できる範囲 —— host-arduino-core 1.6.0 で全部埋まった

| 半分 | 見えるもの |
| --- | --- |
| GPIO | `pinMode` / `digitalWrite`。`digitalRead` は書いた値を返す |
| I2C | トランザクション（アドレス + ペイロード + stop）と、**`begin()` / `setPins` / `setClock` のライフサイクル** |
| SPI | 転送と、`begin()` / 設定系のライフサイクル |
| **analog / PWM** | `analogWrite` / `ledc*` の attach / write / config / detach。**読み出しも `setAnalogMilliVolts` で差し込める** |

1.5.0 では `Wire.begin()` と PWM が順序に載らなかったが、1.6.0 で両方フックが付いた。

**これで `#if defined(ARDUINO_ARCH_ESP32)` のガードを外せた。**
それまで `BacklightPwm` と `PowerAdc` はホストで中身を実行しないようにしていたが、
今は**実機と同じコードがそのまま走る。** 検査していない経路が残らない。

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

### 3.6 ゴールデンに映らないもの —— `tests/unit/`

**ゴールデンは `begin()` しか見ていない。** ボタンが仕事をするのは `update()` で、
そこは 1 行もトレースに出ない。しかもボタンは**ボードに依らない 1 つのクラス**なので、
機種ごとのゴールデンに入れる形にもならない。

そこで `tests/unit/` を別に置く。今あるのは `Button/` 1 本。

| | |
| --- | --- |
| 何を見るか | デバウンス・押下と離しのエッジ・長押し・クリック回数（D36） |
| 時刻 | **`update(msec)` の引数**。600 ms の長押しも実時間 0 秒で、速さに依存しない |
| 期待値 | **スケッチの中に、刺激の隣に書く。** 39 検査 |
| 落ち方 | `output/checks.txt` の `FAIL` 行がそのまま assert のメッセージになる |

**ここはゴールデンにしない。** 凍結が効くのは上流から起こした値
（§1）で、状態機械の期待値は上流を見なくても導ける。
「1110 ms でクリックが立つ」は刺激の隣に書いてあるほうが読める。

ビルドも実行も 1 本なので**約 7 秒**。CI では matrix の外に別ジョブで置く。

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
| 単体（`tests/unit/`） | `lang-ship:host`（profile 固定） | ✅ **matrix の外**。7 秒で終わるので独立ジョブ |
| 1 | `lang-ship:host`（profile 固定） | ✅ |
| 2 | `esp32:esp32`（profile 固定） | ✅（重いので代表ボードのみ） |
| 3 | 実機 | ❌ 手動 |

### 7.1 群ごとに並列化する

**`tests/begin/` は群でディレクトリを分けてある**ので、群がそのまま
GitHub Actions の matrix の軸になる。

```yaml
matrix:
  family: ${{ fromJson(needs.catalogue.outputs.families) }}
run: uv run pytest "begin/${{ matrix.family }}" --profile host
```

軸は `tools/gen_boards.py --families` がカタログから出すので、
**群を足しても workflow は触らなくてよい。**

ローカルでも同じ単位で絞れる。

```sh
uv run pytest begin/Stick --profile host    # 3 機種、約 2 分
uv run pytest begin --profile host          # 全部、約 5〜8 分
```

**必要な理由**: `begin` のテストは 1 本ごとにスケッチをビルドして実行するので、
所要時間が機種数に線形に伸びる。10 スケッチで 5〜8 分、**60 機種なら 30 分を超える。**

結果が群単位で出るのは副産物だが効く（[DECISIONS.ja.md](DECISIONS.ja.md) D19）。
64 機種の緑ランプより「Stick 系 全機種通過」のほうが読める。

`--check`（生成物が最新か）は 1 回だけ走らせ、**全 matrix ジョブの前段**に置く。
生成物が古いと、他のジョブは全部「違うものを検査した」ことになるため。
