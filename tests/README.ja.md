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

### 既知の穴

| | |
| --- | --- |
| `Wire.begin()` | フックできないので順序を持つ部分に現れない。ピンとクロックは `--- state ---` に記録している。**I2C のトランザクションは正しい順序で並ぶ** |
| PWM / analog | フックが無いので**バックライトの初期化はトレースに出ない**。輝度カーブは `Backlight.duty()` が整数関数なので単体で検査できる |
