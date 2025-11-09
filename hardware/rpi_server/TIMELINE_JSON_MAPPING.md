# タイムラインJSON仕様 → MQTTマッピング

最終更新: 2025年11月8日

---

## 概要

このドキュメントは、最新のタイムラインJSON仕様（`docs/project_report/09_json_specification.md`）と、ラズパイサーバーのMQTTコマンド（`src/mqtt/event_mapper.py`）のマッピング対応表です。

---

## デバイス構成

| デバイス | 役割 | MQTTトピックプレフィックス |
|---------|------|------------------------|
| ESP1 (alive_esp1_water) | Water/Wind | `/4dx/water`, `/4dx/wind` |
| ESP2 (alive_esp2_led) | LED/RGB | `/4dx/light`, `/4dx/color` |
| ESP3 (alive_esp3_motor1) | Motor1（おしり） | `/4dx/motor1/control` |
| ESP4 (alive_esp4_motor2) | Motor2（背中） | `/4dx/motor2/control` |

---

## 1. Water（水しぶき）

### JSON仕様

```json
{
  "t": 2.0,
  "action": "shot",
  "effect": "water",
  "mode": "burst"
}
```

### MQTTマッピング

| effect | mode | action | MQTT Topic | MQTT Payload |
|--------|------|--------|------------|--------------|
| water | burst | shot | `/4dx/water` | `trigger` |

**注意**: `water`は`shot`アクションのみ使用。`start`/`stop`は不要。

---

## 2. Wind（風）

### JSON仕様（start）

```json
{
  "t": 1.0,
  "action": "start",
  "effect": "wind",
  "mode": "burst"
}
```

### JSON仕様（stop）

```json
{
  "t": 5.0,
  "action": "stop",
  "effect": "wind",
  "mode": "burst"
}
```

### MQTTマッピング

| effect | mode | action | MQTT Topic | MQTT Payload |
|--------|------|--------|------------|--------------|
| wind | burst | start | `/4dx/wind` | `ON` |
| wind | burst | stop | `/4dx/wind` | `OFF` |
| wind | long | start | `/4dx/wind` | `ON` |
| wind | long | stop | `/4dx/wind` | `OFF` |

---

## 3. Flash（光）

### JSON仕様

```json
{
  "t": 3.0,
  "action": "start",
  "effect": "flash",
  "mode": "fast_blink"
}
```

### MQTTマッピング

| effect | mode | action | MQTT Topic | MQTT Payload |
|--------|------|--------|------------|--------------|
| flash | steady | start | `/4dx/light` | `ON` |
| flash | steady | stop | `/4dx/light` | `OFF` |
| flash | slow_blink | start | `/4dx/light` | `BLINK_SLOW` |
| flash | slow_blink | stop | `/4dx/light` | `OFF` |
| flash | fast_blink | start | `/4dx/light` | `BLINK_FAST` |
| flash | fast_blink | stop | `/4dx/light` | `OFF` |

**旧仕様との互換性**:
- `flash` + `burst` → `BLINK_FAST`
- `flash` + `strobe` → `BLINK_FAST`

---

## 4. Color（色）

### JSON仕様

```json
{
  "t": 5.0,
  "action": "start",
  "effect": "color",
  "mode": "red"
}
```

### MQTTマッピング

| effect | mode | action | MQTT Topic | MQTT Payload |
|--------|------|--------|------------|--------------|
| color | red | start | `/4dx/color` | `RED` |
| color | red | stop | `/4dx/color` | `RED` |
| color | green | start | `/4dx/color` | `GREEN` |
| color | green | stop | `/4dx/color` | `RED` |
| color | blue | start | `/4dx/color` | `BLUE` |
| color | blue | stop | `/4dx/color` | `RED` |
| color | yellow | start | `/4dx/color` | `YELLOW` |
| color | yellow | stop | `/4dx/color` | `RED` |
| color | cyan | start | `/4dx/color` | `CYAN` |
| color | cyan | stop | `/4dx/color` | `RED` |
| color | purple | start | `/4dx/color` | `PURPLE` |
| color | purple | stop | `/4dx/color` | `RED` |

**注意**: `stop`時は赤色に戻る（OFFにはしない）

---

## 5. Vibration（振動）

### 5.1 下（おしり）のみ - Motor1 (ESP3)

#### JSON仕様

```json
{
  "t": 0.0,
  "action": "start",
  "effect": "vibration",
  "mode": "down_weak"
}
```

#### MQTTマッピング

| effect | mode | action | MQTT Topic | MQTT Payload |
|--------|------|--------|------------|--------------|
| vibration | down_weak | start | `/4dx/motor1/control` | `WEAK` |
| vibration | down_weak | stop | `/4dx/motor1/control` | `OFF` |
| vibration | down_mid_weak | start | `/4dx/motor1/control` | `MEDIUM_WEAK` |
| vibration | down_mid_weak | stop | `/4dx/motor1/control` | `OFF` |
| vibration | down_mid_strong | start | `/4dx/motor1/control` | `MEDIUM_STRONG` |
| vibration | down_mid_strong | stop | `/4dx/motor1/control` | `OFF` |
| vibration | down_strong | start | `/4dx/motor1/control` | `STRONG` |
| vibration | down_strong | stop | `/4dx/motor1/control` | `OFF` |

---

### 5.2 上（背中）のみ - Motor2 (ESP4)

#### JSON仕様

```json
{
  "t": 1.0,
  "action": "start",
  "effect": "vibration",
  "mode": "up_weak"
}
```

#### MQTTマッピング

| effect | mode | action | MQTT Topic | MQTT Payload |
|--------|------|--------|------------|--------------|
| vibration | up_weak | start | `/4dx/motor2/control` | `WEAK` |
| vibration | up_weak | stop | `/4dx/motor2/control` | `OFF` |
| vibration | up_mid_weak | start | `/4dx/motor2/control` | `MEDIUM_WEAK` |
| vibration | up_mid_weak | stop | `/4dx/motor2/control` | `OFF` |
| vibration | up_mid_strong | start | `/4dx/motor2/control` | `MEDIUM_STRONG` |
| vibration | up_mid_strong | stop | `/4dx/motor2/control` | `OFF` |
| vibration | up_strong | start | `/4dx/motor2/control` | `STRONG` |
| vibration | up_strong | stop | `/4dx/motor2/control` | `OFF` |

---

### 5.3 上下同時 - Motor1 + Motor2

#### JSON仕様

```json
{
  "t": 2.0,
  "action": "start",
  "effect": "vibration",
  "mode": "up_down_weak"
}
```

#### MQTTマッピング

| effect | mode | action | MQTT Topics | MQTT Payloads |
|--------|------|--------|-------------|---------------|
| vibration | up_down_weak | start | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `WEAK`<br>`WEAK` |
| vibration | up_down_weak | stop | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `OFF`<br>`OFF` |
| vibration | up_down_mid_weak | start | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `MEDIUM_WEAK`<br>`MEDIUM_WEAK` |
| vibration | up_down_mid_weak | stop | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `OFF`<br>`OFF` |
| vibration | up_down_mid_strong | start | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `MEDIUM_STRONG`<br>`MEDIUM_STRONG` |
| vibration | up_down_mid_strong | stop | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `OFF`<br>`OFF` |
| vibration | up_down_strong | start | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `STRONG`<br>`STRONG` |
| vibration | up_down_strong | stop | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `OFF`<br>`OFF` |

---

### 5.4 特殊パターン（旧仕様との互換性維持）

#### MQTTマッピング

| effect | mode | action | MQTT Topics | MQTT Payloads |
|--------|------|--------|-------------|---------------|
| vibration | heartbeat | start | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `HEARTBEAT`<br>`HEARTBEAT` |
| vibration | heartbeat | stop | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `OFF`<br>`OFF` |
| vibration | long | start | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `RUMBLE_SLOW`<br>`RUMBLE_SLOW` |
| vibration | long | stop | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `OFF`<br>`OFF` |
| vibration | strong | start | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `STRONG`<br>`STRONG` |
| vibration | strong | stop | `/4dx/motor1/control`<br>`/4dx/motor2/control` | `OFF`<br>`OFF` |

---

## 6. Caption（キャプション）

### JSON仕様

```json
{
  "t": 0.0,
  "action": "caption",
  "text": "車を運転中の男性が、無線機に向かって「急げ！」と指示を出している。"
}
```

**注意**: キャプションはMQTTコマンドに変換されません。フロントエンド（debug_frontend）で字幕表示に使用されます。

---

## ESP-12Eデバイスのペイロード仕様

### Motor（振動）ペイロード

| ペイロード | 説明 |
|-----------|------|
| `WEAK` | 弱 |
| `MEDIUM_WEAK` | 中弱 |
| `MEDIUM_STRONG` | 中強 |
| `STRONG` | 強 |
| `HEARTBEAT` | ハートビートパターン |
| `RUMBLE_SLOW` | 低速振動 |
| `RUMBLE_FAST` | 高速振動 |
| `OFF` | 停止 |

### Light（LED）ペイロード

| ペイロード | 説明 |
|-----------|------|
| `ON` | 点灯 |
| `BLINK_SLOW` | ゆっくり点滅 |
| `BLINK_FAST` | 速く点滅 |
| `OFF` | 消灯 |

### Color（RGB）ペイロード

| ペイロード | 説明 |
|-----------|------|
| `RED` | 赤 |
| `GREEN` | 緑 |
| `BLUE` | 青 |
| `YELLOW` | 黄色 |
| `CYAN` | シアン |
| `PURPLE` | 紫 |

### Water（水）ペイロード

| ペイロード | 説明 |
|-----------|------|
| `trigger` | 単発発射 |

### Wind（風）ペイロード

| ペイロード | 説明 |
|-----------|------|
| `ON` | 起動 |
| `OFF` | 停止 |

---

## 互換性について

### 旧JSON仕様との互換性

以下の旧仕様も引き続きサポートされます：

- `flash` + `burst` → `BLINK_FAST`
- `flash` + `strobe` → `BLINK_FAST`
- `vibration` + `heartbeat` → Motor1+Motor2でハートビートパターン
- `vibration` + `long` → Motor1+Motor2で低速振動
- `vibration` + `strong` → Motor1+Motor2で強振動
- `wind` + `long` → Wind ON

### デバッグコントローラーとの互換性

デバッグコントローラー（`templates/controller.html`）の手動操作は、直接MQTTコマンドを送信するため、このマッピングとは独立しています。両方の機能が共存可能です。

---

## タイムラインJSON例

```json
{
  "events": [
    {
      "t": 0.0,
      "action": "caption",
      "text": "車が急加速する"
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
      "t": 1.0,
      "action": "start",
      "effect": "vibration",
      "mode": "up_down_mid_strong"
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
      "t": 3.5,
      "action": "stop",
      "effect": "flash",
      "mode": "fast_blink"
    },
    {
      "t": 4.0,
      "action": "stop",
      "effect": "vibration",
      "mode": "up_down_mid_strong"
    }
  ]
}
```

---

## 実装ファイル

- **マッピング定義**: `src/mqtt/event_mapper.py`
- **タイムライン処理**: `src/timeline/processor.py`
- **JSON仕様書**: `docs/project_report/09_json_specification.md`

---

**最終更新**: 2025年11月8日  
**バージョン**: 2.0.0  
**対応JSON仕様**: 09_json_specification.md
