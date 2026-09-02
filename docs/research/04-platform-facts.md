# プラットフォームの実測

SoC と Arduino Core を実際に調べた結果。**設計方針は含まない。**

調査時点: IDF 5.4 / m5stack_esp32 3.3.7 / esp32 3.3.11

---

## 1. FPU を持たない SoC がある

`soc_caps.h` の `SOC_CPU_HAS_FPU` より:

| SoC | FPU |
|---|---|
| ESP32 / ESP32-S3 / ESP32-P4 | **あり** |
| ESP32-S2 / C3 / C6 / H2 / C5 | **なし** |

**M5 の新しめのボードは RISC-V が多い** — StampC3 / NanoC6 / UnitC6L / NessoN1 /
ToughC5 / CoreMatrix / NanoH2 / StampC5 / StampC6。
これらで `float` を使うと soft-float ライブラリ (1〜2 KB) が入り、実行も遅い。

M5Unified の `getExtVoltage()` は `float` を返している。

## 2. I2C コントローラの数

`soc_caps.h` の `SOC_I2C_NUM` より:

| SoC | I2C 数 |
|---|---|
| ESP32 / S3 | 2 |
| **C3** | **1** |
| C6 / H2 | 2 |
| P4 | 3 |

**ESP32-C3 は I2C が 1 個しかなく `Wire1` が存在しない。**
Arduino-ESP32 の `Wire.h` は `#if SOC_I2C_NUM > 1` で `Wire1` をガードしている。
StampC3 / StampC3U が該当する。

**P4 は I2C が 3 個あるが `Wire2` は宣言されない。**
`Wire.h` の `#elif SOC_I2C_NUM > 2` は先行する `#if SOC_I2C_NUM > 1` に吸われて到達しない。

## 3. 内部 I2C と外部 Grove

M5Unified `_pin_table_i2c_ex_in` より:

| ボード | 内部 (`Wire`) | 外部 Grove (`Wire1`) |
|---|---|---|
| StickC / StickC Plus / StickC Plus2 | SDA `21` / SCL `22` | SDA `32` / SCL `33` |
| StickS3 | SDA `47` / SCL `48` | SDA `9` / SCL `10` |

**ToughC5 / CoreMatrix / NessoN1 は内部と外部が物理的に同一。**
M5Unified のコメントに明示されている。

## 4. Arduino Core の M5 系ボード定義

| Core | M5 系ボード定義数 |
|---|---|
| M5Stack 公式 core (`m5stack_esp32` 3.3.7) | **41** |
| 公式 esp32 core (`esp32` 3.3.11) | **26** |
| `boards.hpp` の全機種 | 64 (表示 35 + 非表示 29) |

**カバー率およそ 2/3。**

**両 core でマクロ名は同一。** `m5stack_stickc_plus2.build.board=M5STACK_STICKC_PLUS2`
はどちらの core でも同じ。ただし StickS3 / AtomS3R / PaperS3 / StopWatch などは
M5Stack 公式 core にしか無い。

### 4-1. 一意に対応するもの (Stick 系)

```
m5stack_stickc.build.board        = M5STACK_STICKC
m5stack_stickc_plus.build.board   = M5STACK_STICKC_PLUS
m5stack_stickc_plus2.build.board  = M5STACK_STICKC_PLUS2
m5stack_sticks3.build.board       = M5STACK_STICKS3
```

4 機種とも 1 対 1。

### 4-2. 複数の実機に対応してしまうもの

| Arduino マクロ | 実機 | 差 |
|---|---|---|
| `M5STACK_CORE2` | Core2 v1.0 / v1.1 | **PMIC が AXP192 / AXP2101** |
| `M5STACK_CARDPUTER` | Cardputer / CardputerADV | **内部 I2C のピンが違う** (ADV は SDA 8 / SCL 9、無印は内部 I2C 無し) |
| `M5STACK_ATOMS3` | AtomS3 / AtomS3Lite / AtomS3U | **画面の有無** |
| `M5STACK_ATOM` | AtomLite / Matrix / Voice / U / Psram | RGB LED の数。電源は同一 |
| `M5STACK_CORES3` | CoreS3 / CoreS3SE / StackChan | カメラの有無。電源は同一 |
| `M5STACK_CORE` | Basic / Gray / Go | ほぼ同一 |
