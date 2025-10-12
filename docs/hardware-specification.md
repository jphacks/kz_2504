# 4DX@HOME ハードウェア仕様書

## 概要

4DX@HOMEのハードウェアシステムは、Raspberry Piを中心としたデバイスハブと、Arduino制御のアクチュエーターで構成されます。リアルタイム通信により動画と同期した物理フィードバック（振動、光、風、水、香り）を提供し、没入型エンターテインメント体験を実現します。

## システム構成

### アーキテクチャ概要
```
[バックエンドサーバー] 
        ↓ WebSocket/TCP
[Raspberry Pi デバイスハブ] 
        ↓ Serial/MQTT
[Arduino アクチュエーター群]
        ↓ 物理制御
[振動・光・風・水・香り デバイス]
```

### 主要コンポーネント
1. **デバイスハブ**: Raspberry Pi 4 - 通信・制御管理
2. **アクチュエーター制御**: Arduino Uno - 物理デバイス制御
3. **物理フィードバック**: 各種センサー・モーター

## デバイスハブ仕様 (Raspberry Pi)

### ハードウェア要件
- **Raspberry Pi 4 Model B** (推奨)
  - CPU: ARM Cortex-A72 (4コア 1.8GHz)
  - RAM: 4GB以上推奨
  - Storage: microSD 32GB以上 (Class 10)
  - 接続: Wi-Fi, Ethernet, USB, GPIO

### OS・環境
- **Raspberry Pi OS** (Debian-based)
- **Python** 3.9+ 
- **システムサービス**: systemd管理

### 依存ライブラリ
```txt
websockets==11.0.3     # WebSocket通信
pyserial==3.5          # シリアル通信
paho-mqtt-client       # MQTT通信
RPi.GPIO==0.7.1        # GPIO制御
psutil==5.9.5          # システム監視
asyncio                # 非同期処理
```

### 通信プロトコル

#### 1. WebSocket通信 (バックエンド ↔ デバイスハブ)
```python
# 接続先
BACKEND_WS_URL = "ws://backend-server:8000/device/ws/{session_id}"

# 受信データ形式
{
  "type": "timeline_update",
  "events": [
    {
      "t": 15.5,           # タイムスタンプ(秒)
      "action": "start",   # "start", "stop", "shot"
      "effect": "vibration", # 効果タイプ
      "mode": "strong",    # モード
      "intensity": 0.8     # 強度(0.0-1.0)
    }
  ]
}

# 時刻同期データ
{
  "type": "time_sync",
  "current_time": 15.5,
  "session_id": "1234"
}
```

#### 2. シリアル通信 (デバイスハブ ↔ Arduino)
```python
# ポート設定
SERIAL_PORTS = {
    'wind': '/dev/ttyACM2',    # 風生成装置
    'water': '/dev/ttyACM1',   # 水噴射装置
    'flash': '/dev/ttyACM0'    # 光・色彩装置
}

# 通信設定
BAUD_RATE = 9600
TIMEOUT = 1.0

# コマンド形式
"ON\n"              # 風デバイス開始
"OFF\n"             # 風デバイス停止
"SPLASH\n"          # 水噴射(1回)
"FLASH 15\n"        # ストロボ点滅
"COLOR 255 0 0\n"   # RGB色指定
```

#### 3. MQTT通信 (振動制御)
```python
# ブローカー設定
MQTT_HOST = "172.18.28.55"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "raspberrypi_controller"

# トピック構成
MQTT_TOPICS = {
    'heart': '/vibration/heart',      # ハートビート振動
    'all': '/vibration/all',          # 全体振動
    'off': '/vibration/off'           # 振動停止
}

# メッセージ形式
Topic: /vibration/heart
Payload: "" (空文字列)
QoS: 1
```

### メインサーバープログラム

#### hardware_server.py の主要機能
```python
class TimelinePlayer:
    """タイムライン管理・デバイス制御クラス"""
    
    def set_timeline(self, events):
        """新しいタイムラインを設定"""
        
    def update_to_time(self, current_time):
        """指定時刻に同期してデバイス制御"""
        
    def control_effect(self, effect, mode, state):
        """個別効果の制御"""

class VibrationController:
    """MQTT経由振動制御"""
    
class SerialController:
    """シリアル通信制御"""
    
class SocketServer:
    """TCP/WebSocket サーバー"""
```

#### 並列処理アーキテクチャ
```python
# ThreadPoolExecutor使用
MAX_WORKERS = 10

# 非同期タスク分散
- WebSocket通信処理
- シリアル通信処理  
- MQTT通信処理
- タイムライン管理
- エラーハンドリング
```

## アクチュエーター仕様 (Arduino)

### ハードウェア要件
- **Arduino Uno R3** (各効果1台)
- **動作電圧**: 5V
- **電源**: USB/外部アダプター 9V-12V
- **I/O**: デジタル・アナログピン使用

### 対応効果・デバイス

#### 1. 振動システム (MQTT制御)
```cpp
// 振動モーター仕様
- DCモーター 3V-5V
- PWM制御対応
- 振動パターン: 3種類

// 制御モード
enum VibrationMode {
  HEARTBEAT,    // ハートビート: ドクドク
  STRONG,       // 強振動: 連続強振動
  LONG,         // 長振動: 連続弱振動
  OFF           // 停止
};
```

#### 2. 光・フラッシュシステム
```cpp
// LED仕様
- RGB LED (赤・緑・青)
- 高輝度LED (フラッシュ用)
- PWM制御 (256段階)

// コマンド
"FLASH 15"      // 15Hz ストロボ
"FLASH 10"      // 10Hz バースト
"ON"            // 定常点灯
"OFF"           // 消灯
"COLOR R G B"   // RGB指定 (0-255)

// 光モード
enum FlashMode {
  STROBE,       // 高速点滅
  BURST,        // バースト点滅  
  STEADY,       // 定常点灯
  OFF           // 消灯
};
```

#### 3. 風生成システム
```cpp
// ファン仕様
- DCファン 5V-12V
- 可変速制御
- モーター制御IC使用

// コマンド
"ON"            // ファン開始
"OFF"           // ファン停止

// 風パターン
enum WindMode {
  BURST,        // 瞬間風
  LONG,         // 持続風
  OFF           // 停止
};
```

#### 4. 水噴射システム
```cpp
// ポンプ仕様
- 小型水中ポンプ 5V
- ソレノイドバルブ
- 単発動作専用

// コマンド
"SPLASH"        // 1回噴射

// 安全機能
- 過熱保護
- 水位センサー連動
- 連続動作制限
```

#### 5. 香り拡散システム (予定)
```cpp
// 拡散デバイス
- ペルチェ素子加熱
- 小型ファン送風
- アロマカートリッジ

// 制御
"SCENT_ON"      // 香り放出開始
"SCENT_OFF"     // 香り放出停止
```

### Arduino制御プログラム

#### vibration.ino (振動制御)
```cpp
#include <WiFi.h>
#include <PubSubClient.h>

// MQTT設定
const char* mqtt_server = "172.18.28.55";
const int mqtt_port = 1883;

// 振動パターン制御
void vibrateHeartbeat();
void vibrateStrong();
void vibrateLong();
void vibrateOff();

void callback(char* topic, byte* payload, unsigned int length) {
  String topicStr = String(topic);
  
  if (topicStr == "/vibration/heart") {
    vibrateHeartbeat();
  } else if (topicStr == "/vibration/all") {
    vibrateStrong();
  } else if (topicStr == "/vibration/off") {
    vibrateOff();
  }
}
```

#### lights.ino (光制御)
```cpp
// RGB LED制御
const int RED_PIN = 9;
const int GREEN_PIN = 10;
const int BLUE_PIN = 11;
const int FLASH_PIN = 13;

void setup() {
  Serial.begin(9600);
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(FLASH_PIN, OUTPUT);
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
}

void processCommand(String cmd) {
  if (cmd.startsWith("COLOR")) {
    // RGB色設定
    int r, g, b;
    sscanf(cmd.c_str(), "COLOR %d %d %d", &r, &g, &b);
    setColor(r, g, b);
  } else if (cmd.startsWith("FLASH")) {
    // フラッシュ制御
    int frequency;
    sscanf(cmd.c_str(), "FLASH %d", &frequency);
    startFlash(frequency);
  }
}
```

#### water.ino (水制御)
```cpp
const int PUMP_PIN = 7;
const int WATER_SENSOR_PIN = A0;

void setup() {
  Serial.begin(9600);
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    
    if (command == "SPLASH") {
      if (checkWaterLevel()) {
        splash();
      }
    }
  }
}

void splash() {
  digitalWrite(PUMP_PIN, HIGH);
  delay(500);  // 0.5秒噴射
  digitalWrite(PUMP_PIN, LOW);
}
```

## 物理設計・回路

### 電源設計
- **5V系統**: Arduino、センサー、LED
- **12V系統**: DCファン、ポンプ
- **3.3V系統**: Raspberry Pi GPIO
- **電流容量**: 合計5A以上
- **安全保護**: ヒューズ、サージ保護

### 筐体設計
- **サイズ**: 150mm × 100mm × 80mm (手のひらサイズ)
- **材質**: ABS樹脂、アクリル
- **防水**: IP54相当 (水噴射部分)
- **放熱**: ファン冷却、ヒートシンク

### 配線・接続
```
Raspberry Pi GPIO:
├── UART (Serial) → Arduino通信
├── I2C → センサー接続
├── SPI → 拡張ボード  
└── PWM → サーボ制御

Arduino Digital Pins:
├── Pin 2-13 → アクチュエーター制御
├── Pin 9-11 → PWM制御 (RGB LED)
└── Pin A0-A5 → アナログセンサー
```

## 同期制御

### タイムライン処理
```python
def update_to_time(self, current_time):
    """現在時刻に基づくデバイス状態更新"""
    
    # 継続効果の管理
    target_effects = self.get_active_effects(current_time)
    
    # 開始効果
    start_effects = target_effects - self.active_effects
    for effect in start_effects:
        self.start_effect(effect)
    
    # 停止効果  
    stop_effects = self.active_effects - target_effects
    for effect in stop_effects:
        self.stop_effect(effect)
    
    # 瞬間効果 (shot)
    shot_events = self.get_shot_events(current_time)
    for event in shot_events:
        self.trigger_shot(event)
```

### 同期精度管理
- **目標精度**: ±50ms以内
- **測定方法**: タイムスタンプ比較
- **補正機能**: ネットワーク遅延補償
- **品質監視**: 同期ずれ検出・警告

### エラー回復
```python
def handle_communication_error(self, device, error):
    """通信エラー時の回復処理"""
    
    # 再接続試行
    if self.retry_connection(device):
        return True
    
    # フォールバック動作
    self.disable_device(device)
    self.notify_user(f"Device {device} disconnected")
    
    return False
```

## 安全機能

### 電気的安全
- **過電流保護**: ヒューズ・ブレーカー
- **絶縁保護**: 電源部完全分離
- **サージ保護**: バリスタ・フィルター
- **接地保護**: 適切なアース接続

### 物理的安全
- **温度監視**: 過熱時自動停止
- **動作時間制限**: 連続運転時間制約
- **緊急停止**: 手動停止スイッチ
- **状態表示**: LED インジケーター

### ソフトウェア安全
```python
# 安全制約例
MAX_VIBRATION_TIME = 30.0      # 振動最大継続時間
MAX_WATER_SHOTS_PER_MINUTE = 10 # 水噴射頻度制限
OVERHEAT_THRESHOLD = 70.0       # 過熱しきい値(℃)
WATCHDOG_TIMEOUT = 5.0          # ウォッチドッグタイムアウト
```

## 組み立て・設置

### 必要部品リスト
#### 電子部品
- Raspberry Pi 4 (4GB) × 1
- Arduino Uno R3 × 3-4台
- DCモーター(振動用) × 2
- RGB LED × 1
- 高輝度LED × 1  
- DCファン × 1
- 小型ポンプ × 1
- ブレッドボード・ジャンパー線

#### 機構部品
- 筐体 (3Dプリント/アクリル加工)
- ネジ・スペーサー
- 配線・コネクター
- 電源アダプター (12V/5A)

### 組み立て手順
1. **電子回路組み立て**: ブレッドボードで配線
2. **動作確認**: 個別デバイステスト
3. **筐体組み込み**: 部品固定・配線整理
4. **総合テスト**: システム全体動作確認
5. **校正調整**: 同期精度・効果強度調整

### 設置・設定
```bash
# Raspberry Pi セットアップ
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip git -y
pip3 install -r requirements.txt

# 自動起動設定
sudo systemctl enable 4dx-home.service
sudo systemctl start 4dx-home.service

# 動作確認
python3 hardware_server.py
```

## メンテナンス・トラブルシューティング

### 定期メンテナンス
- **清掃**: 月1回、埃・汚れ除去
- **水タンク**: 週1回、水交換・清掃
- **校正**: 月1回、同期精度確認
- **部品交換**: 半年毎、消耗品点検

### よくある問題
#### 1. 同期ずれ
- **症状**: 映像と効果のタイミングずれ
- **原因**: ネットワーク遅延、処理遅延
- **対策**: Wi-Fi環境改善、処理負荷軽減

#### 2. デバイス無応答
- **症状**: 特定効果が動作しない
- **原因**: シリアル通信エラー、Arduino異常
- **対策**: 接続確認、Arduino再起動

#### 3. 過熱停止
- **症状**: システム自動停止
- **原因**: 通風不良、連続運転
- **対策**: 設置環境改善、運転時間制限

### ログ・診断機能
```python
# システム状態監視
def system_diagnostics():
    return {
        "cpu_temperature": get_cpu_temp(),
        "memory_usage": get_memory_usage(), 
        "device_status": get_device_status(),
        "communication_quality": get_comm_quality(),
        "error_count": get_error_count()
    }
```

## 今後の拡張予定

### ハードウェア拡張
- **温度制御**: ペルチェ素子による温冷感
- **香り拡散**: 多種類アロマカートリッジ
- **触覚拡張**: エアバッグ、形状変化
- **音響連動**: 方向性スピーカー

### 制御精度向上
- **リアルタイムOS**: 確定的レスポンス
- **ハードウェアタイマー**: マイクロ秒精度
- **予測制御**: 遅延補償アルゴリズム
- **学習機能**: 個人設定最適化

### 安全性強化
- **冗長化**: 重要システムの二重化
- **無線化**: ケーブルレス接続
- **監視強化**: IoTセンサー統合
- **認証機能**: デバイス正当性確認