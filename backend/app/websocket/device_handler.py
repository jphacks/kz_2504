# app/websocket/device_handler.py - デバイス制御WebSocketハンドラー
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
import json
import logging
from datetime import datetime

from .manager import websocket_manager, ClientType
from app.models.session_models import session_manager

class DeviceHandler:
    """デバイス制御WebSocketハンドラー"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def handle_connection(self, websocket: WebSocket, session_id: str):
        """デバイスWebSocket接続処理"""
        # セッション存在確認
        session = session_manager.get_session(session_id)
        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return
            
        connection_id = None
        
        try:
            # WebSocket接続確立
            connection_id = await websocket_manager.connect(
                websocket, session_id, ClientType.DEVICE
            )
            
            # 接続確認メッセージ送信
            await websocket.send_json({
                "type": "connection_established",
                "message": "デバイス接続が確立されました",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # メッセージ受信ループ
            while True:
                # メッセージ受信待機
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # メッセージ処理
                await self._handle_device_message(session_id, message)
                
        except WebSocketDisconnect:
            self.logger.info(f"デバイス切断: セッション {session_id}")
            
        except Exception as e:
            self.logger.error(f"デバイスハンドラーエラー: セッション {session_id}, エラー: {e}")
            
        finally:
            # 切断処理
            if connection_id:
                websocket_manager.disconnect(websocket)
                
    async def _handle_device_message(self, session_id: str, message: Dict[str, Any]):
        """デバイスメッセージ処理"""
        message_type = message.get("type")
        
        self.logger.info(f"デバイスメッセージ: セッション {session_id}, タイプ: {message_type}")
        
        if message_type == "device_connected":
            await self._handle_device_connected(session_id, message)
            
        elif message_type == "device_ready":
            await self._handle_device_ready(session_id, message)
            
        elif message_type == "ready_for_playback":
            await self._handle_ready_for_playback(session_id, message)
            
        elif message_type == "effect_status":
            await self._handle_effect_status(session_id, message)
            
        elif message_type == "pong":
            await self._handle_pong(session_id, message)
            
        elif message_type == "error":
            await self._handle_device_error(session_id, message)
            
        else:
            # 未知のメッセージタイプ
            await websocket_manager.send_to_device(session_id, {
                "type": "error",
                "message": f"未対応のメッセージタイプ: {message_type}",
                "timestamp": datetime.now().isoformat()
            })
            
    async def _handle_device_connected(self, session_id: str, message: Dict[str, Any]):
        """デバイス接続通知処理"""
        device_info = message.get("device_info", {})
        
        # セッション状態更新
        session = session_manager.get_session(session_id)
        if session:
            session.status = "connected"
            
        # Webアプリに通知
        await websocket_manager.send_to_webapp(session_id, {
            "type": "device_ready",
            "message": "デバイスが接続され、準備完了です",
            "device_info": device_info,
            "timestamp": datetime.now().isoformat()
        })
        
        # デバイスに確認応答
        await websocket_manager.send_to_device(session_id, {
            "type": "connection_acknowledged",
            "message": "デバイス接続を確認しました",
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(f"デバイス接続確認: セッション {session_id}")
        
    async def _handle_device_ready(self, session_id: str, message: Dict[str, Any]):
        """デバイス準備完了処理"""
        device_info = message.get("device_info", {})
        
        # セッション状態更新
        session = session_manager.get_session(session_id)
        if session:
            session.status = "connected"
            
        # Webアプリに準備完了通知
        await websocket_manager.send_to_webapp(session_id, {
            "type": "device_ready",
            "message": "デバイスが準備完了しました",
            "device_info": device_info,
            "timestamp": datetime.now().isoformat()
        })
        
        # デバイスに確認応答
        await websocket_manager.send_to_device(session_id, {
            "type": "ready_acknowledged",
            "message": "デバイス準備完了を確認しました",
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(f"デバイス準備完了: セッション {session_id}")
        
    async def _handle_ready_for_playback(self, session_id: str, message: Dict[str, Any]):
        """再生準備完了通知処理"""
        video_id = message.get("video_id")
        capabilities = message.get("capabilities", [])
        
        # Webアプリに準備完了通知
        await websocket_manager.send_to_webapp(session_id, {
            "type": "playback_ready",
            "message": "デバイス再生準備完了",
            "video_id": video_id,
            "capabilities": capabilities,
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(f"再生準備完了: セッション {session_id}, 動画 {video_id}")
        
    async def _handle_effect_status(self, session_id: str, message: Dict[str, Any]):
        """エフェクト実行状態通知処理"""
        effect_id = message.get("effect_id")
        status = message.get("status")  # started, completed, failed
        
        # Webアプリに状態通知
        await websocket_manager.send_to_webapp(session_id, {
            "type": "effect_status_update",
            "effect_id": effect_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.debug(f"エフェクト状態: セッション {session_id}, ID {effect_id}, 状態 {status}")
        
    async def _handle_pong(self, session_id: str, message: Dict[str, Any]):
        """pong応答処理"""
        # 接続情報更新（ping時刻更新）
        pass
        
    async def _handle_device_error(self, session_id: str, message: Dict[str, Any]):
        """デバイスエラー処理"""
        error_code = message.get("error_code")
        error_message = message.get("message", "デバイスエラーが発生しました")
        
        # Webアプリにエラー通知
        await websocket_manager.send_to_webapp(session_id, {
            "type": "device_error",
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.error(f"デバイスエラー: セッション {session_id}, コード {error_code}, メッセージ: {error_message}")
        
    # デバイスへのコマンド送信メソッド
    
    async def send_prepare_playback(self, session_id: str, video_id: str, sync_data: Dict[str, Any]) -> bool:
        """再生準備コマンド送信"""
        message = {
            "type": "prepare_playback",
            "video_id": video_id,
            "sync_data": sync_data,
            "timestamp": datetime.now().isoformat()
        }
        
        sent_count = await websocket_manager.send_to_device(session_id, message)
        self.logger.info(f"再生準備コマンド送信: セッション {session_id}, 動画 {video_id}")
        
        return sent_count > 0
        
    async def send_effect_command(self, session_id: str, effect_data: Dict[str, Any]) -> bool:
        """エフェクト実行コマンド送信"""
        message = {
            "type": "effect_command",
            "effect_id": effect_data.get("effect_id"),
            "action": effect_data.get("action"),
            "intensity": effect_data.get("intensity"),
            "duration": effect_data.get("duration"),
            "timestamp": datetime.now().isoformat()
        }
        
        sent_count = await websocket_manager.send_to_device(session_id, message)
        self.logger.debug(f"エフェクトコマンド送信: セッション {session_id}, アクション {effect_data.get('action')}")
        
        return sent_count > 0
        
    async def send_stop_playback(self, session_id: str) -> bool:
        """再生停止コマンド送信"""
        message = {
            "type": "stop_playback",
            "timestamp": datetime.now().isoformat()
        }
        
        sent_count = await websocket_manager.send_to_device(session_id, message)
        self.logger.info(f"再生停止コマンド送信: セッション {session_id}")
        
        return sent_count > 0

# グローバル関数（main.pyから呼び出し用）
async def handle_device_message(session_id: str, message: Dict[str, Any], ws_manager):
    """デバイスメッセージ処理のグローバル関数"""
    device_handler = DeviceHandler()
    await device_handler._handle_device_message(session_id, message)

# グローバルデバイスハンドラー
device_handler = DeviceHandler()