#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4DX@HOME PC用デバッグ版 - Windows/macOS対応
raspberry-pi-cloudrun.py のPC版。ハードウェア制御をモック化してデバッグ可能

実際のGPIO/Serial/MQTT処理を仮想化し、ログ出力でエフェクト動作を確認
ハードウェアロジックは完全に保持、通信部分も同じ
"""

import json
import asyncio
import websockets
import ssl
import time
import threading
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import logging
import traceback
import platform
import sys

# --- PC環境での設定 ---
PC_DEBUG_MODE = True
SYSTEM_INFO = {
    "platform": platform.system(),
    "python_version": platform.python_version(),
    "machine": platform.machine()
}

# --- モックハードウェアクラス ---

class MockMQTTClient:
    """モックMQTTクライアント（デバッグ用）"""
    def __init__(self, client_id):
        self.client_id = client_id
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
    def connect(self, host, port, timeout):
        self.logger.info(f"🔶 [MOCK MQTT] 接続シミュレーション: {host}:{port}")
        time.sleep(0.1)  # 接続遅延シミュレーション
        self.is_connected = True
        # on_connect callback をシミュレーション
        if hasattr(self, 'on_connect'):
            self.on_connect(self, None, None, 0)
    
    def loop_start(self):
        self.logger.debug("🔶 [MOCK MQTT] ループ開始")
        
    def loop_stop(self):
        self.logger.debug("🔶 [MOCK MQTT] ループ停止")
        
    def disconnect(self):
        self.logger.info("🔶 [MOCK MQTT] 切断シミュレーション")
        self.is_connected = False
        
    def publish(self, topic, payload, qos=0):
        self.logger.info(f"📤 [MOCK MQTT] 送信: {topic} -> {payload} (QoS: {qos})")

class MockSerialConnection:
    """モックシリアル接続（デバッグ用）"""
    def __init__(self, port, baud_rate, timeout=1):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.is_open = True
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🔶 [MOCK SERIAL] 接続シミュレーション: {port} @ {baud_rate}bps")
        
    def write(self, data):
        command = data.decode('utf-8').strip()
        self.logger.info(f"📤 [MOCK SERIAL] 送信: {self.port} -> {command}")
        time.sleep(0.01)  # 送信遅延シミュレーション
        
    def close(self):
        self.logger.info(f"🔶 [MOCK SERIAL] 切断: {self.port}")
        self.is_open = False

# --- 設定クラス ---
@dataclass  
class Config:
    """システム設定（PC版）"""
    # CloudRun WebSocket設定
    api_base_url: str = "https://fourdk-backend-333203798555.asia-northeast1.run.app/api"
    ws_base_url: str = "wss://fourdk-backend-333203798555.asia-northeast1.run.app"
    
    # デバイス設定
    product_code: str = "PC_DBG"  # PC版識別子
    session_id: str = "pc_debug_session"
    
    # モックハードウェア設定
    serial_ports: Dict[str, str] = None
    mqtt_host: str = "mock_mqtt_broker"
    mqtt_port: int = 1883
    mqtt_client_id: str = "pc_debug_controller"
    
    # パフォーマンス設定
    max_workers: int = 10
    connect_timeout: int = 10
    reconnect_max_attempts: int = 10
    ping_interval: int = 20
    
    def __post_init__(self):
        if self.serial_ports is None:
            self.serial_ports = {
                'wind': 'COM_MOCK_WIND',
                'water': 'COM_MOCK_WATER',
                'flash': 'COM_MOCK_FLASH'
            }

# --- ハードウェア制御クラス（モック対応版） ---

class VibrationController:
    """MQTT経由で振動を制御するクラス（PC版モック対応）"""
    def __init__(self, config: Config):
        self.config = config
        self.is_connected = False
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # PC環境ではモックMQTTクライアント使用
        self.client = MockMQTTClient(config.mqtt_client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        self.logger.info(f"🔶 [PC VIBRATION] モック初期化: {config.mqtt_host}:{config.mqtt_port}")
        self.client.connect(config.mqtt_host, config.mqtt_port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("✅ [PC VIBRATION] モックMQTT接続成功")
            self.is_connected = True
        else:
            self.logger.error(f"❌ [PC VIBRATION] モック接続失敗: {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.logger.warning("⚠️ [PC VIBRATION] モックMQTT切断")
        self.is_connected = False

    def control(self, mode: str, state: str):
        """振動制御（モック版 - 視覚的フィードバック付き）"""
        with self.lock:
            # 元コードのMQTTトピック選択ロジック保持
            mqtt_topics = {
                'heart': '/vibration/heart',
                'all': '/vibration/all',
                'off': '/vibration/off'
            }
            
            topic = None
            visual_feedback = ""
            
            if state == 'off':
                topic = mqtt_topics['off']
                visual_feedback = "⭕ 振動停止"
            elif mode == 'heartbeat':
                topic = mqtt_topics['heart'] 
                visual_feedback = "💓 ハートビート振動"
            elif mode in ['strong', 'long']:
                topic = mqtt_topics['all']
                visual_feedback = f"🟡 強振動 ({mode})"

            if topic:
                self.client.publish(topic, "", qos=1)
                self.logger.info(f"🎮 [VIBRATION] {visual_feedback} -> {topic}")

    def stop(self):
        if hasattr(self, 'client'):
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.info("🔶 [PC VIBRATION] モック停止")

class SerialController:
    """シリアル通信制御クラス（PC版モック対応）"""
    def __init__(self, config: Config):
        self.config = config
        self.connections = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

        self.logger.info("🔶 [PC SERIAL] モック初期化開始")
        
        # モック接続を作成
        for device, port_name in config.serial_ports.items():
            try:
                self.connections[device] = MockSerialConnection(port_name, 9600, timeout=1)
                self.logger.info(f"✅ [PC SERIAL] モック接続成功: {device} -> {port_name}")
                time.sleep(0.5)  # Arduino起動シミュレーション
            except Exception as e:
                self.logger.error(f"❌ [PC SERIAL] モック接続失敗 {device}: {e}")
                self.connections[device] = None

    def send_command(self, device: str, command: str):
        """シリアルコマンド送信（モック版 - 視覚的フィードバック付き）"""
        with self.lock:
            connection = self.connections.get(device)
            if not connection or not connection.is_open:
                self.logger.warning(f"⚠️ [PC SERIAL] 接続なし: {device}")
                return

            # 視覚的フィードバック生成
            visual_feedback = self._get_visual_feedback(device, command)
            
            try:
                connection.write((command + '\n').encode('utf-8'))
                self.logger.info(f"🎮 [{device.upper()}] {visual_feedback} -> {command}")
            except Exception as e:
                self.logger.error(f"❌ [PC SERIAL] 送信エラー {device}: {e}")

    def _get_visual_feedback(self, device: str, command: str) -> str:
        """コマンドに応じた視覚的フィードバック生成"""
        if device == 'wind':
            return "🌪️ 風ON" if command == "ON" else "⭕ 風OFF"
        elif device == 'water':
            return "💦 水しぶき" if command == "SPLASH" else f"💧 {command}"
        elif device == 'flash':
            if command == "OFF":
                return "⭕ フラッシュOFF"
            elif "FLASH" in command:
                return f"⚡ フラッシュ {command}"
            elif "COLOR" in command:
                return f"🌈 カラー {command}"
            elif command == "ON":
                return "💡 照明ON"
        return f"📡 {command}"

    def stop_all(self):
        with self.lock:
            for device, connection in self.connections.items():
                if connection and connection.is_open:
                    self.logger.info(f"🔶 [PC SERIAL] モック切断: {device}")
                    connection.close()

class TimelinePlayer:
    """タイムライン管理・ハードウェア制御クラス（PC版 - ロジック完全保持）"""
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
        """タイムライン設定（元コードロジック完全保持）"""
        with self.lock:
            self.timeline_events = sorted(events, key=lambda x: x.get('t', 0))
            self.prev_time = -1.0
            self.build_effects_map()
            self.executor.submit(self.reset_all_effects)
            
            # PC版専用: タイムライン概要表示
            duration = max(e.get('t', 0) for e in events) if events else 0
            effect_types = set(e.get('effect') for e in events if e.get('effect'))
            
            self.logger.info(f"🗓️ [PC TIMELINE] 新タイムライン: {len(events)}イベント, {duration:.1f}秒, エフェクト種類: {effect_types}")

    def build_effects_map(self):
        """エフェクトマップ構築（元コードロジック完全保持）"""
        self.effects_map.clear()
        start_events = [e for e in self.timeline_events if e.get('action') == 'start']
        
        for start_event in start_events:
            key = (start_event.get('effect'), start_event.get('mode'))
            start_time = start_event.get('t', 0.0)
            end_time = float('inf')
            
            # 対応するstopイベントを検索
            for stop_event in self.timeline_events:
                if (stop_event.get('t', 0.0) > start_time and
                    stop_event.get('action') == 'stop' and
                    stop_event.get('effect') == key[0] and
                    stop_event.get('mode') == key[1]):
                    end_time = stop_event.get('t', 0.0)
                    break
                    
            self.effects_map.append({'key': key, 'start': start_time, 'end': end_time})

        # PC版専用: エフェクトマップ表示
        self.logger.debug(f"🔧 [PC TIMELINE] エフェクトマップ: {len(self.effects_map)}区間")

    def update_to_time(self, current_time: float):
        """時刻更新処理（元コードロジック完全保持 + PC拡張ログ）"""
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
                self.logger.info(f"▶️ [PC PLAYER] {current_time:.2f}s: 開始 {effect}/{mode}")
                self.executor.submit(self.control_effect, effect, mode, 'on')

            # エフェクト停止処理
            effects_to_stop = self.active_continuous_effects - target_continuous_effects
            for effect, mode in effects_to_stop:
                self.logger.info(f"🛑 [PC PLAYER] {current_time:.2f}s: 停止 {effect}/{mode}")
                self.executor.submit(self.control_effect, effect, mode, 'off')
            
            self.active_continuous_effects = target_continuous_effects

            # 色制御
            if target_color != self.active_color:
                if target_color:
                    self.logger.info(f"🎨 [PC PLAYER] {current_time:.2f}s: 色変更 -> {target_color}")
                    self.executor.submit(self.control_effect, 'color', target_color, 'on')
                else:
                    self.logger.info(f"⚫ [PC PLAYER] {current_time:.2f}s: 色OFF")
                    self.executor.submit(self.control_effect, 'color', self.active_color, 'off')
                self.active_color = target_color

            # ショットエフェクト処理（元コードロジック）
            if current_time > self.prev_time:
                for event in self.timeline_events:
                    if event.get('action') == 'shot':
                        event_time = event.get('t', 0.0)
                        if self.prev_time < event_time <= current_time:
                            self.logger.info(f"💥 [PC PLAYER] {current_time:.2f}s: ショット {event.get('effect')}/{event.get('mode')}")
                            self.executor.submit(self.control_effect, event.get('effect'), event.get('mode'), 'on')

            self.prev_time = current_time

    def control_effect(self, effect: str, mode: str, state: str):
        """エフェクト制御（元コードロジック完全保持）"""
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
            command = "COLOR 0 0 0"  # デフォルト: 消灯
            if state == 'on':
                if mode == 'red':
                    command = "COLOR 255 0 0"
                elif mode == 'blue':
                    command = "COLOR 0 0 255"
                elif mode == 'green':
                    command = "COLOR 0 255 0"
            self.serial_controller.send_command('flash', command)

    def reset_all_effects(self):
        """全エフェクトリセット（元コードロジック完全保持）"""
        with self.lock:
            self.logger.info("🔄 [PC PLAYER] 全エフェクトリセット...")
            self.executor.submit(self.vibration_controller.control, None, 'off')
            self.executor.submit(self.serial_controller.send_command, 'wind', 'OFF')
            self.executor.submit(self.serial_controller.send_command, 'flash', 'OFF')
            self.executor.submit(self.serial_controller.send_command, 'flash', 'COLOR 0 0 0')
            self.active_continuous_effects.clear()
            self.active_color = None
            self.prev_time = -1.0

# --- WebSocket通信クラス（ラズパイ版と同じ） ---

class CloudRunWebSocketClient:
    """CloudRun WebSocket通信クライアント（PC版）"""
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
        self.logger.info(f"🚀 4DX@HOME PC Client Starting: session={self.config.session_id}")
        self.logger.info(f"🔧 System: {SYSTEM_INFO}")
        
        try:
            if not await self.register_device():
                self.logger.error("❌ デバイス登録失敗")
                return
            
            await self.connect_websocket()
            
        except KeyboardInterrupt:
            self.logger.info("\n⏹️ 停止要求を受信しました")
        except Exception as e:
            self.logger.error(f"❌ クライアント開始エラー: {e}")
            self.logger.debug(traceback.format_exc())

    async def register_device(self) -> bool:
        """デバイス登録（PC版識別情報付き）"""
        import aiohttp
        
        registration_data = {
            "product_code": self.config.product_code,
            "capabilities": ["VIBRATION", "WATER", "WIND", "FLASH", "COLOR"],
            "device_info": {
                "platform": f"pc_debug_{SYSTEM_INFO['platform'].lower()}",
                "os_version": f"{SYSTEM_INFO['platform']} {platform.release()}",
                "hardware_version": "debug_1.0.0",
                "python_version": SYSTEM_INFO['python_version']
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config.api_base_url}/device-registration"
                async with session.post(url, json=registration_data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.device_id = result.get("device_id")
                        self.logger.info(f"✅ PC版デバイス登録成功: device_id={self.device_id}")
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
            
            self.logger.info("✅ PC版WebSocket接続成功")
            
            await self._send_device_status()
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
        """受信メッセージ処理（ラズパイ版と同じロジック + PC拡張ログ）"""
        message_type = data.get("type")
        self.logger.debug(f"📨 [PC CLIENT] メッセージ受信: {message_type}")
        
        if message_type == "device_connected":
            self.logger.info(f"🤝 [PC CLIENT] デバイス接続確認: {data.get('message', '')}")
            
        elif message_type == "sync_data_bulk_transmission":
            await self._handle_bulk_sync_data(data)
            
        elif message_type == "sync_relay":
            await self._handle_sync_relay(data)
            
        elif message_type == "currentTime":
            await self._handle_current_time(data)
            
        else:
            self.logger.debug(f"📨 [PC CLIENT] 未処理メッセージ: {message_type}")

    async def _handle_bulk_sync_data(self, data: Dict[str, Any]):
        """JSON同期データ一括処理"""
        sync_data = data.get("sync_data", {})
        video_id = data.get("video_id")
        session_id = data.get("session_id")
        
        self.logger.info(f"📥 [PC CLIENT] JSON同期データ受信: {video_id}")
        
        events = sync_data.get("events", [])
        if events:
            self.timeline_player.set_timeline(events)
            self.logger.info(f"✅ [PC CLIENT] タイムライン設定完了: {len(events)}イベント")
            
        await self._send_bulk_reception_confirmation(session_id, video_id, sync_data)

    async def _handle_sync_relay(self, data: Dict[str, Any]):
        """リアルタイム同期処理"""
        sync_data = data.get("sync_data", {})
        session_id = data.get("session_id")
        
        state = sync_data.get("state")
        time_pos = sync_data.get("time", 0.0)
        duration = sync_data.get("duration", 0.0)
        
        self.logger.info(f"🎬 [PC CLIENT] 同期信号: {state} at {time_pos:.3f}s / {duration:.1f}s")
        
        if state == "play":
            self.timeline_player.update_to_time(time_pos)
        elif state in ["pause", "stop"]:
            self.timeline_player.reset_all_effects()
        
        await self._send_sync_acknowledgment(session_id, sync_data)

    async def _handle_current_time(self, data: Dict[str, Any]):
        """連続時間同期処理"""
        current_time = data.get("currentTime", 0.0)
        is_playing = data.get("is_playing", False)
        events = data.get("events", [])
        
        self.logger.debug(f"⏰ [PC CLIENT] 時間更新: {current_time:.2f}s, playing={is_playing}, events={len(events)}")
        
        if is_playing:
            self.timeline_player.update_to_time(current_time)
        else:
            self.timeline_player.reset_all_effects()

    async def _send_device_status(self):
        """デバイス状態送信（PC版情報付き）"""
        if not self.websocket or not self.device_id:
            return
            
        status_message = {
            "type": "device_status",
            "device_id": self.device_id,
            "status": "ready",
            "debug_mode": "pc_debug",
            "actuator_status": {
                "VIBRATION": "mock_ready",
                "WATER": "mock_ready",
                "WIND": "mock_ready", 
                "FLASH": "mock_ready",
                "COLOR": "mock_ready"
            },
            "system_info": SYSTEM_INFO,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self.websocket.send(json.dumps(status_message))
            self.logger.info(f"📤 [PC CLIENT] デバイス状態送信: PC Debug Ready")
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
                "debug_mode": "pc_mock",
                "reception_timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            await self.websocket.send(json.dumps(confirmation))
            self.logger.info(f"📤 [PC CLIENT] JSON受信確認送信: {video_id}")
        except Exception as e:
            self.logger.error(f"❌ JSON受信確認エラー: {e}")

    async def _send_sync_acknowledgment(self, session_id: str, sync_data: Dict):
        """同期確認送信"""
        ack_message = {
            "type": "sync_ack",
            "session_id": session_id,
            "received_time": sync_data.get("time", 0.0),
            "received_state": sync_data.get("state"),
            "processing_delay_ms": 5,  # PC版は高速
            "debug_mode": "pc_mock"
        }
        
        try:
            await self.websocket.send(json.dumps(ack_message))
            self.logger.debug(f"📤 [PC CLIENT] 同期確認送信")
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
        
        self.logger.info(f"🔄 [PC CLIENT] 再接続 {self.reconnect_attempts}/{self.config.reconnect_max_attempts} in {delay}s")
        await asyncio.sleep(delay)

    def stop(self):
        """クライアント停止"""
        self.logger.info("🛑 [PC CLIENT] クライアント停止要求")
        self.should_reconnect = False
        self.is_running = False

# --- メインアプリケーション ---

class FourDXPCDebugApp:
    """4DX@HOME PC用デバッグアプリケーション"""
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()
        
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # モックハードウェアコントローラー
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
        """PC版ログ設定（詳細表示）"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 [PC DEBUG] ログ設定完了 - {SYSTEM_INFO}")
        return logger

    async def start(self):
        """アプリケーション開始"""
        self.logger.info("🚀 4DX@HOME PC Debug App Starting...")
        self.logger.info("💡 ヒント: Ctrl+C で停止")
        
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
        self.logger.info("🧹 [PC DEBUG] クリーンアップ開始...")
        
        self.ws_client.stop()
        self.timeline_player.reset_all_effects()
        self.serial_controller.stop_all()
        self.vibration_controller.stop()
        self.executor.shutdown(wait=True)
        
        self.logger.info("✅ [PC DEBUG] クリーンアップ完了")

# --- エントリーポイント ---

async def main():
    """メイン関数"""
    print("🔧 4DX@HOME PC Debug Version")
    print("=" * 50)
    
    # セッションIDをコマンドライン引数から取得
    session_id = sys.argv[1] if len(sys.argv) > 1 else "pc_debug_session"
    
    config = Config(session_id=session_id)
    app = FourDXPCDebugApp(config)
    
    await app.start()

if __name__ == '__main__':
    asyncio.run(main())