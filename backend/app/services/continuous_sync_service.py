"""
リアルタイム同期サービス - ラズパイ連続送信パターン実装

0.5秒ごとのcurrentTime連続送信とループ再生対応
ラズパイデバッグコードの連続送信ループを再現
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime
import time

from app.services.sync_data_service import sync_data_service

logger = logging.getLogger(__name__)

class ContinuousSyncService:
    """連続時間同期サービス"""
    
    def __init__(self):
        self.active_syncs: Dict[str, Dict[str, Any]] = {}
        self.sync_tasks: Dict[str, asyncio.Task] = {}
        self.sync_callbacks: Dict[str, Callable] = {}
    
    async def start_continuous_sync(
        self, 
        session_id: str,
        callback: Callable[[Dict[str, Any]], None],
        interval: float = 0.5  # ラズパイと同じ0.5秒間隔
    ):
        """
        連続同期開始（ラズパイパターン）
        
        Args:
            session_id: セッションID
            callback: 時間更新時のコールバック関数
            interval: 送信間隔（秒）
        """
        if session_id in self.sync_tasks:
            logger.warning(f"[CONTINUOUS_SYNC] 既に開始済み: {session_id}")
            return
        
        # タイムライン状態確認
        timeline_state = sync_data_service.get_timeline_state(session_id)
        if not timeline_state:
            logger.error(f"[CONTINUOUS_SYNC] タイムライン状態が見つかりません: {session_id}")
            return
        
        # 同期状態初期化
        self.active_syncs[session_id] = {
            'start_time': time.time(),
            'current_time': 0.0,
            'is_playing': True,
            'interval': interval,
            'total_duration': timeline_state.get('total_duration', 0.0),
            'loop_count': 0
        }
        
        self.sync_callbacks[session_id] = callback
        
        # 連続同期タスク開始
        task = asyncio.create_task(self._continuous_sync_loop(session_id))
        self.sync_tasks[session_id] = task
        
        logger.info(f"[CONTINUOUS_SYNC] 連続同期開始: {session_id}, interval={interval}s")
    
    async def _continuous_sync_loop(self, session_id: str):
        """
        連続同期ループ（ラズパイのメイン処理を再現）
        
        ラズパイデバッグコードのwhile Trueループに対応
        """
        try:
            sync_state = self.active_syncs[session_id]
            interval = sync_state['interval']
            start_time = sync_state['start_time']
            total_duration = sync_state['total_duration']
            
            logger.info(f"[CONTINUOUS_SYNC] ループ開始: {session_id}, duration={total_duration}s")
            
            while session_id in self.active_syncs:
                # 現在時刻計算
                elapsed = time.time() - start_time
                current_time = elapsed
                
                # ループ再生チェック（ラズパイと同様）
                if current_time > total_duration and total_duration > 0:
                    sync_state['loop_count'] += 1
                    logger.info(f"[CONTINUOUS_SYNC] ループ再生リセット: {session_id}, loop#{sync_state['loop_count']}")
                    
                    # 時間をリセット（ラズパイパターン）
                    start_time = time.time()
                    sync_state['start_time'] = start_time
                    current_time = 0.0
                
                # 状態更新
                sync_state['current_time'] = current_time
                
                # 同期データサービスに時刻更新
                time_state = sync_data_service.update_current_time(
                    session_id, current_time, sync_state['is_playing']
                )
                
                # 時刻周辺のイベント検索
                events = sync_data_service.find_events_at_time(session_id, current_time)
                
                # 送信データ作成（ラズパイのtime_update_data形式）
                time_update_data = {
                    'type': 'currentTime',
                    'session_id': session_id,
                    'currentTime': round(current_time, 2),
                    'total_duration': total_duration,
                    'is_playing': sync_state['is_playing'],
                    'loop_count': sync_state['loop_count'],
                    'events': events,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.debug(f"[CONTINUOUS_SYNC] 時刻送信: {current_time:.2f}s, events={len(events)}")
                
                # コールバック実行
                callback = self.sync_callbacks.get(session_id)
                if callback:
                    try:
                        await callback(time_update_data)
                    except Exception as e:
                        logger.error(f"[CONTINUOUS_SYNC] コールバックエラー: {e}")
                
                # インターバル待機
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.info(f"[CONTINUOUS_SYNC] 同期ループキャンセル: {session_id}")
            
        except Exception as e:
            logger.error(f"[CONTINUOUS_SYNC] ループエラー: {e}")
            
        finally:
            # クリーンアップ
            await self._cleanup_sync(session_id)
    
    def pause_sync(self, session_id: str):
        """同期一時停止"""
        if session_id in self.active_syncs:
            self.active_syncs[session_id]['is_playing'] = False
            logger.info(f"[CONTINUOUS_SYNC] 一時停止: {session_id}")
    
    def resume_sync(self, session_id: str):
        """同期再開"""
        if session_id in self.active_syncs:
            # 時間をリセットして再開
            self.active_syncs[session_id].update({
                'is_playing': True,
                'start_time': time.time()
            })
            logger.info(f"[CONTINUOUS_SYNC] 再開: {session_id}")
    
    def seek_sync(self, session_id: str, seek_time: float):
        """
        シーク処理
        
        Args:
            session_id: セッションID
            seek_time: シーク先時刻（秒）
        """
        if session_id in self.active_syncs:
            # シーク時刻に合わせて開始時刻を調整
            current_real_time = time.time()
            self.active_syncs[session_id].update({
                'start_time': current_real_time - seek_time,
                'current_time': seek_time
            })
            
            # 同期データサービスも更新
            sync_data_service.update_current_time(session_id, seek_time, True)
            
            logger.info(f"[CONTINUOUS_SYNC] シーク: {session_id} -> {seek_time}s")
    
    async def stop_sync(self, session_id: str):
        """同期停止"""
        if session_id in self.sync_tasks:
            task = self.sync_tasks[session_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            logger.info(f"[CONTINUOUS_SYNC] 同期停止: {session_id}")
    
    async def _cleanup_sync(self, session_id: str):
        """同期状態クリーンアップ"""
        # タスク削除
        if session_id in self.sync_tasks:
            del self.sync_tasks[session_id]
        
        # 状態削除
        if session_id in self.active_syncs:
            del self.active_syncs[session_id]
        
        # コールバック削除
        if session_id in self.sync_callbacks:
            del self.sync_callbacks[session_id]
        
        logger.info(f"[CONTINUOUS_SYNC] クリーンアップ完了: {session_id}")
    
    def get_sync_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """同期状態取得"""
        if session_id not in self.active_syncs:
            return None
        
        sync_state = self.active_syncs[session_id]
        return {
            'session_id': session_id,
            'is_active': session_id in self.sync_tasks,
            'is_playing': sync_state.get('is_playing', False),
            'current_time': sync_state.get('current_time', 0.0),
            'total_duration': sync_state.get('total_duration', 0.0),
            'loop_count': sync_state.get('loop_count', 0),
            'interval': sync_state.get('interval', 0.5)
        }
    
    def get_all_active_syncs(self) -> Dict[str, Dict[str, Any]]:
        """全アクティブ同期状態取得"""
        return {
            session_id: self.get_sync_status(session_id)
            for session_id in self.active_syncs
        }

# サービスインスタンス
continuous_sync_service = ContinuousSyncService()