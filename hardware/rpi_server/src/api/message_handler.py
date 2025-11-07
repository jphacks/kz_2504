"""
4DX@HOME WebSocket Message Handler
Cloud Run APIから受信したメッセージを処理し、適切なアクションを実行
"""

import logging
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketMessageHandler:
    """WebSocketメッセージハンドラー"""
    
    def __init__(
        self,
        on_sync_data: Optional[Callable[[Dict], None]] = None,
        on_sync_time: Optional[Callable[[float], None]] = None,
        on_control_command: Optional[Callable[[Dict], None]] = None,
        on_device_test: Optional[Callable[[Dict], None]] = None,
        on_video_sync: Optional[Callable[[Dict], None]] = None,
        on_stop_signal: Optional[Callable[[Dict], None]] = None
    ):
        """
        Args:
            on_sync_data: タイムラインデータ受信時のコールバック
            on_sync_time: 同期時刻受信時のコールバック
            on_control_command: 制御コマンド受信時のコールバック
            on_device_test: デバイステスト受信時のコールバック
            on_video_sync: 動画同期受信時のコールバック
            on_stop_signal: ストップ信号受信時のコールバック
        """
        self.on_sync_data = on_sync_data
        self.on_sync_time = on_sync_time
        self.on_control_command = on_control_command
        self.on_device_test = on_device_test
        self.on_video_sync = on_video_sync
        self.on_stop_signal = on_stop_signal
    
    def handle_message(self, message: Dict[str, Any]) -> None:
        """受信メッセージを処理
        
        Args:
            message: WebSocketから受信したメッセージ
        """
        message_type = message.get("type", "unknown")
        
        logger.debug(f"メッセージ処理開始: type={message_type}")
        
        # メッセージタイプ別処理
        if message_type == "sync_data_bulk_transmission":
            self._handle_sync_data_bulk(message)
        
        elif message_type == "sync":
            self._handle_sync(message)
        
        elif message_type == "video_sync":
            self._handle_video_sync(message)
        
        elif message_type == "sync_ack":
            self._handle_sync_ack(message)
        
        elif message_type == "control":
            self._handle_control(message)
        
        elif message_type == "device_test":
            self._handle_device_test(message)
        
        elif message_type == "stop_signal":
            self._handle_stop_signal(message)
        
        elif message_type == "device_ack":
            self._handle_device_ack(message)
        
        elif message_type == "device_connected":
            self._handle_device_connected(message)
        
        elif message_type == "ping":
            self._handle_ping(message)
        
        elif message_type == "pong":
            self._handle_pong(message)
        
        else:
            logger.warning(f"未知のメッセージタイプ: {message_type}")
    
    def _handle_sync_data_bulk(self, message: Dict[str, Any]) -> None:
        """タイムラインデータ一括送信メッセージを処理
        
        メッセージ形式:
        {
            "type": "sync_data_bulk_transmission",
            "session_id": "demo1",
            "video_id": "demo1",
            "transmission_metadata": {...},
            "sync_data": {
                "timeline": [
                    {"t": 0, "effect": "vibration", "mode": "strong", "action": "start"},
                    ...
                ]
            }
        }
        """
        try:
            # バックエンドからの実際のメッセージ構造に対応
            session_id = message.get("session_id")
            video_id = message.get("video_id")
            sync_data = message.get("sync_data", {})
            timeline = sync_data.get("timeline", [])
            
            logger.info(
                f"タイムラインデータ受信: session_id={session_id}, "
                f"video_id={video_id}, events={len(timeline)}"
            )
            
            # コールバック実行（sync_dataとメタデータをまとめて渡す）
            if self.on_sync_data:
                full_data = {
                    "session_id": session_id,
                    "video_id": video_id,
                    "sync_data": sync_data,
                    "transmission_metadata": message.get("transmission_metadata", {})
                }
                self.on_sync_data(full_data)
        
        except Exception as e:
            logger.error(f"sync_data_bulk処理エラー: {e}", exc_info=True)
    
    def _handle_sync(self, message: Dict[str, Any]) -> None:
        """同期時刻メッセージを処理
        
        メッセージ形式:
        {
            "type": "sync",
            "currentTime": 12.5,
            "timestamp": "2025-01-06T10:30:00Z"
        }
        """
        try:
            current_time = message.get("currentTime")
            
            if current_time is not None:
                logger.debug(f"同期時刻受信: {current_time}秒")
                
                # コールバック実行
                if self.on_sync_time:
                    self.on_sync_time(current_time)
            else:
                logger.warning("currentTimeがありません")
        
        except Exception as e:
            logger.error(f"sync処理エラー: {e}", exc_info=True)
    
    def _handle_video_sync(self, message: Dict[str, Any]) -> None:
        """動画同期メッセージを処理
        
        メッセージ形式:
        {
            "type": "video_sync",
            "session_id": "demo1",
            "video_time": 12.5,
            "video_state": "play" | "pause" | "seeking" | "seeked",
            "video_duration": 120.0,
            "client_timestamp": 1234567890,
            "server_timestamp": 1234567891
        }
        """
        try:
            video_time = message.get("video_time", 0)
            video_state = message.get("video_state", "unknown")
            
            logger.info(f"🎬 動画同期受信: state={video_state}, time={video_time:.2f}秒")
            
            # on_video_syncコールバックがあれば実行
            if self.on_video_sync:
                self.on_video_sync({
                    "video_time": video_time,
                    "video_state": video_state,
                    "video_duration": message.get("video_duration"),
                    "session_id": message.get("session_id")
                })
            # なければon_sync_timeにフォールバック（既存の同期処理）
            elif self.on_sync_time and video_state == "play":
                self.on_sync_time(video_time)
        
        except Exception as e:
            logger.error(f"video_sync処理エラー: {e}", exc_info=True)
    
    def _handle_sync_ack(self, message: Dict[str, Any]) -> None:
        """同期確認応答メッセージを処理
        
        メッセージ形式:
        {
            "type": "sync_ack",
            "session_id": "demo1",
            "received_time": 12.5,
            "received_state": "play",
            "server_time": "2025-11-07T10:30:00Z",
            "relayed_to_devices": true
        }
        """
        try:
            received_time = message.get("received_time", 0)
            received_state = message.get("received_state", "unknown")
            relayed = message.get("relayed_to_devices", False)
            
            logger.debug(
                f"同期ACK受信: state={received_state}, time={received_time}秒, "
                f"relayed={relayed}"
            )
            
            # 必要に応じてログ記録のみ（アクションは不要）
        
        except Exception as e:
            logger.error(f"sync_ack処理エラー: {e}", exc_info=True)
    
    def _handle_control(self, message: Dict[str, Any]) -> None:
        """制御コマンドメッセージを処理
        
        メッセージ形式:
        {
            "type": "control",
            "command": "start_playback" | "stop_playback" | "reset",
            "params": {...}
        }
        """
        try:
            command = message.get("command")
            params = message.get("params", {})
            
            logger.info(f"制御コマンド受信: command={command}")
            
            # コールバック実行
            if self.on_control_command:
                self.on_control_command({
                    "command": command,
                    "params": params
                })
        
        except Exception as e:
            logger.error(f"control処理エラー: {e}", exc_info=True)
    
    def _handle_device_test(self, message: Dict[str, Any]) -> None:
        """デバイステストメッセージを処理
        
        メッセージ形式:
        {
            "type": "device_test",
            "session_id": "demo1",
            "test_type": "basic",
            "timestamp": "2025-11-07T10:30:00Z"
        }
        """
        try:
            session_id = message.get("session_id")
            test_type = message.get("test_type", "basic")
            
            logger.info(f"🧪 デバイステスト受信: session_id={session_id}, test_type={test_type}")
            
            # コールバック実行
            if self.on_device_test:
                self.on_device_test({
                    "session_id": session_id,
                    "test_type": test_type,
                    "timestamp": message.get("timestamp")
                })
        
        except Exception as e:
            logger.error(f"device_test処理エラー: {e}", exc_info=True)
    
    def _handle_stop_signal(self, message: Dict[str, Any]) -> None:
        """ストップ信号メッセージを処理（全アクチュエータ停止）
        
        メッセージ形式:
        {
            "type": "stop_signal",
            "session_id": "session_xyz",
            "timestamp": 1699999999.999,
            "message": "stop_all_actuators",
            "action": "stop_all",
            "source": "websocket" | "rest"
        }
        """
        try:
            session_id = message.get("session_id")
            action = message.get("action", "stop_all")
            source = message.get("source", "unknown")
            
            logger.info(
                f"🛑 ストップ信号受信: session_id={session_id}, "
                f"action={action}, source={source}"
            )
            
            # コールバック実行（全アクチュエータ停止処理）
            if self.on_stop_signal:
                self.on_stop_signal({
                    "session_id": session_id,
                    "action": action,
                    "timestamp": message.get("timestamp"),
                    "source": source
                })
            else:
                logger.warning("on_stop_signal コールバックが未設定です")
        
        except Exception as e:
            logger.error(f"stop_signal処理エラー: {e}", exc_info=True)
    
    def _handle_device_ack(self, message: Dict[str, Any]) -> None:
        """デバイス接続確認応答メッセージを処理
        
        実際のメッセージ形式（バックエンドから送信）:
        {
            "type": "device_ack",
            "received_type": "device_status" | "device_test_result" | etc.,
            "device_id": "DH001" (オプション),
            "server_time": "2025-11-07T10:30:00Z"
        }
        """
        try:
            # デバッグ: 実際のメッセージ構造を確認
            logger.debug(f"device_ack 受信メッセージ全体: {message}")
            
            # バックエンドからの実際のフィールド名に対応
            received_type = message.get("received_type", "unknown")
            device_id = message.get("device_id")
            server_time = message.get("server_time")
            
            logger.info(
                f"✅ デバイスACK受信: received_type={received_type}, "
                f"device_id={device_id}, server_time={server_time}"
            )
            
            # 必要に応じてログ記録のみ（アクションは不要）
        
        except Exception as e:
            logger.error(f"device_ack処理エラー: {e}", exc_info=True)
    
    def _handle_device_connected(self, message: Dict[str, Any]) -> None:
        """デバイス接続通知メッセージを処理
        
        実際のメッセージ形式（バックエンドから送信）:
        {
            "type": "device_connected",
            "connection_id": "conn_abc123",
            "session_id": "demo1",
            "server_time": "2025-11-07T10:30:00Z"
        }
        """
        try:
            # デバッグ: 実際のメッセージ構造を確認
            logger.debug(f"device_connected 受信メッセージ全体: {message}")
            
            # バックエンドからの実際のフィールド名に対応
            connection_id = message.get("connection_id")
            session_id = message.get("session_id")
            server_time = message.get("server_time")
            
            logger.info(
                f"🔌 デバイス接続通知受信: connection_id={connection_id}, "
                f"session_id={session_id}, server_time={server_time}"
            )
            
            # 必要に応じてログ記録のみ（アクションは不要）
        
        except Exception as e:
            logger.error(f"device_connected処理エラー: {e}", exc_info=True)
    
    def _handle_ping(self, message: Dict[str, Any]) -> None:
        """Pingメッセージを処理（ログのみ）"""
        logger.debug("Ping受信")
    
    def _handle_pong(self, message: Dict[str, Any]) -> None:
        """Pongメッセージを処理（ログのみ）"""
        logger.debug("Pong受信")
