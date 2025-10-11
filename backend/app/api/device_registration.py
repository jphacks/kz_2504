"""
Device Registration API - デバイス登録・認証エンドポイント

Handles device registration and authentication using product codes.
Manages device capabilities and generates device IDs for session management.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import settings
from models.device import (
    DeviceRegistrationRequest,
    DeviceRegistrationResponse, 
    DeviceError,
    DeviceInfo
)

# ログ設定
logger = logging.getLogger(__name__)

# APIルーター作成
router = APIRouter(
    prefix="/api/device",
    tags=["Device Registration"],
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Device Not Found"},
        500: {"description": "Internal Server Error"}
    }
)

# デバイス情報の読み込み
def load_device_data() -> dict:
    """devices.jsonファイルからデバイス情報を読み込み"""
    try:
        # 環境変数からデータパスを取得
        data_dir = settings.get_data_path()
        devices_file = data_dir / "devices.json"
        
        with open(devices_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"デバイス情報読み込み完了: {len(data.get('devices', {}))}件")
            return data
    except FileNotFoundError:
        logger.error("devices.jsonファイルが見つかりません")
        raise HTTPException(
            status_code=500,
            detail="デバイス情報ファイルが見つかりません"
        )
    except json.JSONDecodeError as e:
        logger.error(f"devices.jsonの解析エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="デバイス情報ファイルの形式が正しくありません"
        )

def generate_device_id() -> str:
    """ユニークなデバイスIDを生成"""
    return f"device_{uuid.uuid4().hex[:8]}"

def validate_product_code(product_code: str, device_data: dict) -> DeviceInfo:
    """製品コードの検証とデバイス情報取得"""
    devices = device_data.get('devices', {})
    
    # 製品コード存在確認
    if product_code not in devices:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "invalid_product_code",
                "message": f"製品コード '{product_code}' は登録されていません"
            }
        )
    
    # デバイス情報取得
    device_info_dict = devices[product_code]
    
    # デバイス有効性確認
    if not device_info_dict.get('is_active', False):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "device_inactive", 
                "message": "このデバイスはサポートが終了しています"
            }
        )
    
    # DeviceInfoモデルに変換
    try:
        device_info = DeviceInfo(**device_info_dict)
        return device_info
    except Exception as e:
        logger.error(f"デバイス情報の変換エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "data_conversion_error",
                "message": "デバイス情報の処理中にエラーが発生しました"
            }
        )

@router.post("/register", response_model=DeviceRegistrationResponse)
async def register_device(request: DeviceRegistrationRequest):
    """
    デバイス登録エンドポイント
    
    製品コードを受け取り、デバイス情報を検証して登録を行います。
    正常な場合はデバイスIDと機能情報を返します。
    """
    
    logger.info(f"デバイス登録リクエスト: {request.product_code}")
    
    try:
        # デバイス情報読み込み
        device_data = load_device_data()
        
        # 製品コード検証
        device_info = validate_product_code(request.product_code, device_data)
        
        # デバイスID生成
        device_id = generate_device_id()
        
        # セッションタイムアウト設定
        timeout_minutes = device_data.get('validation_rules', {}).get('session_timeout_minutes', 60)
        
        # レスポンス作成
        response = DeviceRegistrationResponse(
            device_id=device_id,
            device_name=device_info.device_name,
            capabilities=device_info.capabilities,
            status="registered",
            session_timeout=timeout_minutes
        )
        
        logger.info(f"デバイス登録成功: {device_id} ({device_info.device_name})")
        
        return response
        
    except HTTPException:
        # HTTP例外は再発生
        raise
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "registration_failed",
                "message": "デバイス登録中に予期しないエラーが発生しました"
            }
        )

@router.get("/info/{product_code}", response_model=DeviceInfo)
async def get_device_info(product_code: str):
    """
    デバイス情報取得エンドポイント（認証前確認用）
    
    製品コードからデバイス情報を取得します。
    登録前の確認や、デバイス仕様の確認に使用します。
    """
    
    logger.info(f"デバイス情報取得リクエスト: {product_code}")
    
    try:
        # デバイス情報読み込み
        device_data = load_device_data()
        
        # 製品コード検証（情報取得のみなので有効性チェックは緩和）
        devices = device_data.get('devices', {})
        
        if product_code not in devices:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "product_not_found",
                    "message": f"製品コード '{product_code}' が見つかりません"
                }
            )
        
        # デバイス情報返却
        device_info_dict = devices[product_code]
        device_info = DeviceInfo(**device_info_dict)
        
        logger.info(f"デバイス情報取得成功: {device_info.device_name}")
        
        return device_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"デバイス情報取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "info_retrieval_failed",
                "message": "デバイス情報の取得中にエラーが発生しました"
            }
        )

@router.get("/capabilities")
async def get_supported_capabilities():
    """
    サポートされている機能一覧取得
    
    システムでサポートされているデバイス機能の一覧を返します。
    """
    
    from models.device import VALID_CAPABILITIES
    
    return {
        "supported_capabilities": VALID_CAPABILITIES,
        "descriptions": {
            "VIBRATION": "振動機能",
            "MOTION": "モーション機能", 
            "SCENT": "香り機能",
            "AUDIO": "オーディオ機能",
            "LIGHTING": "ライティング機能",
            "WIND": "風機能"
        }
    }