# バックエンド実装分析 - 現在の状況と新仕様対応

## 📊 現在のバックエンド実装状況

### ✅ **依然必要な既存機能**

#### 1. **セッション管理システム** (継続利用)
**ファイル**: `app/api/phase1.py`, `app/models/session_models.py`
**機能**:
- セッション作成: `POST /api/sessions`
- セッション情報取得: `GET /api/sessions/{session_id}`
- セッション削除: `DELETE /api/sessions/{session_id}`

**新仕様での位置づけ**:
- デバイス登録後のセッション作成に利用
- 既存のセッション管理機能をそのまま活用

#### 2. **WebSocket通信基盤** (継続利用)
**ファイル**: `app/main.py`, `app/websocket/manager.py`
**機能**:
- デバイス専用WebSocket: `/ws/device/{session_id}`
- Webアプリ専用WebSocket: `/ws/webapp/{session_id}`
- リアルタイム双方向通信

**新仕様での位置づけ**:
- 準備状況の双方向通信
- リアルタイム再生同期通信
- 完全に継続利用

#### 3. **動画・同期データ管理** (部分的継続)
**ファイル**: `app/services/video_service.py`, `app/api/phase1.py`
**機能**:
- 動画リスト取得: `GET /api/videos`
- 同期データ取得: `GET /api/sync-data/{video_id}`

**新仕様での位置づけ**:
- 動画選択画面での動画リスト表示
- 待機画面でのJSONファイル配信

#### 4. **基本API構造** (継続利用)
**ファイル**: `app/main.py`, `app/config/`
**機能**:
- FastAPI基盤
- CORS設定
- ログ設定
- 環境設定管理

---

### ❌ **不要になる既存機能**

#### 1. **レガシーWebSocket** (削除対象)
**ファイル**: `app/main.py` の `websocket_endpoint`
**理由**: 
- 新仕様では専用エンドポイント（`/ws/device`, `/ws/webapp`）を使用
- 混在による複雑性排除

#### 2. **開発用テスト機能** (削除対象)
**ファイル**: `app/main.py` の `/test` エンドポイント
**理由**:
- 本番環境で不要
- 新しいテスト基盤を別途構築

---

### 🆕 **新規実装が必要な機能**

#### 1. **デバイス登録・認証API** (新規)
**実装場所**: `app/api/device_registration.py`
**エンドポイント**: `POST /api/device/register`

```python
# 必要な新規実装
@router.post("/api/device/register")
async def register_device(product_code: str):
    # 製品コード検証
    # デバイス情報取得
    # 認証トークン発行
    pass
```

**依存ファイル**:
- `app/models/device.py` - デバイスモデル定義
- `app/services/device_service.py` - デバイス管理ロジック
- `backend/data/devices.json` - 製品コードマスタ

#### 2. **動画管理拡張API** (新規)
**実装場所**: `app/api/video_management.py`
**エンドポイント**:
- `GET /api/videos/available?device_id={device_id}`
- `POST /api/videos/select`

```python
# 必要な新規実装
@router.get("/api/videos/available")
async def get_available_videos(device_id: str):
    # デバイス対応動画フィルタリング
    # 準備状況確認
    pass

@router.post("/api/videos/select") 
async def select_video(video_id: str, device_id: str):
    # 動画選択処理
    # 準備プロセス開始
    pass
```

#### 3. **準備処理制御API** (新規)
**実装場所**: `app/api/preparation.py`
**エンドポイント**:
- `GET /api/sessions/{session_id}/preparation-status`
- `POST /api/sessions/{session_id}/start-preparation`

```python
# 必要な新規実装
@router.get("/api/sessions/{session_id}/preparation-status")
async def get_preparation_status(session_id: str):
    # 動画プリロード状況
    # JSON配信状況
    # デバイス通信テスト状況
    pass
```

**依存ファイル**:
- `app/services/preparation_service.py` - 準備処理ロジック
- `app/models/preparation.py` - 準備状況モデル

#### 4. **強化された同期データ配信** (拡張)
**実装場所**: 既存の `app/api/phase1.py` を拡張

```python
# 既存機能の拡張
@router.post("/api/sessions/{session_id}/sync-data")
async def upload_sync_data_enhanced(session_id: str, sync_data_request: dict):
    # デバイス側での事前準備用JSON送信
    # アクチュエーターテスト指示
    pass
```

---

## 🔄 **実装優先順位と依存関係**

### Phase 1: 基盤拡張 (1-2日)
```
1. デバイスモデル定義 (app/models/device.py)
   ↓
2. 製品コードマスタ作成 (backend/data/devices.json)  
   ↓
3. デバイス認証API実装 (app/api/device_registration.py)
```

### Phase 2: 動画管理拡張 (1日)
```
4. 動画管理API拡張 (app/api/video_management.py)
   ↓
5. VideoService強化 (app/services/video_service.py)
```

### Phase 3: 準備処理制御 (2-3日)
```
6. 準備処理サービス実装 (app/services/preparation_service.py)
   ↓
7. 準備処理API実装 (app/api/preparation.py)
   ↓
8. WebSocket拡張 (準備状況通知)
```

### Phase 4: 統合・テスト (1日)
```
9. 既存機能クリーンアップ
   ↓
10. 統合テスト実装
   ↓
11. デプロイメント
```

---

## 📂 **新規ファイル構成**

### 追加が必要なファイル
```
backend/
├── app/
│   ├── api/
│   │   ├── device_registration.py     # NEW - デバイス登録API
│   │   ├── video_management.py        # NEW - 動画管理API拡張
│   │   └── preparation.py             # NEW - 準備処理API
│   ├── models/
│   │   ├── device.py                  # NEW - デバイスモデル
│   │   ├── video.py                   # NEW - 動画モデル拡張
│   │   └── preparation.py             # NEW - 準備処理モデル
│   └── services/
│       ├── device_service.py          # NEW - デバイス管理サービス
│       ├── preparation_service.py     # NEW - 準備処理サービス
│       └── video_service.py           # EXTEND - 既存拡張
└── data/
    └── devices.json                   # NEW - 製品コードマスタ
```

### 修正が必要なファイル
```
backend/
├── app/
│   ├── main.py                        # MODIFY - レガシー削除
│   ├── api/phase1.py                  # EXTEND - 機能拡張
│   └── models/schemas.py              # EXTEND - スキーマ追加
```

---

## 🛠️ **技術的考慮事項**

### 1. **後方互換性**
- 既存のセッション管理APIは維持
- WebSocket エンドポイントは段階的移行
- 既存テストコードの動作保証

### 2. **パフォーマンス**
- 準備処理の並列実行
- WebSocket接続の効率化
- データベース不使用による高速化

### 3. **セキュリティ**
- 製品コード認証の強化
- セッション管理の堅牢化
- 不正アクセス防止

### 4. **エラーハンドリング**
- 準備失敗時のリトライ機構
- 通信断絶時の自動復旧
- ユーザーフレンドリーなエラーメッセージ

---

## 📋 **実装チェックリスト**

### ✅ 既存機能保持
- [x] セッション管理API
- [x] WebSocket基盤
- [x] 動画・同期データ取得
- [x] 基本設定・ログ機能

### 🔄 拡張実装
- [ ] デバイス登録・認証API
- [ ] 動画管理API拡張
- [ ] 準備処理制御API
- [ ] 強化された同期データ配信

### ❌ 削除対象
- [ ] レガシーWebSocketエンドポイント
- [ ] 開発用テスト機能
- [ ] 不要なデバッグコード

---

**最終目標**: 新仕様に完全対応しつつ、既存機能の安定性を保持したバックエンドシステムの完成

**推定実装時間**: 5-7日
**リスク**: 既存機能への影響を最小化しながらの段階的実装が必要