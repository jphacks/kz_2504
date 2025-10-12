"""
Video Management API - 動画一覧・選択エンドポイント

動画リスト取得、デバイス互換性フィルタリング、動画選択処理を提供
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.config.settings import settings
from app.models.video import VideoListResponse, VideoSelectRequest, VideoSelectResponse
from app.services.video_service import video_service

# ログ設定
logger = logging.getLogger(__name__)

# APIルーター作成
router = APIRouter(
    prefix="/api/videos",
    tags=["Video Management"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Video Not Found"},
        500: {"description": "Internal Server Error"}
    }
)

@router.get("/available", response_model=VideoListResponse)
async def get_available_videos(
    device_id: Optional[str] = Query(None, description="デバイスIDでフィルタリング"),
    category: Optional[str] = Query(None, description="カテゴリでフィルタリング"),
    force_rescan: bool = Query(False, description="強制再スキャン")
):
    """
    利用可能な動画一覧を取得
    
    デバイスIDが指定された場合、そのデバイスに対応した動画のみを返す
    """
    logger.info(f"動画一覧取得リクエスト: device_id={device_id}, category={category}")
    
    try:
        # 全動画を取得
        all_videos = video_service.scan_video_files(force_rescan=force_rescan)
        
        if not all_videos:
            logger.warning("利用可能な動画が見つかりません")
            return VideoListResponse(
                videos=[],
                total_count=0,
                available_count=0,
                device_id=device_id,
                filter_applied=device_id is not None
            )
        
        # デバイスフィルタリング
        filtered_videos = all_videos
        device_capabilities = None
        
        if device_id:
            try:
                # デバイス情報から機能を取得（device_registration APIと連携）
                device_capabilities = await _get_device_capabilities(device_id)
                if device_capabilities:
                    filtered_videos = video_service.filter_videos_by_device(all_videos, device_capabilities)
                else:
                    logger.warning(f"デバイス情報が見つかりません: {device_id}")
            except Exception as e:
                logger.error(f"デバイス情報取得エラー: {e}")
                # エラーの場合はフィルタリング無しで続行
        
        # カテゴリフィルタリング
        if category:
            filtered_videos = [v for v in filtered_videos if category in v.video_info.categories]
            logger.info(f"カテゴリフィルタ適用: {category}")
        
        # レスポンス用に変換
        video_list = []
        for video in filtered_videos:
            video_dict = {
                "video_id": video.video_id,
                "title": video.title,
                "description": video.video_info.description,
                "duration": video.duration,
                "thumbnail_url": video.video_info.thumbnail_url,
                "ready": video.status.value == "ready",
                "effects_count": len(video.compatibility.supported_effects),
                "required_capabilities": video.compatibility.required_capabilities,
                "effect_complexity": video.compatibility.effect_complexity.value,
                "content_rating": video.video_info.content_rating.value,
                "categories": video.video_info.categories,
                "file_size_mb": video.video_info.file_size_mb
            }
            
            # デバイス互換性情報を追加
            if device_capabilities:
                video_dict["compatible"] = video.is_compatible_with_device(device_capabilities)
                video_dict["missing_capabilities"] = video.get_missing_capabilities(device_capabilities)
            
            video_list.append(video_dict)
        
        # ソート（準備完了順、タイトル順）
        video_list.sort(key=lambda x: (not x["ready"], x["title"]))
        
        response = VideoListResponse(
            videos=video_list,
            total_count=len(all_videos),
            available_count=len(filtered_videos),
            device_id=device_id,
            filter_applied=device_id is not None or category is not None
        )
        
        logger.info(f"動画一覧取得成功: {len(video_list)}件返却")
        
        return response
        
    except Exception as e:
        logger.error(f"動画一覧取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "video_list_failed",
                "message": "動画一覧の取得中にエラーが発生しました"
            }
        )

@router.get("/{video_id}")
async def get_video_details(video_id: str):
    """
    特定動画の詳細情報を取得
    """
    logger.info(f"動画詳細取得リクエスト: {video_id}")
    
    try:
        video = video_service.get_video_by_id(video_id)
        
        if not video:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "video_not_found",
                    "message": f"動画 '{video_id}' が見つかりません"
                }
            )
        
        # 詳細情報レスポンス
        video_details = {
            "video_id": video.video_id,
            "title": video.title,
            "description": video.video_info.description,
            "duration": video.duration,
            "file_name": video.video_info.file_name,
            "file_size_mb": video.video_info.file_size_mb,
            "status": video.status.value,
            "thumbnail_url": video.video_info.thumbnail_url,
            "video_url": video_service.get_video_url(video_id),
            "sync_data_url": video_service.get_sync_data_url(video_id),
            
            # メタデータ
            "categories": video.video_info.categories,
            "tags": video.video_info.tags,
            "content_rating": video.video_info.content_rating.value,
            "created_at": video.video_info.created_at.isoformat(),
            "updated_at": video.video_info.updated_at.isoformat() if video.video_info.updated_at else None,
            
            # 互換性・エフェクト情報
            "required_capabilities": video.compatibility.required_capabilities,
            "recommended_capabilities": video.compatibility.recommended_capabilities,
            "effect_complexity": video.compatibility.effect_complexity.value,
            "supported_effects": [
                {
                    "type": effect.effect_type,
                    "count": effect.count,
                    "intensity_avg": effect.intensity_avg,
                    "duration_total": effect.duration_total
                }
                for effect in video.compatibility.supported_effects
            ],
            
            # 統計
            "play_count": video.play_count,
            "avg_rating": video.avg_rating
        }
        
        logger.info(f"動画詳細取得成功: {video_id}")
        
        return video_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"動画詳細取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "video_details_failed", 
                "message": "動画詳細の取得中にエラーが発生しました"
            }
        )

@router.post("/select", response_model=VideoSelectResponse)
async def select_video(request: VideoSelectRequest):
    """
    動画を選択してセッションを開始
    
    将来的には準備処理APIと連携する
    """
    logger.info(f"動画選択リクエスト: video_id={request.video_id}, device_id={request.device_id}")
    
    try:
        # 動画存在確認
        video = video_service.get_video_by_id(request.video_id)
        if not video:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "video_not_found",
                    "message": f"動画 '{request.video_id}' が見つかりません"
                }
            )
        
        # デバイス互換性確認（簡易版）
        try:
            device_capabilities = await _get_device_capabilities(request.device_id)
            if device_capabilities and not video.is_compatible_with_device(device_capabilities):
                missing = video.get_missing_capabilities(device_capabilities)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "incompatible_device",
                        "message": f"デバイスが対応していません（不足機能: {missing}）"
                    }
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"デバイス互換性チェックエラー: {e}")
            # 互換性チェックエラーは警告のみで続行
        
        # セッションID生成（簡易版）
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.video_id[:8]}"
        
        # レスポンス作成
        response = VideoSelectResponse(
            session_id=session_id,
            video_url=video_service.get_video_url(request.video_id) or f"/assets/videos/{video.video_info.file_name}",
            sync_data_url=video_service.get_sync_data_url(request.video_id),
            preparation_started=True,  # 将来的には実際の準備処理と連携
            estimated_preparation_time=30 if video.compatibility.effect_complexity.value == "high" else 15
        )
        
        logger.info(f"動画選択成功: セッション {session_id} 作成")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"動画選択エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "video_selection_failed",
                "message": "動画選択中にエラーが発生しました"
            }
        )

@router.get("/categories/list")
async def get_video_categories():
    """
    利用可能な動画カテゴリ一覧を取得
    """
    from app.models.video import VIDEO_CATEGORIES
    
    return {
        "categories": VIDEO_CATEGORIES,
        "descriptions": {
            "action": "アクション映画",
            "horror": "ホラー映画",
            "adventure": "アドベンチャー",
            "comedy": "コメディ",
            "drama": "ドラマ",
            "scifi": "SF映画",
            "fantasy": "ファンタジー",
            "demo": "デモンストレーション",
            "test": "テスト用"
        }
    }

# ヘルパー関数
async def _get_device_capabilities(device_id: str) -> Optional[List[str]]:
    """
    デバイスIDから機能一覧を取得
    
    TODO: device_registration APIと連携して実際の機能を取得
    現在は簡易実装
    """
    # 簡易マッピング（将来的にはデバイスサービスと連携）
    device_capability_map = {
        "device_basic": ["VIBRATION", "AUDIO"],
        "device_standard": ["VIBRATION", "MOTION", "SCENT", "AUDIO"],
        "device_premium": ["VIBRATION", "MOTION", "SCENT", "AUDIO", "LIGHTING", "WIND"]
    }
    
    # device_idがdevice_で始まる場合の処理
    if device_id.startswith("device_"):
        # デバイス登録APIで生成されたIDのパターンを想定
        # 実際の実装では、デバイス情報ストレージから取得
        return ["VIBRATION", "MOTION", "AUDIO"]  # デフォルト機能
    
    return device_capability_map.get(device_id, ["VIBRATION"])  # 最低限の機能