"""
Preparation API - 準備処理REST APIエンドポイント

待機画面で使用する準備処理の制御とステータス監視API
"""

from datetime import datetime
from typing import Dict, Optional, List
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.preparation_service import preparation_service
from app.models.preparation import (
    PreparationState, PreparationStatus, PreparationProgress,
    ActuatorType, ActuatorTestResult, ActuatorTestStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preparation", tags=["preparation"])

# WebSocket接続管理
websocket_connections: Dict[str, WebSocket] = {}

class PreparationStartRequest(BaseModel):
    """準備開始リクエスト"""
    video_id: str
    device_id: str
    force_restart: bool = False

class PreparationResponse(BaseModel):
    """準備処理レスポンス"""
    success: bool
    message: str
    data: Optional[Dict] = None

class PreparationStatusSummary(BaseModel):
    """準備状態サマリー"""
    session_id: str
    overall_status: PreparationStatus
    overall_progress: int
    ready_for_playback: bool
    estimated_completion_time: Optional[datetime]
    min_required_actuators_ready: bool
    all_actuators_ready: bool
    
    # 詳細情報
    video_preload_progress: int
    video_preload_status: PreparationStatus
    sync_data_status: PreparationStatus
    device_connection_status: PreparationStatus
    websocket_connected: bool
    supported_actuators: List[str]
    ready_actuators: List[str]
    failed_actuators: List[str]

@router.post("/start/{session_id}", response_model=PreparationResponse)
async def start_preparation(
    session_id: str,
    request: PreparationStartRequest,
    background_tasks: BackgroundTasks
):
    """
    準備処理開始
    
    Args:
        session_id: セッションID
        request: 準備開始リクエスト
        
    Returns:
        準備処理開始レスポンス
    """
    try:
        logger.info(f"準備処理開始API呼び出し: session={session_id}, video={request.video_id}")
        
        # 準備処理開始
        prep_state = await preparation_service.start_preparation(
            session_id=session_id,
            video_id=request.video_id,
            device_id=request.device_id,
            force_restart=request.force_restart
        )
        
        # WebSocket進捗通知設定
        if session_id in websocket_connections:
            preparation_service.add_progress_callback(
                session_id, 
                lambda progress: notify_websocket_progress(session_id, progress)
            )
        
        return PreparationResponse(
            success=True,
            message="準備処理を開始しました",
            data={
                "session_id": session_id,
                "status": prep_state.overall_status.value,
                "progress": prep_state.overall_progress,
                "estimated_completion": prep_state.estimated_completion_time.isoformat() if prep_state.estimated_completion_time else None
            }
        )
        
    except ValueError as e:
        logger.error(f"準備処理開始バリデーションエラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"準備処理開始エラー: {e}")
        raise HTTPException(status_code=500, detail="準備処理の開始に失敗しました")

@router.get("/status/{session_id}", response_model=PreparationStatusSummary)
async def get_preparation_status(session_id: str):
    """
    準備処理状態取得
    
    Args:
        session_id: セッションID
        
    Returns:
        準備処理状態詳細
    """
    try:
        prep_state = await preparation_service.get_preparation_status(session_id)
        
        if not prep_state:
            raise HTTPException(status_code=404, detail="準備処理が見つかりません")
        
        # アクチュエータ状態分析
        supported_actuators = [act.value for act in prep_state.device_communication.supported_actuators]
        ready_actuators = []
        failed_actuators = []
        
        for actuator_name, test_result in prep_state.device_communication.actuator_tests.items():
            if test_result.status == ActuatorTestStatus.READY:
                ready_actuators.append(actuator_name)
            elif test_result.status in [ActuatorTestStatus.FAILED, ActuatorTestStatus.TIMEOUT]:
                failed_actuators.append(actuator_name)
        
        return PreparationStatusSummary(
            session_id=prep_state.session_id,
            overall_status=prep_state.overall_status,
            overall_progress=prep_state.overall_progress,
            ready_for_playback=prep_state.ready_for_playback,
            estimated_completion_time=prep_state.estimated_completion_time,
            min_required_actuators_ready=prep_state.min_required_actuators_ready,
            all_actuators_ready=prep_state.all_actuators_ready,
            video_preload_progress=prep_state.video_preparation.preload_progress,
            video_preload_status=prep_state.video_preparation.preload_status,
            sync_data_status=prep_state.sync_data_preparation.preparation_status,
            device_connection_status=prep_state.device_communication.connection_status,
            websocket_connected=prep_state.device_communication.websocket_connected,
            supported_actuators=supported_actuators,
            ready_actuators=ready_actuators,
            failed_actuators=failed_actuators
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"準備状態取得エラー: {e}")
        raise HTTPException(status_code=500, detail="準備状態の取得に失敗しました")

@router.delete("/stop/{session_id}", response_model=PreparationResponse)
async def stop_preparation(session_id: str):
    """
    準備処理停止
    
    Args:
        session_id: セッションID
        
    Returns:
        停止結果
    """
    try:
        logger.info(f"準備処理停止API呼び出し: {session_id}")
        
        success = await preparation_service.stop_preparation(session_id)
        
        # WebSocket接続クリーンアップ
        if session_id in websocket_connections:
            try:
                await websocket_connections[session_id].close()
            except:
                pass
            del websocket_connections[session_id]
        
        return PreparationResponse(
            success=success,
            message="準備処理を停止しました" if success else "準備処理の停止に失敗しました"
        )
        
    except Exception as e:
        logger.error(f"準備処理停止エラー: {e}")
        raise HTTPException(status_code=500, detail="準備処理の停止に失敗しました")

@router.get("/actuators/{session_id}")
async def get_actuator_test_results(session_id: str):
    """
    アクチュエータテスト結果取得
    
    Args:
        session_id: セッションID
        
    Returns:
        アクチュエータテスト結果詳細
    """
    try:
        prep_state = await preparation_service.get_preparation_status(session_id)
        
        if not prep_state:
            raise HTTPException(status_code=404, detail="準備処理が見つかりません")
        
        test_results = []
        for actuator_name, test_result in prep_state.device_communication.actuator_tests.items():
            result_data = {
                "actuator_type": test_result.actuator_type.value,
                "status": test_result.status.value,
                "test_intensity": test_result.test_intensity,
                "response_time_ms": test_result.response_time_ms,
                "tested_at": test_result.tested_at.isoformat() if test_result.tested_at else None,
                "error_message": test_result.error_message
            }
            
            # アクチュエータ固有データ追加
            if test_result.vibration_frequency is not None:
                result_data["vibration_frequency"] = test_result.vibration_frequency
            if test_result.water_pressure is not None:
                result_data["water_pressure"] = test_result.water_pressure
            if test_result.wind_speed is not None:
                result_data["wind_speed"] = test_result.wind_speed
            if test_result.flash_brightness is not None:
                result_data["flash_brightness"] = test_result.flash_brightness
            if test_result.color_accuracy is not None:
                result_data["color_accuracy"] = test_result.color_accuracy
            
            test_results.append(result_data)
        
        return {
            "session_id": session_id,
            "total_actuators": len(prep_state.device_communication.supported_actuators),
            "ready_actuators": len([r for r in test_results if r["status"] == "READY"]),
            "test_results": test_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アクチュエータテスト結果取得エラー: {e}")
        raise HTTPException(status_code=500, detail="アクチュエータテスト結果の取得に失敗しました")

@router.get("/progress/{session_id}")
async def get_preparation_progress(session_id: str):
    """
    準備処理進捗詳細取得
    
    Args:
        session_id: セッションID
        
    Returns:
        詳細進捗情報
    """
    try:
        prep_state = await preparation_service.get_preparation_status(session_id)
        
        if not prep_state:
            raise HTTPException(status_code=404, detail="準備処理が見つかりません")
        
        return {
            "session_id": session_id,
            "overall": {
                "progress": prep_state.overall_progress,
                "status": prep_state.overall_status.value,
                "estimated_completion": prep_state.estimated_completion_time.isoformat() if prep_state.estimated_completion_time else None
            },
            "video_preparation": {
                "preload_progress": prep_state.video_preparation.preload_progress,
                "status": prep_state.video_preparation.preload_status.value,
                "video_url": prep_state.video_preparation.video_url,
                "file_size_mb": prep_state.video_preparation.file_size_mb
            },
            "sync_data_preparation": {
                "download_progress": prep_state.sync_data_preparation.download_progress,
                "parsing_progress": prep_state.sync_data_preparation.parsing_progress,
                "status": prep_state.sync_data_preparation.preparation_status.value,
                "effects_count": prep_state.sync_data_preparation.effects_count,
                "required_actuators": [act.value for act in prep_state.sync_data_preparation.required_actuators]
            },
            "device_communication": {
                "connection_status": prep_state.device_communication.connection_status.value,
                "websocket_connected": prep_state.device_communication.websocket_connected,
                "last_ping_ms": prep_state.device_communication.last_ping_ms,
                "device_name": prep_state.device_communication.device_name
            },
            "readiness": {
                "ready_for_playback": prep_state.ready_for_playback,
                "min_required_actuators_ready": prep_state.min_required_actuators_ready,
                "all_actuators_ready": prep_state.all_actuators_ready
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"準備進捗詳細取得エラー: {e}")
        raise HTTPException(status_code=500, detail="準備進捗詳細の取得に失敗しました")

# WebSocket エンドポイント
@router.websocket("/ws/{session_id}")
async def preparation_websocket(websocket: WebSocket, session_id: str):
    """
    準備処理進捗WebSocket
    
    Args:
        websocket: WebSocket接続
        session_id: セッションID
    """
    await websocket.accept()
    websocket_connections[session_id] = websocket
    
    logger.info(f"準備処理WebSocket接続確立: {session_id}")
    
    # 進捗コールバック登録
    preparation_service.add_progress_callback(
        session_id, 
        lambda progress: notify_websocket_progress(session_id, progress)
    )
    
    try:
        # 現在の状態送信
        prep_state = await preparation_service.get_preparation_status(session_id)
        if prep_state:
            await websocket.send_json({
                "type": "status_update",
                "data": {
                    "overall_status": prep_state.overall_status.value,
                    "overall_progress": prep_state.overall_progress,
                    "ready_for_playback": prep_state.ready_for_playback
                }
            })
        
        # 接続維持
        while True:
            try:
                # クライアントからのメッセージ待機
                message = await websocket.receive_text()
                
                # Pingメッセージ処理
                if message == "ping":
                    await websocket.send_text("pong")
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket切断: {session_id}")
                break
            except Exception as e:
                logger.error(f"WebSocketメッセージ処理エラー: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket処理エラー: {e}")
    
    finally:
        # クリーンアップ
        if session_id in websocket_connections:
            del websocket_connections[session_id]

async def notify_websocket_progress(session_id: str, progress: PreparationProgress):
    """WebSocket進捗通知"""
    if session_id not in websocket_connections:
        return
    
    websocket = websocket_connections[session_id]
    
    try:
        await websocket.send_json({
            "type": "progress_update",
            "data": {
                "component": progress.component,
                "progress": progress.progress,
                "status": progress.status.value,
                "message": progress.message,
                "timestamp": progress.timestamp.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"WebSocket進捗通知エラー: {e}")
        # 接続エラーの場合は削除
        if session_id in websocket_connections:
            del websocket_connections[session_id]

# 同期データ送信詳細取得
@router.get("/sync-transmission/{session_id}")
async def get_sync_transmission_details(session_id: str):
    """同期データ送信詳細取得"""
    prep_state = await preparation_service.get_preparation_status(session_id)
    
    if not prep_state:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    sync_prep = prep_state.sync_data_preparation
    transmission_result = sync_prep.transmission_result
    
    if not transmission_result:
        return {
            "session_id": session_id,
            "transmission_status": "not_started",
            "message": "同期データ送信は未実行です"
        }
    
    return {
        "session_id": session_id,
        "transmission_status": "completed" if transmission_result.transmitted else "failed",
        "transmission_details": {
            "device_hub_url": transmission_result.device_hub_url,
            "transmission_size_kb": transmission_result.transmission_size_kb,
            "supported_events": transmission_result.supported_events,
            "unsupported_events": transmission_result.unsupported_events,
            "transmission_timestamp": transmission_result.transmission_timestamp,
            "checksum": transmission_result.checksum,
            "error_message": transmission_result.error_message
        },
        "sync_data_info": {
            "total_effects": sync_prep.effects_count,
            "file_size_kb": sync_prep.file_size_kb,
            "required_actuators": [act.value for act in sync_prep.required_actuators],
            "preparation_status": sync_prep.preparation_status.value
        }
    }

# ヘルスチェック
@router.get("/health")
async def preparation_health():
    """準備処理サービスヘルスチェック"""
    active_count = len(preparation_service.active_preparations)
    websocket_count = len(websocket_connections)
    
    return {
        "status": "healthy",
        "active_preparations": active_count,
        "websocket_connections": websocket_count,
        "timestamp": datetime.now().isoformat()
    }