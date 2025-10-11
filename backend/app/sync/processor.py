# app/sync/processor.py - リアルタイム同期処理エンジン
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.models.schemas import SyncEvent, SyncData
from app.config.settings import Settings
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)

class TimingController:
    """高精度タイミング制御クラス"""
    
    def __init__(self):
        self.network_delay_buffer_ms = 50  # ネットワーク遅延バッファ
        self.processing_delay_buffer_ms = 20  # 処理遅延バッファ
        self.sync_tolerance_ms = 500  # 同期許容誤差
        
    def calculate_send_timing(self, event_time: float, current_time: float) -> tuple[bool, float]:
        """
        イベント送信タイミング計算
        Returns: (should_send, delay_adjustment)
        """
        time_diff = event_time - current_time
        total_buffer = (self.network_delay_buffer_ms + self.processing_delay_buffer_ms) / 1000.0
        
        # 送信判定：イベント時刻の前後500ms以内
        tolerance = self.sync_tolerance_ms / 1000.0
        should_send = abs(time_diff) <= tolerance
        
        # 遅延調整計算
        if should_send and time_diff > 0:
            # 未来のイベント：バッファを考慮して早めに送信
            delay_adjustment = max(0, time_diff - total_buffer)
        else:
            delay_adjustment = 0
            
        return should_send, delay_adjustment
    
    def is_event_in_sync_window(self, event_time: float, current_time: float) -> bool:
        """イベントが同期ウィンドウ内にあるかチェック"""
        tolerance = self.sync_tolerance_ms / 1000.0
        return abs(event_time - current_time) <= tolerance

class CapabilityFilter:
    """デバイス能力フィルタリングクラス"""
    
    def __init__(self):
        self.supported_actions = {
            "vibration": ["vibration", "haptic"],
            "motion": ["motion", "movement"],
            "scent": ["scent", "fragrance", "aroma"],
            "audio": ["audio", "sound"],
            "wind": ["wind", "air"]
        }
    
    def filter_events_by_capabilities(self, events: List[SyncEvent], 
                                    device_capabilities: List[str]) -> List[SyncEvent]:
        """デバイス能力に基づくイベントフィルタリング"""
        if not device_capabilities:
            return events
            
        filtered_events = []
        for event in events:
            # アクションタイプがデバイス能力に含まれているかチェック
            action_supported = False
            for capability in device_capabilities:
                if (event.action.lower() == capability.lower() or 
                    capability.lower() in self.supported_actions.get(event.action.lower(), [])):
                    action_supported = True
                    break
                    
            if action_supported:
                filtered_events.append(event)
            else:
                logger.debug(f"イベント除外: {event.action} (デバイス能力不足)")
                
        return filtered_events
    
    def apply_user_preferences(self, events: List[SyncEvent], 
                             user_settings: Dict[str, Any]) -> List[SyncEvent]:
        """ユーザー設定に基づくイベント調整"""
        adjusted_events = []
        
        for event in events:
            # ユーザーがこのアクションを無効にしている場合はスキップ
            if not user_settings.get(f"{event.action}_enabled", True):
                logger.debug(f"ユーザー設定によりイベント除外: {event.action}")
                continue
            
            # 強度設定適用
            intensity_multiplier = user_settings.get(f"{event.action}_intensity", 1.0)
            adjusted_intensity = min(100, int(event.intensity * intensity_multiplier))
            
            # 調整されたイベントを作成
            adjusted_event = SyncEvent(
                time=event.time,
                action=event.action,
                intensity=adjusted_intensity,
                duration=event.duration
            )
            adjusted_events.append(adjusted_event)
            
        return adjusted_events

class SyncProcessor:
    """リアルタイム同期処理メインクラス（新仕様対応）"""
    
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.video_service = VideoService(self.settings)
        self.timing_controller = TimingController()
        self.capability_filter = CapabilityFilter()
        
        # 同期データキャッシュ
        self._sync_data_cache: Dict[str, SyncData] = {}
        
        # アクティブセッション管理（新仕様：事前データ保存）
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # 新仕様：事前送信された同期データファイル管理
        self.preloaded_sync_data: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SyncProcessor初期化完了（新仕様対応）")
    
    async def start_playback_sync(self, session_id: str, video_id: str, 
                                device_capabilities: List[str] = None,
                                user_settings: Dict[str, Any] = None) -> bool:
        """
        再生同期開始
        """
        try:
            # 同期データ読み込み
            sync_data = self.video_service.get_sync_data(video_id)
            if not sync_data:
                logger.error(f"同期データ取得失敗: {video_id}")
                return False
            
            # セッション情報登録
            self.active_sessions[session_id] = {
                "video_id": video_id,
                "sync_data": sync_data,
                "device_capabilities": device_capabilities or [],
                "user_settings": user_settings or {},
                "start_time": datetime.now(),
                "last_sync_time": 0.0
            }
            
            logger.info(f"再生同期開始: セッション {session_id}, 動画 {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"再生同期開始エラー: セッション {session_id}, エラー: {e}")
            return False
    
    def find_sync_events_for_time(self, session_id: str, current_time: float) -> List[Dict[str, Any]]:
        """
        指定時刻の同期イベント検索・コマンド生成
        """
        if session_id not in self.active_sessions:
            logger.warning(f"アクティブでないセッション: {session_id}")
            return []
            
        session_info = self.active_sessions[session_id]
        sync_data = session_info["sync_data"]
        
        # 同期ウィンドウ内のイベント検索
        candidate_events = []
        for event in sync_data.sync_events:
            if self.timing_controller.is_event_in_sync_window(event.time, current_time):
                candidate_events.append(event)
        
        if not candidate_events:
            return []
            
        # デバイス能力フィルタリング
        filtered_events = self.capability_filter.filter_events_by_capabilities(
            candidate_events, session_info["device_capabilities"]
        )
        
        # ユーザー設定適用
        adjusted_events = self.capability_filter.apply_user_preferences(
            filtered_events, session_info["user_settings"]
        )
        
        # コマンド生成
        commands = []
        for event in adjusted_events:
            should_send, delay_adjustment = self.timing_controller.calculate_send_timing(
                event.time, current_time
            )
            
            if should_send:
                command = {
                    "type": "effect_command",
                    "effect_id": f"{session_id}_{event.time}_{event.action}",
                    "action": event.action,
                    "intensity": event.intensity,
                    "duration": event.duration,
                    "delay_ms": int(delay_adjustment * 1000),
                    "sync_time": event.time,
                    "current_time": current_time
                }
                commands.append(command)
                
        # 最終同期時刻更新
        session_info["last_sync_time"] = current_time
        
        if commands:
            logger.debug(f"同期コマンド生成: セッション {session_id}, 時刻 {current_time:.1f}s, コマンド数 {len(commands)}")
            
        return commands
    
    def stop_playback_sync(self, session_id: str):
        """再生同期停止"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"再生同期停止: セッション {session_id}")
    
    def get_sync_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """同期状態取得"""
        if session_id not in self.active_sessions:
            return None
            
        session_info = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "video_id": session_info["video_id"],
            "is_active": True,
            "last_sync_time": session_info["last_sync_time"],
            "total_events": len(session_info["sync_data"].sync_events),
            "device_capabilities": session_info["device_capabilities"]
        }
    
    def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        """期限切れセッション削除"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        expired_sessions = []
        
        for session_id, session_info in self.active_sessions.items():
            if session_info["start_time"] < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
            
        if expired_sessions:
            logger.info(f"期限切れセッション削除: {len(expired_sessions)}件")
            
        return len(expired_sessions)
    
    # 新仕様対応メソッド
    
    async def preload_sync_data(self, session_id: str, sync_data_file: Dict[str, Any]) -> bool:
        """
        同期データファイル事前読み込み（待機画面時）
        """
        try:
            from app.models.schemas import SyncDataFile, SyncEvent
            
            # 同期データファイル解析
            sync_events = [SyncEvent(**event) for event in sync_data_file.get("sync_events", [])]
            
            # 事前データ保存
            self.preloaded_sync_data[session_id] = {
                "video_id": sync_data_file["video_id"],
                "video_duration": sync_data_file["video_duration"],
                "sync_events": sync_events,
                "preloaded_at": datetime.now(),
                "processed": False
            }
            
            logger.info(f"同期データ事前読み込み: セッション {session_id}, 動画 {sync_data_file['video_id']}, イベント数 {len(sync_events)}")
            return True
            
        except Exception as e:
            logger.error(f"同期データ事前読み込みエラー: セッション {session_id}, エラー: {e}")
            return False
    
    async def process_realtime_sync(self, session_id: str, playback_sync: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        リアルタイム再生時刻同期処理（新仕様）
        """
        if session_id not in self.preloaded_sync_data:
            logger.warning(f"事前読み込みデータなし: セッション {session_id}")
            return []
        
        try:
            current_time = playback_sync["current_time"]
            is_playing = playback_sync.get("is_playing", True)
            video_id = playback_sync["video_id"]
            
            # 事前読み込みデータ取得
            preload_data = self.preloaded_sync_data[session_id]
            
            if preload_data["video_id"] != video_id:
                logger.warning(f"動画ID不一致: 事前読み込み {preload_data['video_id']} vs 現在 {video_id}")
                return []
            
            if not is_playing:
                # 一時停止中は同期処理しない
                return []
            
            # タイムライン同期処理
            sync_commands = []
            tolerance = 0.1  # 許容誤差100ms
            
            for event in preload_data["sync_events"]:
                # 現在時刻に対応するイベントを検索
                if abs(event.time - current_time) <= tolerance:
                    command = {
                        "type": "timeline_sync_command",
                        "command_type": event.action,
                        "intensity": event.intensity,
                        "duration": event.duration,
                        "video_time": event.time,
                        "sync_precision": abs(event.time - current_time),
                        "timestamp": datetime.now().isoformat()
                    }
                    sync_commands.append(command)
            
            # 処理状況更新
            if sync_commands:
                preload_data["last_sync_time"] = current_time
                logger.debug(f"リアルタイム同期処理: セッション {session_id}, 時刻 {current_time:.2f}s, コマンド数 {len(sync_commands)}")
            
            return sync_commands
            
        except Exception as e:
            logger.error(f"リアルタイム同期処理エラー: セッション {session_id}, エラー: {e}")
            return []
    
    async def execute_direct_command(self, session_id: str, sync_command: Dict[str, Any]) -> bool:
        """
        直接同期コマンド実行（新仕様）
        """
        try:
            # 直接実行のため特別な処理は不要、ログ記録のみ
            logger.info(f"直接同期コマンド実行: セッション {session_id}, コマンド {sync_command.get('command_type')} @ {sync_command.get('video_time', 0):.1f}s")
            return True
            
        except Exception as e:
            logger.error(f"直接同期コマンド実行エラー: セッション {session_id}, エラー: {e}")
            return False
    
    def get_preload_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """事前読み込み状態取得"""
        if session_id not in self.preloaded_sync_data:
            return None
            
        preload_data = self.preloaded_sync_data[session_id]
        return {
            "session_id": session_id,
            "video_id": preload_data["video_id"],
            "events_count": len(preload_data["sync_events"]),
            "preloaded_at": preload_data["preloaded_at"].isoformat(),
            "last_sync_time": preload_data.get("last_sync_time", 0),
            "is_ready": True
        }
    
    def cleanup_preload_data(self, session_id: str):
        """事前読み込みデータ削除"""
        if session_id in self.preloaded_sync_data:
            del self.preloaded_sync_data[session_id]
            logger.info(f"事前読み込みデータ削除: セッション {session_id}")

# グローバル同期プロセッサ
sync_processor = SyncProcessor()