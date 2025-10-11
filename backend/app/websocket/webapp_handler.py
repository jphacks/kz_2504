# app/websocket/webapp_handler.py - Webアプリ同期WebSocketハンドラー
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime

from .manager import websocket_manager, ClientType
from .device_handler import device_handler
from app.models.session_models import session_manager
from app.services.video_service import VideoService
from app.config.settings import Settings

class WebAppHandler:
    """Webアプリ同期WebSocketハンドラー"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.video_service = VideoService(Settings())
        
    async def handle_connection(self, websocket: WebSocket, session_id: str):
        """WebアプリWebSocket接続処理"""
        # セッション存在確認
        session = session_manager.get_session(session_id)
        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return
            
        connection_id = None
        
        try:
            # WebSocket接続確立
            connection_id = await websocket_manager.connect(
                websocket, session_id, ClientType.WEBAPP
            )
            
            # 接続確認メッセージ送信
            await websocket.send_json({
                "type": "connection_established",
                "message": "Webアプリ接続が確立されました",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # 現在のセッション状態通知
            await self._send_session_status(session_id)
            
            # メッセージ受信ループ
            while True:
                # メッセージ受信待機
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # メッセージ処理
                await self._handle_webapp_message(session_id, message)
                
        except WebSocketDisconnect:
            self.logger.info(f"Webアプリ切断: セッション {session_id}")
            
        except Exception as e:
            self.logger.error(f"Webアプリハンドラーエラー: セッション {session_id}, エラー: {e}")
            
        finally:
            # 切断処理
            if connection_id:
                websocket_manager.disconnect(websocket)
                
    async def _handle_webapp_message(self, session_id: str, message: Dict[str, Any]):
        """Webアプリメッセージ処理"""
        message_type = message.get("type")
        
        self.logger.info(f"Webアプリメッセージ: セッション {session_id}, タイプ: {message_type}")
        
        if message_type == "start_playback":
            await self._handle_start_playback(session_id, message)
            
        elif message_type == "playback_sync":
            await self._handle_playback_sync(session_id, message)
            
        elif message_type == "end_playback":
            await self._handle_end_playback(session_id, message)
            
        elif message_type == "pause_playback":
            await self._handle_pause_playback(session_id, message)
            
        elif message_type == "resume_playback":
            await self._handle_resume_playback(session_id, message)
            
        elif message_type == "pong":
            await self._handle_pong(session_id, message)
            
        else:
            # 未知のメッセージタイプ
            await websocket_manager.send_to_webapp(session_id, {
                "type": "error",
                "message": f"未対応のメッセージタイプ: {message_type}",
                "timestamp": datetime.now().isoformat()
            })
            
    async def _handle_start_playback(self, session_id: str, message: Dict[str, Any]):
        """再生開始処理"""
        video_id = message.get("video_id")
        
        if not video_id:
            await websocket_manager.send_to_webapp(session_id, {
                "type": "error",
                "message": "video_idが指定されていません",
                "timestamp": datetime.now().isoformat()
            })
            return
            
        # 同期データ取得
        sync_data = self.video_service.get_sync_data(video_id)
        if not sync_data:
            await websocket_manager.send_to_webapp(session_id, {
                "type": "error",
                "message": f"同期データが見つかりません: {video_id}",
                "timestamp": datetime.now().isoformat()
            })
            return
            
        # セッション状態更新
        session = session_manager.get_session(session_id)
        if session:
            session.status = "playing"
            
        # デバイスに再生準備コマンド送信
        success = await device_handler.send_prepare_playback(
            session_id, video_id, sync_data.dict()
        )
        
        if success:
            # Webアプリに開始確認
            await websocket_manager.send_to_webapp(session_id, {
                "type": "playback_started",
                "video_id": video_id,
                "message": "再生が開始されました",
                "timestamp": datetime.now().isoformat()
            })
        else:
            # デバイス未接続
            await websocket_manager.send_to_webapp(session_id, {
                "type": "error",
                "message": "デバイスが接続されていません",
                "timestamp": datetime.now().isoformat()
            })
            
        self.logger.info(f"再生開始: セッション {session_id}, 動画 {video_id}")
        
    async def _handle_playback_sync(self, session_id: str, message: Dict[str, Any]):
        """再生同期処理"""
        current_time = message.get("current_time")
        video_id = message.get("video_id")
        
        if current_time is None or not video_id:
            return
            
        # 同期イベント検索
        sync_events = self.video_service.get_sync_events_for_timeframe(
            video_id, current_time - 0.5, current_time + 0.5
        )
        
        # エフェクトコマンド送信
        for event in sync_events:
            effect_data = {
                "effect_id": f"{video_id}_{event.time}_{event.action}",
                "action": event.action,
                "intensity": event.intensity,
                "duration": event.duration
            }
            
            await device_handler.send_effect_command(session_id, effect_data)
            
        # 同期確認応答
        await websocket_manager.send_to_webapp(session_id, {
            "type": "sync_acknowledged",
            "current_time": current_time,
            "events_sent": len(sync_events),
            "timestamp": datetime.now().isoformat()
        })
        
        if sync_events:
            self.logger.debug(f"同期処理: セッション {session_id}, 時刻 {current_time}, イベント数 {len(sync_events)}")
        
    async def _handle_end_playback(self, session_id: str, message: Dict[str, Any]):
        """再生終了処理"""
        video_id = message.get("video_id")
        
        # セッション状態更新
        session = session_manager.get_session(session_id)
        if session:
            session.status = "connected"
            
        # デバイスに停止コマンド送信
        await device_handler.send_stop_playback(session_id)
        
        # Webアプリに終了確認
        await websocket_manager.send_to_webapp(session_id, {
            "type": "playback_ended",
            "video_id": video_id,
            "message": "再生が終了しました",
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(f"再生終了: セッション {session_id}, 動画 {video_id}")
        
    async def _handle_pause_playback(self, session_id: str, message: Dict[str, Any]):
        """再生一時停止処理"""
        current_time = message.get("current_time")
        
        # デバイスに一時停止通知
        await websocket_manager.send_to_device(session_id, {
            "type": "playback_paused",
            "current_time": current_time,
            "timestamp": datetime.now().isoformat()
        })
        
        # Webアプリに確認
        await websocket_manager.send_to_webapp(session_id, {
            "type": "pause_acknowledged",
            "current_time": current_time,
            "timestamp": datetime.now().isoformat()
        })
        
    async def _handle_resume_playback(self, session_id: str, message: Dict[str, Any]):
        """再生再開処理"""
        current_time = message.get("current_time")
        
        # デバイスに再開通知
        await websocket_manager.send_to_device(session_id, {
            "type": "playback_resumed",
            "current_time": current_time,
            "timestamp": datetime.now().isoformat()
        })
        
        # Webアプリに確認
        await websocket_manager.send_to_webapp(session_id, {
            "type": "resume_acknowledged",
            "current_time": current_time,
            "timestamp": datetime.now().isoformat()
        })
        
    async def _handle_pong(self, session_id: str, message: Dict[str, Any]):
        """pong応答処理"""
        # 接続情報更新
        pass
        
    async def _send_session_status(self, session_id: str):
        """セッション状態通知"""
        session = session_manager.get_session(session_id)
        websocket_info = websocket_manager.get_session_info(session_id)
        
        status_message = {
            "type": "session_status",
            "session_info": session.to_dict() if session else None,
            "connections": websocket_info,
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket_manager.send_to_webapp(session_id, status_message)
        
    # Webアプリへの通知メソッド
    
    async def notify_device_ready(self, session_id: str, device_info: Dict[str, Any]):
        """デバイス準備完了通知"""
        await websocket_manager.send_to_webapp(session_id, {
            "type": "device_ready",
            "message": "デバイスが準備完了しました",
            "device_info": device_info,
            "timestamp": datetime.now().isoformat()
        })
        
    async def notify_device_error(self, session_id: str, error_info: Dict[str, Any]):
        """デバイスエラー通知"""
        await websocket_manager.send_to_webapp(session_id, {
            "type": "device_error",
            "error_info": error_info,
            "timestamp": datetime.now().isoformat()
        })

# グローバル関数（main.pyから呼び出し用）
async def handle_webapp_message(session_id: str, message: Dict[str, Any], ws_manager):
    """Webアプリメッセージ処理のグローバル関数"""
    webapp_handler = WebAppHandler()
    await webapp_handler._handle_webapp_message(session_id, message)

# グローバルWebアプリハンドラー
webapp_handler = WebAppHandler()