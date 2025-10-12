#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4DX@HOME ラズベリーパイ CloudRun対応版
既存のハードウェア制御ロジックを尊重しつつ、WebSocket通信でCloudRunと連携

Original socket-based design → WebSocket + CloudRun integration
Hardware control logic preserved from rasberry-pi-code.py
"""

import json
import asyncio
import websockets
import ssl
import time
import threading
import subprocess
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import logging
import traceback

# ハードウェア制御ライブラリ（Raspberry Pi環境）
try:
    import paho.mqtt.client as mqtt
    import serial
    import RPi.GPIO as GPIO
    RASPBERRY_PI_MODE = True
except ImportError:
    # PC環境での開発時はモック
    print("⚠️ ハードウェアライブラリが見つかりません。モックモードで動作します。")
    RASPBERRY_PI_MODE = False

# --- 設定クラス ---
@dataclass
class Config:
    """システム設定"""
    # CloudRun WebSocket設定
    api_base_url: str = "https://fourdk-backend-333203798555.asia-northeast1.run.app/api"
    ws_base_url: str = "wss://fourdk-backend-333203798555.asia-northeast1.run.app"
    
    # デバイス設定
    product_code: str = "RPI001"  # 6文字以内
    session_id: str = "default_session"
    
    # ハードウェア設定（元コード準拠）
    serial_ports: Dict[str, str] = None
    mqtt_host: str = "172.18.28.55"
    mqtt_port: int = 1883
    mqtt_client_id: str = "raspberrypi_controller"
    
    # パフォーマンス設定
    max_workers: int = 10
    connect_timeout: int = 10
    reconnect_max_attempts: int = 10
    ping_interval: int = 20
    
    def __post_init__(self):
        if self.serial_ports is None:
            self.serial_ports = {
                'wind': '/dev/ttyACM2',
                'water': '/dev/ttyACM0', 
                'flash': '/dev/ttyACM1'
            }

# --- ハードウェア制御クラス（元コード保持） ---

class VibrationController:
    """MQTT経由で振動を制御するクラス（元コードベース）"""
    def __init__(self, config: Config):
        self.config = config
        self.is_connected = False
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        if not RASPBERRY_PI_MODE:
            self.logger.warning("🔶 VibrationController: モックモード")
            self.is_connected = True
            return
            
        try:
            self.client = mqtt.Client(
                client_id=config.mqtt_client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1
            )
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            
            self.logger.info(f"[MQTT] Connecting to broker at {config.mqtt_host}:{config.mqtt_port}...")
            self.client.connect(config.mqtt_host, config.mqtt_port, 60)
            self.client.loop_start()
        except Exception as e:
            self.logger.error(f"❌ [MQTT] Connection failed: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("✅ [MQTT] Broker connected successfully.")
            self.is_connected = True
        else:
            self.logger.error(f"❌ [MQTT] Connection failed. Return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.logger.warning("⚠️ [MQTT] Disconnected from broker.")
        self.is_connected = False

    def control(self, mode: str, state: str):
        """振動制御（元コードロジック保持）"""
        with self.lock:
            if not RASPBERRY_PI_MODE:
                self.logger.debug(f"🔶 [VIBRATION] Mock: {mode} -> {state}")
                return
                
            if not self.is_connected:
                return

            # 元コードのMQTTトピック選択ロジック
            mqtt_topics = {
                'heart': '/vibration/heart',
                'all': '/vibration/all', 
                'off': '/vibration/off'
            }
            
            topic = None
            if state == 'off':
                topic = mqtt_topics['off']
            elif mode == 'heartbeat':
                topic = mqtt_topics['heart']
            elif mode in ['strong', 'long']:
                topic = mqtt_topics['all']

            if topic:
                self.client.publish(topic, "", qos=1)
                self.logger.debug(f"📤 [MQTT] Published: {topic}")

    def stop(self):
        if RASPBERRY_PI_MODE and hasattr(self, 'client'):
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.info("[MQTT] Connection closed.")

class SerialController:
    """pyserialを使用してシリアルポートを制御するクラス（元コードベース）"""
    def __init__(self, config: Config):
        self.config = config
        self.connections = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

        if not RASPBERRY_PI_MODE:
            self.logger.warning("🔶 SerialController: モックモード")
            # モック接続を作成
            for device in config.serial_ports.keys():
                self.connections[device] = "mock_connection"
            return

        for device, port_name in config.serial_ports.items():
            try:
                self.connections[device] = serial.Serial(port_name, 9600, timeout=1)
                self.logger.info(f"✅ [Serial] Connected to {device} on {port_name}")
                time.sleep(2)  # Arduinoのリセットを待つ
            except Exception as e:
                self.logger.error(f"❌ [Serial] FAILED to connect to {device} on {port_name}: {e}")
                self.connections[device] = None

    def send_command(self, device: str, command: str):
        """シリアルコマンド送信（元コードロジック保持）"""
        with self.lock:
            if not RASPBERRY_PI_MODE:
                self.logger.debug(f"🔶 [SERIAL] Mock: {device} -> {command}")
                return
                
            connection = self.connections.get(device)
            if not (connection and hasattr(connection, 'is_open') and connection.is_open):
                return

            try:
                line_to_send = (command + '\n').encode('utf-8')
                connection.write(line_to_send)
                self.logger.debug(f"📤 [Serial] Sent to '{device}': {command}")
            except Exception as e:
                self.logger.error(f"❌ [Serial] Error writing to {device}: {e}")

    def stop_all(self):
        with self.lock:
            for device, connection in self.connections.items():
                if RASPBERRY_PI_MODE and connection and hasattr(connection, 'is_open') and connection.is_open:
                    self.logger.info(f"🔌 [Serial] Closing connection to {device}")
                    connection.close()

class TimelinePlayer:
    """タイムラインを管理し、ハードウェアを並列制御するクラス（元コードロジック保持）"""
    def __init__(self, vibration_controller: VibrationController, serial_controller: SerialController, executor: ThreadPoolExecutor):
        self.vibration_controller = vibration_controller
        self.serial_controller = serial_controller
        self.executor = executor
        self.timeline_events = []
        self.effects_map = []
        self.active_continuous_effects = set()
        self.active_color = None
        self.prev_time = -1.0
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def set_timeline(self, events: List[Dict]):
        """タイムライン設定（元コードロジック保持）"""
        with self.lock:
            self.timeline_events = sorted(events, key=lambda x: x.get('t', 0))
            self.prev_time = -1.0
            self.build_effects_map()
            self.executor.submit(self.reset_all_effects)
            self.logger.info(f"🗓️ [Player] New timeline received with {len(self.timeline_events)} events.")

    def build_effects_map(self):
        """エフェクトマップ構築（元コードロジック保持）"""
        self.effects_map.clear()
        start_events = [e for e in self.timeline_events if e.get('action') == 'start']
        for start_event in start_events:
            key = (start_event.get('effect'), start_event.get('mode'))
            start_time = start_event.get('t', 0.0)
            end_time = float('inf')
            for stop_event in self.timeline_events:
                if stop_event.get('t', 0.0) > start_time and \
                   stop_event.get('action') == 'stop' and \
                   stop_event.get('effect') == key[0] and \
                   stop_event.get('mode') == key[1]:
                    end_time = stop_event.get('t', 0.0)
                    break
            self.effects_map.append({'key': key, 'start': start_time, 'end': end_time})

    def update_to_time(self, current_time: float):
        """時刻更新処理（元コードロジック保持）"""
        with self.lock:
            if not self.timeline_events:
                return

            # 連続エフェクトの状態管理（元コードロジック）
            target_continuous_effects = set()
            target_color = None
            for interval in self.effects_map:
                effect, mode = interval['key']
                if interval['start'] <= current_time < interval['end']:
                    if effect == 'color':
                        target_color = mode
                    else:
                        target_continuous_effects.add(interval['key'])

            # エフェクト開始処理
            effects_to_start = target_continuous_effects - self.active_continuous_effects
            for effect, mode in effects_to_start:
                self.logger.info(f"▶️ [Player] At {current_time:.2f}s: Starting {effect}/{mode}")
                self.executor.submit(self.control_effect, effect, mode, 'on')

            # エフェクト停止処理
            effects_to_stop = self.active_continuous_effects - target_continuous_effects
            for effect, mode in effects_to_stop:
                self.logger.info(f"🛑 [Player] At {current_time:.2f}s: Stopping {effect}/{mode}")
                self.executor.submit(self.control_effect, effect, mode, 'off')
            
            self.active_continuous_effects = target_continuous_effects

            # 色制御
            if target_color != self.active_color:
                if target_color:
                    self.logger.info(f"🎨 [Player] At {current_time:.2f}s: Color -> {target_color}")
                    self.executor.submit(self.control_effect, 'color', target_color, 'on')
                else:
                    self.logger.info(f"⚫ [Player] At {current_time:.2f}s: Color -> OFF")
                    self.executor.submit(self.control_effect, 'color', self.active_color, 'off')
                self.active_color = target_color

            # ショットエフェクト処理（元コードロジック）
            if current_time > self.prev_time:
                for event in self.timeline_events:
                    if event.get('action') == 'shot':
                        event_time = event.get('t', 0.0)
                        if self.prev_time < event_time <= current_time:
                            self.logger.info(f"💥 [Player] At {current_time:.2f}s: Shot {event.get('effect')}/{event.get('mode')}")
                            self.executor.submit(self.control_effect, event.get('effect'), event.get('mode'), 'on')

            self.prev_time = current_time

    def control_effect(self, effect: str, mode: str, state: str):
        """エフェクト制御（元コードロジック保持）"""
        if effect == 'vibration':
            self.vibration_controller.control(mode, state)
        elif effect == 'wind':
            self.serial_controller.send_command('wind', "ON" if state == 'on' else "OFF")
        elif effect == 'water' and state == 'on':
            self.serial_controller.send_command('water', "SPLASH")
        elif effect == 'flash':
            command = None
            if state == 'on':
                if mode == 'strobe':
                    command = "FLASH 15"
                elif mode == 'burst':
                    command = "FLASH 10"
                elif mode == 'steady':
                    command = "ON"
            elif state == 'off':
                command = "OFF"
            if command:
                self.serial_controller.send_command('flash', command)
        elif effect == 'color':
            command = "COLOR 0 0 0"
            if state == 'on':
                if mode == 'red':
                    command = "COLOR 255 0 0"
                elif mode == 'blue':
                    command = "COLOR 0 0 255"
                elif mode == 'green':
                    command = "COLOR 0 255 0"
            self.serial_controller.send_command('flash', command)

    def reset_all_effects(self):
        """全エフェクトリセット（元コードロジック保持）"""
        with self.lock:
            self.logger.info("🔄 [Player] Resetting all effects...")
            self.executor.submit(self.vibration_controller.control, None, 'off')
            self.executor.submit(self.serial_controller.send_command, 'wind', 'OFF')
            self.executor.submit(self.serial_controller.send_command, 'flash', 'OFF')
            self.executor.submit(self.serial_controller.send_command, 'flash', 'COLOR 0 0 0')
            self.active_continuous_effects.clear()
            self.active_color = None
            self.prev_time = -1.0

# --- WebSocket通信クラス（新規追加） ---

class CloudRunWebSocketClient:
    """CloudRun WebSocket通信クライアント"""
    def __init__(self, config: Config, timeline_player: TimelinePlayer):
        self.config = config
        self.timeline_player = timeline_player
        self.websocket = None
        self.device_id = None
        self.is_running = False
        self.should_reconnect = True
        self.reconnect_attempts = 0
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """クライアント開始"""
        self.logger.info(f"📱 4DX@HOME CloudRun Client Starting: session={self.config.session_id}")
        
        try:
            # デバイス登録
            if not await self.register_device():
                self.logger.error("❌ デバイス登録失敗")
                return
            
            # WebSocket接続開始
            await self.connect_websocket()
            
        except Exception as e:
            self.logger.error(f"❌ クライアント開始エラー: {e}")
            self.logger.debug(traceback.format_exc())

    async def register_device(self) -> bool:
        """デバイス登録（HTTP API）"""
        import aiohttp
        
        registration_data = {
            "product_code": self.config.product_code,
            "capabilities": ["VIBRATION", "WATER", "WIND", "FLASH", "COLOR"],
            "device_info": {
                "platform": "raspberry_pi_4",
                "os_version": "raspberry_pi_os_64bit",
                "hardware_version": "1.0.0"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.api_base_url}/device-registration"
                async with session.post(url, json=registration_data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.device_id = result.get("device_id")
                        self.logger.info(f"✅ デバイス登録成功: device_id={self.device_id}")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ 登録失敗: HTTP {response.status} - {error_text}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ デバイス登録エラー: {e}")
            return False

    async def connect_websocket(self):
        """WebSocket接続とメッセージループ"""
        while self.should_reconnect:
            try:
                await self._connect_websocket_once()
            except Exception as e:
                self.logger.error(f"❌ WebSocket接続エラー: {e}")
                await self._handle_reconnection()

    async def _connect_websocket_once(self):
        """単回WebSocket接続"""
        # CloudRunのdevice WebSocketエンドポイントに接続
        ws_url = f"{self.config.ws_base_url}/api/playback/ws/device/{self.config.session_id}"
        
        ssl_context = ssl.create_default_context()
        
        self.logger.info(f"🔌 WebSocket接続開始: {ws_url}")
        
        async with websockets.connect(
            ws_url,
            ssl=ssl_context,
            timeout=self.config.connect_timeout,
            ping_interval=self.config.ping_interval,
            ping_timeout=10
        ) as websocket:
            
            self.websocket = websocket
            self.is_running = True
            self.reconnect_attempts = 0
            
            self.logger.info("✅ WebSocket接続成功")
            
            # デバイス状態送信
            await self._send_device_status()
            
            # メッセージ受信ループ
            await self._message_loop()

    async def _message_loop(self):
        """メッセージ受信ループ"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    self.logger.error(f"❌ Invalid JSON: {message}")
                except Exception as e:
                    self.logger.error(f"❌ メッセージ処理エラー: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("🔌 WebSocket接続が閉じられました")
        except Exception as e:
            self.logger.error(f"❌ メッセージループエラー: {e}")

    async def _handle_message(self, data: Dict[str, Any]):
        """受信メッセージ処理"""
        message_type = data.get("type")
        
        if message_type == "device_connected":
            self.logger.info(f"🤝 デバイス接続確認: {data.get('message', '')}")
            
        elif message_type == "sync_data_bulk_transmission":
            # JSON同期データ一括受信（CloudRunから送信）
            await self._handle_bulk_sync_data(data)
            
        elif message_type == "sync_relay":
            # リアルタイム同期データ処理
            await self._handle_sync_relay(data)
            
        elif message_type == "currentTime":
            # 連続時間同期データ処理（新しいパターン）
            await self._handle_current_time(data)
            
        else:
            self.logger.debug(f"📨 未処理メッセージ: {message_type}")

    async def _handle_bulk_sync_data(self, data: Dict[str, Any]):
        """JSON同期データ一括処理"""
        sync_data = data.get("sync_data", {})
        video_id = data.get("video_id")
        session_id = data.get("session_id")
        
        self.logger.info(f"📥 JSON同期データ受信: {video_id}")
        
        # タイムラインイベント抽出・設定
        events = sync_data.get("events", [])
        if events:
            self.timeline_player.set_timeline(events)
            self.logger.info(f"✅ タイムライン設定完了: {len(events)}イベント")
            
        # 受信確認送信
        await self._send_bulk_reception_confirmation(session_id, video_id, sync_data)

    async def _handle_sync_relay(self, data: Dict[str, Any]):
        """リアルタイム同期処理（従来パターン）"""
        sync_data = data.get("sync_data", {})
        session_id = data.get("session_id")
        
        state = sync_data.get("state")
        time_pos = sync_data.get("time", 0.0)
        duration = sync_data.get("duration", 0.0)
        
        self.logger.info(f"🎬 同期信号: {state} at {time_pos:.3f}s / {duration:.1f}s")
        
        # タイムライン更新
        if state == "play":
            self.timeline_player.update_to_time(time_pos)
        elif state in ["pause", "stop"]:
            self.timeline_player.reset_all_effects()
        
        # 同期確認送信
        await self._send_sync_acknowledgment(session_id, sync_data)

    async def _handle_current_time(self, data: Dict[str, Any]):
        """連続時間同期処理（新しいパターン）"""
        current_time = data.get("currentTime", 0.0)
        is_playing = data.get("is_playing", False)
        events = data.get("events", [])
        
        self.logger.debug(f"⏰ 時間更新: {current_time:.2f}s, playing={is_playing}, events={len(events)}")
        
        if is_playing:
            self.timeline_player.update_to_time(current_time)
        else:
            self.timeline_player.reset_all_effects()

    async def _send_device_status(self):
        """デバイス状態送信"""
        if not self.websocket or not self.device_id:
            return
            
        status_message = {
            "type": "device_status",
            "device_id": self.device_id,
            "status": "ready",
            "actuator_status": {
                "VIBRATION": "ready",
                "WATER": "ready", 
                "WIND": "ready",
                "FLASH": "ready",
                "COLOR": "ready"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self.websocket.send(json.dumps(status_message))
            self.logger.info(f"📤 デバイス状態送信: ready")
        except Exception as e:
            self.logger.error(f"❌ デバイス状態送信エラー: {e}")

    async def _send_bulk_reception_confirmation(self, session_id: str, video_id: str, sync_data: Dict):
        """JSON受信確認送信"""
        confirmation = {
            "type": "sync_data_bulk_received",
            "session_id": session_id,
            "video_id": video_id,
            "reception_result": {
                "received": True,
                "events_count": len(sync_data.get("events", [])),
                "reception_timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            await self.websocket.send(json.dumps(confirmation))
            self.logger.info(f"📤 JSON受信確認送信: {video_id}")
        except Exception as e:
            self.logger.error(f"❌ JSON受信確認エラー: {e}")

    async def _send_sync_acknowledgment(self, session_id: str, sync_data: Dict):
        """同期確認送信"""
        ack_message = {
            "type": "sync_ack",
            "session_id": session_id,
            "received_time": sync_data.get("time", 0.0),
            "received_state": sync_data.get("state"),
            "processing_delay_ms": 8
        }
        
        try:
            await self.websocket.send(json.dumps(ack_message))
            self.logger.debug(f"📤 同期確認送信")
        except Exception as e:
            self.logger.error(f"❌ 同期確認送信エラー: {e}")

    async def _handle_reconnection(self):
        """再接続処理"""
        if self.reconnect_attempts >= self.config.reconnect_max_attempts:
            self.logger.error("❌ 最大再接続回数に達しました")
            self.should_reconnect = False
            return
            
        delay = min(2 ** self.reconnect_attempts, 60)
        self.reconnect_attempts += 1
        
        self.logger.info(f"🔄 再接続 {self.reconnect_attempts}/{self.config.reconnect_max_attempts} in {delay}s")
        await asyncio.sleep(delay)

    def stop(self):
        """クライアント停止"""
        self.logger.info("🛑 クライアント停止要求")
        self.should_reconnect = False
        self.is_running = False

# --- メインアプリケーション ---

class FourDXCloudRunApp:
    """4DX@HOME CloudRun対応メインアプリケーション"""
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()
        
        # ThreadPoolExecutor（元コード準拠）
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # ハードウェアコントローラー（元コードロジック保持）
        self.vibration_controller = VibrationController(config)
        self.serial_controller = SerialController(config)
        self.timeline_player = TimelinePlayer(
            self.vibration_controller, 
            self.serial_controller, 
            self.executor
        )
        
        # WebSocketクライアント
        self.ws_client = CloudRunWebSocketClient(config, self.timeline_player)

    def _setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    async def start(self):
        """アプリケーション開始"""
        self.logger.info("🚀 4DX@HOME CloudRun App Starting...")
        
        try:
            await self.ws_client.start()
        except KeyboardInterrupt:
            self.logger.info("\n⏹️ 停止要求を受信しました")
        except Exception as e:
            self.logger.error(f"❌ アプリケーションエラー: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """クリーンアップ"""
        self.logger.info("🧹 クリーンアップ開始...")
        
        self.ws_client.stop()
        self.timeline_player.reset_all_effects()
        self.serial_controller.stop_all()
        self.vibration_controller.stop()
        self.executor.shutdown(wait=True)
        
        self.logger.info("✅ クリーンアップ完了")

# --- エントリーポイント ---

async def main():
    """メイン関数"""
    import sys
    
    # セッションIDをコマンドライン引数から取得
    session_id = sys.argv[1] if len(sys.argv) > 1 else "default_session"
    
    config = Config(session_id=session_id)
    app = FourDXCloudRunApp(config)
    
    await app.start()

if __name__ == '__main__':
    asyncio.run(main())