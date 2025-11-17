# 4DX@HOME バックエンド仕様書

> **⚠️ HackDay 2025時点の仕様書**  
> この文書はJPHacks2025 HackDay（2024年10月11-12日）時点の仕様です。  
> 最新の実装については以下を参照してください：
> - **最新バックエンド実装**: `backend/app/`
> - **Cloud Runデプロイガイド**: `backend/DEPLOYMENT_GUIDE.md`
> - **詳細設計資料**: `docs/backend-report/`
> - **最新アーキテクチャ**: 3層構成（Frontend ↔ Cloud Run API ↔ Raspberry Pi）

## 概要

4DX@HOMEのバックエンドは、FastAPIベースのWebサーバーで、デバイス管理、動画管理、リアルタイム同期制御を提供します。WebSocketを使用したリアルタイム通信により、フロントエンドとハードウェアデバイス間の高精度同期を実現します。

## 技術スタック

### 主要フレームワーク・ライブラリ
- **FastAPI** 0.104.1 - 高性能Web APIフレームワーク
- **Uvicorn** 0.24.0 - ASGI サーバー
- **WebSockets** 11.0.3 - リアルタイム双方向通信
- **Pydantic** 2.5.0 - データバリデーション・シリアライゼーション

### データ処理・IO
- **aiofiles** 25.1.0 - 非同期ファイル操作
- **python-multipart** 0.0.6 - マルチパート形式対応
- **httpx** 0.25.2 - 非同期HTTPクライアント
- **aiohttp** 3.9.5 - 非同期HTTP通信
- **pydantic-settings** 2.1.0 - Pydantic設定管理拡張

### ログ・開発支援
- **python-json-logger** 2.0.7 - 構造化ログ出力

### 開発・テスト
- **pytest** 7.4.3 - テストフレームワーク
- **pytest-asyncio** 0.21.1 - 非同期テスト対応

## アーキテクチャ

### ディレクトリ構造
```
backend/
├── app/                       # アプリケーションコード
│   ├── main.py               # FastAPIアプリエントリーポイント
│   ├── config/
│   │   └── settings.py       # 環境設定管理
│   ├── api/                  # APIエンドポイント
│   │   ├── device_registration.py # デバイス登録API
│   │   ├── video_management.py    # 動画管理API
│   │   ├── preparation.py         # 準備処理API
│   │   └── playback_control.py    # 再生制御API
│   ├── models/               # Pydanticデータモデル
│   │   ├── device.py         # デバイス関連モデル
│   │   ├── video.py          # 動画関連モデル
│   │   └── preparation.py    # 準備処理関連モデル
│   └── services/             # ビジネスロジック
├── data/                     # データファイル（実際の配置）
│   ├── devices.json          # デバイス情報
│   └── videos/               # 動画メタデータ
├── assets/                   # 静的アセット
│   ├── thumbnails/           # サムネイル画像
│   └── videos/               # 動画ファイル
├── logs/                     # ログファイル
├── requirements.txt          # Python依存関係
├── Dockerfile               # Docker設定
└── docker-compose.yml       # Docker Compose設定
```

### アプリケーション構成
```python
# FastAPI アプリケーション設定
app = FastAPI(
    title="4DX@HOME Backend API",
    description="4DX@HOME システムのバックエンドAPI",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc"         # ReDoc
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 本番環境では制限
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

## API エンドポイント

### 1. システム情報
```http
GET /
Response: システム状態とバージョン情報

GET /health
Response: 詳細ヘルスチェック情報

GET /api/version
Response: APIバージョンとエンドポイント一覧
- /api/device/register
- /api/device/info/{product_code}  
- /api/device/capabilities
- /api/videos/available
- /api/videos/{video_id}
- /api/videos/select
- /api/videos/categories/list
- /api/preparation/start/{session_id}
- /api/preparation/status/{session_id}
- /api/preparation/stop/{session_id}
- /api/preparation/ws/{session_id}
- /api/preparation/health
```

### 2. デバイス管理 (`/api/device/`)
#### デバイス登録
```http
POST /api/device/register
Content-Type: application/json

Request:
{
  "product_code": "DH001"
}

Response:
{
  "device_id": "device_12345678",
  "device_name": "4DX Home Basic",
  "capabilities": ["VIBRATION", "MOTION", "AUDIO"],
  "status": "registered",
  "registered_at": "2024-10-13T12:00:00Z",
  "session_timeout": 60
}
```

#### デバイス情報取得
```http
GET /api/device/info/{product_code}

Response:
{
  "product_code": "DH001",
  "device_name": "4DX Home Basic",
  "manufacturer": "4DX Technologies",
  "model": "Home Basic v1.0",
  "capabilities": ["VIBRATION", "MOTION", "AUDIO"],
  "max_connections": 1,
  "is_active": true,
  "description": "基本的な4D体験機能を提供する家庭用デバイス",
  "price_tier": "basic"
}
```

#### デバイス機能一覧
```http
GET /api/device/capabilities

Response:
{
  "supported_capabilities": ["VIBRATION", "MOTION", "SCENT", "AUDIO", "LIGHTING", "WIND"],
  "descriptions": {
    "VIBRATION": "振動機能",
    "MOTION": "モーション機能",
    "SCENT": "香り機能", 
    "AUDIO": "オーディオ機能",
    "LIGHTING": "ライティング機能",
    "WIND": "風機能"
  }
}
```

### 3. 動画管理 (`/api/videos/`)
#### 利用可能動画一覧
```http
GET /api/videos/available

Response:
{
  "videos": [
    {
      "video_id": "demo1",
      "title": "Demo Video 1",
      "description": "First demonstration video",
      "duration": 120,
      "thumbnail": "/assets/thumbnails/demo1.jpg",
      "category": "demo",
      "effects_available": true
    }
  ],
  "categories": ["demo", "action", "adventure"]
}
```

#### 動画詳細取得
```http
GET /api/videos/{video_id}

Response:
{
  "video_id": "demo1",
  "title": "Demo Video 1",
  "file_path": "/assets/videos/demo1.mp4",
  "sync_data_path": "/assets/sync-data/demo1.json",
  "metadata": {
    "duration": 120,
    "resolution": "1920x1080",
    "fps": 30
  }
}
```

#### 動画選択
```http
POST /api/videos/select
Content-Type: application/json

Request:
{
  "video_id": "demo1",
  "device_id": "device_12345678"
}

Response:
{
  "session_id": "session_20241013_120000_demo1",
  "video_url": "/assets/videos/demo1.mp4",
  "sync_data_url": "/assets/sync-data/demo1.json",
  "preparation_started": true,
  "estimated_preparation_time": 30
}
```

#### 動画カテゴリ一覧
```http
GET /api/videos/categories/list

Response:
{
  "categories": ["action", "horror", "adventure", "comedy", "drama", "scifi", "fantasy", "demo", "test"],
  "descriptions": {
    "action": "アクション映画",
    "horror": "ホラー映画", 
    "adventure": "アドベンチャー",
    "comedy": "コメディ",
    "drama": "ドラマ",
    "scifi": "SF映画",
    "fantasy": "ファンタジー",
    "demo": "デモンストレーション",
    "test": "テスト用"
  }
}
```

### 4. 準備処理 (`/api/preparation/`)
#### 準備開始
```http
POST /api/preparation/start/{session_id}

Response:
{
  "success": true,
  "message": "Preparation started",
  "session_id": "1234",
  "websocket_url": "ws://localhost:8000/api/preparation/ws/1234"
}
```

#### 準備状態確認
```http
GET /api/preparation/status/{session_id}

Response:
{
  "session_id": "1234",
  "status": "ready",
  "device_connected": true,
  "video_selected": true,
  "sync_data_loaded": true
}
```

#### 準備停止
```http
DELETE /api/preparation/stop/{session_id}

Response:
{
  "success": true,
  "message": "準備処理を停止しました"
}
```

#### 準備処理ヘルスチェック
```http
GET /api/preparation/health

Response:
{
  "status": "healthy",
  "active_preparations": 2,
  "websocket_connections": 2,
  "timestamp": "2024-10-13T12:00:00Z"
}
```

#### WebSocket接続
```websocket
WS /api/preparation/ws/{session_id}

# 受信メッセージ例（進捗更新）
{
  "type": "progress_update",
  "data": {
    "component": "video_preparation",
    "progress": 75,
    "status": "preparing",
    "message": "動画データ読み込み中...",
    "timestamp": "2024-10-13T12:00:00Z"
  }
}

# 送信メッセージ例（状態更新）
{
  "type": "status_update", 
  "data": {
    "overall_status": "ready",
    "overall_progress": 100,
    "ready_for_playback": true
  }
}
```

## データモデル

### デバイス情報
```python
class DeviceRegistrationRequest(BaseModel):
    product_code: str = Field(..., min_length=5, max_length=6)

class DeviceInfo(BaseModel):
    product_code: str
    device_name: str
    manufacturer: str
    model: str
    capabilities: List[str]  # ["VIBRATION", "MOTION", "AUDIO", etc.]
    max_connections: int
    is_active: bool
    description: str
    price_tier: str

class DeviceRegistrationResponse(BaseModel):
    device_id: str
    device_name: str
    capabilities: List[str]
    status: str = "registered"
    registered_at: datetime
    session_timeout: int = 60
```

### 動画情報
```python
class VideoInfo(BaseModel):
    video_id: str
    title: str
    description: str
    duration_seconds: float
    file_name: str
    file_size_mb: Optional[float]
    thumbnail_url: Optional[str]
    categories: List[str]
    tags: List[str]
    content_rating: ContentRating = ContentRating.G
    created_at: datetime
    updated_at: Optional[datetime]

class VideoCompatibility(BaseModel):
    required_capabilities: List[str]
    recommended_capabilities: List[str]
    supported_effects: List[EffectInfo]
    effect_complexity: EffectComplexity
    min_device_version: Optional[str]

class EnhancedVideo(BaseModel):
    video_info: VideoInfo
    compatibility: VideoCompatibility
    status: VideoStatus = VideoStatus.READY
    sync_data_file: Optional[str]
    play_count: int = 0
    avg_rating: Optional[float]

class VideoSelectRequest(BaseModel):
    video_id: str
    device_id: str
    session_preferences: Optional[Dict[str, Any]] = {}

class VideoSelectResponse(BaseModel):
    session_id: str
    video_url: str
    sync_data_url: Optional[str]
    preparation_started: bool = False
    estimated_preparation_time: int = 30
```

### 同期データ・準備処理
```python
class SyncEvent(BaseModel):
    t: float                    # タイムスタンプ(秒)
    action: str                # "start", "stop", "shot"
    effect: str                # "VIBRATION", "MOTION", "SCENT", etc.
    mode: str                  # 効果のモード
    intensity: Optional[float] # 強度(0.0-1.0)

class TimelineData(BaseModel):
    events: List[SyncEvent]
    video_id: str
    duration: float

class PreparationState(BaseModel):
    session_id: str
    overall_status: PreparationStatus
    overall_progress: int
    ready_for_playback: bool
    estimated_completion_time: Optional[datetime]
    video_preparation: VideoPreparation
    sync_data_preparation: SyncDataPreparation
    device_communication: DeviceCommunication

class PreparationProgress(BaseModel):
    component: str
    progress: int
    status: PreparationStatus
    message: str
    timestamp: datetime
```

## WebSocket通信プロトコル

### 接続フロー
1. **クライアント接続**: `/api/preparation/ws/{session_id}`
2. **認証確認**: セッションIDの有効性確認
3. **初期化**: デバイス状態とタイムラインデータ送信
4. **リアルタイム同期**: 動画時刻の連続送信

### メッセージ形式（準備処理用）
```python
# 進捗更新メッセージ
{
  "type": "progress_update",
  "data": {
    "component": "video_preparation",
    "progress": 75,
    "status": "preparing",
    "message": "動画データ読み込み中...",
    "timestamp": "2024-10-13T12:00:00Z"
  }
}

# 状態更新メッセージ
{
  "type": "status_update",
  "data": {
    "overall_status": "ready",
    "overall_progress": 100,
    "ready_for_playback": true
  }
}

# Ping/Pongメッセージ
# クライアント → サーバー: "ping"
# サーバー → クライアント: "pong"
```

### エラーハンドリング
```python
{
  "type": "error",
  "error_code": "SESSION_NOT_FOUND",
  "message": "Session not found or expired",
  "timestamp": "2024-10-13T12:00:00Z"
}
```

## セッション管理

### セッションライフサイクル
1. **作成**: デバイス登録時に4桁セッションコード生成
2. **アクティブ**: 動画選択・WebSocket接続時
3. **実行中**: 動画再生・リアルタイム同期時
4. **終了**: 動画終了・接続切断時

### セッション状態
```python
class SessionState(BaseModel):
    session_id: str
    device_id: str
    video_id: str
    device_connected: bool
    video_selected: bool
    sync_data_loaded: bool
    websocket_connected: bool
    status: str  # "created", "ready", "active", "ended"
    created_at: datetime
    expires_at: datetime
```

## 設定管理

### 環境変数
```python
# .env ファイル
APP_NAME="4DX@HOME Backend"
APP_VERSION="1.0.0"
ENVIRONMENT="development"
DEBUG=true
HOST="0.0.0.0"
PORT=8080
LOG_LEVEL="INFO"
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"

# セキュリティ設定
SECRET_KEY="4dx-home-super-secret-key-change-in-production"
API_KEY=""

# WebSocket設定
WEBSOCKET_TIMEOUT=300
MAX_CONNECTIONS=100
PING_INTERVAL=30

# デバイス接続設定
DEVICE_WEBSOCKET_BASE_URL="wss://fourdk-backend-xxxxxxxxxxxx.asia-northeast1.run.app"

# デバッグ設定
DEBUG_MODE=false
DEBUG_SKIP_PREPARATION=false
DEBUG_AUTO_READY=false
DEBUG_FAST_CONNECTION=false

# クラウド設定（GCP）
CLOUD_PROJECT_ID=""
CLOUD_REGION="asia-northeast1"
SERVICE_ACCOUNT_KEY=""

# データベース設定（将来用）
DATABASE_URL=""
REDIS_URL=""
```

### 設定クラス
```python
class Settings(BaseSettings):
    # アプリケーション基本情報
    app_name: str = "4DX@HOME Backend"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    
    # サーバー設定
    host: str = "0.0.0.0"
    port: int = 8080
    reload: bool = True
    workers: int = 1
    
    # CORS設定
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # セキュリティ設定
    secret_key: str = "4dx-home-super-secret-key-change-in-production"
    api_key: Optional[str] = None
    
    # WebSocket設定
    websocket_timeout: int = 300
    max_connections: int = 100
    ping_interval: int = 30
    
    # デバイス接続設定
    device_websocket_base_url: str = "wss://fourdk-backend-xxxxxxxxxxxx.asia-northeast1.run.app"
    
    # デバッグ設定
    debug_mode: bool = False
    debug_skip_preparation: bool = False
    debug_auto_ready: bool = False
    debug_fast_connection: bool = False
    
    # ファイルパス設定
    data_path: str = "./data"
    assets_path: str = "../../assets"
    logs_path: str = "./logs"
    video_assets_path: str = "../assets/videos"
    sync_data_path: str = "../assets/sync-data"
    
    # ログ設定
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def get_cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        return self.environment.lower() == "development"
    
    def get_device_websocket_url(self, session_id: str) -> str:
        return f"{self.device_websocket_base_url}/api/preparation/ws/{session_id}"
```

## ログ・監視

### ログ設定
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 主要ログポイント
- デバイス登録・切断
- 動画選択・再生開始
- WebSocket接続・切断
- エラー・例外発生
- パフォーマンス指標
```

### メトリクス監視
- **API レスポンス時間**
- **WebSocket接続数**
- **同期精度**(タイムスタンプずれ)
- **エラー発生率**
- **リソース使用量**

## セキュリティ

### API セキュリティ
- **入力バリデーション**: Pydanticによる厳密な型チェック
- **CORS設定**: 許可オリジンの限定
- **レート制限**: API呼び出し頻度制限(予定)
- **認証**: セッションベース認証

### データ保護
- **ログサニタイゼーション**: 機密情報のマスク
- **エラー情報制限**: 内部情報の漏洩防止
- **セッション管理**: 適切な有効期限設定

## デプロイ・運用

### Docker対応
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 起動コマンド
```bash
# 開発環境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 本番環境
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### ヘルスチェック
```bash
# 基本ヘルスチェック
curl http://localhost:8000/health

# 詳細状態確認
curl http://localhost:8000/api/version
```

## パフォーマンス要件

### 応答時間
- **REST API**: < 100ms (95th percentile)
- **WebSocket**: < 50ms (同期メッセージ)
- **ファイル配信**: < 500ms (動画・画像)

### スループット
- **同時接続**: 100セッション
- **API リクエスト**: 1000 req/sec
- **WebSocket メッセージ**: 10,000 msg/sec

### リソース使用量
- **メモリ**: < 512MB (通常時)
- **CPU**: < 50% (通常時)
- **ディスク**: 1GB (ログ・キャッシュ含む)

## エラーハンドリング

### HTTP エラーコード
- **400 Bad Request**: 不正なリクエスト形式
- **404 Not Found**: リソースが見つからない
- **409 Conflict**: セッション重複・競合
- **422 Unprocessable Entity**: バリデーションエラー
- **500 Internal Server Error**: サーバー内部エラー

### WebSocket エラー
```python
{
  "type": "error",
  "error_code": "SESSION_NOT_FOUND",
  "message": "Session not found or expired",
  "timestamp": "2024-10-12T10:00:00Z"
}
```

## 今後の拡張予定

### 機能拡張
- **ユーザー認証**: JWT認証システム
- **動画アップロード**: ユーザー動画対応
- **AI動画解析**: GPT-4o-mini Vision統合
- **マルチデバイス**: 複数デバイス同時制御

### 技術的改善
- **Redis**: セッション・キャッシュ管理
- **PostgreSQL**: 永続化データベース
- **Kubernetes**: コンテナオーケストレーション
- **監視**: Prometheus + Grafana