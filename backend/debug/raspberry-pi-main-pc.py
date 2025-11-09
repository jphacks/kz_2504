#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4DX@HOME ラズベリーパイ メインアプリケーション (PC環境対応版)
WebSocket通信とハードウェア制御の統合システム

Author: 4DX@HOME Team
Date: 2025-10-12
"""

import asyncio
import signal
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from datetime import datetime
import platform

# 自作モジュールインポート（同じディレクトリから）
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# WebSocket通信クライアント（上記で作成したコードから必要な部分を再利用）
from dataclasses import dataclass
import json
import ssl
import websockets
import aiohttp
import time
import hashlib

# ===============================
# 統合アプリケーション設定
# ===============================

@dataclass
class AppConfig:
    """アプリケーション設定"""
    # 基本設定
    product_code: str = "AB999"  # PC環境用デモシミュレーター
    session_id: str = "session_demo123"  # デフォルトセッション
    
    # サーバー設定
    api_base_url: str = "https://fourdk-backend-333203798555.asia-northeast1.run.app/api"
    ws_base_url: str = "wss://fourdk-backend-333203798555.asia-northeast1.run.app"
    
    # ログ設定
    log_level: str = "DEBUG"
    log_dir: str = "./logs"  # PC環境用パス
    
    # データ保存設定
    sync_data_dir: str = "./temp/4dx_sync_data"  # PC環境用パス
    
    # 接続設定
    connect_timeout: int = 10
    reconnect_max_attempts: int = 10
    ping_interval: int = 20
    
    # PC環境フラグ
    pc_environment: bool = True

# ===============================
# メインアプリケーションクラス
# ===============================

class FourDXHomeApp:
    """4DX@HOME メインアプリケーション"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = self._setup_logging()
        
        # 接続管理
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.device_id: Optional[str] = None
        self.is_running = False
        
        # 同期データ管理
        self.sync_data_cache: Optional[Dict] = None
        self.time_effect_map: Dict[float, list] = {}
        
        # ハードウェア制御（プレースホルダー）
        self.hardware_available = False
        
        # シグナルハンドラー設定
        if platform.system() != "Windows":
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"START 4DX@HOME アプリケーション初期化: {config.product_code}")

    def _setup_logging(self) -> logging.Logger:
        """ログ設定"""
        # ログディレクトリ作成
        os.makedirs(self.config.log_dir, exist_ok=True)
        
        # フォーマッター（絵文字なし）
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d [%(levelname)8s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ロガー設定
        logger = logging.getLogger('4dx_app')
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # コンソールハンドラー
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)
        
        # ファイルハンドラー
        file_handler = logging.FileHandler(f"{self.config.log_dir}/4dx-app.log", encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

    async def start(self):
        """アプリケーション開始"""
        self.logger.info("START 4DX@HOME アプリケーション開始")
        
        try:
            # ハードウェア初期化チェック
            self._check_hardware_availability()
            
            # デバイス登録
            if not await self._register_device():
                self.logger.error("ERROR デバイス登録失敗")
                return False
            
            # WebSocket接続開始
            await self._connect_websocket()
            
        except Exception as e:
            self.logger.error(f"ERROR アプリケーション開始エラー: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def _check_hardware_availability(self):
        """ハードウェア利用可能性チェック"""
        try:
            import RPi.GPIO as GPIO
            import gpiozero
            self.hardware_available = True
            self.logger.info("OK ハードウェア制御: 利用可能（GPIO + gpiozero）")
        except ImportError:
            self.logger.warning("WARN ハードウェア制御: 利用不可（開発環境）")

    async def _register_device(self) -> bool:
        """デバイス登録"""
        self.logger.info(f"AUTH デバイス登録: {self.config.product_code}")
        
        if len(self.config.product_code) > 6:
            self.logger.error(f"ERROR 製品コード長エラー: {len(self.config.product_code)}文字")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                register_data = {"product_code": self.config.product_code}
                
                self.logger.debug(f"REQUEST 登録リクエスト: {register_data}")
                
                async with session.post(
                    f"{self.config.api_base_url}/device/register",
                    json=register_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        self.device_id = result.get("device_id")
                        self.logger.info(f"SUCCESS デバイス登録成功: {self.device_id}")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"ERROR 登録失敗: HTTP {response.status} - {error_text}")
                        return False
        
        except Exception as e:
            self.logger.error(f"ERROR 登録エラー: {e}")
            return False

    async def _connect_websocket(self):
        """WebSocket接続"""
        ws_url = f"{self.config.ws_base_url}/api/preparation/ws/{self.config.session_id}"
        ssl_context = ssl.create_default_context()
        
        self.logger.info(f"CONNECT WebSocket接続: {ws_url}")
        
        reconnect_attempts = 0
        
        while reconnect_attempts < self.config.reconnect_max_attempts:
            try:
                # タイムアウト設定をPython 3.11対応に修正
                async with websockets.connect(
                    ws_url,
                    ssl=ssl_context,
                    ping_interval=self.config.ping_interval,
                    open_timeout=self.config.connect_timeout
                ) as websocket:
                    
                    self.websocket = websocket
                    reconnect_attempts = 0
                    
                    self.logger.info("SUCCESS WebSocket接続成功")
                    
                    # 初期状態送信
                    await self._send_device_status()
                    
                    # メッセージループ
                    await self._message_loop()
                    
            except websockets.exceptions.ConnectionClosed as e:
                self.logger.warning(f"DISCONNECT WebSocket切断: {e}")
                reconnect_attempts += 1
                await self._handle_reconnection(reconnect_attempts)
                
            except Exception as e:
                self.logger.error(f"ERROR WebSocket接続エラー: {e}")
                reconnect_attempts += 1
                await self._handle_reconnection(reconnect_attempts)
        
        self.logger.error("ERROR 最大再接続試行回数に到達")

    async def _message_loop(self):
        """メッセージ受信ループ"""
        self.logger.info("LOOP メッセージ受信開始")
        self.is_running = True
        message_count = 0
        
        try:
            async for message in self.websocket:
                message_count += 1
                start_time = time.time()
                
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    self.logger.debug(f"MSG メッセージ #{message_count}: {message_type}")
                    
                    # メッセージ処理
                    await self._handle_message(data)
                    
                    # 処理時間監視
                    process_time = (time.time() - start_time) * 1000
                    if process_time > 10:
                        self.logger.warning(f"SLOW 処理遅延: {process_time:.1f}ms")
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"ERROR JSON解析エラー: {e}")
                except Exception as e:
                    self.logger.error(f"ERROR メッセージ処理エラー: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("END WebSocket正常終了")
        finally:
            self.is_running = False
            self.logger.info(f"END メッセージループ終了: 総受信={message_count}")

    async def _handle_message(self, data: Dict[str, Any]):
        """メッセージ処理"""
        message_type = data.get("type")
        
        if message_type == "device_connected":
            await self._handle_device_connected(data)
        elif message_type == "sync_data_bulk_transmission":
            await self._handle_bulk_sync_data(data)
        elif message_type == "sync_relay":
            await self._handle_sync_relay(data)
        else:
            self.logger.debug(f"MSG 未処理メッセージ: {message_type}")

    async def _handle_device_connected(self, data: Dict[str, Any]):
        """デバイス接続確認"""
        message = data.get("message", "")
        server_time = data.get("server_time")
        
        self.logger.info(f"CONNECTED サーバー接続確認: {message}")
        self.logger.debug(f"TIME サーバー時刻: {server_time}")

    async def _handle_bulk_sync_data(self, data: Dict[str, Any]):
        """JSON同期データ一括受信処理"""
        self.logger.info("BULK 同期データ一括受信開始")
        
        try:
            session_id = data.get("session_id")
            video_id = data.get("video_id")
            metadata = data.get("transmission_metadata", {})
            sync_data = data.get("sync_data", {})
            
            # 受信データ情報表示
            total_size = metadata.get("total_size_kb", 0)
            total_events = metadata.get("total_events", 0)
            supported_events = metadata.get("supported_events", 0)
            
            self.logger.info(f"VIDEO 動画: {video_id}, サイズ: {total_size}KB")
            self.logger.info(f"EVENTS イベント: {total_events}件 (対応: {supported_events}件)")
            
            # チェックサム検証
            expected_checksum = metadata.get("checksum")
            if expected_checksum and not self._verify_checksum(sync_data, expected_checksum):
                raise ValueError(f"チェックサム不一致: 期待値={expected_checksum}")
            
            # ファイル保存
            file_path = await self._save_sync_data(video_id, sync_data)
            
            # エフェクトインデックス作成
            indexed_count = await self._index_effects(sync_data)
            
            # 受信確認送信
            await self._send_bulk_confirmation(
                session_id, video_id, file_path, metadata, indexed_count
            )
            
            self.logger.info(f"SUCCESS 同期データ準備完了: {indexed_count}エフェクト")
            
        except Exception as e:
            self.logger.error(f"ERROR 同期データ処理エラー: {e}")
            await self._send_bulk_error(session_id, str(e))

    async def _handle_sync_relay(self, data: Dict[str, Any]):
        """リアルタイム同期処理"""
        sync_data = data.get("sync_data", {})
        session_id = data.get("session_id")
        
        state = sync_data.get("state")
        time_pos = sync_data.get("time", 0.0)
        duration = sync_data.get("duration", 0.0)
        
        self.logger.info(f"SYNC 同期信号: {state} @ {time_pos:.3f}s / {duration:.1f}s")
        
        # エフェクト実行
        executed_effects = await self._execute_effects(state, time_pos)
        
        # 同期確認送信
        await self._send_sync_ack(session_id, sync_data, executed_effects)

    async def _save_sync_data(self, video_id: str, sync_data: Dict) -> str:
        """同期データ保存"""
        os.makedirs(self.config.sync_data_dir, exist_ok=True)
        
        file_path = f"{self.config.sync_data_dir}/{video_id}_sync.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sync_data, f, ensure_ascii=False, indent=2)
        
        file_size = os.path.getsize(file_path) / 1024
        self.logger.debug(f"SAVE ファイル保存: {file_path} ({file_size:.1f}KB)")
        
        # キャッシュに保存
        self.sync_data_cache = sync_data
        
        return file_path

    async def _index_effects(self, sync_data: Dict) -> int:
        """エフェクトインデックス作成"""
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
                    processed_effect = {
                        "actuator": effect.get("type", "UNKNOWN").upper(),
                        "intensity": self._mode_to_intensity(effect.get("mode", "default")),
                        "duration": self._estimate_duration(effect.get("action", ""), effect.get("mode", "")),
                        "pattern": effect.get("mode", "default"),
                        "original": effect
                    }
                    
                    self.time_effect_map[time_pos].append(processed_effect)
                    indexed_count += 1
        
        self.logger.debug(f"INDEX インデックス完了: {indexed_count}件")
        return indexed_count

    async def _execute_effects(self, state: str, time_pos: float) -> list:
        """エフェクト実行"""
        executed = []
        
        if state != "play":
            return executed
        
        # 時刻付近のエフェクト検索
        tolerance = 0.1
        
        for event_time, effects in self.time_effect_map.items():
            if abs(event_time - time_pos) <= tolerance:
                self.logger.debug(f"FOUND エフェクト発見: t={event_time:.3f}s")
                
                for effect in effects:
                    try:
                        result = await self._control_actuator(effect)
                        executed.append(result)
                        
                        # ログ出力（信号確認用）
                        self.logger.info(f"EFFECT エフェクト実行: {effect['actuator']} "
                                       f"強度={effect['intensity']:.1%} "
                                       f"時間={effect['duration']:.2f}s")
                        
                    except Exception as e:
                        self.logger.error(f"ERROR エフェクト実行エラー: {e}")
        
        if executed:
            self.logger.info(f"SUCCESS エフェクト完了: {len(executed)}件 @ {time_pos:.3f}s")
        
        return executed

    async def _control_actuator(self, effect: Dict) -> Dict:
        """アクチュエーター制御"""
        start_time = time.time()
        
        actuator = effect["actuator"]
        intensity = effect["intensity"]
        duration = effect["duration"]
        pattern = effect["pattern"]
        
        # ハードウェア制御実行
        if self.hardware_available:
            # 実際のハードウェア制御
            await self._hardware_control(actuator, intensity, duration, pattern)
        else:
            # シミュレーション
            await self._simulate_hardware(actuator, intensity, duration, pattern)
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "actuator": actuator,
            "intensity": intensity,
            "duration": duration,
            "pattern": pattern,
            "execution_time_ms": execution_time,
            "status": "completed"
        }

    async def _hardware_control(self, actuator: str, intensity: float, duration: float, pattern: str):
        """実際のハードウェア制御"""
        # TODO: 実際のGPIO/Arduino制御実装
        self.logger.debug(f"HW ハードウェア制御: {actuator}")
        await asyncio.sleep(min(duration, 0.01))

    async def _simulate_hardware(self, actuator: str, intensity: float, duration: float, pattern: str):
        """ハードウェア制御シミュレーション"""
        # PC環境での詳細シミュレーション
        gpio_pins = {
            "VIBRATION": 18, "WATER": 23, "WIND": 24, 
            "FLASH": 25, "COLOR": 12
        }
        
        pin = gpio_pins.get(actuator, 0)
        
        # 実際の制御をシミュレート
        self.logger.info(f"SIM [SIMULATION] GPIO{pin} {actuator} 制御開始")
        self.logger.info(f"SIM    強度: {intensity:.1%} (PWM値: {int(intensity * 255)})")
        self.logger.info(f"SIM    パターン: {pattern}")
        self.logger.info(f"SIM    持続時間: {duration:.2f}秒")
        
        # パターン別の視覚的フィードバック
        if pattern == "heartbeat":
            self.logger.info(f"SIM    HEARTBEAT効果実行中...")
        elif pattern == "pulse":
            self.logger.info(f"SIM    PULSE効果実行中...")
        elif pattern == "strong":
            self.logger.info(f"SIM    STRONG効果実行中...")
        elif pattern == "weak":
            self.logger.info(f"SIM    WEAK効果実行中...")
        else:
            self.logger.info(f"SIM    DEFAULT効果実行中...")
        
        # 実際の待機時間でリアルタイム感を演出
        await asyncio.sleep(min(duration, 2.0))
        
        self.logger.info(f"SIM [SIMULATION] GPIO{pin} {actuator} 制御完了")

    def _mode_to_intensity(self, mode: str) -> float:
        """モード→強度変換"""
        mode_map = {
            "strong": 1.0,
            "medium": 0.7,
            "weak": 0.3,
            "steady": 0.5,
            "heartbeat": 0.6,
            "default": 0.5
        }
        return mode_map.get(mode.lower(), 0.5)

    def _estimate_duration(self, action: str, mode: str) -> float:
        """持続時間推定"""
        if action == "shot":
            return 0.3
        elif action == "start" and mode in ["heartbeat", "steady"]:
            return 2.0
        elif action == "stop":
            return 0.0
        return 1.0

    def _verify_checksum(self, sync_data: Dict, expected: str) -> bool:
        """チェックサム検証"""
        data_str = json.dumps(sync_data, sort_keys=True, ensure_ascii=False)
        actual = hashlib.md5(data_str.encode('utf-8')).hexdigest()[:8]
        return actual == expected

    async def _send_device_status(self):
        """デバイス状態送信"""
        if not self.websocket or not self.device_id:
            return
        
        status_message = {
            "type": "device_status",
            "device_id": self.device_id,
            "status": "ready",
            "json_loaded": self.sync_data_cache is not None,
            "actuator_status": {
                "VIBRATION": "ready",
                "WATER": "ready",
                "WIND": "ready",
                "FLASH": "ready",
                "COLOR": "ready"
            },
            "performance_metrics": {
                "cpu_usage": self._get_cpu_usage(),
                "memory_usage": self._get_memory_usage(),
                "temperature": self._get_temperature(),
                "network_latency_ms": 25
            },
            "hardware_available": self.hardware_available,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self.websocket.send(json.dumps(status_message))
            self.logger.debug("SEND デバイス状態送信")
        except Exception as e:
            self.logger.error(f"ERROR 状態送信エラー: {e}")

    async def _send_bulk_confirmation(self, session_id: str, video_id: str, file_path: str, 
                                     metadata: Dict, indexed_count: int):
        """一括受信確認送信"""
        file_size_kb = os.path.getsize(file_path) / 1024
        
        confirmation = {
            "type": "sync_data_bulk_received",
            "session_id": session_id,
            "video_id": video_id,
            "reception_result": {
                "received": True,
                "saved_to_file": file_path,
                "verified_checksum": metadata.get("checksum"),
                "indexed_events": indexed_count,
                "file_size_kb": file_size_kb,
                "reception_timestamp": datetime.now().isoformat()
            },
            "device_status": {
                "storage_available_mb": self._get_storage_mb(),
                "ready_for_playback": True
            }
        }
        
        try:
            await self.websocket.send(json.dumps(confirmation))
            self.logger.debug(f"SEND 受信確認送信: {video_id}")
        except Exception as e:
            self.logger.error(f"ERROR 確認送信エラー: {e}")

    async def _send_bulk_error(self, session_id: str, error_msg: str):
        """一括受信エラー送信"""
        error_response = {
            "type": "sync_data_bulk_received",
            "session_id": session_id,
            "reception_result": {
                "received": False,
                "error": error_msg,
                "reception_timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            await self.websocket.send(json.dumps(error_response))
            self.logger.error(f"SEND エラー送信: {error_msg}")
        except Exception as e:
            self.logger.error(f"ERROR エラー送信失敗: {e}")

    async def _send_sync_ack(self, session_id: str, sync_data: Dict, executed_effects: list):
        """同期確認送信"""
        ack_message = {
            "type": "sync_ack",
            "session_id": session_id,
            "received_time": sync_data.get("time", 0.0),
            "received_state": sync_data.get("state"),
            "processing_delay_ms": 8,
            "effects_executed": executed_effects
        }
        
        try:
            await self.websocket.send(json.dumps(ack_message))
            self.logger.debug(f"SEND 同期確認: {len(executed_effects)}エフェクト")
        except Exception as e:
            self.logger.error(f"ERROR 同期確認エラー: {e}")

    async def _handle_reconnection(self, attempt: int):
        """再接続処理"""
        delay = min(2.0 * (2 ** (attempt - 1)), 60.0)
        self.logger.warning(f"RETRY 再接続待機 ({attempt}回目): {delay:.1f}秒後")
        await asyncio.sleep(delay)

    def _get_cpu_usage(self) -> float:
        """CPU使用率取得"""
        if self.config.pc_environment:
            # PC環境での簡易CPU使用率シミュレーション
            import random
            return random.uniform(10.0, 30.0)
        else:
            try:
                with open('/proc/loadavg', 'r') as f:
                    load_avg = float(f.read().split()[0])
                    return min(load_avg * 100, 100.0)
            except:
                return 15.0

    def _get_memory_usage(self) -> float:
        """メモリ使用率取得"""
        if self.config.pc_environment:
            # PC環境での簡易メモリ使用率シミュレーション
            import random
            return random.uniform(30.0, 60.0)
        else:
            try:
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                    mem_total = int([l for l in lines if 'MemTotal' in l][0].split()[1])
                    mem_avail = int([l for l in lines if 'MemAvailable' in l][0].split()[1])
                    return ((mem_total - mem_avail) / mem_total) * 100
            except:
                return 45.0

    def _get_temperature(self) -> float:
        """CPU温度取得"""
        if self.config.pc_environment:
            # PC環境での温度シミュレーション
            import random
            return random.uniform(35.0, 50.0)
        else:
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    return int(f.read().strip()) / 1000.0
            except:
                return 42.0

    def _get_storage_mb(self) -> float:
        """ストレージ容量取得"""
        try:
            import shutil
            _, _, free = shutil.disk_usage(self.config.sync_data_dir)
            return free / (1024 * 1024)
        except:
            return 500.0

    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        self.logger.info(f"SIGNAL シグナル受信: {signum}")
        self.is_running = False

    def stop(self):
        """アプリケーション停止"""
        self.logger.info("STOP アプリケーション停止")
        self.is_running = False

# ===============================
# メイン実行部分
# ===============================

async def main():
    """メイン関数"""
    print("=" * 60)
    print("START 4DX@HOME ラズベリーパイ システム起動 (PC環境)")
    print("=" * 60)
    
    # 設定読み込み
    config = AppConfig()
    
    # 引数からセッションID取得（オプション）
    if len(sys.argv) > 1:
        config.session_id = sys.argv[1]
        print(f"SESSION セッションID: {config.session_id}")
    
    # アプリケーション作成・起動
    app = FourDXHomeApp(config)
    
    try:
        await app.start()
    except KeyboardInterrupt:
        print("\nSTOP ユーザーによる停止")
    except Exception as e:
        print(f"ERROR 予期しないエラー: {e}")
        traceback.print_exc()
    finally:
        app.stop()
        print("END 4DX@HOME システム終了")

def run():
    """実行用エントリーポイント"""
    asyncio.run(main())

if __name__ == "__main__":
    run()