# app/api/phase1.py - Phase 1 HTTP API実装
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
import logging

from app.models.schemas import (
    SessionCreateRequest, SessionResponse, SessionInfo,
    Video, SyncData
)
from app.models.session_models import session_manager
from app.services.video_service import VideoService
from app.config.settings import Settings

# ルーター作成
router = APIRouter(prefix="/api", tags=["Phase 1 API"])

# ロガー設定
logger = logging.getLogger(__name__)

# 依存関係
def get_video_service():
    """VideoServiceのDI"""
    return VideoService(Settings())

@router.post("/sessions", response_model=SessionResponse, summary="セッション作成")
async def create_session(request: SessionCreateRequest):
    """
    デバイス登録とセッション作成
    
    - **product_code**: デバイス製品コード (DH001-DH999)
    - **capabilities**: デバイス機能リスト 
    - **device_info**: デバイス詳細情報
    """
    try:
        # セッションID生成
        session_id = str(uuid.uuid4())
        
        # セッション作成
        session = session_manager.create_session(
            session_id=session_id,
            product_code=request.product_code,
            capabilities=request.capabilities,
            device_info=request.device_info.dict()
        )
        
        logger.info(f"セッション作成: {session_id}, 製品コード: {request.product_code}")
        
        # レスポンス作成
        return SessionResponse(
            session_id=session_id,
            product_code=request.product_code,
            status=session.status,
            websocket_url=f"/ws/sessions/{session_id}"
        )
        
    except Exception as e:
        logger.error(f"セッション作成エラー: {e}")
        raise HTTPException(status_code=500, detail="セッション作成に失敗しました")

@router.get("/sessions/{session_id}", response_model=SessionInfo, summary="セッション情報取得")
async def get_session_info(session_id: str):
    """
    セッション情報を取得
    
    - **session_id**: 取得対象のセッションID
    """
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
    return SessionInfo(**session.to_dict())

@router.delete("/sessions/{session_id}", summary="セッション削除")
async def delete_session(session_id: str):
    """
    セッションを削除
    
    - **session_id**: 削除対象のセッションID
    """
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
        
    session_manager.remove_session(session_id)
    logger.info(f"セッション削除: {session_id}")
    
    return {"message": "セッションが削除されました", "session_id": session_id}

@router.get("/videos", response_model=List[Video], summary="動画リスト取得")
async def get_videos(video_service: VideoService = Depends(get_video_service)):
    """
    利用可能な動画リストを取得
    """
    try:
        videos = video_service.get_available_videos()
        logger.info(f"動画リスト取得: {len(videos)}件")
        return videos
        
    except Exception as e:
        logger.error(f"動画リスト取得エラー: {e}")
        raise HTTPException(status_code=500, detail="動画リストの取得に失敗しました")

@router.get("/videos/{video_id}", response_model=Video, summary="動画情報取得")
async def get_video_info(video_id: str, video_service: VideoService = Depends(get_video_service)):
    """
    指定動画の詳細情報を取得
    
    - **video_id**: 動画ID
    """
    video = video_service.get_video_info(video_id)
    
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")
        
    logger.info(f"動画情報取得: {video_id}")
    return video

@router.get("/sync-data/{video_id}", response_model=SyncData, summary="同期データ取得")
async def get_sync_data(video_id: str, video_service: VideoService = Depends(get_video_service)):
    """
    動画の同期データを取得
    
    - **video_id**: 同期データ取得対象の動画ID
    """
    # 動画存在確認
    if not video_service.validate_video_exists(video_id):
        raise HTTPException(status_code=404, detail="動画が見つかりません")
        
    # 同期データ取得
    sync_data = video_service.get_sync_data(video_id)
    
    if not sync_data:
        raise HTTPException(status_code=404, detail="同期データが見つかりません")
        
    logger.info(f"同期データ取得: {video_id}, イベント数: {len(sync_data.sync_events)}")
    return sync_data

@router.get("/sessions", summary="全セッション一覧")
async def get_all_sessions():
    """
    現在のすべてのセッション情報を取得（デバッグ用）
    """
    sessions = session_manager.get_all_sessions()
    logger.info(f"セッション一覧取得: {len(sessions)}件")
    return {"sessions": sessions, "count": len(sessions)}

# 新仕様対応エンドポイント

@router.post("/sessions/{session_id}/sync-data", summary="同期データファイル送信")
async def upload_sync_data(session_id: str, sync_data_request: dict):
    """
    待機画面時に同期データファイルをデバイスに事前送信（新仕様）
    
    - **session_id**: セッションID
    - **sync_data_request**: 同期データファイル情報
    """
    # セッション存在確認
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    try:
        from app.models.schemas import SyncDataFile, SyncEvent
        from app.websocket.manager import websocket_manager
        
        # 同期データファイル作成
        sync_events = [SyncEvent(**event) for event in sync_data_request.get("sync_events", [])]
        sync_data_file = SyncDataFile(
            video_id=sync_data_request["video_id"],
            video_duration=sync_data_request["video_duration"],
            sync_events=sync_events
        )
        
        # デバイスに送信
        device_connected = websocket_manager.is_device_connected(session_id)
        if device_connected:
            await websocket_manager.send_to_device(session_id, {
                "type": "sync_data_file",
                "sync_data_file": sync_data_file.dict(),
                "message": "同期データファイル事前送信",
                "timestamp": sync_data_file.created_at.isoformat()
            })
        
        logger.info(f"同期データファイル送信: セッション {session_id}, 動画 {sync_data_file.video_id}")
        
        return {
            "success": True,
            "video_id": sync_data_file.video_id,
            "events_count": len(sync_events),
            "device_connected": device_connected,
            "message": "同期データファイルが送信されました"
        }
        
    except Exception as e:
        logger.error(f"同期データファイル送信エラー: {e}")
        raise HTTPException(status_code=500, detail="同期データファイル送信に失敗しました")

@router.post("/sessions/{session_id}/playback-sync", summary="再生時刻同期送信")
async def send_playback_sync(session_id: str, playback_data: dict):
    """
    リアルタイム再生時刻をデバイスに直接送信（新仕様）
    
    - **session_id**: セッションID
    - **playback_data**: 再生時刻同期データ
    """
    # セッション存在確認
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    try:
        from app.models.schemas import PlaybackTimeSync
        from app.websocket.manager import websocket_manager
        
        # 再生時刻同期データ作成
        playback_sync = PlaybackTimeSync(
            current_time=playback_data["current_time"],
            is_playing=playback_data.get("is_playing", True),
            playback_rate=playback_data.get("playback_rate", 1.0),
            video_id=playback_data["video_id"]
        )
        
        # デバイスに送信
        device_connected = websocket_manager.is_device_connected(session_id)
        if device_connected:
            await websocket_manager.send_to_device(session_id, {
                "type": "playback_time_sync",
                "playback_sync": playback_sync.dict(),
                "timestamp": playback_sync.timestamp.isoformat()
            })
        
        logger.debug(f"再生時刻同期送信: セッション {session_id}, 時刻 {playback_sync.current_time:.2f}s")
        
        return {
            "success": True,
            "current_time": playback_sync.current_time,
            "is_playing": playback_sync.is_playing,
            "device_connected": device_connected
        }
        
    except Exception as e:
        logger.error(f"再生時刻同期送信エラー: {e}")
        raise HTTPException(status_code=500, detail="再生時刻同期送信に失敗しました")

@router.post("/sessions/{session_id}/direct-command", summary="直接同期コマンド送信")
async def send_direct_command(session_id: str, command_data: dict):
    """
    即座に実行する同期コマンドをデバイスに送信（新仕様）
    
    - **session_id**: セッションID
    - **command_data**: 同期コマンドデータ
    """
    # セッション存在確認
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    try:
        from app.models.schemas import SyncCommand
        from app.websocket.manager import websocket_manager
        
        # 直接同期コマンド作成
        sync_command = SyncCommand(
            command_type=command_data["command_type"],
            intensity=command_data.get("intensity", 50),
            duration=command_data.get("duration", 1000),
            video_time=command_data.get("video_time", 0)
        )
        
        # デバイスに送信
        device_connected = websocket_manager.is_device_connected(session_id)
        if device_connected:
            await websocket_manager.send_to_device(session_id, {
                "type": "direct_sync_command",
                "sync_command": sync_command.dict(),
                "message": "即時同期コマンド実行",
                "timestamp": sync_command.timestamp.isoformat()
            })
        
        logger.info(f"直接同期コマンド送信: セッション {session_id}, コマンド {sync_command.command_type}")
        
        return {
            "success": True,
            "command_type": sync_command.command_type,
            "video_time": sync_command.video_time,
            "device_connected": device_connected,
            "message": "直接同期コマンドが送信されました"
        }
        
    except Exception as e:
        logger.error(f"直接同期コマンド送信エラー: {e}")
        raise HTTPException(status_code=500, detail="直接同期コマンド送信に失敗しました")

# ヘルスチェックエンドポイント
@router.get("/health", summary="ヘルスチェック")
async def health_check():
    """
    APIサーバーの稼働状態確認
    """
    return {
        "status": "healthy",
        "service": "4DX@HOME Backend API",
        "version": "1.0.0"
    }