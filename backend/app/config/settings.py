# app/config/settings.py - 4DX@HOME 設定管理
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """アプリケーション設定クラス"""
    
    # アプリケーション基本情報
    app_name: str = "4DX@HOME Backend"
    app_version: str = "1.0.0"
    environment: str = "development"
    
    # アプリケーション制御（.envから）
    debug: bool = True
    log_level: str = "INFO"
    log_format: str = "text"
    
    # サーバー設定（.envから）
    host: str = "0.0.0.0"  # Cloud Run対応
    port: int = 8080  # Cloud Run標準ポート
    workers: int = 1
    
    # CORS設定（.envから文字列で受け取り、リストに変換）
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,https://fourdk-home-frontend.web.app"
    
    # WebSocket設定（.envから）
    websocket_timeout: int = 300
    max_connections: int = 100
    
    # ファイルパス（.envから）
    assets_path: str = "./assets"
    data_path: str = "./assets/data"
    video_path: str = "./assets/videos"
    
    # セッション管理（.envから）
    session_timeout: int = 3600
    sync_tolerance: float = 0.5
    
    # 動画ストレージ設定
    video_storage_type: str = "local"  # local | gcs
    gcs_bucket_name: str = "4dx-home-videos"
    gcs_cdn_url: str = "https://cdn.4dx-home.app"
    
    @property
    def allowed_origins(self) -> List[str]:
        """CORS許可オリジンをリストで返却"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def server_host(self) -> str:
        """サーバーホスト（Cloud Run対応）"""
        return os.getenv("HOST", self.host)
        
    @property 
    def server_port(self) -> int:
        """サーバーポート（Cloud Run対応）"""
        return int(os.getenv("PORT", self.port))
        
    @property
    def sync_data_directory(self) -> str:
        """同期データディレクトリ"""
        return "./data/sync-patterns"
        
    @property
    def assets_directory(self) -> str:
        """アセットディレクトリ"""
        return self.assets_path
        
    @property
    def sync_tolerance_ms(self) -> float:
        """同期許容誤差（ミリ秒）"""
        return self.sync_tolerance * 1000
        
    @property
    def log_file(self) -> str:
        """ログファイル名"""
        return "backend.log"
    
    def get_video_url(self, video_id: str) -> str:
        """環境に応じた動画URLを生成"""
        if self.video_storage_type == "gcs" and self.environment == "production":
            return f"{self.gcs_cdn_url}/videos/{video_id}.mp4"
        else:
            return f"{self.video_path}/{video_id}.mp4"
    
    @property
    def is_development(self) -> bool:
        """開発環境判定"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """本番環境判定"""  
        return self.environment == "production"
        
    def ensure_directories(self):
        """必要なディレクトリを作成"""
        os.makedirs(self.sync_data_directory, exist_ok=True)
        os.makedirs(self.assets_directory, exist_ok=True)
    
    class Config:
        env_file = ".env"