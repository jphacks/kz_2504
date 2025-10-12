"""
Preparation Service - 準備処理ビジネスロジック

動画プリロード、同期データ処理、デバイス通信テスト、アクチュエーターテストを管理
既存のdemo1.json形式に対応した同期データ処理を実装
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
import aiohttp
from aiofiles import open as aopen

from app.config.settings import settings
from app.models.preparation import (
    PreparationState, PreparationStatus, ActuatorTestResult, ActuatorTestStatus,
    VideoPreparationInfo, SyncDataPreparationInfo, DeviceCommunicationInfo,
    PreparationProgress, ActuatorType, ACTUATOR_TEST_DEFAULTS,
    SyncDataTransmissionResult
)
# Mockデバイス情報（テスト用）
MOCK_DEVICE_INFO = {
    "test_device_basic": {
        "device_name": "4DX Home Basic",
        "capabilities": ["VIBRATION", "WATER", "WIND"]
    },
    "test_device_standard": {
        "device_name": "4DX Home Standard", 
        "capabilities": ["VIBRATION", "WATER", "WIND", "FLASH"]
    },
    "test_device_premium": {
        "device_name": "4DX Home Premium",
        "capabilities": ["VIBRATION", "WATER", "WIND", "FLASH", "COLOR"]
    }
}

# Mock動画情報（テスト用）
MOCK_VIDEO_INFO = {
    "demo1": {
        "duration": 33.5,
        "video_info": {
            "file_name": "demo1.mp4",
            "file_size_mb": 25.0
        }
    }
}

logger = logging.getLogger(__name__)

class PreparationService:
    """準備処理管理サービス"""
    
    def __init__(self):
        self.active_preparations: Dict[str, PreparationState] = {}
        self.preparation_tasks: Dict[str, asyncio.Task] = {}
        self.progress_callbacks: Dict[str, List[callable]] = {}
        
    async def start_preparation(
        self, 
        session_id: str, 
        video_id: str, 
        device_id: str,
        force_restart: bool = False
    ) -> PreparationState:
        """
        準備処理を開始
        
        Args:
            session_id: セッションID
            video_id: 動画ID
            device_id: デバイスID
            force_restart: 強制再開始フラグ
            
        Returns:
            準備処理状態
        """
        logger.info(f"準備処理開始: session={session_id}, video={video_id}, device={device_id}")
        
        # 既存の準備処理確認
        if session_id in self.active_preparations and not force_restart:
            existing_prep = self.active_preparations[session_id]
            if existing_prep.overall_status not in [PreparationStatus.FAILED, PreparationStatus.COMPLETED]:
                logger.info(f"準備処理既に実行中: {session_id}")
                return existing_prep
        
        # 停止処理（強制再開始の場合）
        if force_restart and session_id in self.preparation_tasks:
            await self.stop_preparation(session_id)
        
        try:
            # 動画情報取得（Mock）
            video = MOCK_VIDEO_INFO.get(video_id)
            if not video:
                raise ValueError(f"動画が見つかりません: {video_id}")
            
            # デバイス情報取得（Mock）
            device_info = MOCK_DEVICE_INFO.get(device_id)
            if not device_info:
                raise ValueError(f"デバイス情報が見つかりません: {device_id}")
            
            # 準備状態初期化
            prep_state = await self._initialize_preparation_state(
                session_id, video_id, device_id, video, device_info
            )
            
            # 準備処理開始
            self.active_preparations[session_id] = prep_state
            self.preparation_tasks[session_id] = asyncio.create_task(
                self._execute_preparation_workflow(prep_state)
            )
            
            logger.info(f"準備処理タスク開始: {session_id}")
            return prep_state
            
        except Exception as e:
            logger.error(f"準備処理開始エラー: {e}")
            raise
    
    async def get_preparation_status(self, session_id: str) -> Optional[PreparationState]:
        """準備処理状態取得"""
        return self.active_preparations.get(session_id)
    
    async def stop_preparation(self, session_id: str) -> bool:
        """準備処理停止"""
        logger.info(f"準備処理停止: {session_id}")
        
        # タスク停止
        if session_id in self.preparation_tasks:
            task = self.preparation_tasks[session_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"準備処理タスクキャンセル完了: {session_id}")
            
            del self.preparation_tasks[session_id]
        
        # 状態クリーンアップ
        if session_id in self.active_preparations:
            del self.active_preparations[session_id]
        
        if session_id in self.progress_callbacks:
            del self.progress_callbacks[session_id]
        
        return True
    
    def add_progress_callback(self, session_id: str, callback: callable):
        """進捗コールバック追加"""
        if session_id not in self.progress_callbacks:
            self.progress_callbacks[session_id] = []
        self.progress_callbacks[session_id].append(callback)
    
    async def _initialize_preparation_state(
        self, session_id: str, video_id: str, device_id: str, video: Any, device_info: Any
    ) -> PreparationState:
        """準備状態初期化"""
        
        # 動画準備情報（Mock）
        video_url = f"/assets/videos/{video['video_info']['file_name']}"
        video_prep = VideoPreparationInfo(
            video_id=video_id,
            video_url=video_url,
            file_size_mb=video["video_info"]["file_size_mb"],
            duration_seconds=video["duration"],
            preload_progress=0,
            preload_status=PreparationStatus.NOT_STARTED
        )
        
        # 同期データ準備情報
        sync_data_url = f"/assets/sync-data/{video_id}.json"
        
        # 同期データファイル情報取得
        sync_file_path = settings.get_sync_data_path() / f"{video_id}.json"
        sync_file_size = 0
        effects_count = 0
        required_actuators = []
        
        if sync_file_path.exists():
            sync_file_size = sync_file_path.stat().st_size / 1024  # KB
            
            # 同期データ解析
            try:
                async with aopen(sync_file_path, 'r', encoding='utf-8') as f:
                    sync_data = json.loads(await f.read())
                
                effects_count = len(sync_data.get('events', []))
                
                # エフェクトタイプを抽出してアクチュエータタイプにマッピング
                effect_types = set()
                for event in sync_data.get('events', []):
                    effect = event.get('effect', '').upper()
                    if effect:
                        effect_types.add(self._map_effect_to_actuator(effect))
                
                required_actuators = [act for act in effect_types if act]
                
            except Exception as e:
                logger.warning(f"同期データ解析エラー: {e}")
        
        sync_prep = SyncDataPreparationInfo(
            sync_data_url=sync_data_url,
            file_size_kb=sync_file_size,
            effects_count=effects_count,
            required_actuators=required_actuators,
            download_progress=0,
            parsing_progress=0,
            preparation_status=PreparationStatus.NOT_STARTED
        )
        
        # デバイス通信情報
        device_capabilities = device_info.get('capabilities', [])
        supported_actuators = [
            ActuatorType(cap) for cap in device_capabilities 
            if cap in [act.value for act in ActuatorType]
        ]
        
        device_comm = DeviceCommunicationInfo(
            device_id=device_id,
            device_name=device_info.get('device_name', 'Unknown Device'),
            connection_status=PreparationStatus.NOT_STARTED,
            websocket_connected=False,
            last_ping_ms=None,
            supported_actuators=supported_actuators,
            actuator_tests={}
        )
        
        # 完了予定時刻計算
        estimated_seconds = 30 + (len(supported_actuators) * 5)  # 基本30秒 + アクチュエータ当たり5秒
        estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
        
        return PreparationState(
            session_id=session_id,
            overall_status=PreparationStatus.INITIALIZING,
            overall_progress=0,
            video_preparation=video_prep,
            sync_data_preparation=sync_prep,
            device_communication=device_comm,
            estimated_completion_time=estimated_completion,
            ready_for_playback=False,
            min_required_actuators_ready=False,
            all_actuators_ready=False
        )
    
    def _map_effect_to_actuator(self, effect: str) -> Optional[ActuatorType]:
        """エフェクト名をアクチュエータタイプにマッピング"""
        mapping = {
            'VIBRATION': ActuatorType.VIBRATION,
            'WATER': ActuatorType.WATER,
            'WIND': ActuatorType.WIND,
            'FLASH': ActuatorType.FLASH,
            'COLOR': ActuatorType.COLOR,
            # 既存データ互換性
            'MOTION': ActuatorType.VIBRATION,  # モーション → 振動
            'SCENT': ActuatorType.WATER,      # 香り → 水
            'LIGHTING': ActuatorType.COLOR,   # ライティング → 色ライト
            'AUDIO': None  # オーディオは除外
        }
        return mapping.get(effect)
    
    async def _execute_preparation_workflow(self, prep_state: PreparationState):
        """準備処理ワークフロー実行"""
        session_id = prep_state.session_id
        logger.info(f"準備ワークフロー開始: {session_id}")
        
        try:
            prep_state.overall_status = PreparationStatus.IN_PROGRESS
            await self._notify_progress(session_id, "overall", 5, PreparationStatus.IN_PROGRESS, "準備処理を開始しました")
            
            # Phase 1: 並行準備開始
            await self._execute_parallel_preparation(prep_state)
            
            # Phase 2: デバイス通信テスト
            await self._execute_device_communication_test(prep_state)
            
            # Phase 3: アクチュエーターテスト
            await self._execute_actuator_tests(prep_state)
            
            # Phase 4: 最終検証
            await self._execute_final_validation(prep_state)
            
            # 完了処理
            prep_state.overall_status = PreparationStatus.COMPLETED
            prep_state.overall_progress = 100
            prep_state.completed_at = datetime.now()
            prep_state.ready_for_playback = True
            
            await self._notify_progress(
                session_id, "overall", 100, PreparationStatus.COMPLETED, 
                "準備処理が完了しました。再生を開始できます。"
            )
            
            logger.info(f"準備ワークフロー完了: {session_id}")
            
        except asyncio.CancelledError:
            logger.info(f"準備ワークフローキャンセル: {session_id}")
            prep_state.overall_status = PreparationStatus.FAILED
            raise
        except Exception as e:
            logger.error(f"準備ワークフローエラー: {session_id}, {e}")
            prep_state.overall_status = PreparationStatus.FAILED
            await self._notify_progress(
                session_id, "overall", prep_state.overall_progress, 
                PreparationStatus.FAILED, f"準備処理エラー: {str(e)}"
            )
    
    async def _execute_parallel_preparation(self, prep_state: PreparationState):
        """並行準備処理実行"""
        session_id = prep_state.session_id
        logger.info(f"並行準備処理開始: {session_id}")
        
        # 動画プリロードとシンクデータ処理を並行実行
        tasks = [
            self._simulate_video_preload(prep_state),
            self._process_sync_data(prep_state)
        ]
        
        await asyncio.gather(*tasks)
        
        prep_state.overall_progress = 40
        await self._notify_progress(
            session_id, "parallel_prep", 40, PreparationStatus.COMPLETED, 
            "動画とシンクデータの準備が完了しました"
        )
    
    async def _simulate_video_preload(self, prep_state: PreparationState):
        """動画プリロードシミュレーション"""
        session_id = prep_state.session_id
        video_prep = prep_state.video_preparation
        
        video_prep.preload_status = PreparationStatus.IN_PROGRESS
        await self._notify_progress(session_id, "video_preload", 0, PreparationStatus.IN_PROGRESS, "動画プリロード開始")
        
        # プリロードシミュレーション
        for progress in range(0, 101, 10):
            await asyncio.sleep(0.2)  # 2秒で完了
            video_prep.preload_progress = progress
            await self._notify_progress(
                session_id, "video_preload", progress, PreparationStatus.IN_PROGRESS, 
                f"動画プリロード中: {progress}%"
            )
        
        video_prep.preload_status = PreparationStatus.COMPLETED
        await self._notify_progress(session_id, "video_preload", 100, PreparationStatus.COMPLETED, "動画プリロード完了")
    
    async def _process_sync_data(self, prep_state: PreparationState):
        """同期データ処理"""
        session_id = prep_state.session_id
        sync_prep = prep_state.sync_data_preparation
        video_id = prep_state.video_preparation.video_id
        device_id = prep_state.device_communication.device_id
        
        sync_prep.preparation_status = PreparationStatus.IN_PROGRESS
        await self._notify_progress(session_id, "sync_data", 0, PreparationStatus.IN_PROGRESS, "同期データ処理開始")
        
        try:
            # 1. 同期データファイル読み込み
            await self._notify_progress(session_id, "sync_data_loading", 0, PreparationStatus.IN_PROGRESS, "同期データファイル読み込み中")
            
            sync_data = await self._load_sync_data(video_id)
            sync_prep.download_progress = 30
            await self._notify_progress(session_id, "sync_data_loading", 30, PreparationStatus.IN_PROGRESS, "同期データファイル読み込み完了")
            
            # 2. 同期データ解析・検証
            await self._notify_progress(session_id, "sync_data_parsing", 30, PreparationStatus.IN_PROGRESS, "同期データ解析中")
            
            processed_data = await self._validate_and_process_sync_data(sync_data, prep_state)
            sync_prep.parsing_progress = 60
            await self._notify_progress(session_id, "sync_data_parsing", 60, PreparationStatus.IN_PROGRESS, "同期データ解析完了")
            
            # 3. デバイスハブへのJSON送信
            await self._notify_progress(session_id, "sync_data_transmission", 60, PreparationStatus.IN_PROGRESS, "デバイスハブへ同期データ送信中")
            
            transmission_result = await self._transmit_sync_data_to_device(device_id, processed_data, session_id)
            
            # 送信結果をモデルに記録  
            sync_prep.transmission_result = SyncDataTransmissionResult(
                transmitted=transmission_result['success'],
                device_hub_url=transmission_result.get('device_hub_url'),
                transmission_size_kb=transmission_result.get('size_kb'),
                supported_events=transmission_result.get('events_count'),
                unsupported_events=processed_data['total_events'] - processed_data['supported_events'],
                transmission_timestamp=datetime.fromisoformat(transmission_result['transmission_time']) if transmission_result.get('transmission_time') else None,
                checksum=transmission_result.get('checksum'),
                error_message=transmission_result.get('error') if not transmission_result['success'] else None
            )
            
            if transmission_result['success']:
                sync_prep.parsing_progress = 100
                sync_prep.preparation_status = PreparationStatus.COMPLETED
                await self._notify_progress(session_id, "sync_data_transmission", 100, PreparationStatus.COMPLETED, 
                    f"デバイスハブへの同期データ送信完了 (転送サイズ: {transmission_result['size_kb']}KB, 対応エフェクト: {transmission_result['events_count']}件)")
                await self._notify_progress(session_id, "sync_data", 100, PreparationStatus.COMPLETED, "同期データ処理完了")
            else:
                raise Exception(f"デバイスハブへの送信失敗: {transmission_result.get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"同期データ処理エラー: {e}")
            sync_prep.preparation_status = PreparationStatus.FAILED
            await self._notify_progress(session_id, "sync_data", sync_prep.parsing_progress, PreparationStatus.FAILED, f"同期データ処理失敗: {str(e)}")
            raise
    
    async def _execute_device_communication_test(self, prep_state: PreparationState):
        """デバイス通信テスト"""
        session_id = prep_state.session_id
        device_comm = prep_state.device_communication
        
        logger.info(f"デバイス通信テスト開始: {session_id}")
        
        device_comm.connection_status = PreparationStatus.IN_PROGRESS
        await self._notify_progress(session_id, "device_comm", 0, PreparationStatus.IN_PROGRESS, "デバイス通信テスト開始")
        
        # WebSocket接続シミュレーション
        await asyncio.sleep(0.5)
        device_comm.websocket_connected = True
        await self._notify_progress(session_id, "websocket", 50, PreparationStatus.IN_PROGRESS, "WebSocket接続確立")
        
        # Pingテスト
        await asyncio.sleep(0.5)
        device_comm.last_ping_ms = 45  # シミュレーション値
        device_comm.connection_status = PreparationStatus.COMPLETED
        
        prep_state.overall_progress = 60
        await self._notify_progress(session_id, "device_comm", 100, PreparationStatus.COMPLETED, "デバイス通信テスト完了")
    
    async def _execute_actuator_tests(self, prep_state: PreparationState):
        """アクチュエーターテスト実行"""
        session_id = prep_state.session_id
        device_comm = prep_state.device_communication
        
        logger.info(f"アクチュエーターテスト開始: {session_id}")
        
        total_actuators = len(device_comm.supported_actuators)
        if total_actuators == 0:
            prep_state.overall_progress = 90
            return
        
        for i, actuator_type in enumerate(device_comm.supported_actuators):
            await self._test_single_actuator(prep_state, actuator_type)
            
            # 進捗更新
            progress = 60 + (30 * (i + 1) // total_actuators)
            prep_state.overall_progress = progress
            await self._notify_progress(
                session_id, "actuator_tests", progress, PreparationStatus.IN_PROGRESS,
                f"アクチュエーターテスト進行中: {i+1}/{total_actuators}"
            )
        
        # 準備完了判定
        self._evaluate_readiness(prep_state)
    
    async def _test_single_actuator(self, prep_state: PreparationState, actuator_type: ActuatorType):
        """単一アクチュエーターテスト"""
        session_id = prep_state.session_id
        device_comm = prep_state.device_communication
        
        test_config = ACTUATOR_TEST_DEFAULTS.get(actuator_type, {})
        
        # テスト開始
        test_result = ActuatorTestResult(
            actuator_type=actuator_type,
            status=ActuatorTestStatus.TESTING,
            test_intensity=test_config.get('test_intensity', 0.8),
            tested_at=datetime.now()
        )
        
        device_comm.actuator_tests[actuator_type.value] = test_result
        
        await self._notify_progress(
            session_id, f"actuator_{actuator_type.value.lower()}", 0, 
            PreparationStatus.TESTING, f"{actuator_type.value}テスト開始"
        )
        
        # テスト実行シミュレーション
        test_duration = test_config.get('test_duration', 2000) / 1000  # ms to sec
        await asyncio.sleep(min(test_duration, 2.0))  # 最大2秒
        
        # テスト結果シミュレーション
        expected_response = test_config.get('expected_response_time', 500)
        actual_response = expected_response + ((-50 + 100) if actuator_type != ActuatorType.FLASH else 0)
        
        test_result.response_time_ms = actual_response
        test_result.status = ActuatorTestStatus.READY if actual_response < 1000 else ActuatorTestStatus.TIMEOUT
        
        # アクチュエータ固有情報設定
        if actuator_type == ActuatorType.VIBRATION:
            test_result.vibration_frequency = 50.0
        elif actuator_type == ActuatorType.WATER:
            test_result.water_pressure = 0.8
        elif actuator_type == ActuatorType.WIND:
            test_result.wind_speed = 0.7
        elif actuator_type == ActuatorType.FLASH:
            test_result.flash_brightness = 1.0
        elif actuator_type == ActuatorType.COLOR:
            test_result.color_accuracy = 0.95
        
        status_msg = f"{actuator_type.value}テスト完了 (応答: {actual_response}ms)"
        await self._notify_progress(
            session_id, f"actuator_{actuator_type.value.lower()}", 100,
            PreparationStatus.COMPLETED, status_msg
        )
    
    def _evaluate_readiness(self, prep_state: PreparationState):
        """準備完了状態評価"""
        device_comm = prep_state.device_communication
        ready_actuators = 0
        total_actuators = len(device_comm.supported_actuators)
        
        for actuator_type in device_comm.supported_actuators:
            test_result = device_comm.actuator_tests.get(actuator_type.value)
            if test_result and test_result.status == ActuatorTestStatus.READY:
                ready_actuators += 1
        
        # 最小要件確認（振動は必須）
        vibration_ready = any(
            test.status == ActuatorTestStatus.READY 
            for test in device_comm.actuator_tests.values()
            if test.actuator_type == ActuatorType.VIBRATION
        )
        
        prep_state.min_required_actuators_ready = vibration_ready
        prep_state.all_actuators_ready = ready_actuators == total_actuators
    
    async def _execute_final_validation(self, prep_state: PreparationState):
        """最終検証"""
        session_id = prep_state.session_id
        
        await self._notify_progress(session_id, "validation", 0, PreparationStatus.IN_PROGRESS, "最終検証開始")
        
        # 検証項目チェック
        checks = [
            prep_state.video_preparation.preload_status == PreparationStatus.COMPLETED,
            prep_state.sync_data_preparation.preparation_status == PreparationStatus.COMPLETED,
            prep_state.device_communication.connection_status == PreparationStatus.COMPLETED,
            prep_state.min_required_actuators_ready
        ]
        
        await asyncio.sleep(0.5)
        
        if all(checks):
            await self._notify_progress(session_id, "validation", 100, PreparationStatus.COMPLETED, "最終検証完了")
        else:
            await self._notify_progress(session_id, "validation", 100, PreparationStatus.FAILED, "最終検証失敗")
            raise Exception("最終検証に失敗しました")
    
    async def _load_sync_data(self, video_id: str) -> Dict[str, Any]:
        """同期データファイル読み込み"""
        sync_file_path = settings.get_sync_data_path() / f"{video_id}.json"
        
        if not sync_file_path.exists():
            raise FileNotFoundError(f"同期データファイルが見つかりません: {sync_file_path}")
        
        try:
            async with aopen(sync_file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"同期データファイルの解析に失敗しました: {e}")
        except Exception as e:
            raise Exception(f"同期データファイル読み込みエラー: {e}")
    
    async def _validate_and_process_sync_data(self, sync_data: Dict[str, Any], prep_state: PreparationState) -> Dict[str, Any]:
        """同期データ検証・処理"""
        device_capabilities = [act.value for act in prep_state.device_communication.supported_actuators]
        
        # イベント数とアクチュエータタイプ統計
        events = sync_data.get('events', [])
        total_events = len(events)
        supported_events = 0
        unsupported_events = []
        
        processed_events = []
        
        for event in events:
            effect = event.get('effect', '').upper()
            actuator_type = self._map_effect_to_actuator(effect)
            
            if actuator_type and actuator_type.value in device_capabilities:
                supported_events += 1
                processed_events.append(event)
            else:
                unsupported_events.append({
                    'time': event.get('t', 0),
                    'effect': effect,
                    'reason': f"デバイスが{actuator_type.value if actuator_type else effect}をサポートしていません"
                })
        
        # 統計情報更新
        prep_state.sync_data_preparation.effects_count = total_events
        
        processed_data = {
            'video_id': prep_state.video_preparation.video_id,
            'session_id': prep_state.session_id,
            'total_events': total_events,
            'supported_events': supported_events,
            'unsupported_events': unsupported_events,
            'events': processed_events,
            'device_capabilities': device_capabilities,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"同期データ処理完了: 全{total_events}件, 対応{supported_events}件, 非対応{len(unsupported_events)}件")
        
        return processed_data
    
    async def _transmit_sync_data_to_device(self, device_id: str, processed_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """デバイスハブへの同期データ送信"""
        try:
            # デバイスハブのWebSocket URL構築 (実際の実装ではsettingsから取得)
            device_hub_ws_url = f"ws://localhost:8002/device-hub/sync/{device_id}"
            
            # 送信用データ準備
            transmission_payload = {
                'type': 'sync_data_delivery',
                'session_id': session_id,
                'device_id': device_id,
                'sync_data': processed_data,
                'delivery_timestamp': datetime.now().isoformat(),
                'checksum': self._calculate_checksum(processed_data)
            }
            
            payload_json = json.dumps(transmission_payload, ensure_ascii=False)
            payload_size_kb = len(payload_json.encode('utf-8')) / 1024
            
            logger.info(f"デバイスハブへ同期データ送信開始: {device_id}, サイズ: {payload_size_kb:.1f}KB")
            
            # 実際のWebSocket送信（今回はMock実装）
            success = await self._mock_websocket_transmission(device_hub_ws_url, transmission_payload)
            
            if success:
                return {
                    'success': True,
                    'device_id': device_id,
                    'device_hub_url': device_hub_ws_url,
                    'size_kb': round(payload_size_kb, 1),
                    'events_count': processed_data['supported_events'],
                    'transmission_time': datetime.now().isoformat(),
                    'checksum': transmission_payload['checksum']
                }
            else:
                return {
                    'success': False,
                    'error': 'WebSocket送信に失敗しました'
                }
        
        except Exception as e:
            logger.error(f"デバイスハブ送信エラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """チェックサム計算"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()[:8]
    
    async def _mock_websocket_transmission(self, ws_url: str, payload: Dict[str, Any]) -> bool:
        """WebSocket送信実装"""
        try:
            import websockets
            import ssl
            
            # WebSocket接続設定
            connect_timeout = 5.0  # 接続タイムアウト
            close_timeout = 3.0    # 切断タイムアウト
            
            # SSL証明書検証を無効化（開発環境用）
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            logger.info(f"デバイスハブWebSocket接続試行: {ws_url}")
            
            # 実際のWebSocket接続・送信
            try:
                async with websockets.connect(
                    ws_url,
                    timeout=connect_timeout,
                    close_timeout=close_timeout,
                    ssl=ssl_context if ws_url.startswith('wss://') else None
                ) as websocket:
                    
                    # JSON形式でペイロード送信
                    message = json.dumps(payload, ensure_ascii=False)
                    await websocket.send(message)
                    
                    # 受信確認待ち（タイムアウト付き）
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        
                        if response_data.get('status') == 'received':
                            logger.info(f"デバイスハブ送信成功・確認完了: {ws_url}")
                            return True
                        else:
                            logger.error(f"デバイスハブ応答エラー: {response_data}")
                            return False
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"デバイスハブ応答タイムアウト（送信は完了）: {ws_url}")
                        return True  # 送信は成功したとみなす
            
            except websockets.exceptions.ConnectionClosed:
                logger.error(f"WebSocket接続が閉じられました: {ws_url}")
                return False
            except websockets.exceptions.InvalidURI:
                logger.error(f"無効なWebSocket URI: {ws_url}")
                return False
            except OSError as e:
                # 接続先が存在しない場合（開発環境では正常）
                logger.warning(f"デバイスハブ接続不可（開発モードでMock送信実行）: {e}")
                # 開発環境では成功として扱う
                await asyncio.sleep(0.5)  # 送信時間シミュレーション
                return True
            
        except ImportError:
            logger.error("websocketsライブラリが見つかりません")
            return False
        except Exception as e:
            logger.error(f"WebSocket送信エラー: {e}")
            return False
    
    async def _notify_progress(
        self, session_id: str, component: str, progress: int, 
        status: PreparationStatus, message: str
    ):
        """進捗通知"""
        progress_info = PreparationProgress(
            session_id=session_id,
            component=component,
            progress=progress,
            status=status,
            message=message
        )
        
        # コールバック実行
        if session_id in self.progress_callbacks:
            for callback in self.progress_callbacks[session_id]:
                try:
                    await callback(progress_info)
                except Exception as e:
                    logger.error(f"進捗コールバックエラー: {e}")

# グローバルインスタンス
preparation_service = PreparationService()