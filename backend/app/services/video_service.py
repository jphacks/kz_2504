"""
Video Service - 動画管理ビジネスロジック

動画ファイルの検索、同期データの読み込み、デバイス互換性チェック等を管理
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from config.settings import settings
from models.video import (
    EnhancedVideo, VideoInfo, VideoCompatibility, EffectInfo,
    VideoStatus, EffectComplexity, ContentRating,
    VIDEO_CATEGORIES, EFFECT_TYPES
)

logger = logging.getLogger(__name__)

class VideoService:
    """動画管理サービス"""
    
    def __init__(self):
        self.videos_path = settings.get_video_assets_path()
        self.sync_data_path = settings.get_sync_data_path()
        
        # 対応動画形式
        self.supported_formats = [".mp4", ".webm", ".avi"]
        
        # キャッシュ
        self._video_cache: Dict[str, EnhancedVideo] = {}
        self._last_scan_time: Optional[datetime] = None
    
    def scan_video_files(self, force_rescan: bool = False) -> List[EnhancedVideo]:
        """
        動画ディレクトリをスキャンして動画一覧を生成
        
        Args:
            force_rescan: 強制再スキャン
            
        Returns:
            List[EnhancedVideo]: 検出された動画リスト
        """
        current_time = datetime.now()
        
        # キャッシュチェック（5分間有効）
        if (not force_rescan and 
            self._last_scan_time and 
            (current_time - self._last_scan_time).seconds < 300 and
            self._video_cache):
            logger.info("動画リストをキャッシュから取得")
            return list(self._video_cache.values())
        
        logger.info(f"動画ディレクトリをスキャン中: {self.videos_path}")
        
        if not self.videos_path.exists():
            logger.warning(f"動画ディレクトリが存在しません: {self.videos_path}")
            return []
        
        videos = []
        
        for file_path in self.videos_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    video = self._create_video_from_file(file_path)
                    if video:
                        videos.append(video)
                        self._video_cache[video.video_id] = video
                        logger.info(f"動画を検出: {video.video_id} - {video.title}")
                except Exception as e:
                    logger.error(f"動画ファイル処理エラー {file_path}: {e}")
        
        self._last_scan_time = current_time
        logger.info(f"動画スキャン完了: {len(videos)}件")
        
        return videos
    
    def _create_video_from_file(self, file_path: Path) -> Optional[EnhancedVideo]:
        """
        ファイルパスから動画オブジェクトを生成
        
        Args:
            file_path: 動画ファイルパス
            
        Returns:
            Optional[EnhancedVideo]: 生成された動画オブジェクト
        """
        try:
            # ファイル情報取得
            file_stat = file_path.stat()
            file_size_mb = file_stat.st_size / (1024 * 1024)
            
            # 動画IDはファイル名（拡張子なし）
            video_id = file_path.stem
            
            # 基本情報作成
            video_info = VideoInfo(
                video_id=video_id,
                title=self._generate_title_from_filename(video_id),
                description=self._generate_description_from_filename(video_id),
                duration_seconds=self._estimate_duration_from_filename(video_id),
                file_name=file_path.name,
                file_size_mb=round(file_size_mb, 2),
                thumbnail_url=f"/assets/thumbnails/{video_id}.jpg",
                categories=self._categorize_video(video_id),
                content_rating=self._determine_content_rating(video_id),
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
                updated_at=datetime.fromtimestamp(file_stat.st_mtime)
            )
            
            # 同期データ読み込み
            sync_data = self._load_sync_data(video_id)
            compatibility = self._create_compatibility_info(video_id, sync_data)
            
            # 動画オブジェクト作成
            enhanced_video = EnhancedVideo(
                video_info=video_info,
                compatibility=compatibility,
                status=VideoStatus.READY,
                sync_data_file=f"{video_id}.json" if sync_data else None
            )
            
            return enhanced_video
            
        except Exception as e:
            logger.error(f"動画オブジェクト作成エラー {file_path}: {e}")
            return None
    
    def _generate_title_from_filename(self, video_id: str) -> str:
        """ファイル名から適切なタイトルを生成"""
        title_map = {
            "demo1": "デモ動画1 - アクション",
            "demo2": "デモ動画2 - ホラー",
            "test1": "テスト動画1 - 基本機能",
            "movie": "サンプル動画",
        }
        return title_map.get(video_id, f"4DX動画: {video_id.upper()}")
    
    def _generate_description_from_filename(self, video_id: str) -> str:
        """ファイル名から説明文を生成"""
        description_map = {
            "demo1": "スリリングなアクション映画のデモンストレーション。振動とモーション効果を体験できます。",
            "demo2": "恐怖のホラー映画のデモンストレーション。繊細な効果タイミングが特徴です。",
            "test1": "システム動作確認用のテスト動画。基本的な4D効果をテストできます。",
            "movie": "フロントエンドで使用されるサンプル動画ファイル。",
        }
        return description_map.get(video_id, f"{video_id}の4D体験動画です。")
    
    def _estimate_duration_from_filename(self, video_id: str) -> float:
        """ファイル名から推定再生時間を取得（秒）"""
        duration_map = {
            "demo1": 33.5,   # 実際のdemo1の長さ
            "demo2": 45.0,   # 推定
            "test1": 15.0,   # テスト用短時間
            "movie": 30.0,   # フロントエンドサンプル
        }
        return duration_map.get(video_id, 30.0)  # デフォルト30秒
    
    def _categorize_video(self, video_id: str) -> List[str]:
        """動画をカテゴリ分類"""
        category_map = {
            "demo1": ["action", "demo"],
            "demo2": ["horror", "demo"], 
            "test1": ["test"],
            "movie": ["demo", "test"],
        }
        return category_map.get(video_id, ["demo"])
    
    def _determine_content_rating(self, video_id: str) -> ContentRating:
        """コンテンツレーティングを決定"""
        rating_map = {
            "demo1": ContentRating.PG,     # アクション - 保護者指導
            "demo2": ContentRating.PG13,   # ホラー - 13歳未満注意
            "test1": ContentRating.G,      # テスト - 全年齢
            "movie": ContentRating.G,      # サンプル - 全年齢
        }
        return rating_map.get(video_id, ContentRating.G)
    
    def _load_sync_data(self, video_id: str) -> Optional[Dict[str, Any]]:
        """同期データJSONファイルを読み込み"""
        sync_file = self.sync_data_path / f"{video_id}.json"
        
        if not sync_file.exists():
            logger.info(f"同期データファイルが見つかりません: {sync_file}")
            return None
        
        try:
            with open(sync_file, 'r', encoding='utf-8') as f:
                sync_data = json.load(f)
                logger.info(f"同期データ読み込み成功: {video_id}")
                return sync_data
        except Exception as e:
            logger.error(f"同期データ読み込みエラー {sync_file}: {e}")
            return None
    
    def _create_compatibility_info(self, video_id: str, sync_data: Optional[Dict[str, Any]]) -> VideoCompatibility:
        """同期データから互換性情報を生成"""
        if not sync_data:
            # デフォルト互換性（基本機能のみ）
            return VideoCompatibility(
                required_capabilities=["VIBRATION"],
                effect_complexity=EffectComplexity.LOW
            )
        
        # 同期データから使用エフェクトを解析
        effects_used = set()
        effect_stats = {}
        
        events = sync_data.get('sync_events', [])
        
        for event in events:
            effect_type = event.get('effect', '').upper()
            if effect_type in EFFECT_TYPES:
                effects_used.add(effect_type)
                
                # 統計情報収集
                if effect_type not in effect_stats:
                    effect_stats[effect_type] = {
                        'count': 0,
                        'total_intensity': 0,
                        'total_duration': 0
                    }
                
                effect_stats[effect_type]['count'] += 1
                effect_stats[effect_type]['total_intensity'] += event.get('intensity', 0.5)
                effect_stats[effect_type]['total_duration'] += event.get('duration', 1000) / 1000  # ms to s
        
        # エフェクト情報生成
        supported_effects = []
        for effect_type, stats in effect_stats.items():
            effect_info = EffectInfo(
                effect_type=effect_type,
                count=stats['count'],
                intensity_avg=stats['total_intensity'] / stats['count'] if stats['count'] > 0 else 0,
                duration_total=stats['total_duration']
            )
            supported_effects.append(effect_info)
        
        # 複雑度判定
        if len(effects_used) >= 4:
            complexity = EffectComplexity.HIGH
        elif len(effects_used) >= 2:
            complexity = EffectComplexity.MEDIUM
        else:
            complexity = EffectComplexity.LOW
        
        return VideoCompatibility(
            required_capabilities=list(effects_used) if effects_used else ["VIBRATION"],
            supported_effects=supported_effects,
            effect_complexity=complexity
        )
    
    def get_video_by_id(self, video_id: str) -> Optional[EnhancedVideo]:
        """IDで動画を取得"""
        # キャッシュから確認
        if video_id in self._video_cache:
            return self._video_cache[video_id]
        
        # スキャンして再検索
        videos = self.scan_video_files()
        return next((v for v in videos if v.video_id == video_id), None)
    
    def filter_videos_by_device(self, videos: List[EnhancedVideo], device_capabilities: List[str]) -> List[EnhancedVideo]:
        """デバイス機能でフィルタリング"""
        compatible_videos = []
        
        for video in videos:
            if video.is_compatible_with_device(device_capabilities):
                compatible_videos.append(video)
            else:
                missing = video.get_missing_capabilities(device_capabilities)
                logger.info(f"動画 {video.video_id} は非対応 (不足機能: {missing})")
        
        logger.info(f"デバイスフィルタ結果: {len(compatible_videos)}/{len(videos)} 動画が対応")
        
        return compatible_videos
    
    def get_video_url(self, video_id: str) -> Optional[str]:
        """動画のアクセスURLを生成"""
        video = self.get_video_by_id(video_id)
        if not video:
            return None
        
        return f"/assets/videos/{video.video_info.file_name}"
    
    def get_sync_data_url(self, video_id: str) -> Optional[str]:
        """同期データのアクセスURLを生成"""
        video = self.get_video_by_id(video_id)
        if not video or not video.sync_data_file:
            return None
        
        return f"/assets/sync-data/{video.sync_data_file}"

# グローバルサービスインスタンス
video_service = VideoService()