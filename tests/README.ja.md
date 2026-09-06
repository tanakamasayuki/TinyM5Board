# テスト

> English: [README.md](README.md)

方針は [../docs/TEST_PLAN.ja.md](../docs/TEST_PLAN.ja.md)。

## 走らせ方

```sh
cd tests
uv sync
uv run pytest --profile host          # 全部
uv run pytest unit --profile host     # ボードに依らないクラス。約 16 秒
uv run pytest tier0                   # 全機種のヘッダを実物のコアで。約 2 分半
uv run pytest begin --profile host    # 立ち上げのゴールデン。約 4〜5 分
```

**コアは `arduino-cli core install` で入れない。** 各テストの `sketch.yaml` に
バージョンを書いてあり、`--profile` がそれを `~/.arduino15/internal/` へ
隔離して入れる（[../docs/DECISIONS.ja.md](../docs/DECISIONS.ja.md) D29）。

## 走らせる単位

`begin/` は**群でディレクトリが分かれている**。群がそのまま
GitHub Actions の matrix の軸で、ローカルでも同じ単位で絞れる。

```sh
uv run pytest begin/Stick --profile host    # 4 機種、約 30 秒
uv run pytest begin --profile host          # 32 スケッチ、約 5 分
```

1 本ごとにスケッチをビルドして実行するので、**所要時間は機種数に線形**。
普段は自分が触った群だけを回せばよい。

## `tier0/` — 全機種のヘッダを、実物のツールチェーンで

**何も実行しない。** `arduino-cli compile` が 0 で返ることが結果のすべて。
期待値は `static_assert` と `#error` でスケッチの中に書いてあるので、
外れたときはコンパイルエラーになる。**pytest 側は判定を持たない。**

ゴールデンが走るホストコアは**製品を出すコンパイラではない**。ここが
実物のツールチェーンが通る唯一の層で、しかも**そのボードの SoC 向けに**通す。

見ているもの: ヘッダが単体で成立するか / `#define TINYM5_<ID>` と
`TINYM5_BOARD_HEADER` の入口が同じボードに届くか / 2 つ include したら
止まるか / `TINYM5_NO_GLOBAL_BOARD` が効くか / 機能マクロが全機種で
定義され、**隣の定数と一致している**か / `getPin()` が定数と一致しているか。

FQBN は機種名ではなく **SoC の Dev Module**。ボード variant が持つのは
ピン別名とフラッシュ配置で、このライブラリはどちらも読まない。

```sh
uv run pytest tier0                  # 約 2 分半。--profile は要らない
uv run pytest tier0 -k StickC        # 1 機種だけ
```

初回は `sketch.yaml` が固定している esp32 コアの取得が入る。

## `unit/` — ボードに依らないクラス

ゴールデンが見ているのは `begin()` だけ。しかも**相手が居ないバス**での話。
そこから外れる 2 つをここで見る。

- `Button/` —— ボタンが仕事をするのは `update()` で、バスに何も出さない。
  時刻は `update(msec)` の引数なので、**600 ms の長押しも実時間 0 秒**
- `SdSpiMode/` —— **バスが黙っていると作れない分岐。** 誰も答えなければ
  カードは必ず「モードを落とす」側になるので、**既に SPI モードのカード**は
  SPI の transfer フックで答えを差し込むしかない

期待値は**刺激の隣に書いてある**。スケッチが `output/checks.txt` に書き出し、
`FAIL` 行がそのまま assert のメッセージになる。報告は `tinym5_expect.h`、
起動と判定は `tinym5_check.check_unit()` が持つので、**1 本足すのは
スケッチ 1 つとテスト 3 行**。

生成物ではなく手書き（ボードが出てこないため）。1 本あたり約 8 秒なので、
`src/TinyM5Board/` を触っている間はこれだけ回せばよい。

## `begin/` — 初期化列のゴールデン

`Board.begin()` がバスに対して何をしたかを記録し、凍結した期待値と突き合わせる。

記録は host-arduino-core の**バス観測ポート**に乗っている。GPIO は
`<HostBus.h>`、I2C は `TwoWire` のフックで、**ライブラリ側には計測用のコードが
1 行も入らない。** スケッチと同じようにコンパイルしたものをそのまま見ている。

スケッチは機種ごとに生成し、**README が勧める書き方でヘッダを include する。**
利用者と同じ道を通る。

### ゴールデンは凍結する

**毎回 M5GFX と突き合わせているのではない。** 一度通した状態から変わって
いないかだけを見る（[../docs/TEST_PLAN.ja.md](../docs/TEST_PLAN.ja.md) §1）。

更新は明示的に。**必ず差分を読んでからコミットすること。**

```sh
uv run pytest begin --profile host --update-golden
git diff tests/begin/golden/
```

### 構成

**ボードごとにディレクトリを分けてある**（`begin/AtomLite/` など）。
`dut` はモジュールスコープでビルドパスがスケッチディレクトリに従うので、
共有すると 2 つ目のモジュールが 1 つ目のプロセスに繋がる。
スケッチ・profile・テストはすべて `tools/gen_boards.py` が生成する。

### トレースに入るもの

GPIO・I2C・SPI・PWM の 4 つを**1 本の順序付きストリーム**にする。
立ち上げで間違えるのはたいてい順序なので、そこが揃っていないと意味がない。

host-arduino-core **1.6.0** で `Wire.begin()` と PWM のフックが付き、
穴が無くなった。おかげで `BacklightPwm` と `PowerAdc` の
`#if defined(ARDUINO_ARCH_ESP32)` ガードを外せたので、
**実機と同じコードがそのままホストで走る。**

あわせて、電池の読み出し値を差し込んで**計算結果まで**ゴールデンに残している
（分圧比 1513 の TimerCam が `mV=3026` になること、など）。
