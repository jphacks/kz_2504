# GitHub Copilot Instructions for 4DX@HOME Backend

このファイルはGitHub Copilotがコード生成・提案を行う際に参照する指示書です。

---

## プロジェクト概要

**プロジェクト名**: 4DX@HOME Backend API  
**目的**: 動画再生と連動した4Dエフェクト（振動・風・水・光など）を制御するバックエンドシステム  
**技術スタック**: FastAPI, WebSocket, Pydantic, asyncio  
**デプロイ先**: Google Cloud Run  

---

## コーディング規約

### Python コーディングスタイル

- **PEP 8準拠**: すべてのPythonコードはPEP 8に従う
- **型ヒント必須**: 関数の引数と戻り値には必ず型ヒントを付ける
- **docstring**: すべてのクラスと公開関数にdocstringを記載（Google形式）
- **非同期処理**: I/O処理は必ず`async/await`を使用
- **エラーハンドリング**: 例外は具体的にキャッチし、適切にログ出力

```python
# 良い例
async def process_video(video_id: str, device_id: str) -> VideoProcessResult:
    """
    動画処理を実行する
    
    Args:
        video_id: 動画ID
        device_id: デバイスID
        
    Returns:
        VideoProcessResult: 処理結果
        
    Raises:
        ValueError: 動画IDが無効な場合
        DeviceNotFoundError: デバイスが見つからない場合
    """
    try:
        # 処理
        pass
    except SpecificError as e:
        logger.error(f"処理エラー: {e}")
        raise
```

### 命名規則

- **クラス**: PascalCase (`VideoService`, `DeviceManager`)
- **関数/メソッド**: snake_case (`get_video_info`, `start_preparation`)
- **定数**: UPPER_SNAKE_CASE (`MAX_CONNECTIONS`, `DEFAULT_TIMEOUT`)
- **プライベート**: アンダースコア接頭辞 (`_internal_method`)
- **型エイリアス**: PascalCase (`SessionID = str`)

### ディレクトリ構造の理解

```
backend/app/
├── main.py              # FastAPIアプリケーションエントリーポイント
├── api/                 # エンドポイント定義（REST & WebSocket）
├── models/              # Pydanticモデル（リクエスト/レスポンス）
├── services/            # ビジネスロジック（データ処理・外部連携）
└── config/              # 設定管理（環境変数・定数）
```

**ルール**:
- `api/`にはルーティングとバリデーションのみ記述
- ビジネスロジックは必ず`services/`に配置
- データモデルは`models/`で定義し再利用

---

## 環境設定の重要性

### 開発環境 vs 本番環境

コード生成時は**必ず環境による動作の違いを考慮**すること:

```python
from app.config.settings import settings

# ❌ 避けるべき
app = FastAPI(docs_url="/docs")

# ✅ 推奨
app = FastAPI(
    docs_url="/docs" if settings.is_development() else None
)
```

### 環境変数の扱い

- 機密情報（API KEY、SECRET_KEY）は**絶対にハードコーディングしない**
- すべて`settings.py`経由で取得
- デフォルト値は開発環境用、本番では環境変数で上書き

```python
# ✅ 正しい
from app.config.settings import settings
api_key = settings.external_api_key

# ❌ 間違い
api_key = "sk-1234567890abcdef"  # 絶対にNG
```

---

## WebSocket実装ガイドライン

### セッション管理の注意点

**重要**: 現在のセッション管理はインメモリであり、Cloud Runのスケール時に問題がある。

```python
# 現在の実装（暫定）
class SimpleWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}
```

**新しいWebSocketコードを書く際の注意**:
- セッション情報をインスタンス変数に保存する実装は避ける
- 将来的にRedis/Pub/Subへの移行を前提とした設計にする
- 接続切断時の再接続ロジックを考慮する

### 並列送信パターン

複数クライアントへのメッセージ送信は並列化すること:

```python
# ✅ 推奨: 並列送信
async def send_to_all(session_id: str, message: dict):
    tasks = []
    for conn_id in session_connections[session_id]:
        websocket = active_connections[conn_id]
        task = asyncio.create_task(websocket.send_text(json.dumps(message)))
        tasks.append(task)
    
    await asyncio.gather(*tasks, return_exceptions=True)

# ❌ 避ける: 順次送信
async def send_to_all_slow(session_id: str, message: dict):
    for conn_id in session_connections[session_id]:
        websocket = active_connections[conn_id]
        await websocket.send_text(json.dumps(message))  # 遅い
```

### エラーハンドリング

WebSocketの切断は正常な動作として扱う:

```python
try:
    while True:
        message = await websocket.receive_text()
        await handle_message(message)
except WebSocketDisconnect as e:
    if e.code == 1000:
        logger.info(f"正常切断: {connection_id}")
    else:
        logger.warning(f"異常切断: {connection_id}, code={e.code}")
finally:
    await cleanup_connection(connection_id)
```

---

## Pydanticモデルのベストプラクティス

### モデル設計

- **単一責任**: 1つのモデルは1つの目的のみ
- **再利用性**: 共通フィールドはBaseModelで継承
- **検証**: Field()でバリデーションルールを明示

```python
from pydantic import BaseModel, Field, field_validator

class VideoInfo(BaseModel):
    """動画情報モデル"""
    video_id: str = Field(..., min_length=1, description="動画ID")
    title: str = Field(..., min_length=1, max_length=200)
    duration_seconds: float = Field(..., gt=0, description="再生時間（秒）")
    
    @field_validator('video_id')
    @classmethod
    def validate_video_id(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('video_idは英数字のみ')
        return v
```

### レスポンスモデル

すべてのエンドポイントにresponse_modelを指定:

```python
@router.get("/videos/{video_id}", response_model=VideoDetailResponse)
async def get_video(video_id: str) -> VideoDetailResponse:
    # Pydanticが自動的にバリデーション
    return VideoDetailResponse(...)
```

---

## ログ出力の規則

### ログレベルの使い分け

- **DEBUG**: 開発時のデバッグ情報（本番では出力されない）
- **INFO**: 正常な処理フロー（起動、接続確立、処理完了）
- **WARNING**: 問題ではないが注意が必要（再試行、デフォルト値使用）
- **ERROR**: エラー発生（処理は継続可能）
- **CRITICAL**: 重大なエラー（サービス停止レベル）

```python
import logging
logger = logging.getLogger(__name__)

# 処理開始
logger.info(f"動画処理開始: video_id={video_id}")

# 警告
logger.warning(f"デバイス接続タイムアウト、再試行します: device_id={device_id}")

# エラー
logger.error(f"動画ファイル読み込み失敗: {e}", exc_info=True)
```

### 構造化ログ

重要な処理では構造化された情報を含める:

```python
logger.info(
    "WebSocket接続確立",
    extra={
        "session_id": session_id,
        "connection_id": connection_id,
        "client_ip": client.host
    }
)
```

---

## セキュリティ要件

### 必ず守るべきルール

1. **機密情報のハードコーディング禁止**
   - API KEY, SECRET_KEY, パスワードなどは環境変数
   
2. **入力値の検証**
   - すべての外部入力（API、WebSocket）はPydanticで検証
   
3. **SQLインジェクション対策**
   - 将来的にDB追加時、必ずパラメータ化クエリを使用
   
4. **CORS設定**
   - 本番環境では特定のオリジンのみ許可
   
5. **エラーメッセージ**
   - 本番環境では内部情報を含まない汎用メッセージ

```python
# ✅ 本番環境を考慮したエラーハンドリング
try:
    process_data(user_input)
except Exception as e:
    logger.error(f"処理エラー: {e}", exc_info=True)
    if settings.is_production():
        raise HTTPException(status_code=500, detail="処理中にエラーが発生しました")
    else:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 非同期処理のベストプラクティス

### async/awaitの使い分け

- **I/O処理**: 必ずasync (ファイル読み書き、DB、外部API)
- **CPU処理**: 通常の同期関数でOK
- **並列処理**: `asyncio.gather()` または `asyncio.create_task()`

```python
# ✅ 推奨: 並列実行
async def fetch_multiple_videos(video_ids: List[str]) -> List[VideoInfo]:
    tasks = [fetch_video(vid) for vid in video_ids]
    return await asyncio.gather(*tasks)

# ❌ 避ける: 順次実行
async def fetch_multiple_videos_slow(video_ids: List[str]) -> List[VideoInfo]:
    results = []
    for vid in video_ids:
        result = await fetch_video(vid)  # 1つずつ待つ
        results.append(result)
    return results
```

### リソースクリーンアップ

async contextmanagerを活用:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def websocket_connection(url: str):
    ws = await connect_websocket(url)
    try:
        yield ws
    finally:
        await ws.close()
        logger.info("WebSocket接続をクローズしました")
```

---

## テストの記述方針

### テストファイルの配置

```
tests/
├── test_api/              # APIエンドポイントのテスト
├── test_services/         # サービス層のテスト
└── test_models/           # Pydanticモデルのテスト
```

### pytest + pytest-asyncioを使用

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_video():
    """動画情報取得のテスト"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/videos/demo1")
        assert response.status_code == 200
        data = response.json()
        assert "video_id" in data
```

---

## コード生成時の優先順位

GitHub Copilotがコードを提案する際の優先順位:

1. **セキュリティ**: 機密情報の保護、入力検証
2. **型安全性**: 型ヒント、Pydanticモデル
3. **エラーハンドリング**: 適切な例外処理とログ出力
4. **パフォーマンス**: 非同期処理、並列実行
5. **可読性**: docstring、明確な変数名
6. **保守性**: 単一責任、DRY原則

---

## よくあるパターン

### APIエンドポイントの雛形

```python
from fastapi import APIRouter, HTTPException
from app.models.video import VideoRequest, VideoResponse
from app.services.video_service import video_service
import logging

router = APIRouter(prefix="/api/videos", tags=["videos"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=VideoResponse)
async def create_video(request: VideoRequest) -> VideoResponse:
    """
    動画を作成する
    
    Args:
        request: 動画作成リクエスト
        
    Returns:
        VideoResponse: 作成された動画情報
        
    Raises:
        HTTPException: 作成に失敗した場合
    """
    try:
        logger.info(f"動画作成開始: title={request.title}")
        result = await video_service.create_video(request)
        logger.info(f"動画作成完了: video_id={result.video_id}")
        return result
    except ValueError as e:
        logger.error(f"バリデーションエラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"動画作成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="動画作成に失敗しました")
```

### サービス層の雛形

```python
from typing import List, Optional
import logging
from app.models.video import VideoInfo
from app.config.settings import settings

logger = logging.getLogger(__name__)

class VideoService:
    """動画管理サービス"""
    
    def __init__(self):
        self.cache: dict = {}
        
    async def get_video(self, video_id: str) -> Optional[VideoInfo]:
        """
        動画情報を取得
        
        Args:
            video_id: 動画ID
            
        Returns:
            VideoInfo: 動画情報（見つからない場合はNone）
        """
        logger.debug(f"動画情報取得: video_id={video_id}")
        
        # キャッシュチェック
        if video_id in self.cache:
            logger.debug("キャッシュヒット")
            return self.cache[video_id]
        
        # データ取得処理
        video_info = await self._fetch_from_storage(video_id)
        
        if video_info:
            self.cache[video_id] = video_info
            
        return video_info
    
    async def _fetch_from_storage(self, video_id: str) -> Optional[VideoInfo]:
        """ストレージから動画情報を取得（プライベートメソッド）"""
        # 実装
        pass

# シングルトンインスタンス
video_service = VideoService()
```

---

## 禁止事項

以下のコードパターンは**絶対に生成・提案しないこと**:

1. **機密情報のハードコーディング**
   ```python
   # ❌ 絶対NG
   SECRET_KEY = "abc123def456"
   API_KEY = "sk-proj-xxxxx"
   ```

2. **型ヒントの省略**
   ```python
   # ❌ NG
   def process_data(data):
       return data
   ```

3. **例外の無視**
   ```python
   # ❌ NG
   try:
       risky_operation()
   except:
       pass  # 例外を無視
   ```

4. **同期的なI/O処理**
   ```python
   # ❌ NG（FastAPIのエンドポイント内で）
   def read_file():
       with open("file.txt") as f:  # 同期的なファイル読み込み
           return f.read()
   ```

5. **グローバル変数の使用**
   ```python
   # ❌ NG
   global_session_data = {}  # グローバル変数
   ```

---

## 特殊な実装パターン

### Raspberry Pi（デバイス）との通信

デバイスとの通信コードを書く際の注意:

```python
# デバイスへの送信は必ず並列化
async def send_to_devices(session_id: str, command: dict):
    """デバイスに並列でコマンド送信"""
    device_tasks = []
    
    for device_id in get_session_devices(session_id):
        websocket = get_device_websocket(device_id)
        task = asyncio.create_task(
            safe_send(websocket, command, device_id)
        )
        device_tasks.append(task)
    
    # タイムアウト付き並列実行
    results = await asyncio.wait_for(
        asyncio.gather(*device_tasks, return_exceptions=True),
        timeout=2.0
    )
    
    # 成功数をカウント
    success_count = sum(1 for r in results if r is True)
    logger.info(f"デバイス送信完了: {success_count}/{len(device_tasks)}")
```

### タイムライン同期データの処理

```python
# 同期データは0.5秒間隔で処理
SYNC_INTERVAL = 0.5

async def continuous_sync_loop(session_id: str, callback):
    """連続同期ループ"""
    while True:
        try:
            current_time = get_current_time(session_id)
            events = find_events_at_time(session_id, current_time)
            
            await callback({
                "currentTime": current_time,
                "events": events
            })
            
            await asyncio.sleep(SYNC_INTERVAL)
        except asyncio.CancelledError:
            logger.info("同期ループ停止")
            break
```

---

## まとめ

このプロジェクトでコードを生成・提案する際は:

- ✅ **型安全性**: 型ヒントとPydanticを活用
- ✅ **非同期処理**: async/awaitで並列実行を最大化
- ✅ **セキュリティ**: 機密情報は環境変数、入力は検証
- ✅ **エラー処理**: 適切な例外ハンドリングとログ出力
- ✅ **環境対応**: 開発/本番環境の違いを考慮
- ✅ **将来性**: Redis/Pub/Sub移行を前提とした設計

このガイドラインに従うことで、保守性が高く、スケーラブルで、セキュアなコードを生成できます。

---

## Google Cloud Runデプロイ手順

### 前提条件

- Google Cloud SDK (`gcloud`) がインストール済み
- Docker がインストール済み
- GCPプロジェクト `fourdk-home-2024` へのアクセス権限
- Artifact Registry リポジトリ `my-fastapi-repo` が存在すること

### デプロイ手順

#### 1. プロジェクト設定の確認

```bash
# 現在のプロジェクトIDを確認
gcloud config get-value project
# 出力: fourdk-home-2024
```

#### 2. Dockerイメージのビルド

```bash
# backendディレクトリに移動
cd backend

# Cloud Run用のDockerfileでイメージをビルド
docker build -f Dockerfile.cloudrun \
  -t asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest \
  .
```

**重要な設定**:
- イメージ名: `fdx-home-backend-api` (数字で始まる名前は使用不可のため)
- リポジトリ: `my-fastapi-repo` (既存のArtifact Registryリポジトリを使用)
- リージョン: `asia-northeast1`
- タグ: `latest`

#### 3. Artifact Registryへのプッシュ

```bash
# イメージをArtifact Registryにプッシュ
docker push asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest
```

#### 4. Cloud Runへのデプロイ

```bash
# Cloud Runサービスをデプロイ
gcloud run deploy fdx-home-backend-api \
  --image=asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest \
  --region=asia-northeast1 \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300s \
  --concurrency=80 \
  --max-instances=20 \
  --allow-unauthenticated
```

**デプロイ設定の詳細**:
- **サービス名**: `fdx-home-backend-api`
- **リージョン**: `asia-northeast1` (東京リージョン)
- **ポート**: `8080` (FastAPIのデフォルトポート)
- **メモリ**: `512Mi` (WebSocket接続を考慮)
- **CPU**: `1` (1vCPU)
- **タイムアウト**: `300s` (5分、WebSocket長時間接続対応)
- **並列度**: `80` (1インスタンスあたりの最大同時リクエスト数)
- **最大インスタンス数**: `20` (スケール制限)
- **認証**: `--allow-unauthenticated` (パブリックアクセス許可)

#### 5. デプロイ結果の確認

デプロイが成功すると、以下のURLでサービスが公開されます:

```
Service URL: https://fdx-home-backend-api-47te6uxkwa-an.a.run.app
```

**動作確認**:

```bash
# ヘルスチェック
curl https://fdx-home-backend-api-47te6uxkwa-an.a.run.app/health

# バージョン情報
curl https://fdx-home-backend-api-47te6uxkwa-an.a.run.app/api/version
```

### デプロイ後の設定更新

#### 環境変数ファイル (.env) の更新

デプロイ後、`backend/.env`ファイルのCloud Run URLを更新:

```properties
# === Cloud Run / GCP設定 ===
CLOUD_PROJECT_ID="fourdk-home-2024"
CLOUD_REGION="asia-northeast1"
BACKEND_API_URL="https://fdx-home-backend-api-47te6uxkwa-an.a.run.app"
BACKEND_WS_URL="wss://fdx-home-backend-api-47te6uxkwa-an.a.run.app"
```

### トラブルシューティング

#### リポジトリが存在しない場合

```bash
# Artifact Registryリポジトリを作成
gcloud artifacts repositories create my-fastapi-repo \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="FastAPI Backend Repository"
```

#### サービス設定の確認

```bash
# 現在のサービス設定を確認
gcloud run services describe fdx-home-backend-api \
  --region=asia-northeast1 \
  --format=json
```

#### ログの確認

```bash
# Cloud Runのログを確認
gcloud run services logs read fdx-home-backend-api \
  --region=asia-northeast1 \
  --limit=50
```

### 継続的デプロイメント

新しいバージョンをデプロイする場合は、手順2-4を繰り返します:

```bash
# 1. ビルド
docker build -f Dockerfile.cloudrun \
  -t asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest .

# 2. プッシュ
docker push asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest

# 3. デプロイ（設定は既存のものが保持される）
gcloud run deploy fdx-home-backend-api \
  --image=asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest \
  --region=asia-northeast1
```

### デプロイ履歴

- **2025年11月6日**: 初回デプロイ完了
  - サービス名: `fdx-home-backend-api`
  - イメージ: `asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest`
  - リビジョン: `fdx-home-backend-api-00006-4dw`
  - URL: `https://fdx-home-backend-api-47te6uxkwa-an.a.run.app`

- **2025年11月6日**: CORS設定更新（本番フロントエンド追加）
  - リビジョン: `fdx-home-backend-api-00008-8wc`
  - 追加オリジン: `https://kz-2504.onrender.com` (本番フロントエンド)
  - 設定ファイル: `backend/debug/.env.cloudrun`
