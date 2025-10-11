"""
Video Models - 動画管理データモデル

動画情報、同期データ、デバイス互換性を管理するPydanticモデル
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import os

class VideoStatus(str, Enum):
    """動画準備状況"""
    READY = "ready"          # 再生準備完了
    PREPARING = "preparing"  # 準備中
    UNAVAILABLE = "unavailable"  # 利用不可
    MAINTENANCE = "maintenance"  # メンテナンス中

class EffectComplexity(str, Enum):
    """エフェクト複雑度"""
    LOW = "low"       # 簡単（基本エフェクトのみ）
    MEDIUM = "medium" # 中程度
    HIGH = "high"     # 複雑（全エフェクト利用）

class ContentRating(str, Enum):
    """コンテンツレーティング"""
    G = "G"           # 全年齢対象
    PG = "PG"         # 保護者指導推奨
    PG13 = "PG13"     # 13歳未満注意
    R = "R"           # 制限あり

class VideoInfo(BaseModel):
    """基本動画情報"""
    video_id: str = Field(..., description="動画ID")
    title: str = Field(..., description="動画タイトル")
    description: str = Field(..., description="動画説明")
    duration_seconds: float = Field(..., gt=0, description="再生時間（秒）")
    file_name: str = Field(..., description="動画ファイル名")
    file_size_mb: Optional[float] = Field(default=None, description="ファイルサイズ（MB）")
    
    # メタデータ
    thumbnail_url: Optional[str] = Field(default=None, description="サムネイルURL")
    preview_url: Optional[str] = Field(default=None, description="プレビュー動画URL")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    updated_at: Optional[datetime] = Field(default=None, description="更新日時")
    
    # 分類情報
    categories: List[str] = Field(default_factory=list, description="カテゴリ")
    tags: List[str] = Field(default_factory=list, description="タグ")
    content_rating: ContentRating = Field(default=ContentRating.G, description="レーティング")

class EffectInfo(BaseModel):
    """エフェクト情報"""
    effect_type: str = Field(..., description="エフェクトタイプ")
    count: int = Field(..., ge=0, description="エフェクト回数")
    intensity_avg: float = Field(..., ge=0, le=1, description="平均強度")
    duration_total: float = Field(..., ge=0, description="総実行時間")

class VideoCompatibility(BaseModel):
    """動画・デバイス互換性情報"""
    required_capabilities: List[str] = Field(..., description="必要な機能")
    recommended_capabilities: List[str] = Field(default_factory=list, description="推奨機能")
    supported_effects: List[EffectInfo] = Field(default_factory=list, description="サポートエフェクト")
    effect_complexity: EffectComplexity = Field(default=EffectComplexity.LOW, description="エフェクト複雑度")
    min_device_version: Optional[str] = Field(default=None, description="最小デバイスバージョン")

class EnhancedVideo(BaseModel):
    """拡張動画情報（完全版）"""
    # 基本情報
    video_info: VideoInfo
    
    # 互換性・エフェクト情報
    compatibility: VideoCompatibility
    
    # 状態・メタデータ
    status: VideoStatus = Field(default=VideoStatus.READY, description="動画状態")
    sync_data_file: Optional[str] = Field(default=None, description="同期データファイル名")
    
    # 統計情報
    play_count: int = Field(default=0, ge=0, description="再生回数")
    avg_rating: Optional[float] = Field(default=None, ge=1, le=5, description="平均評価")
    
    @property
    def video_id(self) -> str:
        return self.video_info.video_id
    
    @property
    def title(self) -> str:
        return self.video_info.title
    
    @property
    def duration(self) -> float:
        return self.video_info.duration_seconds
    
    def is_compatible_with_device(self, device_capabilities: List[str]) -> bool:
        """デバイス機能との互換性チェック"""
        required = set(self.compatibility.required_capabilities)
        available = set(device_capabilities)
        return required.issubset(available)
    
    def get_missing_capabilities(self, device_capabilities: List[str]) -> List[str]:
        """不足している機能を取得"""
        required = set(self.compatibility.required_capabilities)
        available = set(device_capabilities)
        return list(required - available)

class VideoListResponse(BaseModel):
    """動画一覧レスポンス"""
    videos: List[Dict[str, Any]] = Field(..., description="動画リスト")
    total_count: int = Field(..., ge=0, description="総動画数")
    available_count: int = Field(..., ge=0, description="利用可能動画数")
    device_id: Optional[str] = Field(default=None, description="フィルタ対象デバイスID")
    filter_applied: bool = Field(default=False, description="デバイスフィルタ適用済み")

class VideoSelectRequest(BaseModel):
    """動画選択リクエスト"""
    video_id: str = Field(..., description="選択する動画ID")
    device_id: str = Field(..., description="使用するデバイスID")
    session_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="セッション設定")

class VideoSelectResponse(BaseModel):
    """動画選択レスポンス"""
    session_id: str = Field(..., description="作成されたセッションID")
    video_url: str = Field(..., description="動画ファイルURL")
    sync_data_url: Optional[str] = Field(default=None, description="同期データURL")
    preparation_started: bool = Field(default=False, description="準備処理開始済み")
    estimated_preparation_time: int = Field(default=30, ge=0, description="推定準備時間（秒）")

# 動画カテゴリ定数
VIDEO_CATEGORIES = [
    "action",      # アクション
    "horror",      # ホラー
    "adventure",   # アドベンチャー
    "comedy",      # コメディ
    "drama",       # ドラマ
    "scifi",       # SF
    "fantasy",     # ファンタジー
    "demo",        # デモンストレーション
    "test"         # テスト用
]

# エフェクトタイプ定数
EFFECT_TYPES = [
    "VIBRATION",   # 振動
    "MOTION",      # モーション
    "SCENT",       # 香り
    "AUDIO",       # オーディオ
    "LIGHTING",    # ライティング
    "WIND"         # 風
]