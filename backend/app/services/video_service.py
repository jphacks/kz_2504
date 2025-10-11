# app/services/video_service.py - Enhanced video management service with device compatibility
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.models.video import EnhancedVideo, VideoManager, DeviceCapability, EffectComplexity, SyncData
from app.models.schemas import Video, SyncEvent
from app.config.settings import Settings

class VideoService:
    """Enhanced video management service with device compatibility support"""
    
    def __init__(self, settings: Settings, video_data_path: str = "backend/data/videos.json"):
        self.settings = settings
        self.sync_data_dir = settings.sync_data_directory
        self.video_data_path = video_data_path
        self.video_manager = VideoManager()
        self._load_video_data()
    def _load_video_data(self) -> None:
        """Load video metadata from JSON file"""
        if os.path.exists(self.video_data_path):
            try:
                with open(self.video_data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert JSON data to EnhancedVideo objects
                for video_data in data.get('videos', []):
                    video = EnhancedVideo(**video_data)
                    self.video_manager.add_video(video)
                    
            except Exception as e:
                print(f"Error loading video data: {e}")
                # Initialize with empty data if loading fails
                self._initialize_default_videos()
        else:
            # Create default video data if file doesn't exist
            self._initialize_default_videos()
    
    def _initialize_default_videos(self) -> None:
        """Initialize default video data for demonstration"""
        default_videos = [
            {
                "id": "demo1",
                "title": "アクション映画デモ - ロボット vs 怪獣",
                "description": "巨大ロボットと怪獣の壮絶なバトルシーン。水しぶき、振動、ライティングエフェクト満載",
                "duration_seconds": 33.5,
                "sync_file": "demo1.json",
                "thumbnail_url": "/assets/thumbnails/demo1.jpg",
                "supported_effects": ["vibration", "water", "color", "flash", "wind"],
                "device_requirements": ["vibration_motor", "water_spray", "led_strip"],
                "effect_complexity": "high",
                "content_rating": "family",
                "categories": ["action", "sci-fi", "demo"],
                "language": "ja"
            },
            {
                "id": "nature1", 
                "title": "自然体験 - 森の中の散歩",
                "description": "静かな森の中を歩く体験。鳥のさえずり、風のそよぎ、自然の香りを楽しむ",
                "duration_seconds": 180.0,
                "sync_file": "nature1.json",
                "thumbnail_url": "/assets/thumbnails/nature1.jpg",
                "supported_effects": ["wind", "scent", "color"],
                "device_requirements": ["fan", "scent_diffuser", "led_strip"],
                "effect_complexity": "low",
                "content_rating": "all_ages",
                "categories": ["nature", "relaxation"],
                "language": "ja"
            },
            {
                "id": "racing1",
                "title": "レーシング体験 - F1グランプリ",
                "description": "高速サーキットでのF1体験。風圧、エンジン音、コーナリングの臨場感を再現",
                "duration_seconds": 240.0,
                "sync_file": "racing1.json", 
                "thumbnail_url": "/assets/thumbnails/racing1.jpg",
                "supported_effects": ["vibration", "wind", "motion"],
                "device_requirements": ["vibration_motor", "fan", "motion_platform"],
                "effect_complexity": "medium",
                "content_rating": "teen",
                "categories": ["racing", "sports"],
                "language": "ja"
            }
        ]
        
        for video_data in default_videos:
            video = EnhancedVideo(**video_data)
            self.video_manager.add_video(video)
        
    def get_all_enhanced_videos(self) -> List[EnhancedVideo]:
        """Get list of all available enhanced videos"""
        return self.video_manager.get_all_videos()
    
    def get_enhanced_video_by_id(self, video_id: str) -> Optional[EnhancedVideo]:
        """Get specific enhanced video by ID"""
        return self.video_manager.get_video_by_id(video_id)
        
    def get_available_videos(self) -> List[Video]:
        """利用可能な動画リストを取得（Legacy compatibility method）"""
        enhanced_videos = self.get_all_enhanced_videos()
        videos = []
        
        for enhanced_video in enhanced_videos:
            # Convert EnhancedVideo to legacy Video format
            video = Video(
                video_id=enhanced_video.id,
                title=enhanced_video.title,
                duration=enhanced_video.duration_seconds,
                video_size=0,  # Will be calculated from actual video file
                video_url=self.settings.get_video_url(enhanced_video.id) if hasattr(self.settings, 'get_video_url') else f"/videos/{enhanced_video.id}.mp4",
                thumbnail=enhanced_video.thumbnail_url
            )
            videos.append(video)
                        
        return videos
    
    def get_compatible_videos(self, device_capabilities: List[DeviceCapability]) -> List[EnhancedVideo]:
        """Get videos compatible with given device capabilities"""
        return self.video_manager.filter_by_device_compatibility(device_capabilities)
    
    def get_videos_by_complexity(self, max_complexity: EffectComplexity) -> List[EnhancedVideo]:
        """Get videos filtered by maximum effect complexity"""
        return self.video_manager.filter_by_complexity(max_complexity)
    
    def get_videos_by_category(self, category: str) -> List[EnhancedVideo]:
        """Get videos filtered by category"""
        all_videos = self.get_all_enhanced_videos()
        return [video for video in all_videos if category in video.categories]
        
    def get_video_info(self, video_id: str) -> Optional[Video]:
        """指定動画の情報を取得（Legacy compatibility method）"""
        enhanced_video = self.get_enhanced_video_by_id(video_id)
        if not enhanced_video:
            return None
            
        return Video(
            video_id=enhanced_video.id,
            title=enhanced_video.title,
            duration=enhanced_video.duration_seconds,
            video_size=0,
            video_url=self.settings.get_video_url(enhanced_video.id) if hasattr(self.settings, 'get_video_url') else f"/videos/{enhanced_video.id}.mp4",
            thumbnail=enhanced_video.thumbnail_url
        )
    
    def get_video_sync_data(self, video_id: str) -> Optional[SyncData]:
        """Get enhanced sync pattern data for a specific video"""
        video = self.get_enhanced_video_by_id(video_id)
        if not video:
            return None
        
        sync_file_path = os.path.join(self.sync_data_dir, video.sync_file)
        if not os.path.exists(sync_file_path):
            return None
        
        try:
            with open(sync_file_path, 'r', encoding='utf-8') as f:
                sync_data = json.load(f)
            
            return SyncData(
                video_id=video_id,
                events=sync_data.get('events', []),
                metadata=sync_data.get('metadata', {})
            )
        except Exception as e:
            print(f"Error loading sync data for {video_id}: {e}")
            return None
        
    def load_sync_data(self, video_id: str) -> Optional[Dict]:
        """同期データファイルを読み込み"""
        sync_file = os.path.join(self.sync_data_dir, f"{video_id}.json")
        
        if not os.path.exists(sync_file):
            return None
            
        try:
            with open(sync_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"同期データ読み込みエラー {video_id}: {e}")
            return None
            
    def get_sync_data(self, video_id: str) -> Optional[SyncData]:
        """動画の同期データを取得"""
        raw_data = self.load_sync_data(video_id)
        if not raw_data:
            return None
            
        try:
            # 同期イベントのパース
            sync_events = []
            for event_data in raw_data.get('sync_events', []):
                event = SyncEvent(
                    time=event_data['time'],
                    action=event_data['action'],
                    intensity=event_data['intensity'],
                    duration=event_data['duration']
                )
                sync_events.append(event)
                
            # SyncDataモデル作成
            sync_data = SyncData(
                video_id=video_id,
                duration=raw_data.get('duration', 0.0),
                video_url=self.settings.get_video_url(video_id),
                video_size=raw_data.get('video_size', 0),
                sync_events=sync_events
            )
            
            return sync_data
            
        except Exception as e:
            print(f"同期データパースエラー {video_id}: {e}")
            return None
            
    def validate_video_exists(self, video_id: str) -> bool:
        """動画の存在確認"""
        return self.get_video_info(video_id) is not None
        
    def get_sync_events_for_timeframe(self, video_id: str, start_time: float, end_time: float) -> List[SyncEvent]:
        """指定時間範囲の同期イベントを取得"""
        sync_data = self.get_sync_data(video_id)
        if not sync_data:
            return []
            
        events = []
        for event in sync_data.sync_events:
            if start_time <= event.time <= end_time:
                events.append(event)
                
        return sorted(events, key=lambda x: x.time)
        
    def create_sample_sync_data(self, video_id: str, duration: float) -> bool:
        """サンプル同期データを作成（開発用）"""
        sample_data = {
            "video_id": video_id,
            "title": f"Sample Video {video_id}",
            "duration": duration,
            "video_size": 1024000,  # 1MB sample
            "sync_events": [
                {
                    "time": 10.0,
                    "action": "vibration",
                    "intensity": 70,
                    "duration": 500
                },
                {
                    "time": 25.0,
                    "action": "scent",
                    "intensity": 50,
                    "duration": 2000
                },
                {
                    "time": 45.0,
                    "action": "vibration",
                    "intensity": 90,
                    "duration": 300
                }
            ]
        }
        
        try:
            os.makedirs(self.sync_data_dir, exist_ok=True)
            sync_file = os.path.join(self.sync_data_dir, f"{video_id}.json")
            
            with open(sync_file, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"サンプルデータ作成エラー {video_id}: {e}")
            return False
    
    def validate_video_compatibility(self, video_id: str, 
                                   device_capabilities: List[DeviceCapability]) -> Dict[str, Any]:
        """
        Validate if a video is compatible with device capabilities
        
        Returns:
            Dict containing compatibility status and details
        """
        video = self.get_enhanced_video_by_id(video_id)
        if not video:
            return {
                "compatible": False,
                "error": "Video not found",
                "missing_capabilities": [],
                "supported_effects": []
            }
        
        is_compatible = self.video_manager.check_device_compatibility(video, device_capabilities)
        
        # Find missing capabilities
        required_caps = set(video.device_requirements)
        available_caps = set([cap.value for cap in device_capabilities])
        missing_caps = list(required_caps - available_caps)
        
        # Find supported effects that can be used
        supported_effects = []
        for effect in video.supported_effects:
            # Map effects to required capabilities (simplified mapping)
            effect_capability_map = {
                "vibration": "vibration_motor",
                "water": "water_spray", 
                "wind": "fan",
                "color": "led_strip",
                "flash": "led_strip",
                "scent": "scent_diffuser",
                "motion": "motion_platform"
            }
            
            required_cap = effect_capability_map.get(effect)
            if required_cap and required_cap in available_caps:
                supported_effects.append(effect)
        
        return {
            "compatible": is_compatible,
            "video_id": video_id,
            "video_title": video.title,
            "missing_capabilities": missing_caps,
            "supported_effects": supported_effects,
            "effect_complexity": video.effect_complexity.value,
            "duration": video.duration_seconds
        }
    
    def get_video_statistics(self) -> Dict[str, Any]:
        """Get statistics about available videos"""
        all_videos = self.get_all_enhanced_videos()
        
        if not all_videos:
            return {
                "total_videos": 0,
                "by_complexity": {},
                "by_category": {},
                "total_duration": 0.0,
                "available_effects": []
            }
        
        # Count by complexity
        complexity_counts = {}
        for complexity in EffectComplexity:
            complexity_counts[complexity.value] = len(
                self.get_videos_by_complexity(complexity)
            )
        
        # Count by category
        category_counts = {}
        all_categories = set()
        for video in all_videos:
            all_categories.update(video.categories)
        
        for category in all_categories:
            category_counts[category] = len(self.get_videos_by_category(category))
        
        # Calculate total duration
        total_duration = sum(video.duration_seconds for video in all_videos)
        
        # Collect all available effects
        all_effects = set()
        for video in all_videos:
            all_effects.update(video.supported_effects)
        
        return {
            "total_videos": len(all_videos),
            "by_complexity": complexity_counts,
            "by_category": category_counts, 
            "total_duration": total_duration,
            "available_effects": sorted(list(all_effects)),
            "last_updated": datetime.now().isoformat()
        }
    
    def search_videos(self, query: str = "", 
                     categories: Optional[List[str]] = None,
                     max_complexity: Optional[EffectComplexity] = None,
                     device_capabilities: Optional[List[DeviceCapability]] = None) -> List[EnhancedVideo]:
        """
        Search videos with filters
        
        Args:
            query: Search term for title/description
            categories: Filter by categories
            max_complexity: Maximum effect complexity
            device_capabilities: Filter by device compatibility
            
        Returns:
            List of matching videos
        """
        videos = self.get_all_enhanced_videos()
        
        # Text search
        if query:
            query_lower = query.lower()
            videos = [
                video for video in videos 
                if query_lower in video.title.lower() or 
                   query_lower in video.description.lower()
            ]
        
        # Category filter
        if categories:
            videos = [
                video for video in videos
                if any(cat in video.categories for cat in categories)
            ]
        
        # Complexity filter
        if max_complexity:
            videos = [
                video for video in videos
                if EffectComplexity.get_complexity_level(video.effect_complexity) <= 
                   EffectComplexity.get_complexity_level(max_complexity)
            ]
        
        # Device compatibility filter  
        if device_capabilities:
            videos = [
                video for video in videos
                if self.video_manager.check_device_compatibility(video, device_capabilities)
            ]
        
        return videos

    def save_video_data(self) -> bool:
        """Save current video data to file"""
        try:
            videos_data = {
                "videos": [video.dict() for video in self.get_all_enhanced_videos()],
                "last_updated": datetime.now().isoformat()
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.video_data_path), exist_ok=True)
            
            with open(self.video_data_path, 'w', encoding='utf-8') as f:
                json.dump(videos_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving video data: {e}")
            return False