# 🚀 4DX@HOME バックエンド実装計画書

## 📋 **実装概要**

### **現状分析**
- ✅ **基本FastAPIアプリケーション**: 既存 (`main.py`)
- ✅ **WebSocket基盤**: 基本的な実装あり
- ❌ **要件定義準拠**: 未対応（画面遷移API、デバイス管理等）
- ❌ **本番環境対応**: 未実装

### **実装目標**
**要件定義書に完全準拠した、段階的デモ対応可能なFastAPIサーバーを構築**

---

## 🎯 **Phase別実装戦略**

### **Phase 1: 画面遷移サポートAPI（HTTP）** 
**期間**: 2日間 | **優先度**: ⭐⭐⭐ **最高**

#### **1.1 デバイス登録API実装**
```
POST /api/sessions
- デバイスハブ起動時のセッション作成・製品コード登録
- 入力: {product_code, capabilities, device_info}
- 出力: {session_id, product_code, status, websocket_url}
```

#### **1.2 動画選択API実装**
```
GET /api/videos
- 静的動画リスト提供
- 出力: [{video_id, title, duration, video_size, thumbnail}]

GET /api/sessions/{product_code}
- 製品コードでセッション検索・デバイス状態確認
- 出力: {session_id, device_connected, status}
```

#### **1.3 同期データAPI実装**
```
GET /api/sync-data/{video_id}
- 動画同期データ＋URL提供
- 出力: {video_id, video_url, sync_events[]}
```

#### **1.4 セッション状態管理**
```
メモリ内辞書: product_code → session_info
状態遷移: registered → connected → playing → ended
```

### **Phase 2: リアルタイム通信（WebSocket）**
**期間**: 3日間 | **優先度**: ⭐⭐⭐ **最高**

#### **2.1 WebSocket接続管理**
```
/ws/device/{session_id}  - デバイス制御チャネル
/ws/webapp/{session_id}  - Webアプリ同期チャネル
```

#### **2.2 メッセージング実装**
```
デバイス ← サーバー:
  - prepare_playback, effect_command
デバイス → サーバー:
  - device_connected, ready_for_playback
  
Webアプリ ← サーバー:
  - device_ready, sync_acknowledged
Webアプリ → サーバー:
  - start_playback, playback_sync, end_playback
```

#### **2.3 接続状態監視**
```
- WebSocket接続・切断検知
- セッション内クライアント管理
- エラーハンドリング・再接続対応
```

### **Phase 3: 同期・状態管理**
**期間**: 2日間 | **優先度**: ⭐⭐⭐ **最高**

#### **3.1 ファイルベースデータ管理**
```
- videos.json: 動画リスト読み込み
- {video_id}_sync.json: 同期データ読み込み
- 同期イベント検索アルゴリズム
```

#### **3.2 リアルタイム同期処理**
```python
def find_sync_events(video_id: str, current_time: float):
    # ±500ms範囲でのイベント検索
    # デバイス能力・ユーザー設定適用
    # 制御コマンド生成・送信
```

---

## 🏗️ **アーキテクチャ設計**

### **ディレクトリ構造（リファクタリング後）**
```
backend/
├── app/
│   ├── main.py                 # FastAPIアプリケーション
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # 環境設定
│   │   └── logging.py          # ログ設定
│   ├── api/
│   │   ├── __init__.py
│   │   ├── sessions.py         # セッション管理API
│   │   ├── videos.py           # 動画リストAPI
│   │   └── sync_data.py        # 同期データAPI
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── manager.py          # WebSocket接続管理
│   │   ├── device_handler.py   # デバイス制御ハンドラー
│   │   └── webapp_handler.py   # Webアプリ同期ハンドラー
│   ├── session/
│   │   ├── __init__.py
│   │   ├── manager.py          # セッション状態管理
│   │   └── models.py           # セッションデータモデル
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── processor.py        # 同期処理エンジン
│   │   └── events.py           # 同期イベント管理
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic データモデル
│   └── services/
│       ├── __init__.py
│       ├── video_service.py    # 動画データサービス
│       └── device_service.py   # デバイス管理サービス
├── data/
│   ├── videos.json             # 動画リスト
│   └── sync-patterns/
│       └── demo_video_sync.json # 同期データ
├── assets/
│   └── videos/
│       ├── demo_video.mp4      # デモ動画ファイル (開発環境用)
│       └── thumbnails/
│           └── demo_thumbnail.jpg # サムネイル画像
├── tests/
│   ├── test_api.py             # APIテスト
│   ├── test_websocket.py       # WebSocketテスト
│   └── test_sync.py            # 同期処理テスト
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### **データモデル設計（Pydantic）**
```python
# app/models/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class DeviceInfo(BaseModel):
    version: str
    ip_address: str

class SessionCreateRequest(BaseModel):
    product_code: str
    capabilities: List[str]
    device_info: DeviceInfo

class SessionResponse(BaseModel):
    session_id: str
    product_code: str
    status: str
    websocket_url: str

class Video(BaseModel):
    video_id: str
    title: str
    duration: float
    video_size: int
    thumbnail: str

class SyncEvent(BaseModel):
    time: float
    action: str
    intensity: int
    duration: int

class SyncData(BaseModel):
    video_id: str
    duration: float
    video_url: str
    video_size: int
    sync_events: List[SyncEvent]

class WebSocketMessage(BaseModel):
    type: str
    data: Optional[Dict[str, Any]] = None
```

---

## 📅 **7日間実装スケジュール**

### **Day 1-2: Phase 1 - HTTP API基盤**
#### **Day 1**
- [ ] 🏗️ **プロジェクト構造リファクタリング**
  - 既存 `main.py` のバックアップ作成
  - 新しいディレクトリ構造構築
  - 基本設定・ログ設定の分離

- [ ] 📊 **データモデル実装**
  - `models/schemas.py`: Pydanticモデル定義
  - `session/models.py`: セッション管理モデル
  - バリデーション・型安全性確保

#### **Day 2**
- [ ] 🔌 **セッション管理API**
  - `POST /api/sessions`: デバイス登録
  - `GET /api/sessions/{product_code}`: セッション検索
  - `session/manager.py`: セッション状態管理

- [ ] 🎥 **動画・同期データAPI**
  - `GET /api/videos`: 動画リスト提供
  - `GET /api/sync-data/{video_id}`: 同期データ提供
  - `services/video_service.py`: ファイル読み込み処理

### **Day 3-5: Phase 2 - WebSocket通信**
#### **Day 3**
- [ ] 🌐 **WebSocket基盤リファクタリング**
  - `websocket/manager.py`: 接続管理の分離
  - セッション別チャネル管理実装
  - 接続・切断の状態監視

#### **Day 4**
- [ ] 🤖 **デバイス制御ハンドラー**
  - `websocket/device_handler.py`: `/ws/device/{session_id}`
  - メッセージ受信: `device_connected`, `ready_for_playback`
  - メッセージ送信: `prepare_playback`, `effect_command`

#### **Day 5**
- [ ] 💻 **Webアプリ同期ハンドラー**
  - `websocket/webapp_handler.py`: `/ws/webapp/{session_id}`
  - メッセージ受信: `start_playback`, `playback_sync`, `end_playback`
  - メッセージ送信: `device_ready`, `sync_acknowledged`

### **Day 6-7: Phase 3 - 同期・統合**
#### **Day 6**
- [ ] 🎯 **同期処理エンジン**
  - `sync/processor.py`: リアルタイム同期処理
  - 動画時間→同期イベント検索
  - デバイス能力・設定適用フィルター

#### **Day 7**
- [ ] 🧪 **統合テスト・デバッグ**
  - エンドツーエンドテスト実行
  - WebSocketテストクライアント作成
  - パフォーマンス・同期精度確認
  - ドキュメント更新

---

## 🔧 **技術実装詳細**

### **1. 設定管理**
```python
# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    app_name: str = "4DX@HOME Backend"
    app_version: str = "1.0.0"
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8001
    
    # CORS settings
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # WebSocket settings
    websocket_timeout: int = 60
    max_connections_per_session: int = 10
    
    # Sync settings
    sync_tolerance_ms: float = 500.0
    
    # File paths
    data_dir: str = "./data"
    assets_dir: str = "./assets"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### **2. WebSocket接続管理**
```python
# app/websocket/manager.py
from fastapi import WebSocket
from typing import Dict, List, Optional
import json
import logging

class WebSocketManager:
    def __init__(self):
        # session_id -> {"device": WebSocket, "webapp": WebSocket}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect_device(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.connections:
            self.connections[session_id] = {}
        self.connections[session_id]["device"] = websocket
        self.logger.info(f"Device connected to session: {session_id}")
    
    async def connect_webapp(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.connections:
            self.connections[session_id] = {}
        self.connections[session_id]["webapp"] = websocket
        self.logger.info(f"WebApp connected to session: {session_id}")
    
    def disconnect(self, session_id: str, client_type: str):
        if session_id in self.connections:
            if client_type in self.connections[session_id]:
                del self.connections[session_id][client_type]
                self.logger.info(f"{client_type} disconnected from session: {session_id}")
    
    async def send_to_device(self, session_id: str, message: dict):
        if (session_id in self.connections and 
            "device" in self.connections[session_id]):
            await self.connections[session_id]["device"].send_text(json.dumps(message))
    
    async def send_to_webapp(self, session_id: str, message: dict):
        if (session_id in self.connections and 
            "webapp" in self.connections[session_id]):
            await self.connections[session_id]["webapp"].send_text(json.dumps(message))
```

### **3. 同期処理エンジン**
```python
# app/sync/processor.py
import json
from typing import List, Dict, Any, Optional
from app.models.schemas import SyncEvent, SyncData
from app.config.settings import settings

class SyncProcessor:
    def __init__(self):
        self._sync_data_cache: Dict[str, SyncData] = {}
    
    def load_sync_data(self, video_id: str) -> Optional[SyncData]:
        """同期データをファイルから読み込み"""
        if video_id in self._sync_data_cache:
            return self._sync_data_cache[video_id]
        
        sync_file_path = f"{settings.data_dir}/sync-patterns/{video_id}_sync.json"
        try:
            with open(sync_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sync_data = SyncData(**data)
                self._sync_data_cache[video_id] = sync_data
                return sync_data
        except FileNotFoundError:
            return None
    
    def find_sync_events(self, video_id: str, current_time: float) -> List[SyncEvent]:
        """指定時間の同期イベントを検索"""
        sync_data = self.load_sync_data(video_id)
        if not sync_data:
            return []
        
        events = []
        tolerance = settings.sync_tolerance_ms / 1000.0  # ms → s
        
        for event in sync_data.sync_events:
            if abs(event.time - current_time) <= tolerance:
                events.append(event)
        
        return events
    
    def generate_effect_commands(self, events: List[SyncEvent], 
                                user_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """同期イベントから制御コマンドを生成"""
        commands = []
        
        for event in events:
            # ユーザー設定チェック
            if not user_settings.get(event.action, True):
                continue
            
            command = {
                "type": "effect_command",
                "action": event.action,
                "intensity": event.intensity,
                "duration": event.duration
            }
            commands.append(command)
        
        return commands
```

---

## 🧪 **テスト戦略**

### **単体テスト**
```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_session():
    response = client.post("/api/sessions", json={
        "product_code": "DH001",
        "capabilities": ["vibration"],
        "device_info": {"version": "1.0.0", "ip_address": "192.168.1.100"}
    })
    assert response.status_code == 200
    assert "session_id" in response.json()

def test_get_videos():
    response = client.get("/api/videos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### **WebSocketテスト**
```python
# tests/test_websocket.py
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app

def test_websocket_device_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws/device/test-session") as websocket:
        websocket.send_json({"type": "device_connected"})
        data = websocket.receive_json()
        assert data["type"] == "connection_acknowledged"
```

---

## 🚀 **デプロイメント準備**

### **Dockerfile最適化**
```dockerfile
# 本番環境用Dockerfile
FROM python:3.12-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイル
COPY app/ ./app/
COPY data/ ./data/
COPY assets/ ./assets/

# 環境変数設定
ENV PORT=8080
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### **docker-compose.yml**
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8001:8080"
    environment:
      - ENVIRONMENT=development
      - CORS_ORIGINS=http://localhost:3000
    volumes:
      - ./data:/app/data
      - ./assets:/app/assets
```

---

## ⚠️ **リスク管理**

### **技術リスク**
| リスク | 影響度 | 対策 |
|--------|--------|------|
| WebSocket接続不安定 | 高 | 自動再接続・ハートビート実装 |
| 同期精度不足 | 高 | アルゴリズム最適化・テスト強化 |
| メモリリーク | 中 | 接続状態監視・定期クリーンアップ |
| ファイル読み込み遅延 | 中 | キャッシュ機構・非同期処理 |

### **スケジュールリスク**
| リスク | 影響度 | 対策 |
|--------|--------|------|
| Phase 1 遅延 | 高 | MVP機能優先・段階的実装 |
| WebSocket複雑性 | 中 | 既存コード参考・简化設計 |
| 統合テスト課題 | 中 | 早期テスト開始・問題早期発見 |

---

## 🎯 **成功指標（Phase別）**

### **Phase 1完了基準**
- [ ] ✅ `POST /api/sessions` - 200ms以内レスポンス
- [ ] ✅ `GET /api/videos` - 動画リスト正常取得
- [ ] ✅ `GET /api/sessions/{product_code}` - セッション検索成功
- [ ] ✅ `GET /api/sync-data/{video_id}` - 同期データ取得成功

### **Phase 2完了基準** 
- [ ] ✅ WebSocket接続・切断の安定動作
- [ ] ✅ セッション内デバイス・Webアプリ通信確立
- [ ] ✅ メッセージタイプ別ハンドリング正常動作
- [ ] ✅ 5分間の連続接続安定性

### **Phase 3完了基準**
- [ ] ✅ 同期イベント検索 < 50ms
- [ ] ✅ エンドツーエンド同期テスト成功
- [ ] ✅ デモシナリオ完全動作
- [ ] ✅ 同期精度 ±500ms以内

---

## 📚 **実装完了後の次ステップ**

### **本番環境移行**
1. **GCP Cloud Run デプロイ**
2. **環境変数・シークレット管理**  
3. **モニタリング・ログ設定**
4. **負荷テスト実行**

### **フロントエンド・ハードウェア統合**
1. **API仕様書共有**
2. **WebSocket通信テスト**
3. **エラーハンドリング調整**
4. **パフォーマンス最適化**

---

## 📹 **ビデオデータ格納戦略**

### **開発環境 vs 本番環境**

#### **🖥️ 開発環境（ローカル）**
```
backend/assets/videos/
├── demo_video.mp4          # 30秒デモ動画 (~15MB)
├── sample_movie_1.mp4      # 追加サンプル動画
└── thumbnails/
    ├── demo_thumbnail.jpg
    └── sample_1_thumb.jpg
```

**配信方法**: FastAPI StaticFiles
```python
from fastapi.staticfiles import StaticFiles
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
```

**URL例**: `http://127.0.0.1:8001/assets/videos/demo_video.mp4`

#### **☁️ 本番環境（GCP）**
```
Google Cloud Storage バケット: "4dx-home-videos"
├── videos/
│   ├── demo_video.mp4
│   └── sample_movie_1.mp4
└── thumbnails/
    ├── demo_thumbnail.jpg
    └── sample_1_thumb.jpg
```

**配信方法**: GCP Cloud Storage + CDN
**URL例**: `https://storage.googleapis.com/4dx-home-videos/videos/demo_video.mp4`

### **環境別URL生成戦略**

#### **設定ベースの動的URL生成**
```python
# app/config/settings.py
class Settings(BaseSettings):
    # Video storage settings
    video_storage_type: str = "local"  # local | gcs
    video_base_url: str = "/assets/videos"
    gcs_bucket_name: str = "4dx-home-videos"
    gcs_cdn_url: str = "https://cdn.4dx-home.app"
    
    def get_video_url(self, video_filename: str) -> str:
        if self.video_storage_type == "gcs":
            return f"{self.gcs_cdn_url}/videos/{video_filename}"
        else:
            return f"{self.video_base_url}/{video_filename}"
```

#### **動画サービスクラス実装**
```python
# app/services/video_service.py
from app.config.settings import settings

class VideoService:
    def get_videos(self) -> List[Video]:
        videos = self._load_video_metadata()
        # 環境に応じたURL生成
        for video in videos:
            video.video_url = settings.get_video_url(f"{video.video_id}.mp4")
            video.thumbnail = settings.get_video_url(f"thumbnails/{video.video_id}_thumb.jpg")
        return videos
```

### **ビデオ仕様・最適化**

#### **推奨ビデオ仕様**
- **フォーマット**: MP4 (H.264 + AAC)
- **解像度**: 1080p (1920x1080)
- **フレームレート**: 30fps
- **ビットレート**: 8-12 Mbps
- **音声**: AAC 128kbps
- **長さ**: デモ用30秒-2分

#### **サイズ最適化**
```bash
# FFmpegでの最適化例
ffmpeg -i input.mp4 \
  -vcodec h264 -acodec aac \
  -b:v 10M -b:a 128k \
  -s 1920x1080 -r 30 \
  -movflags +faststart \
  output_optimized.mp4
```

### **段階的実装プラン**

#### **Phase 1: ローカルファイル配信**
- [ ] `assets/videos/` ディレクトリ作成
- [ ] FastAPI StaticFiles設定
- [ ] デモ動画ファイル配置
- [ ] `video_service.py` ローカル版実装

#### **Phase 2: GCS対応準備**
- [ ] GCS設定・認証準備
- [ ] 環境変数ベースURL切り替え
- [ ] CDN設定・キャッシュ最適化

#### **Phase 3: 本番GCS移行**
- [ ] 動画ファイルGCSアップロード
- [ ] CDN経由配信テスト
- [ ] パフォーマンス最適化

### **デモ用動画データ要件**

#### **必要な動画ファイル**
```json
{
  "videos": [
    {
      "video_id": "demo_video",
      "title": "4DX@HOME デモ動画",
      "duration": 30.0,
      "video_size": 15728640,
      "filename": "demo_video.mp4",
      "thumbnail": "demo_thumbnail.jpg",
      "sync_file": "demo_video_sync.json"
    }
  ]
}
```

#### **同期データとの連携**
```
data/sync-patterns/demo_video_sync.json:
{
  "video_id": "demo_video",
  "video_url": "/assets/videos/demo_video.mp4", // 環境により自動生成
  "sync_events": [
    {"time": 5.2, "action": "vibrate", "intensity": 50, "duration": 1000},
    {"time": 12.5, "action": "vibrate", "intensity": 80, "duration": 1500}
  ]
}
```

---

**作成日**: 2025年10月11日  
**バージョン**: 1.0  
**実装責任者**: 久米（バックエンド開発者）
**完了予定**: 7日間
**ステータス**: 🔄 計画確定・実装開始準備