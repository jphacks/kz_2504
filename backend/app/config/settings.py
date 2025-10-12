"""
Configuration Settings - 環境変数管理

Pydantic Settingsを使用したアプリケーション設定管理
機密情報を環境変数で管理し、セキュリティを確保
"""

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os
from pathlib import Path

class DatabaseSettings(BaseModel):
    """データベース設定（将来の拡張用）"""
    url: Optional[str] = None
    max_connections: int = 10
    timeout: int = 30

class CORSSettings(BaseModel):
    """CORS設定"""
    origins: List[str] = []
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]

class SecuritySettings(BaseModel):
    """セキュリティ設定"""
    secret_key: str = "default-secret-key-change-in-production"
    session_expire_minutes: int = 60
    max_failed_attempts: int = 5

class DebugSettings(BaseModel):
    """デバッグ設定"""
    enabled: bool = False
    skip_preparation: bool = False
    auto_device_ready: bool = False
    fast_connection: bool = False
    lockout_duration_minutes: int = 15

class CloudSettings(BaseModel):
    """クラウド設定"""
    project_id: Optional[str] = None
    region: str = "asia-northeast1"
    service_account_key: Optional[str] = None

class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # アプリケーション基本情報
    app_name: str = Field(default="4DX@HOME Backend", description="アプリケーション名")
    app_version: str = Field(default="1.0.0", description="バージョン")
    environment: str = Field(default="development", description="環境（development/staging/production）")
    debug: bool = Field(default=True, description="デバッグモード")
    
    # サーバー設定
    host: str = Field(default="0.0.0.0", description="バインドホスト")
    port: int = Field(default=8080, description="ポート番号")
    reload: bool = Field(default=True, description="ホットリロード（開発用）")
    workers: int = Field(default=1, description="ワーカー数")
    
    # CORS設定（機密情報）
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="CORS許可オリジン（カンマ区切り）"
    )
    
    # セキュリティ設定（機密情報）
    secret_key: str = Field(
        default="4dx-home-super-secret-key-change-in-production",
        description="JWT署名・暗号化用秘密キー"
    )
    api_key: Optional[str] = Field(default=None, description="API認証キー")
    
    # WebSocket設定
    websocket_timeout: int = Field(default=300, description="WebSocketタイムアウト（秒）")
    max_connections: int = Field(default=100, description="最大同時接続数")
    ping_interval: int = Field(default=30, description="Pingインターバル（秒）")
    
    # WebSocket URL設定（マイコン統合用）
    device_websocket_base_url: str = Field(
        default="wss://fourdk-backend-333203798555.asia-northeast1.run.app",
        description="マイコンWebSocket接続ベースURL"
    )
    
    # デバッグ設定
    debug_mode: bool = Field(default=False, description="デバッグモード有効化")
    debug_skip_preparation: bool = Field(default=False, description="準備処理スキップ")
    debug_auto_ready: bool = Field(default=False, description="自動Ready状態")
    debug_fast_connection: bool = Field(default=False, description="高速接続モード")
    
    # ファイルパス設定
    data_path: str = Field(default="./data", description="データファイルパス")
    assets_path: str = Field(default="../../assets", description="アセットパス")
    logs_path: str = Field(default="./logs", description="ログファイルパス")
    
    # 動画アセット設定
    video_assets_path: str = Field(default="../assets/videos", description="動画アセットパス")
    sync_data_path: str = Field(default="../assets/sync-data", description="シンクデータパス")
    
    # Cloud Run / GCP設定（機密情報）
    cloud_project_id: Optional[str] = Field(default=None, description="GCPプロジェクトID")
    cloud_region: str = Field(default="asia-northeast1", description="GCPリージョン")
    service_account_key: Optional[str] = Field(default=None, description="サービスアカウントキー（JSON）")
    
    # データベース設定（将来用）
    database_url: Optional[str] = Field(default=None, description="データベース接続URL")
    redis_url: Optional[str] = Field(default=None, description="Redis接続URL")
    
    # ログ設定
    log_level: str = Field(default="INFO", description="ログレベル")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="ログフォーマット")
    
    # 外部API設定（機密情報）
    external_api_key: Optional[str] = Field(default=None, description="外部API認証キー")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook署名検証用秘密")
    
    # パフォーマンス設定
    request_timeout: int = Field(default=30, description="リクエストタイムアウト（秒）")
    max_request_size: int = Field(default=16 * 1024 * 1024, description="最大リクエストサイズ（バイト）")
    
    # 設定ファイル
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def get_cors_origins(self) -> List[str]:
        """CORS許可オリジンをリストで取得"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.environment.lower() == "development"
    
    def get_data_path(self) -> Path:
        """データパスをPathオブジェクトで取得"""
        return Path(self.data_path)
    
    def get_assets_path(self) -> Path:
        """アセットパスをPathオブジェクトで取得"""
        return Path(self.assets_path)
    
    def get_logs_path(self) -> Path:
        """ログパスをPathオブジェクトで取得"""
        return Path(self.logs_path)
    
    def get_video_assets_path(self) -> Path:
        """動画アセットパスをPathオブジェクトで取得"""
        return Path(self.video_assets_path)
    
    def get_sync_data_path(self) -> Path:
        """シンクデータパスをPathオブジェクトで取得"""
        return Path(self.sync_data_path)
    
    def get_device_data_path(self) -> Path:
        """デバイスデータファイルパスを取得"""
        return Path("./data/devices.json")
    
    def get_device_websocket_url(self, session_id: str) -> str:
        """マイコンWebSocket URL生成"""
        return f"{self.device_websocket_base_url}/api/preparation/ws/{session_id}"
    
    def is_debug_mode(self) -> bool:
        """デバッグモード判定"""
        return self.debug_mode or self.environment.lower() == "development"
    
    def should_skip_preparation(self) -> bool:
        """準備処理スキップ判定"""
        return self.is_debug_mode() and self.debug_skip_preparation
    
    def should_auto_ready(self) -> bool:
        """自動Ready状態判定"""
        return self.is_debug_mode() and self.debug_auto_ready

# グローバル設定インスタンス
settings = Settings()

# 設定検証
def validate_settings():
    """設定値の検証"""
    if settings.is_production() and settings.secret_key == "4dx-home-super-secret-key-change-in-production":
        raise ValueError("本番環境では SECRET_KEY を必ず変更してください")
    
    if settings.is_production() and settings.debug:
        raise ValueError("本番環境では DEBUG を無効にしてください")
    
    # データディレクトリの存在確認
    data_path = settings.get_data_path()
    if not data_path.exists():
        print(f"警告: データディレクトリが存在しません: {data_path}")
    
    return True

# アプリケーション起動時に設定検証
if __name__ == "__main__":
    validate_settings()
    print("✅ 設定検証完了")
    print(f"Environment: {settings.environment}")
    print(f"Debug: {settings.debug}")
    print(f"CORS Origins: {settings.get_cors_origins()}")
    print(f"Data Path: {settings.get_data_path()}")
else:
    # モジュールインポート時に軽量検証
    try:
        validate_settings()
    except ValueError as e:
        print(f"⚠️  設定警告: {e}")