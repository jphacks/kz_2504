# app/api/device_registration.py - デバイス登録・認証API
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, List
import logging
from datetime import datetime

from app.models.device import (
    DeviceRegistrationRequest, DeviceRegistrationResponse,
    DeviceValidationError, RegisteredDevice
)
from app.services.device_service import DeviceService
from app.config.settings import Settings

# ルーター作成
router = APIRouter(prefix="/api/device", tags=["Device Registration"])

# ロガー設定
logger = logging.getLogger(__name__)

# 依存関係
def get_device_service():
    """DeviceServiceのDI"""
    return DeviceService(Settings())

# グローバルDeviceServiceインスタンス（シングルトン）
_device_service_instance: DeviceService = None

def get_device_service_singleton():
    """DeviceServiceシングルトンインスタンス取得"""
    global _device_service_instance
    if _device_service_instance is None:
        _device_service_instance = DeviceService(Settings())
    return _device_service_instance

@router.post("/register", 
             response_model=DeviceRegistrationResponse, 
             summary="デバイス登録",
             description="製品コードを使用してデバイスを登録し、認証情報を取得します")
async def register_device(
    request: DeviceRegistrationRequest,
    http_request: Request,
    device_service: DeviceService = Depends(get_device_service_singleton)
):
    """
    デバイス登録エンドポイント
    
    - **product_code**: 製品コード (例: DH001, DH002, DX123)
    
    成功時にデバイスID、認証トークン、WebSocketエンドポイント情報を返却
    """
    try:
        # クライアント情報を追加
        client_info = {
            "ip_address": http_request.client.host if http_request.client else "unknown",
            "user_agent": http_request.headers.get("user-agent", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
        request.client_info.update(client_info)
        
        # デバイス登録実行
        response = device_service.register_device(request)
        
        logger.info(f"デバイス登録成功: {request.product_code} → {response.device_id}")
        
        return response
        
    except ValueError as e:
        # バリデーションエラー
        logger.warning(f"デバイス登録バリデーションエラー: {request.product_code} - {str(e)}")
        
        error_parts = str(e).split(': ', 1)
        error_code = error_parts[0] if len(error_parts) > 1 else "validation_error"
        error_message = error_parts[1] if len(error_parts) > 1 else str(e)
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": error_code,
                "message": error_message,
                "product_code": request.product_code
            }
        )
        
    except Exception as e:
        # 予期しないエラー
        logger.error(f"デバイス登録エラー: {request.product_code} - {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "デバイス登録処理でエラーが発生しました"
            }
        )

@router.get("/info/{device_id}",
            summary="デバイス情報取得",
            description="登録済みデバイスの詳細情報を取得します")
async def get_device_info(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service_singleton)
):
    """
    デバイス情報取得エンドポイント
    
    - **device_id**: 取得対象のデバイスID
    """
    device = device_service.get_device(device_id)
    
    if not device:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "device_not_found",
                "message": "デバイスが見つかりません",
                "device_id": device_id
            }
        )
    
    logger.info(f"デバイス情報取得: {device_id}")
    return device.to_dict()

@router.get("/available",
            summary="利用可能デバイス一覧",
            description="セッション参加可能な登録済みデバイスの一覧を取得します")
async def get_available_devices(
    device_service: DeviceService = Depends(get_device_service_singleton)
):
    """
    利用可能デバイス一覧取得エンドポイント
    """
    available_devices = device_service.get_available_devices()
    
    logger.info(f"利用可能デバイス一覧取得: {len(available_devices)}件")
    
    return {
        "available_devices": available_devices,
        "count": len(available_devices),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/verify/{device_id}",
             summary="デバイス認証",
             description="デバイスIDとトークンを使用して認証を確認します")
async def verify_device(
    device_id: str,
    token_data: Dict[str, str],
    device_service: DeviceService = Depends(get_device_service_singleton)
):
    """
    デバイス認証エンドポイント
    
    - **device_id**: 認証対象のデバイスID
    - **token**: セッション認証トークン
    """
    token = token_data.get("token")
    if not token:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "missing_token",
                "message": "認証トークンが必要です"
            }
        )
    
    is_valid = device_service.verify_device_token(device_id, token)
    
    if not is_valid:
        logger.warning(f"デバイス認証失敗: {device_id}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "message": "認証トークンが無効です",
                "device_id": device_id
            }
        )
    
    logger.info(f"デバイス認証成功: {device_id}")
    
    return {
        "valid": True,
        "device_id": device_id,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/statistics",
            summary="デバイス統計",
            description="登録済みデバイスの統計情報を取得します")
async def get_device_statistics(
    device_service: DeviceService = Depends(get_device_service_singleton)
):
    """
    デバイス統計情報取得エンドポイント
    """
    stats = device_service.get_device_statistics()
    
    logger.info("デバイス統計情報取得")
    
    return {
        "statistics": stats,
        "timestamp": datetime.now().isoformat()
    }

@router.delete("/cleanup",
               summary="期限切れデバイスクリーンアップ",
               description="期限切れのデバイス登録情報をクリーンアップします")
async def cleanup_expired_devices(
    expiry_hours: int = 24,
    device_service: DeviceService = Depends(get_device_service_singleton)
):
    """
    期限切れデバイスクリーンアップエンドポイント
    
    - **expiry_hours**: 期限切れ判定時間（デフォルト: 24時間）
    """
    cleaned_count = device_service.cleanup_expired_devices(expiry_hours)
    
    logger.info(f"期限切れデバイスクリーンアップ実行: {cleaned_count}件削除")
    
    return {
        "cleaned_devices": cleaned_count,
        "expiry_hours": expiry_hours,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/capabilities/{product_code}",
            summary="製品機能情報",
            description="製品コードがサポートする機能一覧を取得します")
async def get_product_capabilities(
    product_code: str,
    device_service: DeviceService = Depends(get_device_service_singleton)
):
    """
    製品機能情報取得エンドポイント
    
    - **product_code**: 製品コード (例: DH001)
    """
    capabilities = device_service.get_supported_capabilities(product_code)
    
    if not capabilities:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "product_not_found",
                "message": "製品コードが見つかりません",
                "product_code": product_code
            }
        )
    
    logger.info(f"製品機能情報取得: {product_code}")
    
    return {
        "product_code": product_code,
        "capabilities": capabilities,
        "capability_count": len(capabilities),
        "timestamp": datetime.now().isoformat()
    }