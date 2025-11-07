# Raspberry Pi サーバー統合実装計画

**作成日**: 2025年11月7日  
**対象**: `hardware/rpi_server` ディレクトリ  
**目的**: ハードウェアエンジニアの「4DXHOME」コードを尊重しつつ、「debug_hardware」の機能を統合したRaspberry Pi向けサーバーを構築

---

## 📋 実装計画概要

### 目標
1. **ハードウェアコードの保持**: `4DXHOME/mqtt_server.py`の既存MQTT制御ロジックを尊重
2. **API統合**: Cloud Run APIサーバーとのWebSocket通信機能を追加
3. **デバッグ機能**: 通信ログ・監視ダッシュボードの統合
4. **段階的移行**: ハードウェアエンジニアが既存システムを使い続けながら、新機能を追加可能にする

---

## 🏗️ アーキテクチャ設計

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                  Raspberry Pi サーバー                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         統合制御レイヤー (rpi_server)                 │  │
│  │                                                       │  │
│  │  ┌─────────────────┐    ┌─────────────────┐        │  │
│  │  │ WebSocket        │    │ HTTP Server     │        │  │
│  │  │ クライアント      │    │ (Flask)         │        │  │
│  │  │                 │    │                 │        │  │
│  │  │ Cloud Run API   │    │ ローカル        │        │  │
│  │  │ 接続管理         │    │ 監視UI          │        │  │
│  │  └────────┬────────┘    └────────┬────────┘        │  │
│  │           │                      │                 │  │
│  │           └──────────┬───────────┘                 │  │
│  │                      │                             │  │
│  │           ┌──────────▼──────────┐                  │  │
│  │           │ タイムライン処理     │                  │  │
│  │           │ - JSON解析          │                  │  │
│  │           │ - 時間同期照合      │                  │  │
│  │           │ - イベント実行      │                  │  │
│  │           └──────────┬──────────┘                  │  │
│  │                      │                             │  │
│  └──────────────────────┼─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │         既存MQTTレイヤー (4DXHOME互換)              │  │
│  │                                                     │  │
│  │  ┌─────────────────┐    ┌─────────────────┐       │  │
│  │  │ MQTT Broker     │    │ MQTT Publisher  │       │  │
│  │  │ (mosquitto)     │    │ (Paho MQTT)     │       │  │
│  │  └─────────────────┘    └────────┬────────┘       │  │
│  │                                   │                │  │
│  └───────────────────────────────────┼────────────────┘  │
│                                      │                   │
│  ┌───────────────────────────────────▼────────────────┐  │
│  │          ハードウェア制御レイヤー                    │  │
│  │                                                     │  │
│  │  ESP-12E (Water/Wind) │ ESP-12E (LED)              │  │
│  │  ESP-12E (Motor1)     │ ESP-12E (Motor2)           │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 ディレクトリ構造

```
hardware/rpi_server/
├── README.md                        # プロジェクト概要・セットアップ手順
├── IMPLEMENTATION_PLAN.md           # この実装計画書
├── requirements.txt                 # Python依存パッケージ
├── config.py                        # 設定管理（環境変数）
├── .env.example                     # 環境変数テンプレート
├── .env                             # 環境変数（Git除外）
│
├── main.py                          # アプリケーションエントリーポイント
│
├── legacy/                          # 既存コード（参照・移行用）
│   ├── mqtt_server.py               # 4DXHOME/mqtt_server.py のコピー
│   ├── controller.html              # 4DXHOME/controller.html のコピー
│   ├── timeline_player.html         # 4DXHOME/timeline_player.html のコピー
│   └── timeline.json                # 4DXHOME/timeline.json のコピー
│
├── src/                             # ソースコード
│   ├── __init__.py
│   │
│   ├── mqtt/                        # MQTT制御（既存ロジック）
│   │   ├── __init__.py
│   │   ├── broker.py                # MQTTブローカー接続管理
│   │   ├── publisher.py             # MQTT発行ヘルパー
│   │   ├── device_manager.py        # ESP デバイス管理
│   │   └── event_mapper.py          # タイムラインイベント→MQTTコマンド変換
│   │
│   ├── api/                         # Cloud Run API連携
│   │   ├── __init__.py
│   │   ├── websocket_client.py      # Cloud Run WebSocket接続
│   │   ├── message_handler.py       # WebSocket受信メッセージ処理
│   │   └── connection_manager.py    # WebSocket接続状態管理
│   │
│   ├── timeline/                    # タイムライン処理
│   │   ├── __init__.py
│   │   ├── processor.py             # タイムラインJSON解析・照合
│   │   ├── cache_manager.py         # タイムラインキャッシュ管理
│   │   └── event_executor.py        # イベント実行制御
│   │
│   ├── server/                      # HTTPサーバー（Flask）
│   │   ├── __init__.py
│   │   ├── app.py                   # Flaskアプリケーション
│   │   ├── routes.py                # REST APIエンドポイント
│   │   └── socketio_handler.py      # Socket.IO（監視UI用）
│   │
│   └── utils/                       # ユーティリティ
│       ├── __init__.py
│       ├── logger.py                # ロガー設定
│       ├── timing.py                # タイムスタンプ処理
│       ├── validators.py            # データバリデーション
│       └── communication_logger.py  # 通信ログ記録
│
├── templates/                       # HTMLテンプレート
│   ├── index.html                   # 監視ダッシュボード（debug_hardware ベース）
│   ├── controller.html              # 手動制御UI（4DXHOME ベース）
│   └── timeline_player.html         # タイムライン再生UI（4DXHOME ベース）
│
├── static/                          # 静的ファイル
│   ├── css/
│   │   ├── dashboard.css            # 監視ダッシュボード用CSS
│   │   └── controller.css           # 手動制御UI用CSS
│   └── js/
│       ├── realtime_monitor.js      # リアルタイム監視用JavaScript
│       └── controller.js            # 手動制御用JavaScript
│
├── data/                            # データ保存
│   ├── timeline_cache/              # タイムラインJSONキャッシュ
│   └── communication_logs/          # 通信ログファイル
│
├── tests/                           # テストコード
│   ├── __init__.py
│   ├── test_mqtt_integration.py     # MQTT統合テスト
│   ├── test_websocket_client.py     # WebSocket接続テスト
│   └── test_timeline_processor.py   # タイムライン処理テスト
│
└── scripts/                         # 運用スクリプト
    ├── start_server.sh              # サーバー起動スクリプト
    ├── stop_server.sh               # サーバー停止スクリプト
    ├── install_dependencies.sh      # 依存パッケージインストール
    └── setup_systemd.sh             # systemdサービス登録
```

---

## 🔧 主要コンポーネント設計

### 1. 統合制御レイヤー (`main.py`)

**役割**: アプリケーション全体の起動・停止・統合制御

```python
"""
Raspberry Pi サーバー統合制御
4DXHOME互換 + Cloud Run API統合
"""

import asyncio
import signal
import sys
from src.mqtt.broker import MQTTBrokerClient
from src.api.websocket_client import CloudRunWebSocketClient
from src.server.app import create_flask_app
from src.utils.logger import setup_logger
from config import Config

logger = setup_logger(__name__, Config.LOG_FILE, Config.LOG_LEVEL)

class RaspberryPiServer:
    """統合サーバー制御クラス"""
    
    def __init__(self):
        self.mqtt_client = None
        self.websocket_client = None
        self.flask_app = None
        self.running = False
        
    async def start(self):
        """サーバー起動"""
        logger.info("="*70)
        logger.info("🚀 Raspberry Pi サーバー起動")
        logger.info(f"   デバイスID: {Config.DEVICE_HUB_ID}")
        logger.info(f"   ローカルポート: {Config.LOCAL_SERVER_PORT}")
        logger.info(f"   Cloud Run API: {Config.CLOUD_RUN_API_URL}")
        logger.info("="*70)
        
        # 1. MQTT接続
        self.mqtt_client = MQTTBrokerClient(
            broker_host=Config.MQTT_BROKER_HOST,
            broker_port=Config.MQTT_BROKER_PORT
        )
        await self.mqtt_client.connect()
        
        # 2. WebSocket接続（Cloud Run API）
        self.websocket_client = CloudRunWebSocketClient(
            api_url=Config.CLOUD_RUN_WS_URL,
            session_id=Config.SESSION_ID
        )
        await self.websocket_client.connect()
        
        # 3. Flaskサーバー起動
        self.flask_app = create_flask_app(
            mqtt_client=self.mqtt_client,
            websocket_client=self.websocket_client
        )
        
        self.running = True
        logger.info("✅ 全サービス起動完了")
        
    async def stop(self):
        """サーバー停止"""
        logger.info("🔴 Raspberry Pi サーバー停止中...")
        
        if self.websocket_client:
            await self.websocket_client.disconnect()
            
        if self.mqtt_client:
            await self.mqtt_client.disconnect()
            
        self.running = False
        logger.info("✅ 全サービス停止完了")
        
    async def run(self):
        """メインループ"""
        await self.start()
        
        # シグナルハンドラー登録
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # サーバー実行
        try:
            while self.running:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Ctrl+C 検出")
        finally:
            await self.stop()
    
    def _signal_handler(self, signum, frame):
        """シグナル受信時の処理"""
        logger.info(f"シグナル {signum} 受信")
        self.running = False

if __name__ == "__main__":
    server = RaspberryPiServer()
    asyncio.run(server.run())
```

---

### 2. MQTT制御レイヤー (`src/mqtt/`)

**役割**: 既存の4DXHOMEロジックを継承し、MQTT経由でESPデバイスを制御

#### `src/mqtt/broker.py` - MQTTブローカー接続管理

```python
"""
MQTTブローカー接続管理
4DXHOME/mqtt_server.py の MQTT ロジックを継承
"""

import paho.mqtt.client as mqtt
import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class MQTTBrokerClient:
    """MQTTブローカー接続クライアント"""
    
    def __init__(self, broker_host: str, broker_port: int):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.connected = False
        
        # コールバック登録
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
    async def connect(self):
        """MQTTブローカーに接続"""
        try:
            logger.info(f"MQTT接続開始: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            self.connected = True
            logger.info("✅ MQTT接続成功")
        except Exception as e:
            logger.error(f"❌ MQTT接続エラー: {e}")
            raise
    
    async def disconnect(self):
        """MQTTブローカーから切断"""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT切断完了")
    
    def publish(self, topic: str, payload: str, qos: int = 1):
        """
        MQTTメッセージ発行
        4DXHOME/mqtt_server.py の publish_mqtt_helper() と同等
        """
        try:
            msg_info = self.client.publish(topic, payload, qos=qos)
            logger.debug(f"[MQTT発行] {topic} -> {payload}")
            return msg_info
        except Exception as e:
            logger.error(f"[MQTT発行エラー] {topic}: {e}")
            raise
    
    def subscribe(self, topic: str):
        """MQTTトピック購読"""
        self.client.subscribe(topic)
        logger.info(f"MQTT購読: {topic}")
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT接続確立時のコールバック"""
        if rc == 0:
            logger.info("MQTT接続確立")
            # ハートビート監視トピック購読
            self.subscribe("/4dx/heartbeat")
        else:
            logger.error(f"MQTT接続失敗: rc={rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTTメッセージ受信時のコールバック"""
        try:
            payload = msg.payload.decode('utf-8')
            logger.debug(f"[MQTT受信] {msg.topic}: {payload}")
            
            # デバイスハートビート処理
            # (4DXHOME の on_message_global() ロジックを移植)
            # ... (デバイス管理ロジック)
            
        except Exception as e:
            logger.error(f"MQTTメッセージ処理エラー: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT切断時のコールバック"""
        logger.warning(f"MQTT切断: rc={rc}")
        self.connected = False
```

#### `src/mqtt/event_mapper.py` - イベント→MQTTコマンド変換

```python
"""
タイムラインイベントをMQTTコマンドに変換
4DXHOME/mqtt_server.py の event_map を継承
"""

from typing import Dict, List, Tuple, Union, Optional
import logging

logger = logging.getLogger(__name__)

class EventToMQTTMapper:
    """タイムラインイベント→MQTTコマンドマッピング"""
    
    # 4DXHOME/mqtt_server.py の event_map を継承
    EVENT_MAP: Dict[Tuple[str, str], Union[Tuple[str, str], List[Tuple[str, str]]]] = {
        # (1) ESP1 (Water/Wind)
        ("water", "burst"): ("/4dx/water", "trigger"),
        ("wind", "burst"): ("/4dx/wind", "ON"),
        ("wind", "long"): ("/4dx/wind", "ON"),
        
        # (2) ESP2 (LED)
        ("color", "red"): ("/4dx/color", "RED"),
        ("color", "green"): ("/4dx/color", "GREEN"),
        ("color", "blue"): ("/4dx/color", "BLUE"),
        ("color", "yellow"): ("/4dx/color", "YELLOW"),
        ("color", "cyan"): ("/4dx/color", "CYAN"),
        ("color", "purple"): ("/4dx/color", "PURPLE"),
        
        ("flash", "steady"): ("/4dx/light", "ON"),
        ("flash", "burst"): ("/4dx/light", "BLINK_FAST"),
        ("flash", "strobe"): ("/4dx/light", "BLINK_FAST"),
        
        # (3) ESP3 / ESP4 (Motor)
        ("vibration", "heartbeat"): [
            ("/4dx/motor1/control", "HEARTBEAT"),
            ("/4dx/motor2/control", "HEARTBEAT")
        ],
        ("vibration", "long"): [
            ("/4dx/motor1/control", "RUMBLE_SLOW"),
            ("/4dx/motor2/control", "RUMBLE_SLOW")
        ],
        ("vibration", "strong"): [
            ("/4dx/motor1/control", "STRONG"),
            ("/4dx/motor2/control", "STRONG")
        ],
    }
    
    # 停止アクションのマッピング
    STOP_EVENT_MAP: Dict[str, Union[Tuple[str, str], List[Tuple[str, str]]]] = {
        "wind": ("/4dx/wind", "OFF"),
        "color": ("/4dx/color", "RED"),  # LEDはOFFにせず「赤」に戻す
        "flash": ("/4dx/light", "OFF"),
        "vibration": [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ],
    }
    
    @classmethod
    def get_mqtt_commands(cls, event: dict) -> List[Tuple[str, str]]:
        """
        タイムラインイベントからMQTTコマンドリストを取得
        
        Args:
            event: タイムラインイベント (例: {"action": "start", "effect": "vibration", "mode": "strong"})
            
        Returns:
            MQTTコマンドリスト [(topic, payload), ...]
        """
        action = event.get("action")
        effect = event.get("effect")
        mode = event.get("mode")
        
        commands = []
        
        if action in ["start", "shot"]:
            mqtt_command = cls.EVENT_MAP.get((effect, mode))
            
            if mqtt_command:
                if isinstance(mqtt_command, list):
                    # 複数コマンド（振動など）
                    commands.extend(mqtt_command)
                elif isinstance(mqtt_command, tuple):
                    # 単一コマンド
                    commands.append(mqtt_command)
                    
        elif action == "stop":
            mqtt_command = cls.STOP_EVENT_MAP.get(effect)
            
            if mqtt_command:
                if isinstance(mqtt_command, list):
                    commands.extend(mqtt_command)
                elif isinstance(mqtt_command, tuple):
                    commands.append(mqtt_command)
        
        elif action == "caption":
            # 字幕は無視
            pass
        else:
            logger.warning(f"未知のアクション: {action}")
        
        return commands
```

---

### 3. Cloud Run API連携レイヤー (`src/api/`)

**役割**: Cloud Run APIサーバーとWebSocket通信し、タイムライン・同期データを受信

#### `src/api/websocket_client.py` - WebSocket接続クライアント

```python
"""
Cloud Run WebSocket接続クライアント
debug_hardware/websocket_client.py をベースに改良
"""

import asyncio
import websockets
import json
import logging
from typing import Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CloudRunWebSocketClient:
    """Cloud Run APIサーバーとのWebSocket接続クライアント"""
    
    def __init__(self, api_url: str, session_id: str):
        self.api_url = api_url
        self.session_id = session_id
        self.websocket = None
        self.connected = False
        self.message_handlers = []
        
    async def connect(self):
        """WebSocket接続確立"""
        try:
            # Cloud Run WebSocketエンドポイント
            ws_url = f"{self.api_url}/api/playback/ws/device/{self.session_id}"
            
            logger.info(f"WebSocket接続開始: {ws_url}")
            self.websocket = await websockets.connect(ws_url)
            self.connected = True
            logger.info("✅ WebSocket接続成功")
            
            # 受信ループ開始
            asyncio.create_task(self._receive_loop())
            
        except Exception as e:
            logger.error(f"❌ WebSocket接続エラー: {e}")
            raise
    
    async def disconnect(self):
        """WebSocket切断"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("WebSocket切断完了")
    
    async def send(self, message: dict):
        """メッセージ送信"""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps(message))
                logger.debug(f"[WS送信] {message}")
            except Exception as e:
                logger.error(f"WebSocket送信エラー: {e}")
    
    async def _receive_loop(self):
        """メッセージ受信ループ"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket接続が切断されました")
            self.connected = False
        except Exception as e:
            logger.error(f"WebSocket受信エラー: {e}")
    
    async def _handle_message(self, message: str):
        """受信メッセージ処理"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            logger.debug(f"[WS受信] type={msg_type}")
            
            # メッセージハンドラーに配信
            for handler in self.message_handlers:
                await handler(msg_type, data)
                
        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")
    
    def add_message_handler(self, handler: Callable):
        """メッセージハンドラー登録"""
        self.message_handlers.append(handler)
```

#### `src/api/message_handler.py` - WebSocketメッセージハンドラー

```python
"""
WebSocket受信メッセージの処理
"""

import logging
from typing import Dict, Any
from src.timeline.processor import TimelineProcessor
from src.utils.communication_logger import CommunicationLogger

logger = logging.getLogger(__name__)

class WebSocketMessageHandler:
    """WebSocketメッセージハンドラー"""
    
    def __init__(
        self,
        timeline_processor: TimelineProcessor,
        communication_logger: CommunicationLogger
    ):
        self.timeline_processor = timeline_processor
        self.comm_logger = communication_logger
    
    async def handle_message(self, msg_type: str, data: Dict[str, Any]):
        """
        メッセージタイプに応じた処理
        
        対応メッセージタイプ:
        - sync_data_bulk_transmission: タイムラインJSON受信
        - timeline: タイムラインJSON受信（別形式）
        - sync: 再生時間同期
        - currentTime: 再生時間同期（別形式）
        - ping: 接続確認
        """
        
        # 通信ログ記録
        self.comm_logger.log_websocket_receive(msg_type, data)
        
        if msg_type == "sync_data_bulk_transmission":
            await self._handle_timeline_bulk(data)
            
        elif msg_type == "timeline":
            await self._handle_timeline(data)
            
        elif msg_type == "sync" or msg_type == "currentTime":
            await self._handle_sync(data)
            
        elif msg_type == "ping":
            await self._handle_ping(data)
            
        else:
            logger.warning(f"未知のメッセージタイプ: {msg_type}")
    
    async def _handle_timeline_bulk(self, data: Dict[str, Any]):
        """タイムラインJSON一括受信処理"""
        logger.info("[Timeline] 一括データ受信")
        
        video_id = data.get("video_id")
        sync_data = data.get("sync_data", {})
        metadata = data.get("transmission_metadata", {})
        
        # タイムライン処理に登録
        success = await self.timeline_processor.load_timeline(
            video_id=video_id,
            timeline_data=sync_data,
            metadata=metadata
        )
        
        if success:
            logger.info(f"✅ タイムライン読込完了: {video_id}")
        else:
            logger.error(f"❌ タイムライン読込失敗: {video_id}")
    
    async def _handle_timeline(self, data: Dict[str, Any]):
        """タイムラインJSON受信処理（別形式）"""
        logger.info("[Timeline] データ受信")
        # ... (処理内容は _handle_timeline_bulk と同様)
    
    async def _handle_sync(self, data: Dict[str, Any]):
        """再生時間同期処理"""
        current_time = data.get("currentTime")
        
        if current_time is not None:
            # タイムライン照合・イベント実行
            await self.timeline_processor.process_sync(current_time)
        else:
            logger.warning("currentTime が含まれていません")
    
    async def _handle_ping(self, data: Dict[str, Any]):
        """Ping応答"""
        logger.debug("Ping受信 → Pong応答")
        # WebSocketクライアントから自動応答
```

---

### 4. タイムライン処理レイヤー (`src/timeline/`)

**役割**: タイムラインJSONの解析・時間照合・イベント実行

#### `src/timeline/processor.py` - タイムライン処理コア

```python
"""
タイムライン処理コア
debug_hardware/timeline_processor.py + 4DXHOME/mqtt_server.py の統合
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.mqtt.event_mapper import EventToMQTTMapper
from src.mqtt.broker import MQTTBrokerClient
from config import Config

logger = logging.getLogger(__name__)

class TimelineProcessor:
    """タイムライン処理クラス"""
    
    def __init__(self, mqtt_client: MQTTBrokerClient):
        self.mqtt_client = mqtt_client
        self.timeline_events: List[Dict] = []
        self.last_processed_time: float = -1.0
        self.video_id: Optional[str] = None
        self.sync_tolerance_ms = Config.SYNC_TOLERANCE_MS
        
    async def load_timeline(
        self,
        video_id: str,
        timeline_data: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        タイムラインJSON読み込み
        
        Args:
            video_id: 動画ID
            timeline_data: タイムラインJSONデータ
            metadata: メタデータ（任意）
            
        Returns:
            読み込み成功: True, 失敗: False
        """
        try:
            events = timeline_data.get("events", [])
            
            if not events:
                logger.error("タイムラインにイベントがありません")
                return False
            
            # 時間順にソート
            events.sort(key=lambda x: x.get("t", 0.0))
            
            self.timeline_events = events
            self.video_id = video_id
            self.last_processed_time = -1.0
            
            logger.info(f"タイムライン読込完了: {len(events)}イベント")
            
            if metadata:
                logger.info(f"  メタデータ: {metadata}")
            
            return True
            
        except Exception as e:
            logger.error(f"タイムライン読込エラー: {e}")
            return False
    
    async def process_sync(self, current_time: float):
        """
        再生時間同期処理
        
        Args:
            current_time: 現在の再生時間（秒）
        """
        if not self.timeline_events:
            logger.warning("タイムラインが読み込まれていません")
            return
        
        # 処理範囲: last_processed_time < t <= current_time
        events_to_fire = []
        
        for event in self.timeline_events:
            t = event.get("t", -1.0)
            
            if t > self.last_processed_time and t <= current_time:
                events_to_fire.append(event)
        
        # イベント実行
        if events_to_fire:
            logger.info(f"[Sync @ {current_time:.2f}s] {len(events_to_fire)}イベント実行")
            
            for event in events_to_fire:
                await self._execute_event(event)
        
        # 最終処理時間更新
        self.last_processed_time = current_time
    
    async def _execute_event(self, event: Dict):
        """
        イベント実行
        
        Args:
            event: タイムラインイベント
        """
        try:
            # イベント→MQTTコマンド変換
            mqtt_commands = EventToMQTTMapper.get_mqtt_commands(event)
            
            if not mqtt_commands:
                # 字幕などMQTTコマンドがない場合
                if event.get("action") != "caption":
                    logger.debug(f"MQTTコマンドなし: {event}")
                return
            
            # MQTT発行
            for topic, payload in mqtt_commands:
                self.mqtt_client.publish(topic, payload, qos=1)
                logger.info(f"  [MQTT] {topic} -> {payload}")
                
        except Exception as e:
            logger.error(f"イベント実行エラー: {event}, {e}")
    
    def reset_timeline(self, start_time: float = 0.0):
        """
        タイムライン再生位置リセット
        
        Args:
            start_time: リセット後の開始時間
        """
        logger.info(f"タイムラインリセット: {start_time:.2f}s")
        self.last_processed_time = start_time
    
    def has_timeline(self) -> bool:
        """タイムライン読み込み済みか"""
        return len(self.timeline_events) > 0
```

---

### 5. HTTPサーバーレイヤー (`src/server/`)

**役割**: Flaskによるローカル監視UI・REST APIエンドポイント提供

#### `src/server/app.py` - Flaskアプリケーション

```python
"""
Flaskアプリケーション
debug_hardware/app.py + 4DXHOME/mqtt_server.py の統合
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
from datetime import datetime
from config import Config
from src.mqtt.broker import MQTTBrokerClient
from src.api.websocket_client import CloudRunWebSocketClient

logger = logging.getLogger(__name__)

def create_flask_app(
    mqtt_client: MQTTBrokerClient,
    websocket_client: CloudRunWebSocketClient
) -> Flask:
    """Flaskアプリケーション作成"""
    
    app = Flask(__name__, template_folder='../../templates', static_folder='../../static')
    app.config.from_object(Config)
    CORS(app)
    
    # Socket.IO初期化（フロントエンド監視用）
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # ================== REST APIエンドポイント ==================
    
    @app.route('/')
    def index():
        """監視ダッシュボード（debug_hardware ベース）"""
        return render_template(
            'index.html',
            device_id=Config.DEVICE_HUB_ID,
            device_name=Config.DEVICE_HUB_NAME
        )
    
    @app.route('/controller')
    def controller():
        """手動制御UI（4DXHOME ベース）"""
        return render_template('controller.html')
    
    @app.route('/timeline')
    def timeline_player():
        """タイムライン再生UI（4DXHOME ベース）"""
        return render_template('timeline_player.html')
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """ヘルスチェック"""
        logger.info("📡 [REST] ヘルスチェック要求")
        
        response_data = {
            'status': 'ok',
            'device_id': Config.DEVICE_HUB_ID,
            'device_name': Config.DEVICE_HUB_NAME,
            'timestamp': datetime.now().isoformat(),
            'mqtt_connected': mqtt_client.connected,
            'websocket_connected': websocket_client.connected,
            'session_id': Config.SESSION_ID
        }
        
        logger.info(f"✅ [REST] ヘルスチェック応答: MQTT={response_data['mqtt_connected']}, WS={response_data['websocket_connected']}")
        
        return jsonify(response_data)
    
    @app.route('/device/info', methods=['GET'])
    def device_info():
        """デバイス情報取得"""
        logger.info("📡 [REST] デバイス情報取得要求")
        
        response_data = {
            'device_id': Config.DEVICE_HUB_ID,
            'device_name': Config.DEVICE_HUB_NAME,
            'capabilities': ['vibration', 'wind', 'water', 'flash', 'color'],
            'status': 'active',
            'cloud_run_url': Config.CLOUD_RUN_API_URL,
            'session_id': Config.SESSION_ID
        }
        
        logger.info(f"✅ [REST] デバイス情報応答: {Config.DEVICE_HUB_ID}")
        
        return jsonify(response_data)
    
    @app.route('/publish', methods=['POST'])
    def publish_mqtt():
        """
        手動MQTT発行（4DXHOME互換）
        controller.htmlから呼ばれる
        """
        try:
            data = request.json
            topic = data.get('topic')
            payload = data.get('payload')
            
            if not topic or payload is None:
                raise ValueError("topic and payload are required")
            
            logger.info(f"[HTTP->MQTT] Publishing: [{topic}] -> {payload}")
            mqtt_client.publish(topic, payload, qos=1)
            
            return jsonify({
                'status': 'success',
                'topic': topic,
                'payload': payload
            })
            
        except Exception as e:
            logger.error(f"[HTTP Error /publish] {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 400
    
    # その他のエンドポイント...
    
    return app
```

---

### 6. 設定管理 (`config.py`)

```python
"""
設定管理
環境変数から設定を読み込み
"""

import os
from dotenv import load_dotenv

# .envファイル読み込み
load_dotenv()

class Config:
    """設定クラス"""
    
    # === デバイスハブ設定 ===
    DEVICE_HUB_ID = os.getenv("DEVICE_HUB_ID", "DH001")
    DEVICE_HUB_NAME = os.getenv("DEVICE_HUB_NAME", "RaspberryPi-Hub-001")
    SESSION_ID = os.getenv("SESSION_ID", "DH001")
    LOCAL_SERVER_PORT = int(os.getenv("LOCAL_SERVER_PORT", 5000))
    
    # === MQTT設定 ===
    MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
    MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
    
    # === Cloud Run API設定 ===
    # 注意: 実際の値は .env ファイルに記載してください
    CLOUD_RUN_API_URL = os.getenv(
        "CLOUD_RUN_API_URL",
        "https://your-backend-api.run.app"  # プレースホルダー
    )
    CLOUD_RUN_WS_URL = os.getenv(
        "CLOUD_RUN_WS_URL",
        "wss://your-backend-api.run.app"  # プレースホルダー
    )
    
    # === ログ設定 ===
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "data/communication_logs/rpi_server.log")
    COMMUNICATION_LOG_FILE = os.getenv(
        "COMMUNICATION_LOG_FILE",
        "data/communication_logs/api_communication.log"
    )
    ENABLE_DETAILED_LOGGING = os.getenv("ENABLE_DETAILED_LOGGING", "true").lower() == "true"
    
    # === 同期精度設定 ===
    SYNC_TOLERANCE_MS = int(os.getenv("SYNC_TOLERANCE_MS", 100))
    TIME_LOOKUP_BUFFER_MS = int(os.getenv("TIME_LOOKUP_BUFFER_MS", 50))
    
    # === デバッグモード ===
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
```

---

## 📝 実装フェーズ

### Phase 1: 基盤構築（Week 1-2）

**目標**: ディレクトリ構造作成・既存コード移植

1. ✅ `hardware/rpi_server` ディレクトリ作成
2. ✅ `legacy/` に既存コード（4DXHOME）をコピー
3. ✅ `src/` ディレクトリ構造作成
4. ✅ `config.py`, `.env.example` 作成
5. ✅ `requirements.txt` 作成（依存パッケージ整理）

**成果物**:
- ディレクトリ構造完成
- 既存コード保全

---

### Phase 2: MQTT制御レイヤー実装（Week 3-4）

**目標**: 既存MQTT制御ロジックの移植・モジュール化

1. ✅ `src/mqtt/broker.py` 実装
   - 4DXHOME の MQTT接続ロジック移植
   - ハートビート監視機能統合

2. ✅ `src/mqtt/event_mapper.py` 実装
   - 4DXHOME の `event_map` 移植
   - イベント→MQTTコマンド変換関数作成

3. ✅ `src/mqtt/device_manager.py` 実装
   - ESP デバイス状態管理
   - オンライン/オフライン検出

4. ✅ テスト実施
   - ESP デバイス接続テスト
   - 手動制御UI (`controller.html`) 動作確認

**成果物**:
- MQTT制御機能完成
- 既存ハードウェアとの互換性確認

---

### Phase 3: Cloud Run API連携実装（Week 5-6）

**目標**: WebSocket通信機能の統合

1. ✅ `src/api/websocket_client.py` 実装
   - debug_hardware の WebSocketクライアントをベースに改良
   - 自動再接続ロジック追加

2. ✅ `src/api/message_handler.py` 実装
   - タイムライン受信処理
   - 同期メッセージ処理
   - Ping/Pong処理

3. ✅ テスト実施
   - Cloud Run APIとの接続テスト
   - タイムライン受信テスト
   - 500ms同期テスト

**成果物**:
- WebSocket通信機能完成
- Cloud Run API統合確認

---

### Phase 4: タイムライン処理実装（Week 7-8）

**目標**: タイムライン解析・同期処理の統合

1. ✅ `src/timeline/processor.py` 実装
   - タイムラインJSON解析
   - 時間照合ロジック（±100ms許容範囲）
   - イベント実行制御

2. ✅ `src/timeline/cache_manager.py` 実装
   - タイムラインキャッシュ管理
   - ファイル保存・読み込み

3. ✅ テスト実施
   - タイムライン処理精度検証
   - 同期遅延測定（目標: ±100ms以内）

**成果物**:
- タイムライン処理機能完成
- 同期精度検証完了

---

### Phase 5: HTTPサーバー実装（Week 9-10）

**目標**: Flask監視UI・REST APIの統合

1. ✅ `src/server/app.py` 実装
   - Flaskアプリケーション作成
   - REST APIエンドポイント実装
   - Socket.IO統合

2. ✅ `templates/` 実装
   - 監視ダッシュボード（`index.html`）
   - 手動制御UI（`controller.html`）
   - タイムライン再生UI（`timeline_player.html`）

3. ✅ `static/` 実装
   - CSS/JavaScriptファイル配置

**成果物**:
- Flask監視UI完成
- REST API完成

---

### Phase 6: 統合テスト（Week 11-12）

**目標**: 全機能統合・エンドツーエンドテスト

1. ✅ `main.py` 実装
   - アプリケーション起動制御
   - シグナルハンドリング
   - エラーハンドリング

2. ✅ 統合テスト実施
   - フロントエンド → API → RaspberryPi → ESP デバイス
   - タイムライン送信→同期→エフェクト実行
   - エラーリカバリーテスト

3. ✅ ドキュメント作成
   - README.md
   - セットアップ手順書
   - トラブルシューティングガイド

**成果物**:
- 完全動作するシステム
- ドキュメント完成

---

### Phase 7: デプロイ・運用準備（Week 13-14）

**目標**: Raspberry Pi実機デプロイ・systemdサービス化

1. ✅ `scripts/install_dependencies.sh` 作成
   - 依存パッケージ自動インストール

2. ✅ `scripts/setup_systemd.sh` 作成
   - systemdサービス登録
   - 自動起動設定

3. ✅ 実機デプロイテスト
   - Raspberry Pi実機で動作確認
   - パフォーマンス測定

**成果物**:
- 本番運用可能なシステム
- systemdサービス化完了

---

## 🔍 既存コードとの互換性

### ハードウェアエンジニアの作業継続

1. **既存システムの保持**
   - `legacy/mqtt_server.py` で従来のMQTT制御を継続可能
   - `legacy/controller.html` で手動制御UI継続使用可能
   - ESP デバイス側のコード変更不要

2. **段階的移行**
   - 統合サーバー（`main.py`）起動時も、`legacy/mqtt_server.py` 併用可能
   - MQTTブローカーは共有（ポート1883）
   - 徐々に機能を新サーバーへ移行

3. **デバッグ支援**
   - 監視ダッシュボードで通信状況可視化
   - 通信ログで詳細トレース
   - エラー発生時の原因特定が容易

---

## 🎯 成功基準

### 機能要件
- ✅ Cloud Run APIとのWebSocket常時接続確立
- ✅ タイムラインJSON受信・解析・キャッシュ
- ✅ 500ms間隔の再生時間同期処理
- ✅ ±100ms以内の同期精度達成
- ✅ 既存MQTT制御機能の完全互換

### 非機能要件
- ✅ Raspberry Pi 3 Model B で安定動作
- ✅ メモリ使用量 < 256MB
- ✅ CPU使用率 < 50%（通常時）
- ✅ 自動再接続機能（WebSocket/MQTT）
- ✅ systemdによる自動起動

### 運用要件
- ✅ セットアップ30分以内
- ✅ ログファイルローテーション
- ✅ エラー通知機能
- ✅ リモート監視可能

---

## 📚 参考資料

### 既存コード
- `4DXHOME/mqtt_server.py` - MQTTサーバー実装
- `4DXHOME/controller.html` - 手動制御UI
- `4DXHOME/timeline_player.html` - タイムライン再生UI
- `debug_hardware/app.py` - Flask監視サーバー
- `debug_hardware/websocket_client.py` - WebSocketクライアント
- `debug_hardware/timeline_processor.py` - タイムライン処理

### ドキュメント
- `docs/backend-report/requirements-definition.md` - 要件定義書
- `debug_hardware/README.md` - デバッグ環境ドキュメント
- `backend/debug/RASPBERRY_PI_SETUP.md` - Raspberry Piセットアップガイド

---

## ⚠️ 注意事項

### セキュリティ
- ❗ `.env` ファイルは `.gitignore` に追加（機密情報保護）
- ❗ Cloud Run API URLは環境変数管理
- ❗ MQTTブローカーは外部公開しない（ローカルホストのみ）

### パフォーマンス
- ❗ タイムライン処理は非同期実行（asyncio）
- ❗ MQTT発行は並列化しない（デバイス負荷考慮）
- ❗ ログファイルサイズ監視（自動ローテーション）

### 互換性
- ❗ Python 3.9+ 必須
- ❗ Raspberry Pi OS（旧Raspbian）推奨
- ❗ mosquitto MQTT Broker 必須

---

## 📞 サポート

### 問題発生時の連絡先
- **APIサーバーエンジニア**: Cloud Run API関連
- **ハードウェアエンジニア**: ESP デバイス・MQTT関連
- **フロントエンドエンジニア**: WebSocket通信関連

### デバッグ手順
1. ログファイル確認（`data/communication_logs/`）
2. 監視ダッシュボードで接続状態確認（`http://localhost:5000`）
3. MQTTブローカー動作確認（`mosquitto_sub -t "#"`）
4. Cloud Run API接続確認（`curl` コマンド）

---

## 📅 次のステップ

この実装計画書を確認後、以下の手順で進めます：

1. **計画承認**: ハードウェアエンジニアとレビュー
2. **Phase 1実施**: ディレクトリ構造作成・既存コード移植
3. **週次レビュー**: 進捗確認・問題解決
4. **Phase 6完了後**: 統合デモ実施

---

**実装開始準備完了！** 🚀

この計画に基づき、段階的に実装を進めていきます。
既存のハードウェアエンジニアの作業を妨げることなく、新機能を追加していきます。
