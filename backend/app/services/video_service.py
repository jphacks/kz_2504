# app/services/video_service.py - 動画・同期データ管理サービス
import json
import os
from typing import List, Dict, Optional
from app.models.schemas import Video, SyncData, SyncEvent
from app.config.settings import Settings

class VideoService:
    """動画・同期データ管理サービス"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sync_data_dir = settings.sync_data_directory
        
    def get_available_videos(self) -> List[Video]:
        """利用可能な動画リストを取得"""
        videos = []
        
        # 同期データディレクトリから動画情報を読み取り
        if os.path.exists(self.sync_data_dir):
            for filename in os.listdir(self.sync_data_dir):
                if filename.endswith('.json'):
                    video_id = filename.replace('.json', '')
                    try:
                        sync_data = self.load_sync_data(video_id)
                        if sync_data:
                            video = Video(
                                video_id=video_id,
                                title=sync_data.get('title', f'Video {video_id}'),
                                duration=sync_data.get('duration', 0.0),
                                video_size=sync_data.get('video_size', 0),
                                video_url=self.settings.get_video_url(video_id),
                                thumbnail=f"/assets/thumbnails/{video_id}.jpg"
                            )
                            videos.append(video)
                    except Exception as e:
                        print(f"動画情報読み込みエラー {video_id}: {e}")
                        
        return videos
        
    def get_video_info(self, video_id: str) -> Optional[Video]:
        """指定動画の情報を取得"""
        videos = self.get_available_videos()
        for video in videos:
            if video.video_id == video_id:
                return video
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