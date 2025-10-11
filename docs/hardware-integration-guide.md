# ハードウェア実装ガイド

## Raspberry Pi Hub 実装

### 必要な依存関係
```bash
pip install websockets asyncio requests
```

### WebSocket接続実装例

```python
import asyncio
import websockets
import json
import requests
from datetime import datetime

class FourDXHardwareClient:
    def __init__(self, client_id: str, server_url: str = "ws://127.0.0.1:8001"):
        self.client_id = client_id
        self.server_url = f"{server_url}/ws/{client_id}"
        self.session_code = None
        self.websocket = None

    async def connect(self):
        """WebSocketサーバーに接続"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"Connected to server: {self.server_url}")
            
            # メッセージ受信処理を開始
            asyncio.create_task(self.listen_messages())
            
        except Exception as e:
            print(f"Connection failed: {e}")

    async def listen_messages(self):
        """サーバーからのメッセージを受信"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")

    async def handle_message(self, data):
        """受信メッセージの処理"""
        if data.get("type") == "sync_data":
            sync_data = data.get("data", {})
            await self.process_sync_data(sync_data)
        elif data.get("type") == "session_joined":
            print(f"Joined session: {data.get('session_code')}")

    async def process_sync_data(self, sync_data):
        """同期データの処理とハードウェア制御"""
        print(f"Processing sync data: {sync_data}")
        
        # 映像の時間情報を取得
        timestamp = sync_data.get("timestamp")
        action = sync_data.get("action")
        intensity = sync_data.get("intensity", 50)
        
        if action == "shake":
            await self.control_actuator("shake", intensity)
        elif action == "wind":
            await self.control_fan(intensity)
        elif action == "water":
            await self.control_water_spray(intensity)

    async def control_actuator(self, action: str, intensity: int):
        """アクチュエーター制御"""
        print(f"Actuator control: {action} at {intensity}%")
        # Arduino/モーター制御のロジックをここに実装
        # GPIOやシリアル通信でArduinoに指令送信

    async def control_fan(self, intensity: int):
        """ファン制御"""
        print(f"Fan control: {intensity}%")
        # ファン制御のロジック

    async def control_water_spray(self, intensity: int):
        """水スプレー制御"""
        print(f"Water spray: {intensity}%")
        # 水スプレー制御のロジック

    def create_session(self):
        """新規セッション作成"""
        response = requests.post("http://127.0.0.1:8001/api/session/create")
        data = response.json()
        self.session_code = data["session_code"]
        return self.session_code

    async def join_session(self, session_code: str):
        """セッションに参加"""
        self.session_code = session_code
        message = {
            "type": "join_session",
            "session_code": session_code
        }
        await self.websocket.send(json.dumps(message))

    async def send_hardware_status(self):
        """ハードウェア状態をサーバーに送信"""
        status = {
            "type": "sync_data",
            "session_code": self.session_code,
            "data": {
                "hardware_type": "raspberry_pi",
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "available_effects": ["shake", "wind", "water"]
            }
        }
        await self.websocket.send(json.dumps(status))

# 使用例
async def main():
    client = FourDXHardwareClient("rpi-hub-001")
    await client.connect()
    
    # セッション作成または参加
    session_code = client.create_session()  # 新規作成
    # または
    # await client.join_session("ABC123")  # 既存参加
    
    await client.join_session(session_code)
    await client.send_hardware_status()
    
    # 接続維持
    try:
        await asyncio.Future()  # 無限待機
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
```

## Arduino制御インターフェース

### Raspberry Pi ↔ Arduino 通信
```python
import serial
import json

class ArduinoController:
    def __init__(self, port="/dev/ttyUSB0", baud_rate=9600):
        self.serial = serial.Serial(port, baud_rate)
        
    def send_command(self, action: str, intensity: int, duration: int = 1000):
        """Arduinoに制御コマンドを送信"""
        command = {
            "action": action,
            "intensity": intensity,
            "duration": duration
        }
        self.serial.write(json.dumps(command).encode() + b'\n')
        
    def read_response(self):
        """Arduinoからの応答を読み取り"""
        if self.serial.in_waiting:
            response = self.serial.readline().decode().strip()
            return json.loads(response)
        return None
```

### Arduino側実装例 (C++)
```cpp
#include <ArduinoJson.h>

void setup() {
    Serial.begin(9600);
    // モーター、サーボ、ポンプの初期化
}

void loop() {
    if (Serial.available()) {
        String json_string = Serial.readStringUntil('\n');
        
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, json_string);
        
        String action = doc["action"];
        int intensity = doc["intensity"];
        int duration = doc["duration"];
        
        if (action == "shake") {
            controlShakeMotor(intensity, duration);
        } else if (action == "wind") {
            controlFan(intensity, duration);
        } else if (action == "water") {
            controlWaterPump(intensity, duration);
        }
        
        // 実行完了を通知
        Serial.println("{\"status\":\"complete\",\"action\":\"" + action + "\"}");
    }
}
```

## データフォーマット仕様

### 同期データ構造
```json
{
    "type": "sync_data",
    "session_code": "ABC123",
    "data": {
        "timestamp": "2025-10-11T12:30:45.123Z",
        "video_time": 45.67,
        "action": "shake",
        "intensity": 75,
        "duration": 1500,
        "effects": {
            "wind": 30,
            "water": 0,
            "shake_x": 50,
            "shake_y": 25
        }
    }
}
```