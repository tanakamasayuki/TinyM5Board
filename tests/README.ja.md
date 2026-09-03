# テスト

> English: [README.md](README.md)

方針は [../docs/TEST_PLAN.ja.md](../docs/TEST_PLAN.ja.md)。

## 走らせ方

```sh
cd tests
uv sync
uv run pytest begin --profile host
```

**コアは `arduino-cli core install` で入れない。** 各テストの `sketch.yaml` に
バージョンを書いてあり、`--profile` がそれを `~/.arduino15/internal/` へ
隔離して入れる（[../docs/DECISIONS.ja.md](../docs/DECISIONS.ja.md) D29）。

## 走らせる単位

`begin/` は**群でディレクトリが分かれている**。群がそのまま
GitHub Actions の matrix の軸で、ローカルでも同じ単位で絞れる。

```sh
uv run pytest begin/Stick --profile host    # 3 機種、約 2 分
uv run pytest begin --profile host          # 全部、約 5〜8 分
```

1 本ごとにスケッチをビルドして実行するので、**所要時間は機種数に線形**。
普段は自分が触った群だけを回せばよい。

## `begin/` — 初期化列のゴールデン

`Board.begin()` がバスに対して何をしたかを記録し、凍結した期待値と突き合わせる。

記録は host-arduino-core の**バス観測ポート**に乗っている。GPIO は
`<HostBus.h>`、I2C は `TwoWire` のフックで、**ライブラリ側には計測用のコードが
1 行も入らない。** スケッチと同じようにコンパイルしたものをそのまま見ている。

ボードは `-DTINYM5_BOARD_HEADER="..."` で差し込むので、**1 つのスケッチで
全機種を回せる。** ビルドフラグの入口を用意したのはこのため。

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
