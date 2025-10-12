"""
Phase B-3: 再生制御API - WebSocket同期システム

包括的な再生制御とリアルタイム同期機能
新しいPydanticモデルを使用した型安全な実装
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import json
import logging
from typing import Dict, Set
import asyncio
from datetime import datetime

# 簡素化されたPlaybackモデルをインポート
from app.models.playback import (
    SyncMessage, DeviceStatus,
    ConnectionEstablished, SyncAcknowledge, DeviceConnected,
    create_relay_data, validate_sync_message, validate_device_status
)

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
        
    async def _safe_send_text(self, websocket: WebSocket, message_json: str, connection_id: str) -> tuple[str, bool]:
        """安全なメッセージ送信（並列化用）"""
        try:
            await websocket.send_text(message_json)
            logger.info(f"[WS] メッセージ送信成功: {connection_id}")
            return connection_id, True
        except Exception as e:
            logger.warning(f"[WS] 送信エラー {connection_id}: {e}")
            return connection_id, False

    async def send_to_session(self, session_id: str, message: dict):
        """セッション内の全接続にメッセージ並列送信"""
        if session_id not in self.session_connections:
            logger.warning(f"[WS] セッションが存在しません: {session_id}")
            return
        
        connection_count = len(self.session_connections[session_id])
        logger.info(f"[WS] セッションメッセージ並列送信開始: session={session_id}, connections={connection_count}")
            
        message_json = json.dumps(message, ensure_ascii=False)
        send_tasks = []
        
        # 送信タスク作成
        for connection_id in list(self.session_connections[session_id]):  # listでコピー
            websocket = self.active_connections.get(connection_id)
            if websocket:
                task = asyncio.create_task(
                    self._safe_send_text(websocket, message_json, connection_id)
                )
                send_tasks.append(task)
            else:
                logger.warning(f"[WS] WebSocket接続が見つかりません: {connection_id}")
        
        # 並列実行
        if send_tasks:
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*send_tasks, return_exceptions=True),
                    timeout=1.5
                )
                
                # 失敗した接続を特定してクリーンアップ
                disconnected = []
                success_count = 0
                
                for result in results:
                    if isinstance(result, tuple):
                        connection_id, success = result
                        if success:
                            success_count += 1
                        else:
                            disconnected.append(connection_id)
                    elif isinstance(result, Exception):
                        logger.error(f"[WS] 送信タスクでエラー: {result}")
                
                logger.info(f"[WS] 並列送信完了: {success_count}/{len(send_tasks)} 成功")
                
                # 失敗した接続をクリーンアップ
                for connection_id in disconnected:
                    await self.disconnect(connection_id, session_id)
                    
            except asyncio.TimeoutError:
                logger.warning(f"[WS] セッション送信がタイムアウト: {session_id}")
                for task in send_tasks:
                    if not task.done():
                        task.cancel()
            except Exception as e:
                logger.error(f"[WS] 並列送信でエラー: {e}")

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
        
        # 接続確認メッセージ送信（Pydanticモデル使用）
        connection_msg = ConnectionEstablished(
            connection_id=connection_id,
            session_id=session_id
        )
        await websocket.send_text(connection_msg.json())
        
        # FastAPI WebSocket 受信ループ (receiver.pyパターンを調整)
        while True:
            try:
                # FastAPIのWebSocketからメッセージを受信
                message = await websocket.receive_text()
                logger.info(f"[WS] 受信 ({connection_id}): {message}")
                
                # JSONメッセージを解析
                data = json.loads(message)
                await handle_sync_message(session_id, connection_id, data)
                
            except WebSocketDisconnect as e:
                # 正常な切断 (1000) はログレベルを下げる
                if e.code == 1000:
                    logger.info(f"[WS] 正常切断 ({connection_id}): {e}")
                else:
                    logger.warning(f"[WS] 異常切断 ({connection_id}): {e}")
                break
                
            except json.JSONDecodeError:
                logger.error(f"[WS] JSON解析エラー: {message}")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "無効なJSONフォーマット",
                        "received": message
                    }))
                except:
                    logger.warning(f"[WS] エラー応答送信失敗: 接続切断済み")
                    break
                
            except Exception as e:
                logger.error(f"[WS] メッセージ処理エラー: {e}")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error", 
                        "message": f"メッセージ処理エラー: {str(e)}"
                    }))
                except:
                    logger.warning(f"[WS] エラー応答送信失敗: 接続切断済み")
                break
                
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
        
        # デバイス接続確認（Pydanticモデル使用）
        device_msg = DeviceConnected(
            connection_id=connection_id,
            session_id=session_id
        )
        await websocket.send_text(device_msg.json())
        
        while True:
            try:
                message = await websocket.receive_text()
                logger.info(f"[WS] デバイス受信 ({connection_id}): {message}")
                
                data = json.loads(message)
                await handle_device_message(session_id, connection_id, data)
                
            except WebSocketDisconnect as e:
                # 正常な切断 (1000) はログレベルを下げる
                if e.code == 1000:
                    logger.info(f"[WS] デバイス正常切断 ({connection_id}): {e}")
                else:
                    logger.warning(f"[WS] デバイス異常切断 ({connection_id}): {e}")
                break
                
            except Exception as e:
                logger.error(f"[WS] デバイスメッセージエラー: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"[WS] デバイス接続切断: {connection_id}")
        
    finally:
        await ws_manager.disconnect(connection_id, session_id)

# ================================================================================
# メッセージハンドラー
# ================================================================================

async def handle_sync_message(session_id: str, connection_id: str, data: dict):
    """
    同期メッセージ処理（Pydanticモデル使用）
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
        # receiver.pyパターン: 受信したデータをそのまま中継
        current_time = data.get("time", 0)
        state = data.get("state", "unknown")
        duration = data.get("duration")
        ts = data.get("ts")
        
        logger.info(f"[SYNC] 動画同期: {state} at {current_time}s (session: {session_id})")
        
        # 受信データをそのままデバイスに中継（receiver.pyパターン）
        relay_data = create_relay_data(session_id, data)
        await relay_sync_to_devices(session_id, relay_data)
        
        # フロントエンドに確認応答
        sync_ack = SyncAcknowledge(
            session_id=session_id,
            received_time=current_time,
            received_state=state,
            relayed_to_devices=True
        )
        await ws_manager.send_to_session(session_id, sync_ack.dict())
        
    else:
        logger.warning(f"[SYNC] 未知のメッセージタイプ: {message_type}")

async def handle_device_message(session_id: str, connection_id: str, data: dict):
    """
    デバイスメッセージ処理（Pydanticモデル使用）
    """
    message_type = data.get("type")
    logger.info(f"[DEVICE] メッセージ受信: {message_type} from {connection_id}")
    
    if message_type == "device_status":
        # デバイス状態メッセージの検証
        is_valid, error_msg = validate_device_status(data)
        if not is_valid:
            logger.error(f"[DEVICE] 無効なデバイス状態: {error_msg}")
            return
        
        device_status = DeviceStatus(**data)
        logger.info(f"[DEVICE] デバイス状態更新: {device_status.device_id} - {device_status.status}")
        
        # 基本的な応答
        await ws_manager.send_to_session(session_id, {
            "type": "device_ack",
            "received_type": message_type,
            "device_id": device_status.device_id,
            "server_time": datetime.now().isoformat()
        })
    else:
        # その他のメッセージ
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
        "version": "0.2.0",  # Pydanticモデル対応版
        "status": "running", 
        "active_connections": len(ws_manager.active_connections),
        "active_sessions": len(ws_manager.session_connections),
        "server_time": datetime.now().isoformat(),
        "features": [
            "websocket_sync",
            "pydantic_models", 
            "parallel_relay",
            "error_handling"
        ]
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

# receiver.pyパターンではセッション詳細管理は不要
# 接続状況の基本確認のみ提供

# ================================================================================
# デバイス中継機能
# ================================================================================

async def safe_send_to_device(websocket: WebSocket, sync_data: dict, connection_id: str) -> bool:
    """
    デバイスへの安全な送信処理
    例外処理とログを含む個別送信タスク
    """
    try:
        message_json = json.dumps(sync_data, ensure_ascii=False)
        await websocket.send_text(message_json)
        logger.info(f"[RELAY] デバイス {connection_id} に中継成功")
        return True
    except Exception as e:
        logger.error(f"[RELAY] デバイス {connection_id} への中継エラー: {e}")
        return False

async def relay_sync_to_devices(session_id: str, sync_data: dict):
    """
    同期データをデバイス（ラズベリーパイ）に並列中継
    
    修正内容：
    - 順次送信 → 並列送信による高速化
    - 個別例外処理による安定性向上
    - タイムアウト制御による応答性確保
    """
    logger.info(f"[RELAY] セッション {session_id} のデバイスに同期データ並列中継")
    
    # セッション内のデバイス接続を探す
    if session_id not in ws_manager.session_connections:
        logger.warning(f"[RELAY] セッション {session_id} が存在しません")
        return
    
    device_tasks = []
    device_count = 0
    
    for connection_id in ws_manager.session_connections[session_id]:
        if connection_id.startswith("device_"):
            websocket = ws_manager.active_connections.get(connection_id)
            if websocket:
                # 並列送信タスク作成
                task = asyncio.create_task(
                    safe_send_to_device(websocket, sync_data, connection_id)
                )
                device_tasks.append(task)
                device_count += 1
    
    if not device_tasks:
        logger.warning(f"[RELAY] セッション {session_id} にアクティブなデバイス接続がありません")
        return
    
    # 並列実行（2秒タイムアウト）
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*device_tasks, return_exceptions=True),
            timeout=2.0
        )
        
        # 成功数カウント
        success_count = sum(1 for result in results if result is True)
        logger.info(f"[RELAY] {success_count}/{device_count} デバイスに並列中継完了")
        
    except asyncio.TimeoutError:
        logger.warning(f"[RELAY] デバイス中継がタイムアウト ({device_count}台)")
        # タスクをキャンセル
        for task in device_tasks:
            if not task.done():
                task.cancel()
    except Exception as e:
        logger.error(f"[RELAY] 並列中継でエラー: {e}")

async def get_device_connections(session_id: str) -> list:
    """セッション内のデバイス接続一覧を取得"""
    devices = []
    if session_id in ws_manager.session_connections:
        for connection_id in ws_manager.session_connections[session_id]:
            if connection_id.startswith("device_"):
                websocket = ws_manager.active_connections.get(connection_id)
                if websocket:
                    devices.append({
                        "connection_id": connection_id,
                        "connected": True
                    })
    return devices