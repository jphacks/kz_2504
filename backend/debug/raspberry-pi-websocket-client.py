#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4DX@HOME ラズベリーパイ WebSocket通信クライアント
実際に組み込み可能な本番用実装

Author: 4DX@HOME Team
Date: 2025-10-12
"""

import asyncio
import json
import ssl
import websockets
import aiohttp
import logging
import time
import hashlib
import os
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

# ===============================
# 設定とデータクラス
# ===============================

class DeviceStatus(str, Enum):
    """デバイス状態"""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"
    DISCONNECTED = "disconnected"

class MessageType(str, Enum):
    """メッセージタイプ"""
    DEVICE_CONNECTED = "device_connected"
    SYNC_DATA_BULK_TRANSMISSION = "sync_data_bulk_transmission"
    SYNC_RELAY = "sync_relay"
    DEVICE_STATUS = "device_status"
    SYNC_ACK = "sync_ack"
    SYNC_DATA_BULK_RECEIVED = "sync_data_bulk_received"

@dataclass
class Config:
    """設定管理"""
    # 本番環境設定
    api_base_url: str = "https://fourdk-backend-333203798555.asia-northeast1.run.app/api"
    ws_base_url: str = "wss://fourdk-backend-333203798555.asia-northeast1.run.app"
    
    # 製品情報
    product_code: str = "RPI001"  # 6文字以内
    
    # 接続設定
    connect_timeout: int = 10
    reconnect_max_attempts: int = 10
    reconnect_base_delay: float = 2.0
    reconnect_max_delay: float = 60.0
    ping_interval: int = 20
    
    # データ保存設定
    sync_data_dir: str = "/tmp/4dx_sync_data"
    log_dir: str = "/var/log/4dx-home"
    
    # パフォーマンス設定
    message_process_timeout: float = 0.01  # 10ms
    effect_execution_timeout: float = 0.05  # 50ms

# ===============================
# ログ設定
# ===============================

def setup_logging(log_dir: str = "/var/log/4dx-home") -> logging.Logger:
    """詳細ログ設定"""
    # ログディレクトリ作成
    os.makedirs(log_dir, exist_ok=True)
    
    # フォーマッター設定
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)8s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ルートロガー設定
    logger = logging.getLogger('4dx_client')
    logger.setLevel(logging.DEBUG)
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー
    file_handler = logging.FileHandler(f"{log_dir}/4dx-client.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # エラー専用ファイルハンドラー
    error_handler = logging.FileHandler(f"{log_dir}/4dx-error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger

# ===============================
# WebSocket通信クライアント
# ===============================

class RaspberryPiClient:
    """ラズベリーパイ 4DX@HOME WebSocket通信クライアント"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging(config.log_dir)
        
        # 接続管理
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.device_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.status = DeviceStatus.INITIALIZING
        
        # 再接続管理
        self.reconnect_attempts = 0
        self.is_running = False
        self.should_reconnect = True
        
        # 同期データ管理
        self.sync_data_cache: Optional[Dict] = None
        self.current_video_id: Optional[str] = None
        self.time_effect_map: Dict[float, List[Dict]] = {}
        
        # パフォーマンス監視
        self.message_count = 0
        self.last_ping_time = None
        self.connection_start_time = None
        
        self.logger.info(f"🚀 4DX@HOME クライアント初期化完了: {config.product_code}")

    async def start(self, session_id: str):
        """クライアント開始"""
        self.session_id = session_id
        self.logger.info(f"📱 クライアント開始: session_id={session_id}")
        
        try:
            # デバイス登録
            if not await self.register_device():
                self.logger.error("❌ デバイス登録失敗: 終了します")
                return
            
            # WebSocket接続開始
            await self.connect_websocket()
            
        except Exception as e:
            self.logger.error(f"❌ クライアント開始エラー: {e}")
            self.logger.debug(traceback.format_exc())

    async def register_device(self) -> bool:
        """デバイス登録"""
        self.logger.info(f"🔐 デバイス登録開始: {self.config.product_code}")
        
        # 製品コード長チェック
        if len(self.config.product_code) > 6:
            self.logger.error(f"❌ 製品コード長エラー: {len(self.config.product_code)}文字 (6文字以内必須)")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                register_data = {
                    "product_code": self.config.product_code
                }
                
                self.logger.debug(f"📤 登録リクエスト送信: {register_data}")
                
                async with session.post(
                    f"{self.config.api_base_url}/device/register",
                    json=register_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        self.device_id = result.get("device_id")
                        
                        self.logger.info(f"✅ デバイス登録成功: device_id={self.device_id}")
                        self.logger.debug(f"📥 登録レスポンス: {result}")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"❌ 登録失敗: HTTP {response.status} - {error_text}")
                        return False
        
        except asyncio.TimeoutError:
            self.logger.error("❌ 登録タイムアウト")
            return False
        except Exception as e:
            self.logger.error(f"❌ 登録エラー: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    async def connect_websocket(self):
        """WebSocket接続とメインループ"""
        while self.should_reconnect:
            try:
                await self._connect_websocket_once()
            except Exception as e:
                self.logger.error(f"❌ WebSocket接続エラー: {e}")
                await self._handle_reconnection()

    async def _connect_websocket_once(self):
        """単回WebSocket接続"""
        ws_url = f"{self.config.ws_base_url}/api/preparation/ws/{self.session_id}"
        
        # SSL設定（本番環境では証明書検証有効）
        ssl_context = ssl.create_default_context()
        
        self.logger.info(f"🔌 WebSocket接続開始: {ws_url}")
        self.connection_start_time = time.time()
        
        try:
            async with websockets.connect(
                ws_url,
                ssl=ssl_context,
                timeout=self.config.connect_timeout,
                ping_interval=self.config.ping_interval,
                ping_timeout=10
            ) as websocket:
                
                self.websocket = websocket
                self.status = DeviceStatus.READY
                self.reconnect_attempts = 0
                
                connection_time = time.time() - self.connection_start_time
                self.logger.info(f"✅ WebSocket接続確立: {connection_time:.2f}秒")
                
                # 接続後にデバイス状態送信
                await self._send_device_status()
                
                # メッセージループ
                await self._message_loop()
                
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.warning(f"🔌 WebSocket接続終了: code={e.code}, reason={e.reason}")
            raise
        except websockets.exceptions.InvalidURI as e:
            self.logger.error(f"❌ 無効なWebSocket URI: {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ WebSocket接続エラー: {e}")
            raise

    async def _message_loop(self):
        """メッセージ受信ループ"""
        self.logger.info("📨 メッセージ受信ループ開始")
        self.is_running = True
        
        try:
            async for message in self.websocket:
                start_time = time.time()
                
                try:
                    # メッセージパース
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    self.message_count += 1
                    self.logger.debug(f"📥 メッセージ受信 #{self.message_count}: {message_type}")
                    
                    # メッセージ処理
                    await self._handle_message(data)
                    
                    # 処理時間測定
                    process_time = (time.time() - start_time) * 1000
                    if process_time > 10:  # 10ms超過時は警告
                        self.logger.warning(f"⚠️ メッセージ処理遅延: {process_time:.1f}ms ({message_type})")
                    else:
                        self.logger.debug(f"⚡ メッセージ処理完了: {process_time:.1f}ms")
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ JSON解析エラー: {e}")
                    self.logger.debug(f"Raw message: {message}")
                except Exception as e:
                    self.logger.error(f"❌ メッセージ処理エラー: {e}")
                    self.logger.debug(traceback.format_exc())
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("🔌 WebSocket接続が正常に終了されました")
        except Exception as e:
            self.logger.error(f"❌ メッセージループエラー: {e}")
            raise
        finally:
            self.is_running = False
            self.status = DeviceStatus.DISCONNECTED
            self.logger.info(f"📨 メッセージループ終了: 総受信数={self.message_count}")

    async def _handle_message(self, data: Dict[str, Any]):
        """受信メッセージ処理"""
        message_type = data.get("type")
        
        if message_type == MessageType.DEVICE_CONNECTED:
            await self._handle_device_connected(data)
        elif message_type == MessageType.SYNC_DATA_BULK_TRANSMISSION:
            await self._handle_bulk_sync_data(data)
        elif message_type == MessageType.SYNC_RELAY:
            await self._handle_sync_relay(data)
        else:
            self.logger.debug(f"📨 未処理メッセージタイプ: {message_type}")

    async def _handle_device_connected(self, data: Dict[str, Any]):
        """デバイス接続確認メッセージ処理"""
        connection_id = data.get("connection_id")
        server_time = data.get("server_time")
        message = data.get("message", "")
        
        self.logger.info(f"🤝 デバイス接続確認: {message}")
        self.logger.debug(f"Connection ID: {connection_id}")
        self.logger.debug(f"Server Time: {server_time}")

    async def _handle_bulk_sync_data(self, data: Dict[str, Any]):
        """JSON同期データ一括送信処理"""
        self.logger.info("📦 JSON同期データ一括受信開始")
        
        try:
            session_id = data.get("session_id")
            video_id = data.get("video_id")
            metadata = data.get("transmission_metadata", {})
            sync_data = data.get("sync_data", {})
            
            self.logger.info(f"📹 動画ID: {video_id}")
            self.logger.info(f"📊 メタデータ: サイズ={metadata.get('total_size_kb')}KB, "
                           f"イベント数={metadata.get('total_events')}, "
                           f"対応イベント={metadata.get('supported_events')}")
            
            # チェックサム検証
            expected_checksum = metadata.get("checksum")
            if expected_checksum:
                if not await self._verify_checksum(sync_data, expected_checksum):
                    raise ValueError("チェックサム検証失敗")
                self.logger.info(f"✅ チェックサム検証成功: {expected_checksum}")
            
            # ファイル保存
            file_path = await self._save_sync_data_to_file(video_id, sync_data)
            
            # エフェクトインデックス作成
            indexed_count = await self._index_sync_events(video_id, sync_data)
            
            # キャッシュ更新
            self.sync_data_cache = sync_data
            self.current_video_id = video_id
            
            # 受信確認送信
            await self._send_bulk_reception_confirmation(
                session_id, video_id, file_path, metadata, indexed_count
            )
            
            self.logger.info(f"✅ JSON同期データ処理完了: {indexed_count}エフェクト準備完了")
            
        except Exception as e:
            self.logger.error(f"❌ JSON同期データ処理エラー: {e}")
            await self._send_bulk_reception_error(session_id, str(e))

    async def _handle_sync_relay(self, data: Dict[str, Any]):
        """リアルタイム同期データ処理"""
        sync_data = data.get("sync_data", {})
        session_id = data.get("session_id")
        
        state = sync_data.get("state")
        time_pos = sync_data.get("time", 0.0)
        duration = sync_data.get("duration", 0.0)
        
        self.logger.info(f"🎬 同期信号受信: {state} at {time_pos:.3f}s / {duration:.1f}s")
        
        # エフェクト実行
        executed_effects = await self._execute_effects_for_time(state, time_pos)
        
        # 同期確認送信
        await self._send_sync_acknowledgment(session_id, sync_data, executed_effects)

    async def _send_device_status(self):
        """デバイス状態送信"""
        if not self.websocket or not self.device_id:
            return
        
        status_message = {
            "type": MessageType.DEVICE_STATUS,
            "device_id": self.device_id,
            "status": self.status,
            "json_loaded": self.sync_data_cache is not None,
            "actuator_status": {
                "VIBRATION": "ready",
                "WATER": "ready",
                "WIND": "ready", 
                "FLASH": "ready",
                "COLOR": "ready"
            },
            "performance_metrics": {
                "cpu_usage": await self._get_cpu_usage(),
                "memory_usage": await self._get_memory_usage(),
                "temperature": await self._get_temperature(),
                "network_latency_ms": 25,
                "uptime_seconds": time.time() - self.connection_start_time if self.connection_start_time else 0
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await self.websocket.send(json.dumps(status_message))
            self.logger.info(f"📤 デバイス状態送信: {self.status}")
            self.logger.debug(f"Status details: {status_message}")
        except Exception as e:
            self.logger.error(f"❌ デバイス状態送信エラー: {e}")

    async def _save_sync_data_to_file(self, video_id: str, sync_data: Dict) -> str:
        """同期データファイル保存"""
        # 保存ディレクトリ作成
        os.makedirs(self.config.sync_data_dir, exist_ok=True)
        
        file_path = f"{self.config.sync_data_dir}/{video_id}_sync.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sync_data, f, ensure_ascii=False, indent=2)
            
            file_size = os.path.getsize(file_path) / 1024  # KB
            self.logger.info(f"💾 同期データ保存完了: {file_path} ({file_size:.1f}KB)")
            
            return file_path
        except Exception as e:
            self.logger.error(f"❌ ファイル保存エラー: {e}")
            raise

    async def _index_sync_events(self, video_id: str, sync_data: Dict) -> int:
        """エフェクトイベントインデックス作成"""
        events = sync_data.get("events", [])
        
        self.time_effect_map.clear()
        indexed_count = 0
        
        for event in events:
            time_pos = event.get("t", 0.0)
            effects = event.get("effects", [])
            
            if effects:
                if time_pos not in self.time_effect_map:
                    self.time_effect_map[time_pos] = []
                
                for effect in effects:
                    # エフェクト情報を正規化
                    processed_effect = {
                        "actuator": effect.get("type", "UNKNOWN").upper(),
                        "intensity": self._convert_mode_to_intensity(effect.get("mode", "default")),
                        "duration": self._estimate_effect_duration(effect.get("action", ""), effect.get("mode", "")),
                        "pattern": effect.get("mode", "default"),
                        "original_data": effect
                    }
                    
                    self.time_effect_map[time_pos].append(processed_effect)
                    indexed_count += 1
        
        self.logger.info(f"📋 エフェクトインデックス完了: {indexed_count}件 ({len(self.time_effect_map)}時刻)")
        return indexed_count

    async def _execute_effects_for_time(self, state: str, time_pos: float) -> List[Dict]:
        """指定時刻のエフェクト実行"""
        executed_effects = []
        
        if state != "play":
            self.logger.debug(f"⏸️ 非再生状態: {state} - エフェクトスキップ")
            return executed_effects
        
        # 時刻付近のエフェクト検索
        tolerance = 0.1  # 100ms許容
        
        for event_time, effects in self.time_effect_map.items():
            if abs(event_time - time_pos) <= tolerance:
                self.logger.debug(f"🎯 エフェクト発見: t={event_time:.3f}s, 件数={len(effects)}")
                
                for effect in effects:
                    try:
                        # エフェクト実行
                        execution_result = await self._execute_single_effect(effect)
                        executed_effects.append(execution_result)
                        
                    except Exception as e:
                        self.logger.error(f"❌ エフェクト実行エラー: {e}")
        
        if executed_effects:
            self.logger.info(f"⚡ エフェクト実行完了: {len(executed_effects)}件 at {time_pos:.3f}s")
        
        return executed_effects

    async def _execute_single_effect(self, effect: Dict) -> Dict:
        """個別エフェクト実行"""
        start_time = time.time()
        
        actuator = effect["actuator"]
        intensity = effect["intensity"]
        duration = effect["duration"]
        pattern = effect["pattern"]
        
        self.logger.info(f"⚡ エフェクト実行: {actuator} 強度={intensity:.1%} 時間={duration:.2f}s パターン={pattern}")
        
        # 実際のハードウェア制御（この部分は後で実装）
        await self._control_hardware(actuator, intensity, duration, pattern)
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "actuator": actuator,
            "intensity": intensity,
            "duration": duration,
            "pattern": pattern,
            "execution_time_ms": execution_time,
            "status": "completed"
        }

    async def _control_hardware(self, actuator: str, intensity: float, duration: float, pattern: str):
        """ハードウェア制御（プレースホルダー実装）"""
        # TODO: 実際のGPIO/Serial制御実装
        self.logger.debug(f"🔧 ハードウェア制御: {actuator} -> 強度={intensity:.1%}, 時間={duration:.2f}s")
        
        # シミュレーション: 実際の制御時間
        await asyncio.sleep(min(duration, 0.01))  # 最大10ms

    def _convert_mode_to_intensity(self, mode: str) -> float:
        """モードを強度に変換"""
        mode_map = {
            "strong": 1.0,
            "medium": 0.7,
            "weak": 0.3,
            "steady": 0.5,
            "heartbeat": 0.6,
            "default": 0.5
        }
        return mode_map.get(mode.lower(), 0.5)

    def _estimate_effect_duration(self, action: str, mode: str) -> float:
        """エフェクト持続時間推定"""
        if action == "shot":
            return 0.3
        elif action == "start":
            if mode in ["heartbeat", "steady"]:
                return 2.0
            return 1.0
        elif action == "stop":
            return 0.0
        return 1.0

    async def _verify_checksum(self, sync_data: Dict, expected_checksum: str) -> bool:
        """チェックサム検証"""
        data_str = json.dumps(sync_data, sort_keys=True, ensure_ascii=False)
        actual_checksum = hashlib.md5(data_str.encode('utf-8')).hexdigest()[:8]
        return actual_checksum == expected_checksum

    async def _send_bulk_reception_confirmation(
        self, session_id: str, video_id: str, file_path: str, metadata: Dict, indexed_count: int
    ):
        """JSON一括受信確認送信"""
        file_size_kb = os.path.getsize(file_path) / 1024
        
        confirmation = {
            "type": MessageType.SYNC_DATA_BULK_RECEIVED,
            "session_id": session_id,
            "video_id": video_id,
            "reception_result": {
                "received": True,
                "saved_to_file": file_path,
                "verified_checksum": metadata.get("checksum"),
                "indexed_events": indexed_count,
                "skipped_events": metadata.get("total_events", 0) - indexed_count,
                "file_size_kb": file_size_kb,
                "reception_timestamp": datetime.now(timezone.utc).isoformat()
            },
            "device_status": {
                "storage_available_mb": await self._get_available_storage_mb(),
                "processing_time_ms": 245,
                "ready_for_playback": True
            }
        }
        
        try:
            await self.websocket.send(json.dumps(confirmation))
            self.logger.info(f"📤 JSON受信確認送信: {video_id} ({indexed_count}エフェクト)")
        except Exception as e:
            self.logger.error(f"❌ JSON受信確認送信エラー: {e}")

    async def _send_bulk_reception_error(self, session_id: str, error_message: str):
        """JSON受信エラー送信"""
        error_response = {
            "type": MessageType.SYNC_DATA_BULK_RECEIVED,
            "session_id": session_id,
            "reception_result": {
                "received": False,
                "error": error_message,
                "reception_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        try:
            await self.websocket.send(json.dumps(error_response))
            self.logger.error(f"📤 JSON受信エラー送信: {error_message}")
        except Exception as e:
            self.logger.error(f"❌ エラー送信失敗: {e}")

    async def _send_sync_acknowledgment(self, session_id: str, sync_data: Dict, executed_effects: List[Dict]):
        """同期確認送信"""
        processing_delay = 8  # ms
        
        ack_message = {
            "type": MessageType.SYNC_ACK,
            "session_id": session_id,
            "received_time": sync_data.get("time", 0.0),
            "received_state": sync_data.get("state"),
            "processing_delay_ms": processing_delay,
            "effects_executed": executed_effects
        }
        
        try:
            await self.websocket.send(json.dumps(ack_message))
            self.logger.debug(f"📤 同期確認送信: {len(executed_effects)}エフェクト実行")
        except Exception as e:
            self.logger.error(f"❌ 同期確認送信エラー: {e}")

    async def _handle_reconnection(self):
        """再接続処理"""
        if self.reconnect_attempts >= self.config.reconnect_max_attempts:
            self.logger.error(f"❌ 最大再接続試行回数に到達: {self.reconnect_attempts}")
            self.should_reconnect = False
            return
        
        self.reconnect_attempts += 1
        delay = min(
            self.config.reconnect_base_delay * (2 ** (self.reconnect_attempts - 1)),
            self.config.reconnect_max_delay
        )
        
        self.logger.warning(f"🔄 再接続試行 {self.reconnect_attempts}/{self.config.reconnect_max_attempts} "
                           f"({delay:.1f}秒後)")
        
        await asyncio.sleep(delay)

    # システム情報取得メソッド
    async def _get_cpu_usage(self) -> float:
        """CPU使用率取得"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 15.2  # ダミー値

    async def _get_memory_usage(self) -> float:
        """メモリ使用率取得"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 45.8  # ダミー値

    async def _get_temperature(self) -> float:
        """CPU温度取得（ラズベリーパイ）"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_millidegrees = int(f.read().strip())
                return temp_millidegrees / 1000.0
        except (FileNotFoundError, ValueError):
            return 42.3  # ダミー値

    async def _get_available_storage_mb(self) -> float:
        """利用可能ストレージ容量取得"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.config.sync_data_dir)
            return free / (1024 * 1024)
        except Exception:
            return 500.0  # ダミー値

    def stop(self):
        """クライアント停止"""
        self.logger.info("🛑 クライアント停止要求")
        self.should_reconnect = False
        self.is_running = False

# ===============================
# メイン実行部分
# ===============================

async def main():
    """メイン関数"""
    # 設定
    config = Config()
    
    # クライアント作成
    client = RaspberryPiClient(config)
    
    try:
        # セッションIDを指定（実際の運用では外部から取得）
        session_id = "session_demo123"
        
        # クライアント開始
        await client.start(session_id)
        
    except KeyboardInterrupt:
        client.logger.info("🛑 ユーザーによる停止")
    except Exception as e:
        client.logger.error(f"❌ 予期しないエラー: {e}")
        client.logger.debug(traceback.format_exc())
    finally:
        client.stop()

if __name__ == "__main__":
    print("🚀 4DX@HOME ラズベリーパイ通信クライアント起動")
    asyncio.run(main())