"""
Phase B-3: 再生制御API - WebSocket基本接続実装

receiver.pyのパターンを参考にしたシンプルなWebSocket接続管理
段階的実装のStep 1: 基本的なWebSocket接続とメッセージ受信
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging
from typing import Dict, Set
import asyncio
from datetime import datetime

# ロガー設定
logger = logging.getLogger(__name__)

# APIルーター作成
router = APIRouter(prefix="/api/playback", tags=["playback"])

class SimpleWebSocketManager:
    """
    シンプルなWebSocket接続管理
    receiver.pyのパターンを参考にした基本実装
    """
    def __init__(self):
        # アクティブな接続を管理
        self.active_connections: Dict[str, WebSocket] = {}
        # セッション別接続リスト  
        self.session_connections: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, connection_id: str, session_id: str):
        """WebSocket接続を受け入れて管理開始"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        # セッション別管理
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)
        
        logger.info(f"[WS] 接続受け入れ: {connection_id} (session: {session_id})")
        
    async def disconnect(self, connection_id: str, session_id: str):
        """WebSocket接続を切断・クリーンアップ"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            
        if session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            # セッションに接続がなくなったら削除
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
                
        logger.info(f"[WS] 接続切断: {connection_id} (session: {session_id})")
        
    async def send_to_session(self, session_id: str, message: dict):
        """セッション内の全接続にメッセージ送信"""
        logger.info(f"[WS] セッションメッセージ送信開始: session={session_id}, connections={len(self.session_connections.get(session_id, []))}")
        
        if session_id not in self.session_connections:
            logger.warning(f"[WS] セッションが存在しません: {session_id}")
            return
            
        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for connection_id in self.session_connections[session_id]:
            websocket = self.active_connections.get(connection_id)
            if websocket:
                try:
                    await websocket.send_text(message_json)
                    logger.info(f"[WS] メッセージ送信成功: {connection_id}")
                except Exception as e:
                    logger.error(f"[WS] 送信エラー {connection_id}: {e}")
                    disconnected.append(connection_id)
            else:
                logger.warning(f"[WS] WebSocket接続が見つかりません: {connection_id}")
                    
        # 切断されたコネクションをクリーンアップ
        for connection_id in disconnected:
            await self.disconnect(connection_id, session_id)

# WebSocketManager インスタンス
ws_manager = SimpleWebSocketManager()

# ================================================================================
# WebSocket エンドポイント
# ================================================================================

@router.websocket("/ws/sync/{session_id}")
async def sync_websocket(websocket: WebSocket, session_id: str):
    """
    フロントエンド同期用WebSocket接続
    ws_video_sync_sender.htmlからの接続を受け付ける
    
    receiver.pyのhandler()関数パターンを参考
    """
    # ユニークな接続IDを生成
    connection_id = f"frontend_{session_id}_{datetime.now().strftime('%H%M%S')}"
    
    try:
        # 接続受け入れ
        await ws_manager.connect(websocket, connection_id, session_id)
        
        # 接続確認メッセージ送信
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "connection_id": connection_id,
            "session_id": session_id,
            "server_time": datetime.now().isoformat(),
            "message": "WebSocket接続が確立されました"
        }))
        
        # FastAPI WebSocket 受信ループ (receiver.pyパターンを調整)
        while True:
            try:
                # FastAPIのWebSocketからメッセージを受信
                message = await websocket.receive_text()
                logger.info(f"[WS] 受信 ({connection_id}): {message}")
                
                # JSONメッセージを解析
                data = json.loads(message)
                await handle_sync_message(session_id, connection_id, data)
                
            except json.JSONDecodeError:
                logger.error(f"[WS] JSON解析エラー: {message}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "無効なJSONフォーマット",
                    "received": message
                }))
                
            except Exception as e:
                logger.error(f"[WS] メッセージ処理エラー: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": f"メッセージ処理エラー: {str(e)}"
                }))
                break  # エラー時はループ終了
                
    except WebSocketDisconnect:
        logger.info(f"[WS] 接続が切断されました: {connection_id}")
        
    except Exception as e:
        logger.error(f"[WS] 接続エラー ({connection_id}): {e}")
        
    finally:
        # クリーンアップ
        await ws_manager.disconnect(connection_id, session_id)

@router.websocket("/ws/device/{session_id}")  
async def device_websocket(websocket: WebSocket, session_id: str):
    """
    デバイスハブ用WebSocket接続
    将来の実デバイス接続用
    """
    connection_id = f"device_{session_id}_{datetime.now().strftime('%H%M%S')}"
    
    try:
        await ws_manager.connect(websocket, connection_id, session_id)
        
        # デバイス接続確認
        await websocket.send_text(json.dumps({
            "type": "device_connected",
            "connection_id": connection_id,
            "session_id": session_id,
            "server_time": datetime.now().isoformat()
        }))
        
        while True:
            try:
                message = await websocket.receive_text()
                logger.info(f"[WS] デバイス受信 ({connection_id}): {message}")
                
                data = json.loads(message)
                await handle_device_message(session_id, connection_id, data)
                
            except Exception as e:
                logger.error(f"[WS] デバイスメッセージエラー: {e}")
                break  # エラー時はループ終了
                
    except WebSocketDisconnect:
        logger.info(f"[WS] デバイス接続切断: {connection_id}")
        
    finally:
        await ws_manager.disconnect(connection_id, session_id)

# ================================================================================
# メッセージハンドラー
# ================================================================================

async def handle_sync_message(session_id: str, connection_id: str, data: dict):
    """
    同期メッセージ処理
    ws_video_sync_sender.htmlからのメッセージを処理
    """
    message_type = data.get("type")
    logger.info(f"[SYNC] メッセージ処理開始: type={message_type}, session={session_id}, connection={connection_id}")
    
    if message_type == "hello":
        # 接続確認メッセージ
        logger.info(f"[SYNC] Hello受信: {data.get('agent', 'unknown')} from {connection_id}")
        response_message = {
            "type": "hello_ack",
            "message": "接続を確認しました",
            "server_time": datetime.now().isoformat()
        }
        logger.info(f"[SYNC] Hello応答送信: {response_message}")
        await ws_manager.send_to_session(session_id, response_message)
        
    elif message_type == "sync":
        # 動画同期メッセージ
        current_time = data.get("time", 0)
        state = data.get("state", "unknown")
        
        logger.info(f"[SYNC] 動画同期: {state} at {current_time}s (session: {session_id})")
        
        # 基本的な応答（実際の効果処理は後のステップで実装）
        await ws_manager.send_to_session(session_id, {
            "type": "sync_ack",
            "session_id": session_id,
            "received_time": current_time,
            "received_state": state,
            "server_time": datetime.now().isoformat()
        })
        
    else:
        logger.warning(f"[SYNC] 未知のメッセージタイプ: {message_type}")

async def handle_device_message(session_id: str, connection_id: str, data: dict):
    """
    デバイスメッセージ処理
    将来的な実デバイス通信用
    """
    message_type = data.get("type")
    
    logger.info(f"[DEVICE] メッセージ受信: {message_type} from {connection_id}")
    
    # 基本的な応答
    await ws_manager.send_to_session(session_id, {
        "type": "device_ack",
        "received_type": message_type,
        "server_time": datetime.now().isoformat()
    })

# ================================================================================
# REST API エンドポイント（基本情報）
# ================================================================================

@router.get("/status")
async def get_playback_status():
    """再生制御システム状態取得"""
    return {
        "service": "playback_control",
        "version": "0.1.0",
        "status": "running", 
        "active_connections": len(ws_manager.active_connections),
        "active_sessions": len(ws_manager.session_connections),
        "server_time": datetime.now().isoformat()
    }

@router.get("/connections")
async def get_connections():
    """アクティブ接続情報"""
    return {
        "total_connections": len(ws_manager.active_connections),
        "session_count": len(ws_manager.session_connections),
        "sessions": {
            session_id: len(connections) 
            for session_id, connections in ws_manager.session_connections.items()
        }
    }