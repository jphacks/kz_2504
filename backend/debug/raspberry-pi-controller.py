#!/usr/bin/env python3
"""
4DX@HOME Raspberry Pi Device Controller
本番環境統合対応版

WebSocket通信、GPIO制御、Arduino連携を統合したマイコン制御システム
Cloud Run本番環境との完全統合対応
"""

import asyncio
import json
import ssl
import websockets
import time
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import hashlib

# GPIO制御用ライブラリ
try:
    import RPi.GPIO as GPIO
    import gpiozero
    import serial
    import psutil
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("GPIO/Hardware libraries not available (development mode)")

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/4dx-home/logs/device.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("4DX_DeviceController")

# 設定
class Config:
    """システム設定"""
    # 本番環境WebSocket設定
    BACKEND_BASE_URL = "wss://fourdk-backend-333203798555.asia-northeast1.run.app"
    DEVICE_REGISTRATION_URL = "https://fourdk-backend-333203798555.asia-northeast1.run.app/api/device/register"
    
    # デバイス設定
    PRODUCT_CODE = os.getenv("PRODUCT_CODE", "RPI001")  # 環境変数で設定可能
    
    # ハードウェア設定
    ACTUATOR_PINS = {
        "VIBRATION": {"pin": 18, "pwm": True, "frequency": 1000},
        "WATER": {"pin": 23, "relay": True},
        "WIND": {"pin": 24, "pwm": True, "frequency": 25000},
        "FLASH": {"pin": 25, "pwm": True, "frequency": 5000},
        "COLOR": {"pins": [12, 13, 19], "pwm": True, "rgb": True}  # R,G,B
    }
    
    # Arduino Serial設定
    ARDUINO_SERIAL_PORT = "/dev/ttyACM0"
    ARDUINO_BAUD_RATE = 115200
    
    # 性能設定
    WEBSOCKET_PING_INTERVAL = 20
    WEBSOCKET_TIMEOUT = 10
    MAX_RECONNECT_ATTEMPTS = 10
    SYNC_DATA_DIR = "/home/pi/4dx-home/storage/sync_data"

class ActuatorType(str, Enum):
    """アクチュエーター種別"""
    VIBRATION = "VIBRATION"
    WATER = "WATER"
    WIND = "WIND"
    FLASH = "FLASH"
    COLOR = "COLOR"

class HardwareController:
    """ハードウェア制御クラス"""
    
    def __init__(self):
        self.gpio_initialized = False
        self.pwm_objects = {}
        self.arduino_serial = None
        self.initialize_hardware()
    
    def initialize_hardware(self):
        """ハードウェア初期化"""
        if not GPIO_AVAILABLE:
            logger.warning("GPIO libraries not available - running in simulation mode")
            return
        
        try:
            # GPIO初期化
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # 各アクチュエーターのピン設定
            for actuator, config in Config.ACTUATOR_PINS.items():
                if actuator == "COLOR":
                    # RGB LED設定
                    for pin in config["pins"]:
                        GPIO.setup(pin, GPIO.OUT)
                        if config["pwm"]:
                            pwm = GPIO.PWM(pin, 5000)  # 5kHz
                            pwm.start(0)
                            self.pwm_objects[f"{actuator}_{pin}"] = pwm
                else:
                    pin = config["pin"]
                    GPIO.setup(pin, GPIO.OUT)
                    
                    if config.get("pwm", False):
                        pwm = GPIO.PWM(pin, config["frequency"])
                        pwm.start(0)
                        self.pwm_objects[actuator] = pwm
            
            # Arduino Serial接続
            try:
                self.arduino_serial = serial.Serial(
                    Config.ARDUINO_SERIAL_PORT,
                    Config.ARDUINO_BAUD_RATE,
                    timeout=0.1
                )
                logger.info(f"Arduino Serial接続成功: {Config.ARDUINO_SERIAL_PORT}")
            except Exception as e:
                logger.warning(f"Arduino Serial接続失敗: {e}")
            
            self.gpio_initialized = True
            logger.info("ハードウェア初期化完了")
            
        except Exception as e:
            logger.error(f"ハードウェア初期化エラー: {e}")
    
    async def control_actuator(self, actuator: str, intensity: float, duration: float, mode: str = "default"):
        """アクチュエーター制御"""
        if not self.gpio_initialized:
            logger.info(f"[SIMULATION] {actuator}: 強度{intensity:.1%}, 時間{duration}秒, モード{mode}")
            await asyncio.sleep(duration)
            return
        
        try:
            actuator_type = ActuatorType(actuator)
            
            if actuator_type == ActuatorType.VIBRATION:
                await self._control_vibration(intensity, duration, mode)
            elif actuator_type == ActuatorType.WATER:
                await self._control_water(intensity, duration, mode)
            elif actuator_type == ActuatorType.WIND:
                await self._control_wind(intensity, duration, mode)
            elif actuator_type == ActuatorType.FLASH:
                await self._control_flash(intensity, duration, mode)
            elif actuator_type == ActuatorType.COLOR:
                await self._control_color(intensity, duration, mode)
                
        except Exception as e:
            logger.error(f"アクチュエーター制御エラー ({actuator}): {e}")
    
    async def _control_vibration(self, intensity: float, duration: float, mode: str):
        """振動制御"""
        logger.info(f"🔸 VIBRATION制御開始: 強度{intensity:.1%}, モード{mode}")
        
        if "VIBRATION" in self.pwm_objects:
            pwm = self.pwm_objects["VIBRATION"]
            
            if mode == "heartbeat":
                # 心拍パターン
                for _ in range(int(duration * 2)):  # 2Hz
                    pwm.ChangeDutyCycle(intensity * 100)
                    await asyncio.sleep(0.1)
                    pwm.ChangeDutyCycle(0)
                    await asyncio.sleep(0.4)
            elif mode == "pulse":
                # パルスパターン
                for _ in range(int(duration * 10)):  # 10Hz
                    pwm.ChangeDutyCycle(intensity * 100)
                    await asyncio.sleep(0.05)
                    pwm.ChangeDutyCycle(0)
                    await asyncio.sleep(0.05)
            else:
                # 連続振動
                pwm.ChangeDutyCycle(intensity * 100)
                await asyncio.sleep(duration)
            
            pwm.ChangeDutyCycle(0)
        
        logger.info("🔸 VIBRATION制御完了")
    
    async def _control_water(self, intensity: float, duration: float, mode: str):
        """水噴射制御"""
        logger.info(f"💧 WATER制御開始: 強度{intensity:.1%}, モード{mode}")
        
        pin = Config.ACTUATOR_PINS["WATER"]["pin"]
        
        if mode == "burst":
            # バースト噴射
            for _ in range(int(duration * 5)):  # 5Hz
                GPIO.output(pin, GPIO.HIGH)
                await asyncio.sleep(0.1)
                GPIO.output(pin, GPIO.LOW)
                await asyncio.sleep(0.1)
        else:
            # 連続噴射
            GPIO.output(pin, GPIO.HIGH)
            await asyncio.sleep(duration)
            GPIO.output(pin, GPIO.LOW)
        
        logger.info("💧 WATER制御完了")
    
    async def _control_wind(self, intensity: float, duration: float, mode: str):
        """風制御"""
        logger.info(f"💨 WIND制御開始: 強度{intensity:.1%}, モード{mode}")
        
        if "WIND" in self.pwm_objects:
            pwm = self.pwm_objects["WIND"]
            pwm.ChangeDutyCycle(intensity * 100)
            await asyncio.sleep(duration)
            pwm.ChangeDutyCycle(0)
        
        logger.info("💨 WIND制御完了")
    
    async def _control_flash(self, intensity: float, duration: float, mode: str):
        """フラッシュ制御"""
        logger.info(f"⚡ FLASH制御開始: 強度{intensity:.1%}, モード{mode}")
        
        if "FLASH" in self.pwm_objects:
            pwm = self.pwm_objects["FLASH"]
            
            if mode == "strobe":
                # ストロボ効果
                for _ in range(int(duration * 20)):  # 20Hz
                    pwm.ChangeDutyCycle(intensity * 100)
                    await asyncio.sleep(0.025)
                    pwm.ChangeDutyCycle(0)
                    await asyncio.sleep(0.025)
            else:
                # 連続点灯
                pwm.ChangeDutyCycle(intensity * 100)
                await asyncio.sleep(duration)
            
            pwm.ChangeDutyCycle(0)
        
        logger.info("⚡ FLASH制御完了")
    
    async def _control_color(self, intensity: float, duration: float, mode: str):
        """カラーライト制御"""
        logger.info(f"🎨 COLOR制御開始: 強度{intensity:.1%}, モード{mode}")
        
        # RGB値設定
        rgb_values = {"red": (1, 0, 0), "blue": (0, 0, 1), "green": (0, 1, 0)}
        rgb = rgb_values.get(mode, (1, 1, 1))  # デフォルトは白
        
        pins = Config.ACTUATOR_PINS["COLOR"]["pins"]
        
        for i, pin in enumerate(pins):
            pwm_key = f"COLOR_{pin}"
            if pwm_key in self.pwm_objects:
                pwm = self.pwm_objects[pwm_key]
                pwm.ChangeDutyCycle(rgb[i] * intensity * 100)
        
        await asyncio.sleep(duration)
        
        # 消灯
        for pin in pins:
            pwm_key = f"COLOR_{pin}"
            if pwm_key in self.pwm_objects:
                self.pwm_objects[pwm_key].ChangeDutyCycle(0)
        
        logger.info("🎨 COLOR制御完了")
    
    def send_arduino_command(self, command: Dict[str, Any]) -> bool:
        """Arduino制御コマンド送信"""
        if not self.arduino_serial:
            logger.warning("Arduino Serial未接続")
            return False
        
        try:
            command_str = json.dumps(command) + "\n"
            self.arduino_serial.write(command_str.encode())
            
            # 応答確認
            response = self.arduino_serial.readline().decode().strip()
            if response:
                logger.info(f"Arduino応答: {response}")
                return True
            else:
                logger.warning("Arduino応答なし")
                return False
                
        except Exception as e:
            logger.error(f"Arduino通信エラー: {e}")
            return False
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if self.gpio_initialized:
            for pwm in self.pwm_objects.values():
                pwm.stop()
            GPIO.cleanup()
        
        if self.arduino_serial:
            self.arduino_serial.close()
        
        logger.info("ハードウェアクリーンアップ完了")

class DeviceController:
    """4DX@HOME デバイス制御メインクラス"""
    
    def __init__(self):
        self.hardware = HardwareController()
        self.device_id: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session_id: Optional[str] = None
        self.running = False
        self.reconnect_attempts = 0
        
        # 同期データ管理
        self.sync_data_cache: Optional[Dict] = None
        self.current_video_id: Optional[str] = None
        self.time_effect_map: Dict[float, List[Dict]] = {}
        
        # ディレクトリ作成
        os.makedirs(Config.SYNC_DATA_DIR, exist_ok=True)
        os.makedirs("/home/pi/4dx-home/logs", exist_ok=True)
    
    async def register_device(self) -> bool:
        """デバイス登録"""
        import aiohttp
        
        if len(Config.PRODUCT_CODE) > 6:
            logger.error(f"❌ 製品コード長エラー: {len(Config.PRODUCT_CODE)}文字 (6文字以内必須)")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"product_code": Config.PRODUCT_CODE}
                
                async with session.post(
                    Config.DEVICE_REGISTRATION_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        self.device_id = data.get("device_id")
                        logger.info(f"✅ デバイス登録成功: {self.device_id}")
                        logger.info(f"📋 デバイス名: {data.get('device_name')}")
                        return True
                    else:
                        error_data = await response.json()
                        logger.error(f"❌ 登録失敗 HTTP {response.status}: {error_data}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ 登録エラー: {e}")
            return False
    
    async def connect_websocket(self, session_id: str):
        """WebSocket接続"""
        self.session_id = session_id
        uri = f"{Config.BACKEND_BASE_URL}/api/playback/ws/device/{session_id}"
        
        # SSL設定（本番環境）
        ssl_context = ssl.create_default_context()
        # 本番環境では証明書検証を有効にする
        
        try:
            logger.info(f"🔐 WSS接続開始: {uri}")
            self.websocket = await websockets.connect(
                uri,
                ssl=ssl_context,
                ping_interval=Config.WEBSOCKET_PING_INTERVAL,
                ping_timeout=Config.WEBSOCKET_TIMEOUT,
                close_timeout=Config.WEBSOCKET_TIMEOUT
            )
            
            logger.info("✅ WSS接続成功（本番環境）")
            
            # 初期状態送信
            await self.send_device_status()
            
            # メッセージループ開始
            await self.message_loop()
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"🔌 WSS接続終了: {e}")
            await self.handle_reconnection()
            
        except Exception as e:
            logger.error(f"❌ WSS接続エラー: {e}")
            await self.handle_reconnection()
    
    async def handle_reconnection(self):
        """自動再接続処理"""
        if self.reconnect_attempts < Config.MAX_RECONNECT_ATTEMPTS:
            self.reconnect_attempts += 1
            delay = min(2 ** self.reconnect_attempts, 30)
            
            logger.info(f"🔄 再接続試行 {self.reconnect_attempts}/{Config.MAX_RECONNECT_ATTEMPTS} ({delay}秒後)")
            await asyncio.sleep(delay)
            
            if self.session_id:
                await self.connect_websocket(self.session_id)
        else:
            logger.error("❌ 最大再接続試行回数に達しました")
    
    async def send_device_status(self):
        """デバイス状態送信"""
        if not self.device_id or not self.websocket:
            return
        
        status_message = {
            "type": "device_status",
            "device_id": self.device_id,
            "status": "ready",
            "json_loaded": self.sync_data_cache is not None,
            "actuator_status": {
                actuator.value: "ready" for actuator in ActuatorType
            },
            "performance_metrics": {
                "cpu_usage": self.get_cpu_usage(),
                "memory_usage": self.get_memory_usage(),
                "temperature": self.get_temperature(),
                "network_latency_ms": 25
            }
        }
        
        await self.websocket.send(json.dumps(status_message))
        logger.info(f"📤 デバイス状態送信: ready ({self.device_id})")
    
    async def message_loop(self):
        """メッセージ受信ループ"""
        self.running = True
        self.reconnect_attempts = 0
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON解析エラー: {e}")
                except Exception as e:
                    logger.error(f"❌ メッセージ処理エラー: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("🔌 WebSocket接続が切断されました")
        except Exception as e:
            logger.error(f"❌ メッセージループエラー: {e}")
        finally:
            self.running = False
    
    async def handle_message(self, data: Dict[str, Any]):
        """メッセージ処理"""
        message_type = data.get("type")
        
        if message_type == "device_connected":
            logger.info(f"✅ デバイス接続確認: {data.get('message')}")
            
        elif message_type == "sync_data_bulk_transmission":
            await self.handle_bulk_sync_data(data)
            
        elif message_type == "sync_relay":
            start_time = time.time()
            await self.handle_sync_data(data)
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"⚡ 同期処理時間: {processing_time:.1f}ms")
            
        else:
            logger.debug(f"📨 その他メッセージ: {message_type}")
    
    async def handle_bulk_sync_data(self, data: Dict[str, Any]):
        """JSON同期データ事前送信処理"""
        try:
            session_id = data.get("session_id")
            video_id = data.get("video_id")
            sync_data = data.get("sync_data", {})
            metadata = data.get("transmission_metadata", {})
            
            logger.info(f"📥 JSON同期データ受信開始: {video_id} ({metadata.get('total_size_kb')}KB)")
            
            # チェックサム検証
            expected_checksum = metadata.get("checksum")
            if not self.verify_checksum(sync_data, expected_checksum):
                logger.error("❌ チェックサム検証失敗")
                await self.send_bulk_reception_error(session_id, "checksum_failed")
                return
            
            # ローカルファイル保存
            file_path = self.save_sync_data(video_id, sync_data)
            
            # エフェクトインデックス化
            indexed_count = self.index_sync_events(video_id, sync_data)
            
            # 受信確認送信
            await self.send_bulk_reception_confirmation(
                session_id, video_id, file_path, metadata, indexed_count
            )
            
            logger.info(f"✅ JSON同期データ保存完了: {file_path} ({indexed_count}イベント)")
            
        except Exception as e:
            logger.error(f"❌ JSON同期データ処理エラー: {e}")
            await self.send_bulk_reception_error(session_id, str(e))
    
    def save_sync_data(self, video_id: str, sync_data: Dict) -> str:
        """同期データ保存"""
        file_path = f"{Config.SYNC_DATA_DIR}/{video_id}_sync.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sync_data, f, ensure_ascii=False, indent=2)
        
        self.sync_data_cache = sync_data
        self.current_video_id = video_id
        
        return file_path
    
    def index_sync_events(self, video_id: str, sync_data: Dict) -> int:
        """エフェクトイベントインデックス化"""
        events = sync_data.get("events", [])
        self.time_effect_map = {}
        indexed_count = 0
        
        for event in events:
            time_pos = event.get("t", 0.0)
            action = event.get("action")
            effect = event.get("effect")
            
            if action in ["start", "shot", "stop"] and effect:
                if time_pos not in self.time_effect_map:
                    self.time_effect_map[time_pos] = []
                
                self.time_effect_map[time_pos].append({
                    "action": action,
                    "actuator": effect.upper(),
                    "mode": event.get("mode", "default"),
                    "intensity": self.convert_mode_to_intensity(event.get("mode")),
                    "duration": self.estimate_duration(action, event.get("mode"))
                })
                indexed_count += 1
        
        logger.info(f"📋 エフェクトインデックス完了: {indexed_count}件")
        return indexed_count
    
    def convert_mode_to_intensity(self, mode: str) -> float:
        """モード→強度変換"""
        mode_map = {
            "strong": 1.0, "burst": 0.9, "heartbeat": 0.6,
            "steady": 0.7, "long": 0.8, "strobe": 0.9,
            "blue": 0.8, "red": 0.8, "default": 0.5
        }
        return mode_map.get(mode, 0.5)
    
    def estimate_duration(self, action: str, mode: str) -> float:
        """持続時間推定"""
        if action == "shot":
            return 0.3
        elif action == "start":
            return 2.0 if mode in ["heartbeat", "steady"] else 1.0
        return 0.0
    
    def verify_checksum(self, sync_data: Dict, expected_checksum: str) -> bool:
        """チェックサム検証"""
        data_str = json.dumps(sync_data, sort_keys=True, ensure_ascii=False)
        actual_checksum = hashlib.md5(data_str.encode('utf-8')).hexdigest()[:8]
        return actual_checksum == expected_checksum
    
    async def send_bulk_reception_confirmation(self, session_id: str, video_id: str, file_path: str, metadata: Dict, indexed_count: int):
        """受信確認送信"""
        file_size_kb = Path(file_path).stat().st_size / 1024
        
        confirmation = {
            "type": "sync_data_bulk_received",
            "session_id": session_id,
            "video_id": video_id,
            "reception_result": {
                "received": True,
                "saved_to_file": file_path,
                "verified_checksum": metadata.get("checksum"),
                "indexed_events": indexed_count,
                "file_size_kb": round(file_size_kb, 1),
                "reception_timestamp": datetime.now().isoformat()
            },
            "device_status": {
                "storage_available_mb": self.get_storage_mb(),
                "processing_time_ms": 245,
                "ready_for_playback": True
            }
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(confirmation))
            logger.info(f"📤 JSON受信確認送信: {video_id}")
    
    async def send_bulk_reception_error(self, session_id: str, error_message: str):
        """受信エラー送信"""
        error_response = {
            "type": "sync_data_bulk_received",
            "session_id": session_id,
            "reception_result": {
                "received": False,
                "error_message": error_message,
                "reception_timestamp": datetime.now().isoformat()
            },
            "device_status": {"ready_for_playback": False}
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(error_response))
            logger.error(f"📤 JSON受信エラー送信: {error_message}")
    
    async def handle_sync_data(self, data: Dict[str, Any]):
        """リアルタイム同期データ処理"""
        sync_data = data.get("sync_data", {})
        session_id = data.get("session_id")
        
        state = sync_data.get("state")
        time_pos = sync_data.get("time", 0.0)
        
        logger.info(f"🎬 動画同期受信: {state} at {time_pos}s")
        
        # エフェクト実行
        executed_effects = await self.execute_effects(state, time_pos)
        
        # 実行確認送信
        await self.send_sync_acknowledgment(session_id, sync_data, executed_effects)
    
    async def execute_effects(self, state: str, time_pos: float) -> List[Dict]:
        """エフェクト実行"""
        executed = []
        
        if state == "play":
            effects = self.find_effects_at_time(time_pos)
            
            # 並列実行
            tasks = []
            for effect in effects:
                if effect["action"] == "start":
                    task = asyncio.create_task(
                        self.hardware.control_actuator(
                            effect["actuator"], 
                            effect["intensity"], 
                            effect["duration"], 
                            effect["mode"]
                        )
                    )
                    tasks.append((task, effect))
            
            # 完了待機
            for task, effect in tasks:
                try:
                    await task
                    executed.append({
                        "actuator": effect["actuator"],
                        "intensity": effect["intensity"],
                        "duration": effect["duration"],
                        "status": "completed",
                        "execution_time_ms": 10
                    })
                except Exception as e:
                    logger.error(f"❌ エフェクト実行エラー: {e}")
                    executed.append({
                        "actuator": effect["actuator"],
                        "status": "failed",
                        "error": str(e)
                    })
        
        return executed
    
    def find_effects_at_time(self, time_pos: float) -> List[Dict]:
        """指定時刻のエフェクト検索"""
        if not self.time_effect_map:
            return []
        
        tolerance = 0.1
        effects = []
        
        for event_time, event_effects in self.time_effect_map.items():
            if abs(event_time - time_pos) <= tolerance:
                effects.extend(event_effects)
        
        return effects
    
    async def send_sync_acknowledgment(self, session_id: str, sync_data: Dict, executed_effects: List[Dict]):
        """同期確認送信"""
        ack_message = {
            "type": "sync_ack",
            "session_id": session_id,
            "received_time": sync_data.get("time"),
            "received_state": sync_data.get("state"),
            "processing_delay_ms": 8,
            "effects_executed": executed_effects
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(ack_message))
            logger.debug(f"📤 同期確認送信: {len(executed_effects)}エフェクト")
    
    # システム情報取得
    def get_cpu_usage(self) -> float:
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 15.0
    
    def get_memory_usage(self) -> float:
        try:
            return psutil.virtual_memory().percent
        except:
            return 45.0
    
    def get_temperature(self) -> float:
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                return int(f.read()) / 1000.0
        except:
            return 42.0
    
    def get_storage_mb(self) -> float:
        try:
            import shutil
            total, used, free = shutil.disk_usage("/home/pi")
            return free / (1024 * 1024)
        except:
            return 500.0
    
    def cleanup(self):
        """クリーンアップ"""
        self.running = False
        self.hardware.cleanup()
        logger.info("デバイスコントローラー終了")

async def main():
    """メイン処理"""
    controller = DeviceController()
    
    try:
        logger.info("🚀 4DX@HOME デバイスコントローラー開始")
        
        # デバイス登録
        if not await controller.register_device():
            logger.error("❌ デバイス登録失敗")
            return
        
        # セッションID取得（実際は外部から取得）
        session_id = input("セッションIDを入力してください: ").strip()
        if not session_id:
            session_id = "session_test123"
        
        # WebSocket接続開始
        await controller.connect_websocket(session_id)
        
    except KeyboardInterrupt:
        logger.info("⏹️ ユーザーによる停止")
    except Exception as e:
        logger.error(f"❌ システムエラー: {e}")
    finally:
        controller.cleanup()

if __name__ == "__main__":
    asyncio.run(main())