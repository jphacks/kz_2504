"""
4DX@HOME Timeline Processor
タイムラインイベントを処理し、現在時刻に基づいてMQTTコマンドを発行
"""

import logging
import asyncio
from typing import Dict, List, Optional, Callable
from config import Config

logger = logging.getLogger(__name__)


class TimelineProcessor:
    """タイムライン処理エンジン"""
    
    def __init__(
        self,
        on_event_callback: Optional[Callable[[Dict], None]] = None
    ):
        """
        Args:
            on_event_callback: イベント発火時のコールバック関数
        """
        self.timeline: List[Dict] = []
        self.current_time: float = 0.0
        self.last_processed_time: float = -1.0
        self.is_playing: bool = False
        self.on_event_callback = on_event_callback
        self.sync_tolerance_ms = Config.SYNC_TOLERANCE_MS
    
    def load_timeline(self, timeline_data: Dict) -> None:
        """タイムラインデータをロード
        
        Args:
            timeline_data: タイムラインデータ
                {
                    "events": [
                        {"t": 0, "effect": "vibration", "mode": "strong", "action": "start"},
                        ...
                    ]
                }
                または
                {
                    "session_id": "session123",
                    "video_id": "demo1",
                    "timeline": [...]
                }
        """
        try:
            # 'events'フィールドまたは'timeline'フィールドをサポート
            self.timeline = timeline_data.get("events", timeline_data.get("timeline", []))
            session_id = timeline_data.get("session_id", "unknown")
            video_id = timeline_data.get("video_id", "unknown")
            
            # タイムスタンプでソート
            self.timeline.sort(key=lambda e: e.get("t", 0))
            
            logger.info(
                f"タイムラインロード完了: session_id={session_id}, "
                f"video_id={video_id}, events={len(self.timeline)}"
            )
            
            # 処理状態をリセット
            self.last_processed_time = -1.0
            self.current_time = 0.0
        
        except Exception as e:
            logger.error(f"タイムラインロードエラー: {e}", exc_info=True)
    
    def update_current_time(self, current_time: float) -> None:
        """現在時刻を更新し、該当イベントを処理
        
        Args:
            current_time: 現在時刻（秒）
        """
        self.current_time = current_time
        
        if not self.is_playing:
            return
        
        # 該当イベントを検索・実行
        self._process_events_at_time(current_time)
    
    def start_playback(self) -> None:
        """再生開始"""
        self.is_playing = True
        self.last_processed_time = -1.0
        logger.info("タイムライン再生開始")
    
    def stop_playback(self) -> None:
        """再生停止"""
        self.is_playing = False
        logger.info("タイムライン再生停止")
    
    def reset(self) -> None:
        """リセット"""
        self.is_playing = False
        self.current_time = 0.0
        self.last_processed_time = -1.0
        logger.info("タイムラインリセット")
    
    def _process_events_at_time(self, current_time: float) -> None:
        """指定時刻のイベントを処理
        
        Args:
            current_time: 現在時刻（秒）
        """
        tolerance_sec = self.sync_tolerance_ms / 1000.0
        
        # 処理対象イベントを抽出
        events_to_process = []
        
        for event in self.timeline:
            event_time = event.get("t", 0)
            
            # 既に処理済みの時刻より前のイベントはスキップ
            if event_time <= self.last_processed_time:
                continue
            
            # 現在時刻±tolerance内のイベントを処理
            if abs(event_time - current_time) <= tolerance_sec:
                events_to_process.append(event)
            
            # 現在時刻を過ぎたイベントは次回以降
            if event_time > current_time + tolerance_sec:
                break
        
        # イベント実行
        for event in events_to_process:
            self._execute_event(event)
        
        # 処理済み時刻を更新
        if events_to_process:
            self.last_processed_time = current_time
    
    def _execute_event(self, event: Dict) -> None:
        """イベントを実行
        
        Args:
            event: イベントデータ
                {"t": 1.5, "effect": "vibration", "mode": "strong", "action": "start"}
        """
        try:
            event_time = event.get("t", 0)
            effect = event.get("effect", "unknown")
            mode = event.get("mode", "")
            action = event.get("action", "start")
            
            logger.info(
                f"イベント実行: t={event_time}, effect={effect}, "
                f"mode={mode}, action={action}"
            )
            
            # コールバック実行
            if self.on_event_callback:
                self.on_event_callback(event)
        
        except Exception as e:
            logger.error(f"イベント実行エラー: {e}", exc_info=True)
    
    def get_upcoming_events(self, lookahead_seconds: float = 5.0) -> List[Dict]:
        """今後発生するイベントを取得
        
        Args:
            lookahead_seconds: 先読み秒数
        
        Returns:
            今後lookahead_seconds秒以内に発生するイベントのリスト
        """
        upcoming = []
        end_time = self.current_time + lookahead_seconds
        
        for event in self.timeline:
            event_time = event.get("t", 0)
            
            if event_time > self.current_time and event_time <= end_time:
                upcoming.append(event)
        
        return upcoming
    
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        total_events = len(self.timeline)
        
        processed_events = sum(
            1 for e in self.timeline
            if e.get("t", 0) <= self.last_processed_time
        )
        
        return {
            "total_events": total_events,
            "processed_events": processed_events,
            "remaining_events": total_events - processed_events,
            "current_time": self.current_time,
            "last_processed_time": self.last_processed_time,
            "is_playing": self.is_playing
        }
