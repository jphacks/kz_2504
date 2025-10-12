"""
同期データサービス - ラズパイデバッグコード基準実装

JSON同期データファイルの事前送信とタイムライン管理機能
demo1.jsonなどのタイムラインファイルの読み込み・送信・時間管理を提供
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import aiofiles

from app.config.settings import settings
from app.models.preparation import PreparationStatus

logger = logging.getLogger(__name__)

class SyncDataService:
    """同期データサービス - ラズパイパターン対応"""
    
    def __init__(self):
        self.sync_data_cache: Dict[str, Dict[str, Any]] = {}
        self.timeline_states: Dict[str, Dict[str, Any]] = {}
        self.sync_data_path = settings.get_sync_data_path()
    
    async def send_timeline_data_bulk(self, session_id: str, video_id: str) -> Dict[str, Any]:
        """
        タイムラインファイル丸ごと事前送信（ラズパイパターン）
        
        ラズパイデバッグコードの最初のタイムライン全体送信に対応
        """
        logger.info(f"[SYNC_DATA] タイムライン事前送信開始: {video_id} (session: {session_id})")
        
        try:
            # タイムラインファイル読み込み
            timeline_data = await self._load_timeline_file(video_id)
            if not timeline_data:
                raise FileNotFoundError(f"タイムラインファイルが見つかりません: {video_id}")
            
            # 総再生時間を計算
            total_duration = self._calculate_total_duration(timeline_data)
            events_count = len(timeline_data.get('events', []))
            
            # タイムライン状態を管理に追加
            self.timeline_states[session_id] = {
                'video_id': video_id,
                'timeline_data': timeline_data,
                'total_duration': total_duration,
                'events_count': events_count,
                'current_time': 0.0,
                'is_playing': False,
                'last_update': datetime.now(),
                'loop_count': 0
            }
            
            # メタデータ作成
            transmission_metadata = {
                'video_id': video_id,
                'total_duration': total_duration,
                'events_count': events_count,
                'file_size_kb': self._estimate_file_size(timeline_data),
                'transmission_timestamp': datetime.now().isoformat(),
                'checksum': self._calculate_checksum(timeline_data),
                'format': 'demo_json'
            }
            
            # 送信データ構築
            bulk_data = {
                'type': 'sync_data_bulk_transmission',
                'session_id': session_id,
                'video_id': video_id,
                'transmission_metadata': transmission_metadata,
                'sync_data': timeline_data
            }
            
            logger.info(f"[SYNC_DATA] タイムライン送信準備完了: {events_count}イベント, {total_duration}秒")
            return bulk_data
            
        except Exception as e:
            logger.error(f"[SYNC_DATA] タイムライン送信エラー: {e}")
            raise
    
    async def _load_timeline_file(self, video_id: str) -> Optional[Dict[str, Any]]:
        """タイムラインJSONファイル読み込み"""
        if video_id in self.sync_data_cache:
            logger.debug(f"[SYNC_DATA] キャッシュから取得: {video_id}")
            return self.sync_data_cache[video_id]
        
        timeline_file = self.sync_data_path / f"{video_id}.json"
        
        if not timeline_file.exists():
            logger.warning(f"[SYNC_DATA] ファイルが見つかりません: {timeline_file}")
            return None
        
        try:
            async with aiofiles.open(timeline_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                timeline_data = json.loads(content)
                
            # キャッシュに保存
            self.sync_data_cache[video_id] = timeline_data
            logger.info(f"[SYNC_DATA] タイムラインファイル読み込み完了: {timeline_file}")
            return timeline_data
            
        except Exception as e:
            logger.error(f"[SYNC_DATA] ファイル読み込みエラー {timeline_file}: {e}")
            return None
    
    def _calculate_total_duration(self, timeline_data: Dict[str, Any]) -> float:
        """タイムラインの総再生時間を計算"""
        events = timeline_data.get('events', [])
        if not events:
            return 0.0
        
        # 最後のイベント時刻を取得
        max_time = max(event.get('t', 0) for event in events)
        return float(max_time)
    
    def _estimate_file_size(self, timeline_data: Dict[str, Any]) -> float:
        """ファイルサイズ推定（KB）"""
        try:
            json_str = json.dumps(timeline_data)
            size_bytes = len(json_str.encode('utf-8'))
            return round(size_bytes / 1024, 2)
        except:
            return 0.0
    
    def _calculate_checksum(self, timeline_data: Dict[str, Any]) -> str:
        """簡易チェックサム計算"""
        try:
            json_str = json.dumps(timeline_data, sort_keys=True)
            return f"md5_{hash(json_str) & 0xffffffff:08x}"
        except:
            return "checksum_error"
    
    def get_timeline_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """タイムライン状態取得"""
        return self.timeline_states.get(session_id)
    
    def update_current_time(self, session_id: str, current_time: float, is_playing: bool = True) -> Dict[str, Any]:
        """
        現在時刻更新（ラズパイの連続送信パターン）
        
        ループ再生対応: total_durationに到達したらリセット
        """
        if session_id not in self.timeline_states:
            logger.warning(f"[SYNC_DATA] セッション状態が見つかりません: {session_id}")
            return {}
        
        state = self.timeline_states[session_id]
        total_duration = state.get('total_duration', 0.0)
        
        # ループ再生チェック
        if current_time > total_duration and total_duration > 0:
            state['loop_count'] += 1
            current_time = current_time % total_duration  # 時間をリセット
            logger.info(f"[SYNC_DATA] ループ再生リセット: {session_id}, loop#{state['loop_count']}, time={current_time}")
        
        # 状態更新
        state.update({
            'current_time': current_time,
            'is_playing': is_playing,
            'last_update': datetime.now()
        })
        
        return {
            'session_id': session_id,
            'current_time': current_time,
            'total_duration': total_duration,
            'is_playing': is_playing,
            'loop_count': state['loop_count'],
            'video_id': state.get('video_id')
        }
    
    def find_events_at_time(self, session_id: str, target_time: float, tolerance: float = 0.1) -> List[Dict[str, Any]]:
        """
        指定時刻のイベント検索
        
        ラズパイのタイムライン処理に対応
        """
        if session_id not in self.timeline_states:
            return []
        
        state = self.timeline_states[session_id]
        timeline_data = state.get('timeline_data', {})
        events = timeline_data.get('events', [])
        
        matching_events = []
        for event in events:
            event_time = event.get('t', 0)
            if abs(event_time - target_time) <= tolerance:
                matching_events.append(event)
        
        if matching_events:
            logger.debug(f"[SYNC_DATA] {len(matching_events)}イベント発見 at {target_time}s (session: {session_id})")
        
        return matching_events
    
    def get_timeline_info(self, session_id: str) -> Dict[str, Any]:
        """タイムライン情報取得"""
        if session_id not in self.timeline_states:
            return {}
        
        state = self.timeline_states[session_id]
        return {
            'video_id': state.get('video_id'),
            'total_duration': state.get('total_duration'),
            'events_count': state.get('events_count'),
            'current_time': state.get('current_time'),
            'is_playing': state.get('is_playing'),
            'loop_count': state.get('loop_count'),
            'last_update': state.get('last_update').isoformat() if state.get('last_update') else None
        }
    
    def cleanup_session(self, session_id: str):
        """セッション状態クリーンアップ"""
        if session_id in self.timeline_states:
            del self.timeline_states[session_id]
            logger.info(f"[SYNC_DATA] セッション状態削除: {session_id}")

# サービスインスタンス
sync_data_service = SyncDataService()