# 4DX@HOME タイムラインJSON仕様書

## 📋 概要

このドキュメントは、4DX@HOMEシステムで使用するタイムラインJSONファイルの仕様を定義します。

## 📁 ファイル構造

```json
{
  "events": [
    {
      "t": 0.0,
      "action": "caption",
      "text": "シーンの説明文"
    },
    {
      "t": 0.0,
      "action": "start",
      "effect": "vibration",
      "mode": "down_weak"
    }
  ]
}
```

## 🎯 イベントタイプ（action）

### 1. `caption` - キャプション表示

シーンの説明文を表示します。

**必須フィールド:**
- `t` (float): 時刻（秒）
- `action` (string): `"caption"`
- `text` (string): キャプションのテキスト

**例:**
```json
{
  "t": 0.0,
  "action": "caption",
  "text": "車を運転中の男性が、無線機に向かって「急げ！」と指示を出している。"
}
```

---

### 2. `start` - 効果開始

効果を開始します。開始された効果は、対応する`stop`イベントまで継続します。

**必須フィールド:**
- `t` (float): 時刻（秒）
- `action` (string): `"start"`
- `effect` (string): 効果タイプ（後述）
- `mode` (string): 効果モード（後述）

**例:**
```json
{
  "t": 0.0,
  "action": "start",
  "effect": "vibration",
  "mode": "down_weak"
}
```

---

### 3. `stop` - 効果停止

開始された効果を停止します。必ず対応する`start`イベントが必要です。

**必須フィールド:**
- `t` (float): 時刻（秒）
- `action` (string): `"stop"`
- `effect` (string): 効果タイプ（`start`と同じ）
- `mode` (string): 効果モード（`start`と同じ）

**例:**
```json
{
  "t": 1.5,
  "action": "stop",
  "effect": "vibration",
  "mode": "down_weak"
}
```

---

### 4. `shot` - 一度きりの発射

効果を一度だけ発射します。主に水・ミストの効果で使用されます。

**必須フィールド:**
- `t` (float): 時刻（秒）
- `action` (string): `"shot"`
- `effect` (string): 効果タイプ（例: `"water"` / `"mist"` / `"led_strength"` / `"led_transition"`）
- `mode` (string): 効果モード（通常は`"burst"`）

**例:**
```json
{
  "t": 2.0,
  "action": "shot",
  "effect": "water",
  "mode": "burst"
}
```

---

## ⚡ 効果タイプ（effect）

### 1. `vibration` - 振動

座席の振動を制御します。上（背中）と下（おしり）を個別または同時に制御できます。

**利用可能なモード（mode）:**

#### 上（背中）のみ
- `up_weak`: 上の弱（背中）
- `up_mid_weak`: 上の中弱（背中）
- `up_mid_strong`: 上の中強（背中）※強烈なシーンのみ
- `up_strong`: 上の強（背中）※強烈なシーンのみ

#### 下（おしり）のみ
- `down_weak`: 下の弱（おしり）
- `down_mid_weak`: 下の中弱（おしり）
- `down_mid_strong`: 下の中強（おしり）※強烈なシーンのみ
- `down_strong`: 下の強（おしり）※強烈なシーンのみ

#### 上下同時
- `up_down_weak`: 上＆下同時: 弱
- `up_down_mid_weak`: 上＆下同時: 中弱
- `up_down_mid_strong`: 上＆下同時: 中強
- `up_down_strong`: 上＆下同時: 強（かなり強い）

#### 特殊
- `heartbeat`: ドキドキ（ハートビート）

**使用例:**
```json
{
  "t": 0.0,
  "action": "start",
  "effect": "vibration",
  "mode": "down_weak"
}
```

---

### 2. `flash` - 光

照明効果を制御します。銃の火、閃光、爆発、雷などの特別な光を表現する場合のみ使用します。

**利用可能なモード（mode）:**
- `steady`: 点灯（継続的な光）
- `blink`: 点滅（チカチカ）
- `slow_blink`: 遅い点滅（互換用、blinkと同じ）
- `fast_blink`: 早い点滅（互換用、blinkと同じ）
- `breathe`: 呼吸（ゆっくり明滅）

**使用例:**
```json
{
  "t": 5.0,
  "action": "start",
  "effect": "flash",
  "mode": "blink"
}
```

---

### 3. `color` - 色

色の効果を制御します。一度に1つの色のみ有効です（新しい色を開始すると、前の色は自動的に停止されます）。

**【変更】** LED制御コマンドは `color` と `flash`、`led_strength`、`led_transition` を組み合わせて送信されます。
消灯は `color` を停止するか、`led_strength` を `off` にします（専用の消灯コマンドは不要です）。

**利用可能なモード（mode）:**
- `pink`: ピンク
- `red`: 赤
- `orange`: オレンジ
- `yellow`: 黄色
- `yellow_green`: 黄緑
- `green`: 緑
- `dark_green`: 深緑
- `cyan`: シアン
- `blue`: 青
- `purple`: 紫
- `white`: 白
- `off`: 消灯

**使用例:**
```json
{
  "t": 10.0,
  "action": "start",
  "effect": "color",
  "mode": "red"
}
```

---

### 4. `water` - 水

水しぶきの効果を制御します。

**【変更】** `water`は`start`/`stop`にも対応しました。

**利用可能なモード（mode）:**
- `burst`: 水しぶき（一度きりの発射）
- `stream`: 水（連続噴射）

**使用例（shot）:**
```json
{
  "t": 3.0,
  "action": "shot",
  "effect": "water",
  "mode": "burst"
}
```

**使用例（start/stop）:**
```json
{
  "t": 3.0,
  "action": "start",
  "effect": "water",
  "mode": "stream"
}
```
```json
{
  "t": 5.0,
  "action": "stop",
  "effect": "water",
  "mode": "stream"
}
```

**注意:** `burst`は`shot`、`stream`は`start`/`stop`で使用します。

---

### 4.5 `led_strength` - LED強さ

LEDの明るさ（強さ）を制御します。

**【変更】** LED制御コマンドに対応しました。

**利用可能なモード（mode）:**
- `off`: 消灯（0）
- `weak`: 弱（20%）
- `strong`: 強（100%）

**使用例:**
```json
{
  "t": 3.0,
  "action": "start",
  "effect": "led_strength",
  "mode": "weak"
}
```

**注意:** 明示しない場合は `strong` 扱いになります。

---

### 4.6 `led_transition` - LED変化

LEDの色変化方法を制御します。

**【変更】** LED制御コマンドに対応しました。

**利用可能なモード（mode）:**
- `instant`: 一瞬（パッと変わる）
- `fade`: フェード（フワッと変わる）

**使用例:**
```json
{
  "t": 3.0,
  "action": "start",
  "effect": "led_transition",
  "mode": "fade"
}
```

**注意:** 明示しない場合は `instant` 扱いになります。

---

### 5. `wind` - 風

風の効果を制御します。

**利用可能なモード（mode）:**
- `burst`: 風

**使用例:**
```json
{
  "t": 1.0,
  "action": "start",
  "effect": "wind",
  "mode": "burst"
}
```

---

### 6. `mist` - ミスト

ミスト（霧・蒸気・煙・白い噴霧）の効果を制御します。

**【変更】** `mist`は`start`/`stop`にも対応しました。

**利用可能なモード（mode）:**
- `burst`: ミスト噴射（一度きりの発射）
- `stream`: ミスト（連続噴射）

**使用例（shot）:**
```json
{
  "t": 2.0,
  "action": "shot",
  "effect": "mist",
  "mode": "burst"
}
```

**使用例（start/stop）:**
```json
{
  "t": 2.0,
  "action": "start",
  "effect": "mist",
  "mode": "stream"
}
```
```json
{
  "t": 4.0,
  "action": "stop",
  "effect": "mist",
  "mode": "stream"
}
```

**注意:** `burst`は`shot`、`stream`は`start`/`stop`で使用します。

---

## 📊 完全な例

```json
{
  "events": [
    {
      "t": 0.0,
      "action": "caption",
      "text": "車を運転中の男性が、無線機に向かって「急げ！」と指示を出している。"
    },
    {
      "t": 0.0,
      "action": "start",
      "effect": "vibration",
      "mode": "down_weak"
    },
    {
      "t": 0.5,
      "action": "stop",
      "effect": "vibration",
      "mode": "down_weak"
    },
    {
      "t": 0.5,
      "action": "start",
      "effect": "vibration",
      "mode": "down_mid_weak"
    },
    {
      "t": 2.0,
      "action": "shot",
      "effect": "water",
      "mode": "burst"
    },
    {
      "t": 3.0,
      "action": "start",
      "effect": "flash",
      "mode": "fast_blink"
    },
    {
      "t": 3.2,
      "action": "stop",
      "effect": "flash",
      "mode": "fast_blink"
    },
    {
      "t": 5.0,
      "action": "start",
      "effect": "color",
      "mode": "red"
    },
    {
      "t": 7.0,
      "action": "stop",
      "effect": "color",
      "mode": "red"
    },
    {
      "t": 8.0,
      "action": "start",
      "effect": "wind",
      "mode": "burst"
    },
    {
      "t": 10.0,
      "action": "stop",
      "effect": "wind",
      "mode": "burst"
    },
    {
      "t": 12.0,
      "action": "start",
      "effect": "vibration",
      "mode": "heartbeat"
    },
    {
      "t": 15.0,
      "action": "stop",
      "effect": "vibration",
      "mode": "heartbeat"
    }
  ]
}
```

---

## 🔧 仕様の詳細

### 時刻（t）

- **型:** 浮動小数点数（float）
- **単位:** 秒
- **精度:** 小数点以下3桁まで（例: `0.125`, `1.500`, `10.250`）
- **範囲:** 0.0以上

### 効果の継続

- `start`イベントで効果が開始され、対応する`stop`イベントまで継続します
- `shot`イベントは一度きりの発射で、`stop`は不要です
- 同じ効果・モードの組み合わせは、一度に1つだけアクティブにできます

### 効果の上書き

- **色（color）:** 新しい色を開始すると、前の色は自動的に停止されます
- **振動（vibration）:** 複数の振動モードを同時に有効にできます（例: `up_weak`と`down_weak`を同時に）
- **光（flash）:** 一度に1つの光効果のみ有効です

### 最小継続時間

解析時に、短すぎる効果は自動的に継続時間が延長されます。これは、効果のチラつきを防ぐためです。

---

## 📝 コマンド一覧表

### アクション（action）

| アクション | 説明 | 必要なフィールド |
|-----------|------|----------------|
| `caption` | キャプション表示 | `t`, `action`, `text` |
| `start` | 効果開始 | `t`, `action`, `effect`, `mode` |
| `stop` | 効果停止 | `t`, `action`, `effect`, `mode` |
| `shot` | 一度きりの発射 | `t`, `action`, `effect`, `mode` |

### 効果（effect）とモード（mode）

| 効果 | モード | 説明 | アクション |
|------|--------|------|-----------|
| `vibration` | `up_weak` | 上の弱（背中） | `start`/`stop` |
| `vibration` | `up_mid_weak` | 上の中弱（背中） | `start`/`stop` |
| `vibration` | `up_mid_strong` | 上の中強（背中） | `start`/`stop` |
| `vibration` | `up_strong` | 上の強（背中） | `start`/`stop` |
| `vibration` | `down_weak` | 下の弱（おしり） | `start`/`stop` |
| `vibration` | `down_mid_weak` | 下の中弱（おしり） | `start`/`stop` |
| `vibration` | `down_mid_strong` | 下の中強（おしり） | `start`/`stop` |
| `vibration` | `down_strong` | 下の強（おしり） | `start`/`stop` |
| `vibration` | `up_down_weak` | 上＆下同時: 弱 | `start`/`stop` |
| `vibration` | `up_down_mid_weak` | 上＆下同時: 中弱 | `start`/`stop` |
| `vibration` | `up_down_mid_strong` | 上＆下同時: 中強 | `start`/`stop` |
| `vibration` | `up_down_strong` | 上＆下同時: 強 | `start`/`stop` |
| `vibration` | `heartbeat` | ドキドキ | `start`/`stop` |
| `flash` | `steady` | 点灯 | `start`/`stop` |
| `flash` | `blink` | 点滅 | `start`/`stop` |
| `flash` | `breathe` | 呼吸 | `start`/`stop` |
| `color` | `pink` | ピンク | `start`/`stop` |
| `color` | `red` | 赤 | `start`/`stop` |
| `color` | `orange` | オレンジ | `start`/`stop` |
| `color` | `yellow` | 黄色 | `start`/`stop` |
| `color` | `yellow_green` | 黄緑 | `start`/`stop` |
| `color` | `green` | 緑 | `start`/`stop` |
| `color` | `dark_green` | 深緑 | `start`/`stop` |
| `color` | `cyan` | シアン | `start`/`stop` |
| `color` | `blue` | 青 | `start`/`stop` |
| `color` | `purple` | 紫 | `start`/`stop` |
| `color` | `white` | 白 | `start`/`stop` |
| `led_strength` | `off` | LED消灯 | `start`/`stop` |
| `led_strength` | `weak` | LED弱 | `start`/`stop` |
| `led_strength` | `strong` | LED強 | `start`/`stop` |
| `led_transition` | `instant` | 変化:一瞬 | `start`/`stop` |
| `led_transition` | `fade` | 変化:フェード | `start`/`stop` |
| `water` | `burst` | 水しぶき | `shot` |
| `water` | `stream` | 水（連続噴射） | `start`/`stop` |
| `wind` | `burst` | 風 | `start`/`stop` |
| `mist` | `burst` | ミスト | `shot` |
| `mist` | `stream` | ミスト（連続噴射） | `start`/`stop` |

---

## 🛰️ デバイスコマンド対応（【変更】）

本システムは以下のコマンド形式に対応します（`playback_video.py` 内で送信）。

- `FAN,1` / `FAN,0` : 風 ON/OFF（`wind:burst` の `start/stop`）
- `SPLASH` : 水しぶき一発（`water:burst` の `shot`）
- `MIST,1` : ミスト一瞬（`mist:burst` の `shot`）
- `MIST,2` / `MIST,0` : ミスト継続 ON/OFF（`mist:stream` の `start/stop`）
- `LED,色,強さ,光り方,変化` : LED制御（`color` / `flash` / `led_strength` / `led_transition`）

**補足:**
- `water:stream` は `SPLASH` を一定間隔で連射します。
- 消灯は `color` 停止 or `led_strength:off` で表現します（専用コマンド不要）。

---

## ⚠️ 注意事項

1. **時刻の順序:** イベントは時刻順にソートされている必要があります
2. **start/stopのペア:** `start`イベントには対応する`stop`イベントが必要です
3. **shotの特性:** `shot`イベントは一度きりの発射で、`stop`は不要です
4. **効果の上書き:** 色は新しい色を開始すると自動的に前の色が停止されます
5. **最小継続時間:** 短すぎる効果は自動的に延長される場合があります

---

## 🔍 検証

JSONファイルの検証には、以下の点を確認してください：

1. すべての`start`イベントに対応する`stop`イベントがあるか
2. `shot`イベントに`stop`イベントがないか（不要）
3. 時刻が0.0以上で、時刻順にソートされているか
4. 必須フィールドがすべて存在するか
5. `effect`と`mode`の組み合わせが有効か

---

## 📚 関連ドキュメント

- `README.md`: システム全体の説明
- `JSON生成ガイド.md`: JSON生成方法の詳細
- `TIMING_GUIDE.md`: タイミング調整のガイド

