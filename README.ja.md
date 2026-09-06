# TinyM5Board

> English: [README.md](README.md)

**M5Stack のボードを立ち上げて、ピン表を渡すライブラリ。画面には描きません。**

電源を入れ、レールを投入し、リセットを解き、バックライトを点け、
ボタンとバッテリーを読めるようにするところまで。そこから先——文字を描く、
センサを読む——は、あなたが選んだライブラリの仕事です。

> **まだリリースしていません。実機で動かしてもいません。**
> 各ボードの値は M5Stack 自身のライブラリ（M5Unified / M5GFX）からの転記で、
> `begin()` の動作をホスト実行のゴールデンで凍結し、各 SoC 向けに
> コンパイルまで通してあります。**ピン表は「実測」ではなく「転記」**として
> 読んでください。

## 30 秒で動かす

Arduino IDE のライブラリマネージャから TinyM5Board を入れ、
**自分のボードのヘッダを 1 行 include** します。

```cpp
#include <TinyM5BoardAtomLite.h>   // ← ここを自分のボードに変える

void setup()
{
  Board.begin();

  Serial.printf("board : %s\n", Board.getBoardName());
  Serial.printf("i2c   : sda=%d scl=%d\n", Board.kI2cSda, Board.kI2cScl);
#if TINYM5_HAS_BATTERY
  Serial.printf("batt  : %d mV\n", Board.Power.getBatteryVoltage());
#endif
}

void loop()
{
  Board.update();
#if TINYM5_HAS_BTN_A
  if (Board.BtnA.wasClicked()) Serial.println("BtnA");
#endif
}
```

**ボードを変えるのは include の 1 行だけ**です。残りは全機種で同じように動きます。

- はじめての人 → **[ガイド](docs/GUIDE.ja.md)**
- 全部の定数・関数・マクロ → **[API リファレンス](docs/API.ja.md)**
- 動くコード → **[examples/](examples/README.ja.md)**

## なぜこれを使うのか

| | |
| --- | --- |
| **グラフィックスライブラリを引き込まない** | 画面の無いボードで 1 バイトも余分に積まない。画面のあるボードでは、諸元を渡すので好きな描画ライブラリを使える |
| **ボードはビルド時に決まる** | 実行時の自動判別をしないので、判別のためのコードも、間違った判別も無い |
| **どのボードでも同じ書き方** | StickC の電源キーは PMIC の中、StampPLC のボタンは IO エキスパンダの先、AtomLite のは素の GPIO。**全部 `Board.BtnA.wasClicked()` で読める** |
| **ヘッダだけ** | include しなかったものは 1 行もコンパイルされない |

**やらないこと**: 画面に描く、IMU や RTC のドライバを持つ、実行時にボードを当てる。
理由は [docs/REQUIREMENTS.ja.md](docs/REQUIREMENTS.ja.md) にあります。

## 対応ボード

<!-- BEGIN BOARD TABLE -->

**Atom**

| ボード | include | 画面 | 電池 | ボタン |
| --- | --- | --- | --- | --- |
| M5AtomLite | `<TinyM5BoardAtomLite.h>` | — | — | BtnA |
| M5AtomMatrix | `<TinyM5BoardAtomMatrix.h>` | — | — | BtnA |
| M5AtomU | `<TinyM5BoardAtomU.h>` | — | — | BtnA |
| M5AtomVoice | `<TinyM5BoardAtomVoice.h>` | — | — | BtnA |
| M5AtomS3Lite | `<TinyM5BoardAtomS3Lite.h>` | — | — | BtnA |
| M5AtomS3U | `<TinyM5BoardAtomS3U.h>` | — | — | BtnA |

**Core**

| ボード | include | 画面 | 電池 | ボタン |
| --- | --- | --- | --- | --- |
| M5Tough | `<TinyM5BoardTough.h>` | あり | あり | BtnPwr |
| M5StackCore2 | `<TinyM5BoardCore2.h>` | あり | あり | BtnPwr |
| M5ToughC5 | `<TinyM5BoardToughC5.h>` | あり | あり | BtnPwr |
| M5ChainCaptain | `<TinyM5BoardChainCaptain.h>` | あり | あり | BtnA, BtnB, BtnC, BtnPwr |
| M5StackCoreS3 | `<TinyM5BoardCoreS3.h>` | あり | あり | BtnPwr |
| M5StackCoreS3SE | `<TinyM5BoardCoreS3SE.h>` | あり | あり | BtnPwr |
| M5StackChan | `<TinyM5BoardStackChan.h>` | あり | あり | BtnPwr |
| M5CoreP4X | `<TinyM5BoardCoreP4X.h>` | あり | あり | BtnPwr |

**Other**

| ボード | include | 画面 | 電池 | ボタン |
| --- | --- | --- | --- | --- |
| M5TimerCam | `<TinyM5BoardTimerCam.h>` | — | あり | — |
| M5Capsule | `<TinyM5BoardCapsule.h>` | — | あり | BtnA, BtnB |
| M5AirQ | `<TinyM5BoardAirQ.h>` | あり | あり | BtnA, BtnB |
| M5Cardputer | `<TinyM5BoardCardputer.h>` | あり | あり | BtnA |
| M5CardputerADV | `<TinyM5BoardCardputerADV.h>` | あり | あり | BtnA |
| M5VAMeter | `<TinyM5BoardVAMeter.h>` | あり | — | BtnA, BtnB |
| ArduinoNessoN1 | `<TinyM5BoardNessoN1.h>` | あり | あり | BtnA, BtnB |
| M5Dial | `<TinyM5BoardDial.h>` | あり | — | BtnA, BtnB |
| M5DinMeter | `<TinyM5BoardDinMeter.h>` | あり | あり | BtnA, BtnB |
| M5NanoC6 | `<TinyM5BoardNanoC6.h>` | — | — | BtnA |
| M5NanoH2 | `<TinyM5BoardNanoH2.h>` | — | — | BtnA |
| M5Station | `<TinyM5BoardStation.h>` | あり | あり | BtnA, BtnB, BtnC, BtnPwr |
| M5StopWatch | `<TinyM5BoardStopWatch.h>` | あり | あり | BtnA, BtnB, BtnPwr |

**Paper**

| ボード | include | 画面 | 電池 | ボタン |
| --- | --- | --- | --- | --- |
| M5StackCoreInk | `<TinyM5BoardCoreInk.h>` | あり | あり | BtnA, BtnB, BtnC, BtnExt, BtnPwr |
| M5Paper | `<TinyM5BoardPaper.h>` | あり | あり | BtnA, BtnB, BtnC |
| M5PaperMono | `<TinyM5BoardPaperMono.h>` | あり | あり | BtnA, BtnB, BtnPwr |

**Stamp**

| ボード | include | 画面 | 電池 | ボタン |
| --- | --- | --- | --- | --- |
| M5StampPico | `<TinyM5BoardStampPico.h>` | — | — | BtnA |
| M5StampS3 | `<TinyM5BoardStampS3.h>` | — | — | BtnA |
| M5StampC3 | `<TinyM5BoardStampC3.h>` | — | — | BtnA |
| M5StampC3U | `<TinyM5BoardStampC3U.h>` | — | — | BtnA |
| M5StampPLC | `<TinyM5BoardStampPLC.h>` | あり | — | BtnA, BtnB, BtnC |

**Stick**

| ボード | include | 画面 | 電池 | ボタン |
| --- | --- | --- | --- | --- |
| M5StickC Plus2 | `<TinyM5BoardStickCPlus2.h>` | あり | あり | BtnA, BtnB, BtnPwr |
| M5StickC | `<TinyM5BoardStickC.h>` | あり | あり | BtnA, BtnB, BtnPwr |
| M5StickC Plus | `<TinyM5BoardStickCPlus.h>` | あり | あり | BtnA, BtnB, BtnPwr |
| M5StickS3 | `<TinyM5BoardStickS3.h>` | あり | あり | BtnA, BtnB, BtnPwr |

<!-- END BOARD TABLE -->

自分のボードが無いときは、[Issue](https://github.com/tanakamasayuki/TinyM5Board/issues)
で機種名を教えてください。**回路図が読める機種なら足せます。**
足せない機種とその理由は [docs/DEVELOPMENT_PLAN.ja.md](docs/DEVELOPMENT_PLAN.ja.md) §2-9 にあります。

## 必要なもの

- **arduino-esp32 3.x**（3.3.11 で確認）
- Arduino IDE / arduino-cli / PlatformIO のいずれか

依存ライブラリはありません。

## ライセンス

MIT。[LICENSE](LICENSE) を見てください。

## 開発者向け

内部の記録（日本語のみ）は [docs/README.ja.md](docs/README.ja.md) から。
ボードの追加は [docs/BOARD_CATALOG.ja.md](docs/BOARD_CATALOG.ja.md)、
テストは [tests/README.ja.md](tests/README.ja.md)。
