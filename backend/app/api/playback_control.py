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
import time
from datetime import datetime

# 簡素化されたPlaybackモデルをインポート
from app.models.playback import (
    SyncMessage, DeviceStatus,
    ConnectionEstablished, SyncAcknowledge, DeviceConnected,
    create_relay_data, validate_sync_message, validate_device_status
)

# 新しい同期サービスをインポート
from app.services.sync_data_service import sync_data_service
from app.services.continuous_sync_service import continuous_sync_service

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
    同期メッセージ処理（ラズパイパターン対応強化版）
    JSON同期データとcurrentTime両方に対応
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
    
    elif message_type == "timeline_data_request":
        # タイムラインファイル事前送信要求（ラズパイパターン）
        video_id = data.get("video_id", "demo1")
        logger.info(f"[SYNC] タイムラインデータ要求: {video_id} (session: {session_id})")
        
        try:
            # タイムラインデータ準備・送信
            bulk_data = await sync_data_service.send_timeline_data_bulk(session_id, video_id)
            await ws_manager.send_to_session(session_id, bulk_data)
            logger.info(f"[SYNC] タイムラインデータ送信完了: {video_id}")
            
        except Exception as e:
            logger.error(f"[SYNC] タイムラインデータ送信エラー: {e}")
            error_response = {
                "type": "timeline_data_error",
                "video_id": video_id,
                "error": str(e)
            }
            await ws_manager.send_to_session(session_id, error_response)
    
    elif message_type == "start_continuous_sync":
        # 連続時間同期開始要求
        logger.info(f"[SYNC] 連続同期開始要求: {session_id}")
        
        async def sync_callback(time_data: dict):
            """時間更新コールバック - デバイスに中継"""
            await relay_sync_to_devices(session_id, time_data)
        
        try:
            await continuous_sync_service.start_continuous_sync(session_id, sync_callback)
            
            response = {
                "type": "continuous_sync_started",
                "session_id": session_id,
                "message": "連続同期を開始しました"
            }
            await ws_manager.send_to_session(session_id, response)
            
        except Exception as e:
            logger.error(f"[SYNC] 連続同期開始エラー: {e}")
            error_response = {
                "type": "continuous_sync_error", 
                "error": str(e)
            }
            await ws_manager.send_to_session(session_id, error_response)
    
    elif message_type == "stop_continuous_sync":
        # 連続時間同期停止
        logger.info(f"[SYNC] 連続同期停止要求: {session_id}")
        
        await continuous_sync_service.stop_sync(session_id)
        
        response = {
            "type": "continuous_sync_stopped",
            "session_id": session_id,
            "message": "連続同期を停止しました"
        }
        await ws_manager.send_to_session(session_id, response)
    
    elif message_type == "sync_control":
        # 同期制御（pause/resume/seek）
        action = data.get("action")
        logger.info(f"[SYNC] 同期制御: {action} (session: {session_id})")
        
        if action == "pause":
            continuous_sync_service.pause_sync(session_id)
        elif action == "resume":
            continuous_sync_service.resume_sync(session_id)
        elif action == "seek":
            seek_time = data.get("time", 0.0)
            continuous_sync_service.seek_sync(session_id, seek_time)
        
        status = continuous_sync_service.get_sync_status(session_id)
        response = {
            "type": "sync_control_ack",
            "action": action,
            "status": status
        }
        await ws_manager.send_to_session(session_id, response)
        
    elif message_type == "sync":
        # 従来の動画同期メッセージ（既存機能維持）
        current_time = data.get("time", 0)
        state = data.get("state", "unknown")
        duration = data.get("duration")
        ts = data.get("ts")
        
        logger.info(f"[SYNC] 動画同期: {state} at {current_time}s (session: {session_id})")
        
        # 同期データサービスに時刻更新
        time_state = sync_data_service.update_current_time(session_id, current_time, state == "play")
        
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
        
    elif message_type == "start_signal":
        # スタート信号をデバイスに中継
        logger.info(f"[START_SIGNAL] WebSocketスタート信号受信: session={session_id}")
        
        # スタート信号データを作成
        start_signal_data = {
            "type": "start_signal",
            "session_id": session_id,
            "timestamp": time.time(),
            "message": data.get("message", "start"),
            "source": "websocket"
        }
        
        # デバイスに信号を送信
        sent_count = await relay_start_signal_to_devices(session_id, start_signal_data)
        
        # 送信結果をフロントエンドに返す
        response = {
            "type": "start_signal_ack",
            "session_id": session_id,
            "success": sent_count > 0,
            "sent_to_devices": sent_count,
            "message": f"スタート信号を{sent_count}台のデバイスに送信しました" if sent_count > 0 else "接続されたデバイスがありません"
        }
        await ws_manager.send_to_session(session_id, response)
        
    elif message_type == "stop_signal":
        # ストップ信号をデバイスに中継（全ハードウェア停止）
        logger.info(f"[STOP_SIGNAL] WebSocketストップ信号受信: session={session_id}")
        
        # ストップ信号データを作成
        stop_signal_data = {
            "type": "stop_signal",
            "session_id": session_id,
            "timestamp": time.time(),
            "message": "stop_all_actuators",
            "action": "stop_all",
            "source": "websocket"
        }
        
        # デバイスに信号を送信
        sent_count = await relay_stop_signal_to_devices(session_id, stop_signal_data)
        
        # 送信結果をフロントエンドに返す
        response = {
            "type": "stop_signal_ack",
            "session_id": session_id,
            "success": sent_count > 0,
            "sent_to_devices": sent_count,
            "message": f"ストップ信号を{sent_count}台のデバイスに送信しました" if sent_count > 0 else "接続されたデバイスがありません"
        }
        await ws_manager.send_to_session(session_id, response)
        
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
        
    elif message_type == "device_test_result":
        # デバイステスト結果を処理
        logger.info(f"[DEVICE] デバイステスト結果受信: session_id={session_id}")
        
        # device_registration.pyのhandle_device_test_result関数を呼び出す
        from app.api.device_registration import handle_device_test_result
        await handle_device_test_result(session_id, data)
        
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

# ================================================================================
# デバッグ用RESTエンドポイント（ラズパイパターン対応）
# ================================================================================

@router.post("/debug/timeline/{session_id}")
async def load_timeline_debug(session_id: str, video_id: str = "demo1"):
    """デバッグ用: タイムラインファイル読み込み・準備"""
    try:
        bulk_data = await sync_data_service.send_timeline_data_bulk(session_id, video_id)
        return {
            "success": True,
            "message": f"タイムラインファイル読み込み完了: {video_id}",
            "timeline_info": {
                "video_id": bulk_data["video_id"],
                "total_duration": bulk_data["transmission_metadata"]["total_duration"],
                "events_count": bulk_data["transmission_metadata"]["events_count"]
            }
        }
    except Exception as e:
        logger.error(f"[DEBUG] タイムライン読み込みエラー: {e}")
        raise HTTPException(status_code=400, detail=f"タイムライン読み込み失敗: {str(e)}")

@router.post("/debug/sync/{session_id}/start")
async def start_debug_sync(session_id: str, interval: float = 0.5):
    """デバッグ用: 連続同期開始"""
    try:
        # タイムライン状態確認
        timeline_state = sync_data_service.get_timeline_state(session_id)
        if not timeline_state:
            raise HTTPException(
                status_code=400, 
                detail="タイムラインが読み込まれていません。先に /debug/timeline/{session_id} を呼び出してください"
            )
        
        # デバッグ用簡易コールバック
        async def debug_callback(time_data: dict):
            logger.info(f"[DEBUG_SYNC] currentTime: {time_data.get('currentTime', 0):.2f}s")
        
        await continuous_sync_service.start_continuous_sync(session_id, debug_callback, interval)
        
        return {
            "success": True,
            "message": "連続同期開始",
            "session_id": session_id,
            "interval": interval,
            "timeline_info": sync_data_service.get_timeline_info(session_id)
        }
    except Exception as e:
        logger.error(f"[DEBUG] 連続同期開始エラー: {e}")
        raise HTTPException(status_code=500, detail=f"連続同期開始失敗: {str(e)}")

@router.post("/debug/sync/{session_id}/stop")
async def stop_debug_sync(session_id: str):
    """デバッグ用: 連続同期停止"""
    try:
        await continuous_sync_service.stop_sync(session_id)
        return {
            "success": True,
            "message": "連続同期停止",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"[DEBUG] 連続同期停止エラー: {e}")
        raise HTTPException(status_code=500, detail=f"連続同期停止失敗: {str(e)}")

@router.post("/debug/sync/{session_id}/control")
async def control_debug_sync(session_id: str, action: str, time: float = None):
    """
    デバッグ用: 同期制御
    
    Args:
        action: "pause", "resume", "seek"
        time: シーク時刻（seekの場合のみ）
    """
    try:
        if action == "pause":
            continuous_sync_service.pause_sync(session_id)
            message = "同期一時停止"
        elif action == "resume":
            continuous_sync_service.resume_sync(session_id)
            message = "同期再開"
        elif action == "seek":
            if time is None:
                raise HTTPException(status_code=400, detail="シーク時刻が必要です")
            continuous_sync_service.seek_sync(session_id, time)
            message = f"シーク完了: {time}s"
        else:
            raise HTTPException(status_code=400, detail="無効なアクション")
        
        status = continuous_sync_service.get_sync_status(session_id)
        return {
            "success": True,
            "message": message,
            "action": action,
            "status": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DEBUG] 同期制御エラー: {e}")
        raise HTTPException(status_code=500, detail=f"同期制御失敗: {str(e)}")

@router.get("/debug/sync/{session_id}/status")
async def get_debug_sync_status(session_id: str):
    """デバッグ用: 同期状態取得"""
    return {
        "session_id": session_id,
        "sync_status": continuous_sync_service.get_sync_status(session_id),
        "timeline_info": sync_data_service.get_timeline_info(session_id)
    }

@router.post("/start/{session_id}")
async def send_start_signal(session_id: str):
    """
    スタート信号をデバイスに送信
    
    シンプルなスタート信号をそのままラズパイデバイスに転送する
    
    Args:
        session_id: セッションID
        
    Returns:
        スタート信号送信結果
    """
    try:
        logger.info(f"[START_SIGNAL] スタート信号送信要求: session={session_id}")
        
        # スタート信号データを作成
        start_signal_data = {
            "type": "start_signal",
            "session_id": session_id,
            "timestamp": time.time(),
            "message": "start"
        }
        
        # デバイスに信号を送信
        sent_count = await relay_start_signal_to_devices(session_id, start_signal_data)
        
        if sent_count == 0:
            logger.warning(f"[START_SIGNAL] デバイス未接続: session={session_id}")
            return {
                "success": False,
                "message": "接続されたデバイスがありません",
                "session_id": session_id,
                "sent_to_devices": 0
            }
        
        logger.info(f"[START_SIGNAL] スタート信号送信完了: session={session_id}, devices={sent_count}")
        return {
            "success": True,
            "message": f"スタート信号を{sent_count}台のデバイスに送信しました",
            "session_id": session_id,
            "sent_to_devices": sent_count,
            "signal_data": start_signal_data
        }
        
    except Exception as e:
        logger.error(f"[START_SIGNAL] スタート信号送信エラー: {e}")
        raise HTTPException(status_code=500, detail=f"スタート信号送信失敗: {str(e)}")

@router.post("/stop/{session_id}")
async def send_stop_signal(session_id: str):
    """
    ストップ信号をデバイスに送信（全ハードウェア停止）
    
    再生一時停止時や動画終了時に呼び出され、
    全てのアクチュエータを停止させる信号をデバイスに送信する
    
    Args:
        session_id: セッションID
        
    Returns:
        ストップ信号送信結果
    """
    try:
        logger.info(f"[STOP_SIGNAL] ストップ信号送信要求: session={session_id}")
        
        # ストップ信号データを作成
        stop_signal_data = {
            "type": "stop_signal",
            "session_id": session_id,
            "timestamp": time.time(),
            "message": "stop_all_actuators",
            "action": "stop_all"
        }
        
        # デバイスに信号を送信
        sent_count = await relay_stop_signal_to_devices(session_id, stop_signal_data)
        
        if sent_count == 0:
            logger.warning(f"[STOP_SIGNAL] デバイス未接続: session={session_id}")
            return {
                "success": False,
                "message": "接続されたデバイスがありません",
                "session_id": session_id,
                "sent_to_devices": 0
            }
        
        logger.info(f"[STOP_SIGNAL] ストップ信号送信完了: session={session_id}, devices={sent_count}")
        return {
            "success": True,
            "message": f"ストップ信号を{sent_count}台のデバイスに送信しました",
            "session_id": session_id,
            "sent_to_devices": sent_count,
            "signal_data": stop_signal_data
        }
        
    except Exception as e:
        logger.error(f"[STOP_SIGNAL] ストップ信号送信エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ストップ信号送信失敗: {str(e)}")

@router.get("/debug/sync/all")
async def get_all_debug_syncs():
    """デバッグ用: 全セッションの同期状態"""
    return {
        "active_syncs": continuous_sync_service.get_all_active_syncs(),
        "total_sessions": len(continuous_sync_service.get_all_active_syncs())
    }

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

async def relay_start_signal_to_devices(session_id: str, start_signal_data: dict) -> int:
    """
    スタート信号をデバイス（ラズベリーパイ）に並列送信
    
    Args:
        session_id: セッションID
        start_signal_data: 送信するスタート信号データ
        
    Returns:
        int: 送信に成功したデバイス数
    """
    logger.info(f"[START_SIGNAL_RELAY] セッション {session_id} のデバイスにスタート信号並列送信")
    
    # セッション内のデバイス接続を探す
    if session_id not in ws_manager.session_connections:
        logger.warning(f"[START_SIGNAL_RELAY] セッション {session_id} が存在しません")
        return 0
    
    device_tasks = []
    device_count = 0
    
    for connection_id in ws_manager.session_connections[session_id]:
        if connection_id.startswith("device_"):
            websocket = ws_manager.active_connections.get(connection_id)
            if websocket:
                # 並列送信タスク作成
                task = asyncio.create_task(
                    safe_send_to_device(websocket, start_signal_data, connection_id)
                )
                device_tasks.append(task)
                device_count += 1
    
    if not device_tasks:
        logger.warning(f"[START_SIGNAL_RELAY] セッション {session_id} にアクティブなデバイス接続がありません")
        return 0
    
    # 並列実行（2秒タイムアウト）
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*device_tasks, return_exceptions=True),
            timeout=2.0
        )
        
        # 成功数カウント
        success_count = sum(1 for result in results if result is True)
        logger.info(f"[START_SIGNAL_RELAY] {success_count}/{device_count} デバイスにスタート信号送信完了")
        return success_count
        
    except asyncio.TimeoutError:
        logger.warning(f"[START_SIGNAL_RELAY] スタート信号送信がタイムアウト ({device_count}台)")
        # タスクをキャンセル
        for task in device_tasks:
            if not task.done():
                task.cancel()
        return 0
    except Exception as e:
        logger.error(f"[START_SIGNAL_RELAY] 並列送信でエラー: {e}")
        return 0

async def relay_stop_signal_to_devices(session_id: str, stop_signal_data: dict) -> int:
    """
    ストップ信号をデバイス（ラズベリーパイ）に並列送信
    
    全てのアクチュエータを停止させるための信号を送信する。
    一時停止や動画終了時に使用される。
    
    Args:
        session_id: セッションID
        stop_signal_data: 送信するストップ信号データ
        
    Returns:
        int: 送信に成功したデバイス数
    """
    logger.info(f"[STOP_SIGNAL_RELAY] セッション {session_id} のデバイスにストップ信号並列送信")
    
    # セッション内のデバイス接続を探す
    if session_id not in ws_manager.session_connections:
        logger.warning(f"[STOP_SIGNAL_RELAY] セッション {session_id} が存在しません")
        return 0
    
    device_tasks = []
    device_count = 0
    
    for connection_id in ws_manager.session_connections[session_id]:
        if connection_id.startswith("device_"):
            websocket = ws_manager.active_connections.get(connection_id)
            if websocket:
                # 並列送信タスク作成
                task = asyncio.create_task(
                    safe_send_to_device(websocket, stop_signal_data, connection_id)
                )
                device_tasks.append(task)
                device_count += 1
    
    if not device_tasks:
        logger.warning(f"[STOP_SIGNAL_RELAY] セッション {session_id} にアクティブなデバイス接続がありません")
        return 0
    
    # 並列実行（2秒タイムアウト）
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*device_tasks, return_exceptions=True),
            timeout=2.0
        )
        
        # 成功数カウント
        success_count = sum(1 for result in results if result is True)
        logger.info(f"[STOP_SIGNAL_RELAY] {success_count}/{device_count} デバイスにストップ信号送信完了")
        return success_count
        
    except asyncio.TimeoutError:
        logger.warning(f"[STOP_SIGNAL_RELAY] ストップ信号送信がタイムアウト ({device_count}台)")
        # タスクをキャンセル
        for task in device_tasks:
            if not task.done():
                task.cancel()
        return 0
    except Exception as e:
        logger.error(f"[STOP_SIGNAL_RELAY] 並列送信でエラー: {e}")
        return 0

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