# 4DX@HOME バックエンド保存情報

## 📋 概要
このファイルは環境リセット前のバックエンド実装から重要な情報を保存したものです。  
**作成日**: 2025年10月12日  
**目的**: 環境再構築時の参考資料

---

## 🏗️ 実装済み機能一覧

### ✅ 完全実装済み
1. **FastAPIベースアプリケーション**
2. **デバイス登録・認証システム**
3. **動画管理システム（拡張版）**
4. **WebSocket通信基盤**
5. **セッション管理システム**

### ❌ 未実装（要実装）
1. **準備処理制御API** (`app/api/preparation.py`)
2. **準備処理サービス** (`app/services/preparation_service.py`)
3. **WebSocket準備通知機能**

---

## 📊 API エンドポイント仕様

### デバイス登録・認証 (`/api/device`)

#### POST `/api/device/register`
**目的**: 製品コードによるデバイス登録
```json
// Request
{
  "product_code": "DH001"
}

// Response
{
  "device_id": "DH001_20251012123456_a1b2c3d4",
  "device_name": "4DX Home Basic",
  "capabilities": ["VIBRATION", "MOTION", "AUDIO"],
  "status": "registered",
  "session_token": "4DX_DH001_20251012123456_...",
  "expires_in": 3600,
  "websocket_endpoints": {
    "device_endpoint": "/ws/device/{session_id}",
    "webapp_endpoint": "/ws/webapp/{session_id}",
    "legacy_endpoint": "/ws/sessions/{session_id}"
  }
}
```

#### GET `/api/device/info/{device_id}`
**目的**: 登録済みデバイス情報取得

#### POST `/api/device/verify/{device_id}`
**目的**: デバイス認証確認

#### GET `/api/device/available`
**目的**: 利用可能デバイス一覧取得

#### GET `/api/device/statistics`
**目的**: デバイス統計情報取得

### 動画管理 (`/api/videos`)

#### GET `/api/videos/`
**目的**: 全動画一覧取得

#### GET `/api/videos/{video_id}`
**目的**: 特定動画情報取得

#### GET `/api/videos/{video_id}/sync-data`
**目的**: 動画同期データ取得

#### POST `/api/videos/compatibility-check`
**目的**: 動画・デバイス互換性確認
```json
// Request
{
  "video_id": "demo1",
  "device_capabilities": ["VIBRATION", "MOTION", "AUDIO"]
}

// Response
{
  "compatible": true,
  "video_id": "demo1",
  "video_title": "アクション映画デモ",
  "missing_capabilities": [],
  "supported_effects": ["vibration", "motion", "audio"],
  "effect_complexity": "medium",
  "duration": 33.5
}
```

#### GET `/api/videos/by-device/{token}`
**目的**: デバイス対応動画フィルタリング

#### POST `/api/videos/search`
**目的**: 動画検索（複数フィルタ対応）

### WebSocketエンドポイント

#### `/ws/device/{session_id}`
**目的**: デバイス専用WebSocket通信

#### `/ws/webapp/{session_id}`
**目的**: Webアプリ専用WebSocket通信

#### `/ws/sessions/{session_id}` (レガシー)
**目的**: 互換性維持用WebSocket

---

## 🔧 データモデル定義

### デバイス関連

#### DeviceCapability (Enum)
```python
class DeviceCapability(str, Enum):
    VIBRATION = "VIBRATION"
    MOTION = "MOTION"
    SCENT = "SCENT"
    AUDIO = "AUDIO"
    LIGHTING = "LIGHTING"
    WIND = "WIND"
```

#### ProductCodeInfo
```python
class ProductCodeInfo(BaseModel):
    product_code: str        # 製品コード
    device_name: str         # デバイス名
    manufacturer: str        # 製造元
    model: str              # モデル名
    capabilities: List[DeviceCapability]  # サポート機能
    max_connections: int     # 最大同時接続数
    is_active: bool         # 有効フラグ
```

#### DeviceRegistrationRequest
```python
class DeviceRegistrationRequest(BaseModel):
    product_code: str = Field(
        pattern=r'^[A-Z]{2,3}\d{3}$',
        description="製品コード (例: DH001, DX123)"
    )
    client_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
```

### 動画関連

#### EnhancedVideo
```python
class EnhancedVideo(BaseModel):
    id: str                     # 動画ID
    title: str                  # タイトル
    description: str            # 説明
    duration_seconds: float     # 再生時間
    sync_file: str             # 同期ファイル名
    thumbnail_url: str         # サムネイルURL
    supported_effects: List[str]  # サポートエフェクト
    device_requirements: List[str]  # 必要デバイス機能
    effect_complexity: str      # エフェクト複雑度
    content_rating: str         # コンテンツレーティング
    categories: List[str]       # カテゴリ
```

---

## 🗃️ データファイル構造

### `backend/data/devices.json`
```json
{
  "devices": {
    "DH001": {
      "product_code": "DH001",
      "device_name": "4DX Home Basic",
      "manufacturer": "4DX Technologies",
      "model": "Home Basic v1.0",
      "capabilities": ["VIBRATION", "MOTION", "AUDIO"],
      "max_connections": 1,
      "is_active": true,
      "description": "基本的な4D体験機能を提供する家庭用デバイス",
      "price_tier": "basic"
    },
    "DH002": {
      "product_code": "DH002",
      "device_name": "4DX Home Standard",
      "manufacturer": "4DX Technologies",
      "model": "Home Standard v1.0",
      "capabilities": ["VIBRATION", "MOTION", "SCENT", "AUDIO"],
      "max_connections": 2,
      "is_active": true,
      "description": "香り機能を追加した標準的な家庭用4Dデバイス",
      "price_tier": "standard"
    },
    "DH003": {
      "product_code": "DH003",
      "device_name": "4DX Home Premium",
      "manufacturer": "4DX Technologies",
      "model": "Home Premium v1.0",
      "capabilities": ["VIBRATION", "MOTION", "SCENT", "AUDIO", "LIGHTING", "WIND"],
      "max_connections": 4,
      "is_active": true,
      "description": "全ての4D効果に対応したプレミアム家庭用デバイス",
      "price_tier": "premium"
    }
  },
  "validation_rules": {
    "product_code_pattern": "^[A-Z]{2,3}\\d{3}$",
    "min_length": 5,
    "max_length": 6,
    "required_capabilities": ["VIBRATION"],
    "session_timeout_minutes": 60
  }
}
```

---

## ⚙️ 設定・環境

### `requirements.txt`
```pip-requirements
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==11.0.3
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
httpx==0.25.2
python-json-logger==2.0.7
pytest==7.4.3
pytest-asyncio==0.21.1
```

### Settings設定項目
```python
class Settings(BaseSettings):
    # アプリケーション基本情報
    app_name: str = "4DX@HOME Backend"
    app_version: str = "1.0.0"
    environment: str = "development"
    
    # サーバー設定
    host: str = "0.0.0.0"
    port: int = 8080
    
    # CORS設定
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,https://fourdk-home-frontend.web.app"
    
    # WebSocket設定
    websocket_timeout: int = 300
    max_connections: int = 100
    
    # パス設定
    assets_path: str = "./assets"
    data_path: str = "./assets/data"
    video_path: str = "./assets/videos"
    
    # セッション管理
    session_timeout: int = 3600
    sync_tolerance: float = 0.5
```

---

## 🔐 認証・セキュリティ

### 製品コード検証ルール
1. **形式**: `^[A-Z]{2,3}\\d{3}$`
2. **例**: DH001, DX123, ABC999
3. **長さ**: 5-6文字
4. **必須機能**: VIBRATION

### デバイスID生成方式
```
{product_code}_{timestamp}_{unique_part}
例: DH001_20251012123456_a1b2c3d4
```

### セッショントークン生成方式
```
4DX_{device_id}_{timestamp}_{unique_hash}
例: 4DX_DH001_20251012123456_a1b2c3d4e5f6...
```

---

## 📁 ファイル構造（実装済み）

```
backend/
├── app/
│   ├── main.py                    # メインアプリケーション
│   ├── config/
│   │   ├── settings.py            # 設定管理
│   │   └── logging.py             # ログ設定
│   ├── api/
│   │   ├── device_registration.py # デバイス登録API（完成）
│   │   ├── video_management.py    # 動画管理API（完成）
│   │   └── phase1.py             # セッション管理API（既存）
│   ├── models/
│   │   ├── device.py             # デバイスモデル（完成）
│   │   ├── video.py              # 動画モデル（完成）
│   │   └── session_models.py     # セッションモデル（既存）
│   ├── services/
│   │   ├── device_service.py     # デバイスサービス（完成）
│   │   └── video_service.py      # 動画サービス（完成）
│   └── websocket/
│       ├── manager.py            # WebSocket管理（既存）
│       ├── device_handler.py     # デバイス処理（既存）
│       └── webapp_handler.py     # Webアプリ処理（既存）
├── data/
│   ├── devices.json              # 製品コードマスタ（完成）
│   └── sync-patterns/            # 同期データディレクトリ
├── requirements.txt              # 依存関係（完成）
└── Dockerfile                    # Docker設定（既存）
```

---

## ❌ 不足している実装（要実装）

### 1. 準備処理制御API
**ファイル**: `app/api/preparation.py`  
**エンドポイント**:
- `POST /api/preparation/start` - 準備処理開始
- `GET /api/preparation/{session_id}/status` - 準備状況確認
- `POST /api/preparation/{session_id}/actuator-test` - アクチュエーターテスト
- `POST /api/preparation/{session_id}/ready` - 準備完了通知

### 2. 準備処理サービス
**ファイル**: `app/services/preparation_service.py`
**主要機能**:
- 準備プロセス管理
- アクチュエーターテスト制御
- 進捗状況追跡
- WebSocket通知

### 3. 準備処理モデル
**ファイル**: `app/models/preparation.py`
**主要クラス**:
- PreparationStatus (Enum)
- ActuatorTest
- PreparationState

---

## 🔄 WebSocket通信仕様

### メッセージ形式
```json
{
  "type": "message_type",
  "timestamp": "2025-10-12T12:34:56.789Z",
  "session_id": "session_123",
  "data": { /* payload */ }
}
```

### 主要メッセージタイプ
- `connection_established` - 接続確立
- `device_status` - デバイス状態更新
- `sync_command` - 同期コマンド
- `preparation_progress` - 準備進捗通知
- `actuator_test_request` - アクチュエーターテスト要求
- `actuator_test_result` - アクチュエーターテスト結果

---

## 🚀 デプロイメント情報

### Cloud Run設定
- **ポート**: 8080
- **ホスト**: 0.0.0.0
- **環境変数**: `.env`ファイルから読み込み

### Docker設定
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 📝 開発メモ

### 実装の良い点
1. **モジュラー設計**: 機能別に適切に分離
2. **型安全性**: Pydanticによる厳密な型定義
3. **エラーハンドリング**: 包括的なエラー処理
4. **WebSocket管理**: デバイス・Webアプリ別チャンネル
5. **設定管理**: 環境別設定の適切な管理

### 改善が必要な点
1. **準備処理の実装不足**: 最重要機能が未実装
2. **テストコード不足**: 単体・統合テストが少ない
3. **ログ管理強化**: 構造化ログの改善余地

### 次期実装での注意点
1. **準備処理API**: 最優先で実装
2. **WebSocket拡張**: 準備通知機能の追加
3. **テスト充実**: 包括的なテスト実装
4. **パフォーマンス**: 同期精度の向上

---

**更新日**: 2025年10月12日  
**ステータス**: 環境リセット前保存完了  
**次期作業**: 準備処理システムの実装