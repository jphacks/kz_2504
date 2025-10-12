# 4DX@HOME バックエンド仕様書

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

### 開発・テスト
- **pytest** 7.4.3 - テストフレームワーク
- **pytest-asyncio** 0.21.1 - 非同期テスト対応

## アーキテクチャ

### ディレクトリ構造
```
backend/app/
├── main.py                    # FastAPIアプリエントリーポイント
├── config/
│   └── settings.py            # 環境設定管理
├── api/                       # APIエンドポイント
│   ├── device_registration.py # デバイス登録API
│   ├── video_management.py    # 動画管理API
│   ├── preparation.py         # 準備処理API
│   └── playback_control.py    # 再生制御API
├── models/                    # データモデル
├── services/                  # ビジネスロジック
└── data/                      # データファイル
    ├── devices.json           # デバイス情報
    └── videos/                # 動画メタデータ
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
```

### 2. デバイス管理 (`/api/device/`)
#### デバイス登録
```http
POST /api/device/register
Content-Type: application/json

Request:
{
  "product_code": "4DX001",
  "session_id": "1234"
}

Response:
{
  "success": true,
  "message": "Device registered successfully",
  "session_id": "1234",
  "device_info": {
    "product_code": "4DX001",
    "capabilities": ["vibration", "flash", "wind", "water", "color"]
  }
}
```

#### デバイス情報取得
```http
GET /api/device/info/{product_code}

Response:
{
  "product_code": "4DX001",
  "name": "4DX Home Device",
  "capabilities": ["vibration", "flash", "wind", "water", "color"],
  "version": "1.0.0"
}
```

#### デバイス機能一覧
```http
GET /api/device/capabilities

Response:
{
  "vibration": {
    "modes": ["long", "strong", "heartbeat"],
    "description": "触覚フィードバック"
  },
  "flash": {
    "modes": ["strobe", "burst", "steady"],
    "description": "光演出"
  },
  "color": {
    "modes": ["red", "green", "blue"],
    "description": "カラー照明"
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
  "session_id": "1234"
}

Response:
{
  "success": true,
  "message": "Video selected successfully",
  "video_info": {
    "video_id": "demo1",
    "title": "Demo Video 1",
    "sync_data_loaded": true
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

#### WebSocket接続
```websocket
WS /api/preparation/ws/{session_id}

# 受信メッセージ例
{
  "type": "video_time_update",
  "current_time": 15.5,
  "session_id": "1234"
}

# 送信メッセージ例
{
  "type": "sync_ready",
  "message": "Synchronization ready"
}
```

## データモデル

### デバイス情報
```python
class DeviceInfo(BaseModel):
    product_code: str
    name: str
    capabilities: List[str]
    version: str

class DeviceRegistration(BaseModel):
    product_code: str
    session_id: str
```

### 動画情報
```python
class VideoInfo(BaseModel):
    video_id: str
    title: str
    description: Optional[str]
    duration: int
    thumbnail: Optional[str]
    category: str
    effects_available: bool

class VideoSelection(BaseModel):
    video_id: str
    session_id: str
```

### 同期データ
```python
class SyncEvent(BaseModel):
    t: float                    # タイムスタンプ(秒)
    action: str                # "start", "stop", "shot"
    effect: str                # "vibration", "flash", "wind", etc.
    mode: str                  # 効果のモード
    intensity: Optional[float] # 強度(0.0-1.0)

class TimelineData(BaseModel):
    events: List[SyncEvent]
    video_id: str
    duration: float
```

## WebSocket通信プロトコル

### 接続フロー
1. **クライアント接続**: `/api/preparation/ws/{session_id}`
2. **認証確認**: セッションIDの有効性確認
3. **初期化**: デバイス状態とタイムラインデータ送信
4. **リアルタイム同期**: 動画時刻の連続送信

### メッセージ形式
```python
# フロントエンド → バックエンド
{
  "type": "video_time_update",
  "current_time": 15.5,
  "session_id": "1234",
  "playback_state": "playing"
}

# バックエンド → デバイス
{
  "type": "device_control",
  "events": [
    {
      "t": 15.5,
      "action": "start",
      "effect": "vibration",
      "mode": "strong"
    }
  ]
}
```

### エラーハンドリング
```python
{
  "type": "error",
  "code": "DEVICE_NOT_FOUND",
  "message": "Device not connected",
  "session_id": "1234"
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
    device_connected: bool
    video_selected: bool
    sync_data_loaded: bool
    websocket_connected: bool
    status: str  # "created", "ready", "active", "ended"
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
PORT=8000
LOG_LEVEL="INFO"
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
```

### 設定クラス
```python
class Settings(BaseSettings):
    app_name: str = "4DX@HOME Backend"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    def is_development(self) -> bool:
        return self.environment == "development"
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