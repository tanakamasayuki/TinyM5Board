# サンプル

> English: [README.md](README.md) ／ はじめての人は [ガイド](../docs/GUIDE.ja.md)

**機能ごとに 1 本、ボードは差し替える 1 行。**

機種ごとのサンプルは作りません（40 機種ぶん並べても、必ず「自分のを見つけられない」に
なります）。代わりに**同じサンプルがどのボードでも動くこと自体**を見せます。
先頭の include を自分のボードに変えてください。

| | 見せているもの |
| --- | --- |
| **[Hello](Hello/Hello.ino)** | 立ち上げとピンの照会。**画面を使いません** —— 画面の無いボードのほうが多いので |
| **[Buttons](Buttons/Buttons.ino)** | GPIO のボタン・電源チップの中のキー・エキスパンダの先のピンが、**同じ 6 行で読める** |
| **[Battery](Battery/Battery.ino)** | ADC 直結 / AXP192 / AXP2101 / M5PM1 / AW32001 に**同じ質問**をする |
| **[Backlight](Backlight/Backlight.ino)** | ピンの PWM・レール電圧・エキスパンダの中の PWM・ただのスイッチを、**同じ `set()`** で |

## 動かし方

Arduino IDE なら **ファイル → スケッチ例 → TinyM5Board** から開き、
先頭の include を自分のボードに変えて書き込みます。

arduino-cli なら、各サンプルに `sketch.yaml` が付いているので:

```sh
cd examples/Hello
arduino-cli compile -u -p /dev/ttyUSB0
```

`sketch.yaml` には**既定のボードとコアのバージョンが固定**されています。
別のボードで動かすときは `--fqbn` を渡すか、`sketch.yaml` を書き換えてください。

## 書き方の型

どのサンプルも同じ形です。**無い機能は `#if` で避けて、無いと表示します。**

```cpp
#if TINYM5_HAS_BATTERY
  Serial.printf("%d mV\n", Board.Power.getBatteryVoltage());
#else
  Serial.println("this board has no battery");
#endif
```

`if constexpr` では代用できません（捨てる側も名前解決されるため）。
理由は [ガイド](../docs/GUIDE.ja.md) と [API](../docs/API.ja.md) にあります。
