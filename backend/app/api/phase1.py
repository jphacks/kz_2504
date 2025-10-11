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