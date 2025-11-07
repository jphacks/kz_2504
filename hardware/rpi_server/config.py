"""
4DX@HOME Raspberry Pi Server - Configuration
環境変数を読み込み、アプリケーション全体で使用する設定を管理
"""

import os
from typing import Optional
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Config:
    """アプリケーション設定クラス"""
    
    # === デバイス情報 ===
    DEVICE_HUB_ID: str = os.getenv("DEVICE_HUB_ID", "DH001")
    DEVICE_NAME: str = os.getenv("DEVICE_NAME", "RaspberryPi Device Hub 1")
    
    # === Cloud Run API設定 ===
    # 注意: 実際の値は .env ファイルに記載してください（Gitにコミットしないこと）
    CLOUD_RUN_API_URL: str = os.getenv(
        "CLOUD_RUN_API_URL",
        "https://your-backend-api.run.app"  # デフォルト値（.envで上書き必須）
    )
    CLOUD_RUN_WS_URL: str = os.getenv(
        "CLOUD_RUN_WS_URL",
        "wss://your-backend-api.run.app"  # デフォルト値（.envで上書き必須）
    )
    
    # === MQTT Broker設定 ===
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "rpi_server")
    MQTT_KEEPALIVE: int = int(os.getenv("MQTT_KEEPALIVE", "60"))
    
    # === Flask Server設定 ===
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "8000"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # === Timeline処理設定 ===
    SYNC_TOLERANCE_MS: int = int(os.getenv("SYNC_TOLERANCE_MS", "100"))
    TIMELINE_CACHE_DIR: str = os.getenv("TIMELINE_CACHE_DIR", "data/timeline_cache")
    COMMUNICATION_LOG_DIR: str = os.getenv("COMMUNICATION_LOG_DIR", "data/communication_logs")
    
    # === ログ設定 ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "data/rpi_server.log")
    ENABLE_COMMUNICATION_LOG: bool = os.getenv("ENABLE_COMMUNICATION_LOG", "True").lower() == "true"
    
    # === デバイスハートビート設定 ===
    HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
    HEARTBEAT_TIMEOUT: int = int(os.getenv("HEARTBEAT_TIMEOUT", "15"))
    
    # === WebSocket再接続設定 ===
    WS_RECONNECT_DELAY: int = int(os.getenv("WS_RECONNECT_DELAY", "5"))
    WS_MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("WS_MAX_RECONNECT_ATTEMPTS", "0"))
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", "30"))
    
    @classmethod
    def validate(cls) -> None:
        """設定値の妥当性を検証"""
        errors = []
        
        if not cls.DEVICE_HUB_ID:
            errors.append("DEVICE_HUB_ID is required")
        
        if not cls.CLOUD_RUN_API_URL:
            errors.append("CLOUD_RUN_API_URL is required")
        
        if not cls.CLOUD_RUN_WS_URL:
            errors.append("CLOUD_RUN_WS_URL is required")
        
        if cls.SYNC_TOLERANCE_MS < 0:
            errors.append("SYNC_TOLERANCE_MS must be >= 0")
        
        if cls.HEARTBEAT_INTERVAL <= 0:
            errors.append("HEARTBEAT_INTERVAL must be > 0")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    @classmethod
    def get_websocket_url(cls, session_id: str) -> str:
        """WebSocketエンドポイントURLを生成"""
        return f"{cls.CLOUD_RUN_WS_URL}/api/playback/ws/device/{session_id}"
    
    @classmethod
    def get_device_registration_url(cls) -> str:
        """デバイス登録エンドポイントURLを生成"""
        return f"{cls.CLOUD_RUN_API_URL}/api/device/register"


# アプリケーション起動時に設定を検証
Config.validate()
