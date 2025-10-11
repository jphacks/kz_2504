# 4DX@HOME ハードウェア仕様書

## 1. ハードウェア概要

### 1.1 システム構成
```
[Webアプリ] ←WSS→ [GCPサーバー] ←WSS→ [ラズパイ] ←USB→ [Arduino] → [アクチュエーター]
                                        ↓
                                   [デバイスハブ]
```

### 1.2 ハードウェア構成要素
- **デバイスハブ**: Raspberry Pi 4 Model B
- **マイクロコントローラー**: Arduino Uno R3
- **アクチュエーター**: 振動モーター、香り拡散装置（将来）
- **電源**: USB-C電源アダプター、外部電源モジュール
- **接続**: USB Serial、GPIO、I2C、SPI

## 2. デバイスハブ (Raspberry Pi)

### 2.1 ハードウェア仕様
- **モデル**: Raspberry Pi 4 Model B (4GB RAM推奨)
- **CPU**: Broadcom BCM2711 (Cortex-A72 quad-core 1.5GHz)
- **メモリ**: 4GB LPDDR4-3200 SDRAM
- **ストレージ**: microSD 32GB (Class 10以上)
- **ネットワーク**: 2.4GHz/5GHz IEEE 802.11ac WiFi、Bluetooth 5.0

### 2.2 OS・環境
- **OS**: Raspberry Pi OS Lite (64-bit)
- **Python**: 3.9+
- **主要パッケージ**: websockets, pyserial, asyncio

### 2.3 GPIO・インターフェース利用
```
GPIO ピン利用:
- GPIO 14 (TXD): Arduino との UART通信
- GPIO 15 (RXD): Arduino との UART通信  
- GPIO 18: ステータスLED制御
- GPIO 19: 緊急停止ボタン入力
- 3.3V Power: センサー電源供給
- 5V Power: Arduino VIN 接続
- GND: 共通グランド
```

### 2.4 USB接続仕様
```
USB接続:
- USB Type-A → Arduino Uno (USB Type-B)
- シリアル通信設定:
  - ボーレート: 9600 bps
  - データビット: 8
  - パリティ: なし
  - ストップビット: 1
  - フロー制御: なし
```

### 2.5 ハブソフトウェア構成

#### メインプログラム (hub.py)
```python
import asyncio
import websockets
import serial
import json
from typing import Dict, Any
import logging

class DeviceHub:
    def __init__(self):
        self.websocket = None
        self.serial_connection = None
        self.session_code = None
        self.running = False
        
    async def connect_to_server(self, server_url: str):
        """サーバーへのWebSocket接続"""
        try:
            self.websocket = await websockets.connect(server_url)
            await self.register_device()
            
        except Exception as e:
            logging.error(f"Server connection failed: {e}")
            raise
    
    async def register_device(self):
        """デバイス登録とセッションコード取得"""
        register_msg = {
            "event": "device_register",
            "data": {
                "device_type": "hub",
                "device_id": "rpi_001",
                "capabilities": ["vibration", "scent"],
                "version": "1.0.0"
            }
        }
        
        await self.websocket.send(json.dumps(register_msg))
        response = await self.websocket.recv()
        session_data = json.loads(response)
        
        if session_data["event"] == "session_created":
            self.session_code = session_data["data"]["session_code"]
            print(f"セッションコード: {self.session_code}")
            
    def init_serial_connection(self, port: str = "/dev/ttyUSB0"):
        """Arduino との USB Serial 接続初期化"""
        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=9600,
                timeout=1.0
            )
            # Arduino の起動待機
            time.sleep(2)
            logging.info("Arduino connection established")
            
        except serial.SerialException as e:
            logging.error(f"Arduino connection failed: {e}")
            raise
            
    async def handle_server_messages(self):
        """サーバーからのメッセージ処理"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                
                if data["event"] == "actuator_command":
                    await self.execute_actuator_command(data["data"])
                    
            except json.JSONDecodeError:
                logging.error(f"Invalid JSON received: {message}")
            except Exception as e:
                logging.error(f"Message handling error: {e}")
    
    async def execute_actuator_command(self, command_data: Dict[str, Any]):
        """アクチュエーター制御コマンドの実行"""
        action = command_data.get("action")
        parameters = command_data.get("parameters", {})
        
        if action == "vibrate":
            intensity = int(parameters.get("intensity", 0.5) * 100)
            duration = parameters.get("duration", 500)
            
            # Arduino 向けシリアルコマンド生成
            serial_command = f"v,{intensity},{duration}\n"
            
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.write(serial_command.encode('utf-8'))
                logging.info(f"Command sent to Arduino: {serial_command.strip()}")
```

#### システムサービス設定 (4dx-hub.service)
```ini
[Unit]
Description=4DX@HOME Device Hub Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/4dx-home
ExecStart=/usr/bin/python3 /home/pi/4dx-home/src/hub.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/pi/4dx-home

[Install]
WantedBy=multi-user.target
```

## 3. アクチュエーター (Arduino)

### 3.1 Arduino ハードウェア仕様
- **モデル**: Arduino Uno R3
- **MCU**: ATmega328P
- **クロック**: 16MHz
- **フラッシュメモリ**: 32KB
- **SRAM**: 2KB
- **EEPROM**: 1KB
- **デジタルI/O**: 14ピン (うちPWM対応6ピン)
- **アナログ入力**: 6ピン

### 3.2 回路設計

#### 振動モーター制御回路
```
Arduino Uno:
  Digital Pin 9 (PWM) → モータードライバー (L293D) Input 1
  Digital Pin 8       → モータードライバー Enable 1
  5V                  → モータードライバー VCC
  GND                 → モータードライバー GND
  
L293D Motor Driver:
  Output 1 → 振動モーター (+)
  GND      → 振動モーター (-)
  VS (Pin 8) → 外部電源 +6V (モーター用)
```

#### 回路図 (Fritzing形式)
```
振動モーター制御回路:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Arduino    │    │   L293D     │    │ Vibration   │
│             │    │             │    │   Motor     │
│         D9  │────│ Input 1     │    │             │
│         D8  │────│ Enable 1    │────│     +       │
│        5V   │────│ VCC         │    │             │
│       GND   │────│ GND    Out1 │────│     -       │
└─────────────┘    │        VS   │    └─────────────┘
                   └──────│──────┘
                          │
                    ┌─────────┐
                    │  6V DC  │
                    │ Supply  │
                    └─────────┘
```

### 3.3 Arduino ファームウェア

#### メインスケッチ (actuator.ino)
```cpp
// 4DX@HOME Actuator Controller
// Arduino Uno firmware for vibration motor control

#define MOTOR_PIN 9           // PWM pin for motor control
#define ENABLE_PIN 8          // Motor driver enable pin
#define STATUS_LED 13         // Built-in LED for status indication

// Motor control variables
int motorIntensity = 0;       // 0-100 intensity
unsigned long motorStartTime = 0;
unsigned long motorDuration = 0;
bool motorActive = false;

// Serial communication
String inputString = "";
bool stringComplete = false;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("4DX@HOME Actuator Ready");
  
  // Initialize pins
  pinMode(MOTOR_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  
  // Enable motor driver
  digitalWrite(ENABLE_PIN, HIGH);
  
  // Status LED blink to indicate ready
  for (int i = 0; i < 3; i++) {
    digitalWrite(STATUS_LED, HIGH);
    delay(200);
    digitalWrite(STATUS_LED, LOW);
    delay(200);
  }
}

void loop() {
  // Handle serial communication
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
  
  // Handle motor timeout
  if (motorActive && (millis() - motorStartTime >= motorDuration)) {
    stopMotor();
  }
  
  // Status LED indicates activity
  digitalWrite(STATUS_LED, motorActive ? HIGH : LOW);
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void processCommand(String command) {
  // Parse command format: "v,intensity,duration"
  // Example: "v,80,500" = vibrate at 80% for 500ms
  
  if (command.startsWith("v,")) {
    int firstComma = command.indexOf(',');
    int secondComma = command.indexOf(',', firstComma + 1);
    
    if (firstComma > 0 && secondComma > 0) {
      int intensity = command.substring(firstComma + 1, secondComma).toInt();
      int duration = command.substring(secondComma + 1).toInt();
      
      // Validate parameters
      intensity = constrain(intensity, 0, 100);
      duration = constrain(duration, 0, 5000); // Max 5 seconds
      
      startVibration(intensity, duration);
      
      Serial.print("ACK: v,");
      Serial.print(intensity);
      Serial.print(",");
      Serial.println(duration);
    } else {
      Serial.println("ERROR: Invalid command format");
    }
  }
  else if (command == "stop") {
    stopMotor();
    Serial.println("ACK: stop");
  }
  else if (command == "status") {
    Serial.print("STATUS: ");
    Serial.print(motorActive ? "active" : "idle");
    Serial.print(",");
    Serial.println(motorIntensity);
  }
  else {
    Serial.println("ERROR: Unknown command");
  }
}

void startVibration(int intensity, int duration) {
  motorIntensity = intensity;
  motorDuration = duration;
  motorStartTime = millis();
  motorActive = true;
  
  // Convert intensity (0-100) to PWM value (0-255)
  int pwmValue = map(intensity, 0, 100, 0, 255);
  analogWrite(MOTOR_PIN, pwmValue);
}

void stopMotor() {
  motorActive = false;
  motorIntensity = 0;
  analogWrite(MOTOR_PIN, 0);
}
```

### 3.4 振動モーター仕様
- **型番**: 推奨 - コイン型振動モーター (10mm径)
- **電圧**: 3.3V - 5V DC
- **電流**: 最大 100mA
- **回転数**: 10,000 RPM以上
- **振動強度**: PWM制御による0-100%調整
- **応答性**: 100ms以下での ON/OFF 切り替え

### 3.5 電源設計
```
電源分離設計:
┌─────────────────────────────────────┐
│ USB-C 電源アダプター (5V/3A)         │
└─────────────────┬───────────────────┘
                  │
         ┌────────┴────────┐
         │  ラズパイ 5V     │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │ USB給電 → Arduino │
         └────────┬────────┘
                  │
         ┌────────┴────────┐
         │ 外部6V → モーター │
         └─────────────────┘

外部電源 (振動モーター用):
- 6V DC電源モジュール
- 最大電流: 1A
- 安定化電源推奨
```

## 4. 機械設計・筐体

### 4.1 筐体要件
- **サイズ**: 手のひらサイズ (100mm × 80mm × 40mm以下)
- **重量**: 200g以下 (ポータビリティ重視)
- **材質**: ABS樹脂製ケース（3Dプリント対応）
- **放熱**: 通気孔によるパッシブ冷却
- **操作**: 緊急停止ボタン、ステータスLED

### 4.2 内部レイアウト
```
筐体内レイアウト (上面図):
┌─────────────────────────────────┐
│  [LED] [停止ボタン]              │
│                                │
│  ┌─────────────┐                │
│  │ Raspberry Pi │  ┌──────────┐ │
│  │              │  │ Arduino  │ │
│  │              │  │          │ │
│  └─────────────┘  └──────────┘ │
│                                │
│     ┌─────┐        [振動部]   │
│     │電源 │                   │
│     └─────┘                   │
└─────────────────────────────────┘
```

### 4.3 振動伝達設計
- **振動モーター配置**: 筐体底面近く（机への振動伝達用）
- **共振対策**: ゴム製の防振マウント
- **指向性制御**: ユーザーの手の方向への振動強化

## 5. 拡張設計 (将来対応)

### 5.1 香り拡散装置
```
香り拡散モジュール仕様:
- 制御: I2C通信でArduinoから制御
- 方式: ピエゾ式超音波霧化器
- カートリッジ: 交換式香料カートリッジ
- 拡散量: PWM制御による段階調整
- 安全機能: 過熱保護、液漏れ検知
```

### 5.2 温度制御モジュール
```
温冷感モジュール仕様:
- 素子: ペルチェ素子 (TEC1-12706)
- 制御: PWM による温度制御
- 範囲: ±10℃ (室温基準)
- 応答性: 5秒以内での温度変化
- 安全機能: 過熱保護サーミスタ
```

### 5.3 マルチデバイス対応
```
複数デバイス同期:
Hub 1 (Master) ←→ Server ←→ Hub 2 (Slave)
     ↓                           ↓
  Device A                    Device B

同期方式:
- Masterハブが同期タイミング管理
- Slaveハブは遅延補正機能
- ネットワーク遅延自動調整
```

## 6. 部品リスト・調達情報

### 6.1 必要部品一覧
| 部品名 | 型番・仕様 | 数量 | 調達先 | 概算価格 |
|--------|------------|------|--------|----------|
| Raspberry Pi 4B | 4GB RAM | 1 | RSコンポーネンツ | ¥8,000 |
| microSD カード | 32GB Class10 | 1 | Amazon | ¥1,500 |
| Arduino Uno R3 | 正規品 | 1 | スイッチサイエンス | ¥3,000 |
| 振動モーター | コイン型10mm | 1 | 秋月電子 | ¥300 |
| モータードライバー | L293D IC | 1 | 秋月電子 | ¥200 |
| USB-Cケーブル | 1.5m | 1 | Amazon | ¥800 |
| USB A-Bケーブル | 0.5m | 1 | Amazon | ¥500 |
| ブレッドボード | 半固定 | 1 | 秋月電子 | ¥400 |
| ジャンパーワイヤー | オス-オス 20本 | 1セット | 秋月電子 | ¥300 |
| 筐体 | ABS 100x80x40mm | 1 | 3Dプリント | ¥1,000 |
| **合計** |  |  |  | **¥16,000** |

### 6.2 工具・機材
- はんだごて (温度調整式推奨)
- はんだ (鉛フリー)
- ニッパー、ペンチ
- マルチメーター
- 3Dプリンター (筐体製作用)

## 7. 組み立て手順

### 7.1 Arduino 回路組み立て
1. ブレッドボードにL293Dを配置
2. 電源ライン (5V, GND) を配線  
3. Arduino D9 → L293D Input1 を接続
4. Arduino D8 → L293D Enable1 を接続
5. L293D Output1 → 振動モーター を接続
6. 配線確認とテスト

### 7.2 ラズパイセットアップ
1. Raspberry Pi OS をmicroSDに書き込み
2. SSH、WiFi設定を事前設定
3. 初回起動とパッケージ更新
4. Python環境とライブラリインストール
5. 4DX@HOME ソフトウェア配置
6. システムサービス登録と自動起動設定

### 7.3 統合テスト
1. Arduino ファームウェア書き込み
2. USB Serial 通信テスト
3. ラズパイ → Arduino 制御テスト
4. WebSocket サーバー接続テスト
5. 全体動作確認

## 8. 保守・トラブルシューティング

### 8.1 診断機能
```python
# ハードウェア診断スクリプト (診断例)
def hardware_diagnostics():
    results = {}
    
    # USB Serial 接続チェック
    try:
        ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        ser.write(b'status\n')
        response = ser.readline()
        results['arduino'] = 'OK' if response else 'NG'
        ser.close()
    except:
        results['arduino'] = 'NG'
    
    # WiFi 接続チェック
    ping_result = os.system("ping -c 1 8.8.8.8")
    results['network'] = 'OK' if ping_result == 0 else 'NG'
    
    # CPU温度チェック
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
        temp = int(f.read()) / 1000
        results['temperature'] = f"{temp}°C"
    
    return results
```

### 8.2 よくある問題と対策
| 問題 | 症状 | 原因 | 対策 |
|------|------|------|------|
| Arduino接続不良 | シリアル通信エラー | USBケーブル不良 | ケーブル交換 |
| 振動が弱い | 振動強度不足 | 電源電圧低下 | 外部電源確認 |
| WiFi切断頻発 | 接続不安定 | 電波干渉・距離 | 位置変更・中継器 |
| 同期ずれ | タイミング不正 | ネットワーク遅延 | QoS設定・回線改善 |

---

**更新日**: 2025年10月11日  
**バージョン**: 1.0  
**ハードウェア仕様策定者**: 4DX@HOME開発チーム