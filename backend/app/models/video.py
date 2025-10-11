# app/models/video.py - 動画管理モデル拡張
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from app.models.device import DeviceCapability

class VideoStatus(str, Enum):
    """動画ステータス"""
    READY = "ready"
    PREPARING = "preparing"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"

class VideoGenre(str, Enum):
    """動画ジャンル"""
    ACTION = "action"
    HORROR = "horror"
    COMEDY = "comedy"
    DRAMA = "drama"
    ADVENTURE = "adventure"
    FANTASY = "fantasy"
    DEMO = "demo"

class EffectComplexity(str, Enum):
    """エフェクトの複雑さ"""
    BASIC = "basic"      # 基本的なエフェクト（振動中心）
    STANDARD = "standard"  # 標準的なエフェクト
    ADVANCED = "advanced"  # 高度なエフェクト
    PREMIUM = "premium"   # プレミアムエフェクト（全機能使用）

class VideoMetadata(BaseModel):
    """動画メタデータ"""
    title: str = Field(..., description="動画タイトル")
    description: str = Field(..., description="動画説明")
    genre: VideoGenre = Field(..., description="ジャンル")
    duration_seconds: int = Field(..., description="動画長（秒）")
    release_date: Optional[datetime] = Field(default=None, description="リリース日")
    rating: Optional[str] = Field(default="G", description="レーティング")
    language: str = Field(default="ja", description="言語")
    subtitle_available: bool = Field(default=False, description="字幕利用可能")

class VideoEffectInfo(BaseModel):
    """動画エフェクト情報"""
    required_capabilities: List[DeviceCapability] = Field(..., description="必要な機能")
    optional_capabilities: List[DeviceCapability] = Field(default_factory=list, description="オプション機能")
    effect_complexity: EffectComplexity = Field(..., description="エフェクト複雑さ")
    total_effects: int = Field(..., description="総エフェクト数")
    effect_intensity_avg: float = Field(..., description="平均エフェクト強度")
    sync_data_size: int = Field(..., description="同期データサイズ（バイト）")

class VideoFileInfo(BaseModel):
    """動画ファイル情報"""
    video_url: str = Field(..., description="動画ファイルURL")
    thumbnail_url: str = Field(..., description="サムネイルURL")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    video_format: str = Field(default="mp4", description="動画フォーマット")
    resolution: str = Field(default="1920x1080", description="解像度")
    bitrate: int = Field(default=5000, description="ビットレート（kbps）")
    sync_data_url: str = Field(..., description="同期データファイルURL")

class VideoCompatibility(BaseModel):
    """動画互換性情報"""
    min_device_version: str = Field(default="1.0.0", description="最小デバイスバージョン")
    supported_product_codes: List[str] = Field(..., description="対応製品コード")
    incompatible_product_codes: List[str] = Field(default_factory=list, description="非対応製品コード")
    device_specific_notes: Dict[str, str] = Field(default_factory=dict, description="デバイス固有注意事項")

class EnhancedVideo(BaseModel):
    """拡張動画情報モデル"""
    video_id: str = Field(..., description="動画ID")
    status: VideoStatus = Field(..., description="動画ステータス")
    metadata: VideoMetadata = Field(..., description="動画メタデータ")
    effect_info: VideoEffectInfo = Field(..., description="エフェクト情報")
    file_info: VideoFileInfo = Field(..., description="ファイル情報")
    compatibility: VideoCompatibility = Field(..., description="互換性情報")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新日時")

class VideoAvailabilityRequest(BaseModel):
    """動画利用可能性確認リクエスト"""
    device_id: str = Field(..., description="デバイスID")
    product_code: Optional[str] = Field(default=None, description="製品コード（オプション）")
    required_capabilities: Optional[List[DeviceCapability]] = Field(
        default=None, 
        description="必要機能フィルタ（オプション）"
    )

class VideoAvailabilityResponse(BaseModel):
    """動画利用可能性確認レスポンス"""
    videos: List[Dict[str, Any]] = Field(..., description="利用可能動画一覧")
    total_count: int = Field(..., description="総動画数")
    available_count: int = Field(..., description="利用可能数")
    device_compatibility: Dict[str, Any] = Field(..., description="デバイス互換性情報")
    timestamp: datetime = Field(default_factory=datetime.now, description="取得日時")

class VideoSelectionRequest(BaseModel):
    """動画選択リクエスト"""
    video_id: str = Field(..., description="選択動画ID")
    device_id: str = Field(..., description="デバイスID")
    preparation_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="準備オプション設定"
    )

class VideoSelectionResponse(BaseModel):
    """動画選択レスポンス"""
    session_id: str = Field(..., description="生成されたセッションID")
    video_info: Dict[str, Any] = Field(..., description="選択動画情報")
    preparation_started: bool = Field(..., description="準備処理開始フラグ")
    estimated_preparation_time: int = Field(..., description="推定準備時間（秒）")
    websocket_endpoints: Dict[str, str] = Field(..., description="WebSocketエンドポイント情報")
    expires_at: datetime = Field(..., description="セッション有効期限")

# 内部管理用クラス
class VideoManager:
    """動画管理クラス"""
    
    def __init__(self):
        self.videos: Dict[str, EnhancedVideo] = {}
        self.video_sessions: Dict[str, str] = {}  # session_id -> video_id
    
    def add_video(self, video: EnhancedVideo) -> None:
        """動画を追加"""
        self.videos[video.video_id] = video
        video.updated_at = datetime.now()
    
    def get_video(self, video_id: str) -> Optional[EnhancedVideo]:
        """動画を取得"""
        return self.videos.get(video_id)
    
    def get_available_videos(self, product_code: str = None, 
                           required_capabilities: List[DeviceCapability] = None) -> List[EnhancedVideo]:
        """利用可能動画一覧取得"""
        available = []
        
        for video in self.videos.values():
            if video.status != VideoStatus.READY:
                continue
                
            # 製品コード互換性チェック
            if product_code:
                if (product_code not in video.compatibility.supported_product_codes or
                    product_code in video.compatibility.incompatible_product_codes):
                    continue
            
            # 必要機能チェック
            if required_capabilities:
                if not all(cap in required_capabilities for cap in video.effect_info.required_capabilities):
                    continue
            
            available.append(video)
        
        # 複雑さとリリース日でソート
        return sorted(available, 
                     key=lambda v: (v.effect_info.effect_complexity.value, v.metadata.release_date or datetime.min),
                     reverse=True)
    
    def is_video_compatible(self, video_id: str, product_code: str, 
                          device_capabilities: List[DeviceCapability]) -> Dict[str, Any]:
        """動画互換性チェック"""
        video = self.get_video(video_id)
        if not video:
            return {"compatible": False, "reason": "video_not_found"}
        
        # 製品コード互換性
        if product_code not in video.compatibility.supported_product_codes:
            return {
                "compatible": False, 
                "reason": "product_not_supported",
                "details": f"Product {product_code} is not supported"
            }
        
        if product_code in video.compatibility.incompatible_product_codes:
            return {
                "compatible": False,
                "reason": "product_incompatible", 
                "details": f"Product {product_code} is incompatible"
            }
        
        # 必要機能チェック
        missing_capabilities = []
        for required_cap in video.effect_info.required_capabilities:
            if required_cap not in device_capabilities:
                missing_capabilities.append(required_cap)
        
        if missing_capabilities:
            return {
                "compatible": False,
                "reason": "missing_capabilities",
                "details": f"Missing capabilities: {missing_capabilities}"
            }
        
        # 互換性OK
        return {
            "compatible": True,
            "optional_features": [
                cap for cap in video.effect_info.optional_capabilities 
                if cap in device_capabilities
            ],
            "effect_complexity": video.effect_info.effect_complexity,
            "total_effects": video.effect_info.total_effects
        }
    
    def create_session_for_video(self, session_id: str, video_id: str) -> None:
        """動画セッション作成"""
        self.video_sessions[session_id] = video_id
    
    def get_session_video(self, session_id: str) -> Optional[str]:
        """セッションの動画ID取得"""
        return self.video_sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> None:
        """セッション削除"""
        if session_id in self.video_sessions:
            del self.video_sessions[session_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        total_videos = len(self.videos)
        ready_videos = len([v for v in self.videos.values() if v.status == VideoStatus.READY])
        active_sessions = len(self.video_sessions)
        
        genres = {}
        complexities = {}
        
        for video in self.videos.values():
            genre = video.metadata.genre.value
            genres[genre] = genres.get(genre, 0) + 1
            
            complexity = video.effect_info.effect_complexity.value
            complexities[complexity] = complexities.get(complexity, 0) + 1
        
        return {
            "total_videos": total_videos,
            "ready_videos": ready_videos,
            "active_sessions": active_sessions,
            "genres": genres,
            "complexities": complexities,
            "last_updated": datetime.now().isoformat()
        }