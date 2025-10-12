# 4DX@HOME 包括的開発ロードマップ

## 📋 概要
- **作成日**: 2025年10月12日
- **対象**: Phase B-3完成 → Docker化 → GCP Cloud Run デプロイメント
- **期間**: 2025年10月12日 ～ 2025年11月30日 (7週間)
- **目標**: 本格的な4Dエンターテイメント体験の完全実現

---

## 🎯 現在の実装状況

### ✅ **完了済み実装**
- **Phase B-2**: 準備処理API 100%完成 (7/7テスト成功)
- **demo1.json送信**: 28KB, 185エフェクト正常送信 (チェックサム検証済み)
- **WebSocket基本機能**: 接続管理・メッセージ処理完成 (3/3テスト成功)
- **デバイス検出基盤**: Mock実装完成、実デバイス移行準備完了

### 🔄 **Phase B-3 現在状況** (70%完成)
- **実装済み**: WebSocket接続、基本同期機能
- **問題点**: 統合テストで中継遅延発生 (0/5成功)
- **課題**: relay_sync_to_devices関数の同期タイミング最適化

---

## 📊 3段階開発戦略

### 🏠 **Phase 1: ローカル開発完成** (Week 1-3)
**期間**: 2025年10月12日 ～ 2025年11月2日 (3週間)  
**目標**: 完全機能4D体験システムの実現

#### **Step 1.1: 同期中継問題修正** (1日目)
**ファイル**: `backend/app/api/playback_control.py`

**問題分析**:
- 統合テスト失敗原因: WebSocketメッセージ中継の遅延・順序問題
- relay_sync_to_devices関数でのasync処理タイミング不整合

**修正方針**:
```python
# 修正前: 順次送信による遅延
async def relay_sync_to_devices(session_id: str, sync_data: dict):
    for device_id, websocket in connected_devices[session_id].items():
        await websocket.send_text(json.dumps(sync_data))  # ←遅延発生

# 修正後: 並列送信による高速化
async def relay_sync_to_devices(session_id: str, sync_data: dict):
    if session_id not in connected_devices:
        return
    
    tasks = []
    for device_id, websocket in connected_devices[session_id].items():
        task = asyncio.create_task(
            safe_send_to_device(websocket, sync_data, device_id)
        )
        tasks.append(task)
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
```

**成功基準**: 統合テスト 5/5 成功達成

#### **Step 1.2: 再生モデル実装** (2日目)
**ファイル**: `backend/app/models/playback.py` (新規作成)

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum
import datetime

class PlaybackState(str, Enum):
    IDLE = "idle"
    PLAYING = "playing" 
    PAUSED = "paused"
    SEEKING = "seeking"
    STOPPED = "stopped"

class SyncMessage(BaseModel):
    """フロントエンド同期メッセージ"""
    type: str = "sync"
    state: PlaybackState
    time: float = Field(ge=0.0)
    duration: float = Field(ge=0.0)
    ts: Optional[int] = None

class EffectCommand(BaseModel):
    """デバイスエフェクト命令"""
    actuator_type: str
    intensity: float = Field(ge=0.0, le=1.0)
    duration: float = Field(ge=0.0)
    start_time: float = Field(ge=0.0)
    command_id: str

class PlaybackSession(BaseModel):
    """再生セッション管理"""
    session_id: str
    video_id: str
    current_state: PlaybackState = PlaybackState.IDLE
    current_time: float = 0.0
    connected_devices: List[str] = []
    created_at: datetime.datetime
    last_sync_time: Optional[datetime.datetime] = None
```

#### **Step 1.3: 同期サービス実装** (3-4日目)
**ファイル**: `backend/app/services/sync_service.py` (新規作成)

```python
import json
import asyncio
from typing import Dict, List, Optional
from pathlib import Path

class SyncService:
    def __init__(self):
        self.demo_data: Dict = {}
        self.effect_cache: Dict = {}
        self.load_demo_data()
    
    def load_demo_data(self):
        """demo1.json読み込み・キャッシュ"""
        demo_path = Path("assets/sync-data/demo1.json")
        if demo_path.exists():
            with open(demo_path, 'r', encoding='utf-8') as f:
                self.demo_data = json.load(f)
                self._build_effect_cache()
    
    def _build_effect_cache(self):
        """時刻インデックス付きエフェクトキャッシュ構築"""
        for effect in self.demo_data.get("effects", []):
            time_key = f"{effect['start_time']:.1f}"
            if time_key not in self.effect_cache:
                self.effect_cache[time_key] = []
            self.effect_cache[time_key].append(effect)
    
    def get_effects_at_time(self, time_pos: float) -> List[Dict]:
        """指定時刻のエフェクト取得"""
        time_key = f"{time_pos:.1f}"
        return self.effect_cache.get(time_key, [])
    
    async def distribute_effects(self, session_id: str, time_pos: float, 
                               device_sender_func):
        """エフェクト配信"""
        effects = self.get_effects_at_time(time_pos)
        if effects:
            for effect in effects:
                command = {
                    "type": "effect",
                    "actuator_type": effect["actuator_type"],
                    "intensity": effect["intensity"],
                    "duration": effect["duration"],
                    "start_time": effect["start_time"],
                    "command_id": f"cmd_{int(time_pos*10)}_{effect['id']}"
                }
                await device_sender_func(session_id, command)
```

#### **Step 1.4: 再生制御API完成** (5-7日目)
**ファイル**: `backend/app/api/playback_control.py` (拡張)

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.sync_service import SyncService
from app.models.playback import SyncMessage, PlaybackSession

router = APIRouter(prefix="/api/playbook", tags=["playback"])
sync_service = SyncService()

@router.post("/start/{session_id}")
async def start_playback(session_id: str, start_request: PlaybackStartRequest):
    """再生開始"""
    session = get_session(session_id)
    session.current_state = PlaybackState.PLAYING
    await sync_service.distribute_effects(session_id, 0.0, relay_sync_to_devices)
    return {"status": "started", "session_id": session_id}

@router.websocket("/ws/sync/{session_id}")
async def sync_websocket(websocket: WebSocket, session_id: str):
    """リアルタイム同期WebSocket"""
    await websocket.accept()
    
    # フロントエンド接続登録
    if session_id not in connected_frontends:
        connected_frontends[session_id] = []
    connected_frontends[session_id].append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            sync_msg = SyncMessage.parse_raw(data)
            
            # デバイスに中継
            await relay_sync_to_devices(session_id, sync_msg.dict())
            
            # エフェクト配信
            if sync_msg.state == PlaybackState.PLAYING:
                await sync_service.distribute_effects(
                    session_id, sync_msg.time, relay_sync_to_devices
                )
            
    except WebSocketDisconnect:
        connected_frontends[session_id].remove(websocket)
```

#### **Step 1.5: 包括テスト・品質向上** (8-21日目)
**テストファイル**: `test_phase3_comprehensive.py` (新規作成)

**テスト項目**:
1. **統合同期テスト**: フロントエンド→サーバー→デバイス (5/5成功目標)
2. **負荷テスト**: 20同時セッション処理
3. **エフェクト精度テスト**: demo1.json完全再生検証
4. **エラー復旧テスト**: 接続断絶・復旧シナリオ

### 🐋 **Phase 2: Docker化実装** (Week 4-5)
**期間**: 2025年11月2日 ～ 2025年11月16日 (2週間)  
**目標**: コンテナ化による本格環境構築

#### **Step 2.1: 本格Dockerfile作成** (1-3日目)
**ファイル**: `backend/Dockerfile.production` (新規作成)

```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY app/ ./app/
COPY assets/ ./assets/
COPY data/ ./data/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/preparation/health || exit 1

# Production server
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### **Step 2.2: Docker Compose環境** (4-5日目)
**ファイル**: `backend/docker-compose.prod.yml`

```yaml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - LOG_LEVEL=info
    volumes:
      - ./assets:/app/assets:ro
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/preparation/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
    restart: unless-stopped
```

#### **Step 2.3: コンテナテスト** (6-7日目)
**テストスクリプト**: `test_docker_integration.py`

```python
import docker
import requests
import websockets
import asyncio

class DockerIntegrationTest:
    def __init__(self):
        self.client = docker.from_env()
        
    def test_container_startup(self):
        """コンテナ起動テスト"""
        container = self.client.containers.run(
            "4dx-backend:latest", 
            ports={'8000/tcp': 8000},
            detach=True,
            remove=True
        )
        
        # ヘルスチェック待機
        time.sleep(10)
        
        # API疎通確認
        response = requests.get("http://localhost:8000/api/preparation/health")
        assert response.status_code == 200
        
        container.stop()

    async def test_websocket_in_container(self):
        """コンテナ内WebSocket接続テスト"""
        uri = "ws://localhost:8000/api/playback/ws/sync/docker_test"
        async with websockets.connect(uri) as websocket:
            await websocket.send('{"type":"sync","state":"play","time":0.0}')
            response = await websocket.recv()
            assert '"type":"sync_ack"' in response
```

### ☁️ **Phase 3: GCP Cloud Run デプロイメント** (Week 6-7)
**期間**: 2025年11月16日 ～ 2025年11月30日 (2週間)  
**目標**: 本格クラウド環境での運用開始

#### **Step 3.1: Cloud Run設定** (1-3日目)
**ファイル**: `backend/Dockerfile.cloudrun`

```dockerfile
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY assets/ ./assets/
COPY data/ ./data/

# Cloud Run port
ENV PORT 8080
EXPOSE $PORT

# Production start with Cloud Run optimization
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

**ファイル**: `cloudbuild.yaml`

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/4dx-backend:$SHORT_SHA', '-f', 'backend/Dockerfile.cloudrun', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/4dx-backend:$SHORT_SHA']
  
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', '4dx-backend',
      '--image', 'gcr.io/$PROJECT_ID/4dx-backend:$SHORT_SHA',
      '--region', 'asia-northeast1',
      '--platform', 'managed',
      '--allow-unauthenticated',
      '--max-instances', '10',
      '--memory', '2Gi',
      '--cpu', '2',
      '--concurrency', '100'
    ]
```

#### **Step 3.2: SSL WebSocket対応** (4-5日目)
**設定**: Cloud Run WebSocket + SSL証明書

```python
# app/config/settings.py (Cloud Run対応)
import os

class CloudRunSettings:
    # WebSocket SSL設定
    WS_SCHEME = "wss" if os.getenv("ENV") == "production" else "ws"
    DOMAIN = os.getenv("CUSTOM_DOMAIN", "4dx-backend-xxxxxxxxx-an.a.run.app")
    
    # Cloud Run最適化
    MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", "100"))
    WEBSOCKET_TIMEOUT = int(os.getenv("WS_TIMEOUT", "300"))
```

#### **Step 3.3: 本格負荷テスト** (6-7日目)
**ファイル**: `load_test_cloudrun.py`

```python
import asyncio
import websockets
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class CloudRunLoadTest:
    def __init__(self, base_url: str):
        self.base_url = base_url
        
    async def test_concurrent_websockets(self, concurrent_count: int = 50):
        """同時WebSocket接続負荷テスト"""
        tasks = []
        for i in range(concurrent_count):
            task = asyncio.create_task(
                self.websocket_session(f"load_test_{i}")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        
        print(f"負荷テスト結果: {success_count}/{concurrent_count} 成功")
        return success_count >= concurrent_count * 0.95  # 95%成功率目標
        
    async def websocket_session(self, session_id: str):
        """個別WebSocketセッション"""
        uri = f"{self.base_url}/api/playback/ws/sync/{session_id}"
        async with websockets.connect(uri) as ws:
            # 30秒間の同期メッセージ送信
            for i in range(30):
                sync_msg = {
                    "type": "sync",
                    "state": "playing",
                    "time": i * 1.0,
                    "duration": 30.0
                }
                await ws.send(json.dumps(sync_msg))
                await asyncio.sleep(1)
```

---

## 📊 **技術要件・成功基準**

### **Phase 1 成功基準**
- ✅ 統合テスト: 5/5成功率達成
- ✅ 同期精度: ±100ms以下
- ✅ 同時セッション: 20セッション対応
- ✅ demo1.json完全再生: 185エフェクト配信成功

### **Phase 2 成功基準**
- ✅ コンテナ化: Docker正常起動・ヘルスチェック
- ✅ 統合テスト: コンテナ環境で全テスト成功
- ✅ 負荷テスト: Docker環境で20並列セッション
- ✅ 本格WebSocket: SSL対応・外部アクセス

### **Phase 3 成功基準**
- ✅ Cloud Run デプロイ: 正常稼働・ヘルスチェック
- ✅ SSL WebSocket: wss://接続成功
- ✅ 負荷テスト: 50並列WebSocket接続 (95%成功率)
- ✅ 監視: Cloud Logging・Cloud Monitoring稼働

---

## 🔧 **開発環境・ツール**

### **必要なツール**
```bash
# Docker環境
docker --version                    # Docker 20.10+
docker-compose --version           # Docker Compose 2.0+

# GCP環境  
gcloud --version                   # Google Cloud SDK
gcloud auth login                  # 認証設定
gcloud config set project kz-2504  # プロジェクト設定

# 負荷テストツール
pip install locust                 # HTTP負荷テスト
pip install websockets             # WebSocket接続テスト
pip install aiohttp                # 非同期HTTP接続
```

### **テスト実行コマンド**
```bash
# Phase 1: ローカルテスト
python test_phase3_comprehensive.py

# Phase 2: Dockerテスト  
docker-compose -f docker-compose.prod.yml up --build
python test_docker_integration.py

# Phase 3: Cloud Run テスト
gcloud builds submit --config cloudbuild.yaml
python load_test_cloudrun.py --url https://4dx-backend-xxx-an.a.run.app
```

---

## ⚠️ **リスク管理**

### **技術リスク**
1. **WebSocket同期精度**: ネットワーク遅延による同期ズレ
   - **対策**: 適応的遅延補正、クライアント側バッファリング

2. **Cloud Run制約**: WebSocket長時間接続制限
   - **対策**: 定期再接続、セッション状態復元

3. **負荷スケーリング**: 同時接続数制限
   - **対策**: Cloud Run自動スケール、接続プール最適化

### **プロジェクトリスク**
1. **スケジュール遅延**: 技術的困難による開発遅延
   - **対策**: 毎週マイルストーン確認、機能優先度調整

2. **品質問題**: 急速開発による品質低下
   - **対策**: 段階的テスト、回帰テスト自動化

---

## 📅 **マイルストーン**

### **Weekly Reviews**
- **Week 1 (10/12-10/18)**: 同期問題修正・基本実装
- **Week 2 (10/19-10/25)**: API完成・統合テスト
- **Week 3 (10/26-11/01)**: 品質向上・負荷テスト
- **Week 4 (11/02-11/08)**: Docker化・コンテナテスト
- **Week 5 (11/09-11/15)**: Docker統合・本格テスト
- **Week 6 (11/16-11/22)**: Cloud Run デプロイ
- **Week 7 (11/23-11/30)**: 本格負荷テスト・運用開始

### **Go/No-Go判定**
各Phase終了時に以下を評価:
- ✅ **技術実装**: 全テスト成功
- ✅ **品質基準**: パフォーマンス目標達成  
- ✅ **安定性**: エラー率 < 1%
- ✅ **スケーラビリティ**: 負荷テスト合格

---

**最終目標**: 2025年11月30日までに、本格的な4Dエンターテイメント体験システムの完全運用開始を実現する。

**作成者**: Backend Development Team  
**承認**: プロジェクトマネージャー  
**次期レビュー**: 2025年10月19日 (Phase 1 Week 1完了時)