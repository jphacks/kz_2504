# 4DX@HOME フロントエンド仕様書 (AwardDay版)

**バージョン**: 2.0.0  
**作成日**: 2025年11月14日  
**対象イベント**: JPHACKS2025 AwardDay (2024年11月9日開催)  
**システム**: Render + Cloud Run統合版

---

## 概要

4DX@HOME フロントエンドは、Render上にデプロイされたReact + TypeScript + ViteベースのSPA（シングルページアプリケーション）です。Cloud Run APIと通信し、動画再生と4Dエフェクトの同期体験を提供します。

### システム構成

```
┌─────────────────────────────────────────┐
│  Frontend (React + Vite)                │
│  https://kz-2504.onrender.com           │
│                                         │
│  - HomePage (ランディング)               │
│  - PairingPage (デバイス登録)            │
│  - SelectPage (動画選択)                 │
│  - PlayerPage (再生・同期)               │
└─────────────────────────────────────────┘
               ↓ HTTPS/WSS
┌─────────────────────────────────────────┐
│  Cloud Run API (FastAPI)                │
│  asia-northeast1                        │
│  https://fdx-home-backend-api-...       │
└─────────────────────────────────────────┘
               ↓ WebSocket
┌─────────────────────────────────────────┐
│  Raspberry Pi Hub                       │
│  (Python Server)                        │
└─────────────────────────────────────────┘
               ↓ MQTT
┌─────────────────────────────────────────┐
│  ESP-12E Actuators                      │
│  (Vibration, Wind, Water, Flash, LED)   │
└─────────────────────────────────────────┘
```

---

## 技術スタック

### コアライブラリ
- **React** 18.2.0 - UIライブラリ
- **React Router DOM** 6.30.1 - SPA ルーティング
- **TypeScript** 5.0.0 - 型安全性

### ビルド・開発ツール
- **Vite** 5.0.0 - 高速ビルド・開発サーバー
- **@vitejs/plugin-react** 4.2.0 - React統合

### HTTP通信
- **Axios** 1.6.0 - REST APIクライアント

### WebSocket通信
- **WebSocket API** (ネイティブ) - リアルタイム同期

---

## デプロイ情報

### Render構成

```yaml
サービス名: kz-2504
タイプ: Static Site
ビルドコマンド: npm install && npm run build
公開ディレクトリ: dist
URL: https://kz-2504.onrender.com
```

### 環境変数 (.env)

```env
# === Cloud Run API URLs ===
VITE_BACKEND_API_URL=https://fdx-home-backend-api-xxxxxxxxxxxx.asia-northeast1.run.app
VITE_BACKEND_WS_URL=wss://fdx-home-backend-api-xxxxxxxxxxxx.asia-northeast1.run.app

# === 本番フロー用セッションID ===
VITE_PRODUCTION_SESSION_ID=demo1

# === デフォルトセッションID (デモ用) ===
VITE_DEFAULT_SESSION_ID=demo_session
```

**重要**: Viteは `VITE_` プレフィックスの環境変数のみクライアントに公開します。

---

## 画面構成

### 1. HomePage - ホーム画面

**パス**: `/`

**目的**: キャッチコピー表示・サービス紹介

**主要機能**:
- サービスロゴ・キャッチコピー表示
- 「体験を始める」ボタン → PairingPageへ遷移
- システム概要の簡易説明

**スクリーンショット**: ![Home](../assets/images/home.png)

---

### 2. PairingPage - デバイス登録画面

**パス**: `/session`

**目的**: デバイスハブ製品コード入力・登録

**主要機能**:
- **デバイスハブ製品コード入力**
  - `DH001`: 4DX Home Basic (振動・風・水)
  - `DH002`: 4DX Home Standard (Basic + フラッシュ)
  - `DH003`: 4DX Home Premium (Standard + カラーLED)
- **「接続」ボタン**: `/api/device/register` エンドポイント呼び出し
- **接続状態表示**: 成功/失敗メッセージ
- **次へボタン**: SelectPageへ遷移

**実装例**:
```typescript
const handleRegister = async () => {
  try {
    const response = await axios.post(`${BACKEND_API_URL}/api/device/register`, {
      product_code: productCode // "DH001", "DH002", "DH003"
    });
    
    setDeviceId(response.data.device_id);
    setCapabilities(response.data.capabilities);
    setRegistered(true);
  } catch (error) {
    console.error('デバイス登録失敗:', error);
  }
};
```

**スクリーンショット**: ![Session](../assets/images/session.png)

---

### 3. SelectPage - 動画選択画面

**パス**: `/selectpage`

**目的**: 視聴可能動画の一覧表示・選択

**主要機能**:
- **動画一覧表示**: `/api/videos/available` から取得
- **カテゴリフィルター**: アクション、ホラー、アドベンチャー等
- **サムネイル表示**: 400×225px (16:9)
- **4DX対応バッジ**: エフェクト対応マーク
- **動画選択**: クリックで詳細表示 → 「準備画面へ進む」ボタン
- **ランキング表示** (予定): 人気順・評価順

**サンプル動画**:
- `demo1`: アクション映画 (120秒、24イベント)
- `demo2`: 自然ドキュメンタリー (90秒、18イベント)

**実装例**:
```typescript
useEffect(() => {
  const fetchVideos = async () => {
    const response = await axios.get(`${BACKEND_API_URL}/api/videos/available`);
    setVideos(response.data.videos);
  };
  fetchVideos();
}, []);
```

**スクリーンショット**: ![Select](../assets/images/select.png)

---

### 4. PlayerPage - 動画再生画面

**パス**: `/player`

**目的**: 動画再生・リアルタイム同期・4Dエフェクト体験

**主要機能**:
- **HTML5 Video再生**: ネイティブコントロール
- **WebSocket接続**: 500ms間隔で同期データ送信
- **再生/一時停止コントロール**: カスタムUIボタン
- **シークバー**: 再生位置調整
- **音量コントロール**: 0-100%調整
- **フルスクリーンボタン**: デスクトップ/モバイル対応
- **4DXエフェクト状態表示** (デバッグ用): 現在のエフェクト可視化
- **ストップ処理**: 一時停止・動画終了時に全アクチュエーター停止

**WebSocket同期メッセージ**:
```typescript
const sendSyncMessage = () => {
  if (wsClient?.isConnected()) {
    wsClient.send({
      type: 'sync',
      state: isPlaying ? 'play' : 'pause',
      time: currentTime,
      currentTime: currentTime,
      duration: duration,
      ts: Date.now()
    });
  }
};

// 500ms間隔で送信
useEffect(() => {
  if (isPlaying) {
    const interval = setInterval(sendSyncMessage, 500);
    return () => clearInterval(interval);
  }
}, [isPlaying, currentTime]);
```

**ストップ処理 (AwardDay追加機能)**:
```typescript
const handlePause = async () => {
  setIsPlaying(false);
  videoRef.current?.pause();
  
  // 同期インターバルをクリア
  if (syncIntervalRef.current) {
    clearInterval(syncIntervalRef.current);
    syncIntervalRef.current = null;
  }

  // ストップ信号送信 (REST API)
  try {
    console.log('🛑 ストップ信号送信中...');
    const response = await playbackApi.sendStopSignal(sessionId);
    console.log('✅ ストップ信号送信完了:', response);
  } catch (error) {
    console.error('❌ ストップ信号送信エラー:', error);
  }
  
  // WebSocketでもストップ信号送信 (二重送信で確実性向上)
  if (wsClientRef.current?.isConnected()) {
    wsClientRef.current.send({
      type: 'stop_signal',
      session_id: sessionId,
      timestamp: Date.now(),
    });
    console.log('📤 WebSocketストップ信号送信完了');
  }
};

const handleEnded = async () => {
  setIsPlaying(false);
  
  // 同期インターバルをクリア
  if (syncIntervalRef.current) {
    clearInterval(syncIntervalRef.current);
    syncIntervalRef.current = null;
  }

  // ストップ信号送信
  try {
    console.log('🎬 動画終了: ストップ信号送信中...');
    const response = await playbackApi.sendStopSignal(sessionId);
    console.log('✅ 終了時ストップ信号送信完了:', response);
  } catch (error) {
    console.error('❌ 終了時ストップ信号送信エラー:', error);
  }
  
  // WebSocketでもストップ信号送信
  if (wsClientRef.current?.isConnected()) {
    wsClientRef.current.send({
      type: 'stop_signal',
      session_id: sessionId,
      timestamp: Date.now(),
    });
    console.log('📤 WebSocket終了時ストップ信号送信完了');
  }

  // 2秒後にページ遷移
  setTimeout(() => {
    navigate('/selectpage'); // 動画選択画面へ戻る
  }, 2000);
};
```

**スクリーンショット**: ![Player](../assets/images/player.png)

---

## ルーティング構成

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/session" element={<PairingPage />} />
        <Route path="/selectpage" element={<SelectPage />} />
        <Route path="/player" element={<PlayerPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

## WebSocket通信プロトコル

### エンドポイント

```
wss://fdx-home-backend-api-xxxxxxxxxxxx.asia-northeast1.run.app/api/playback/ws/sync/{sessionId}
```

### 接続フロー

1. **接続確立**: WebSocketコンストラクタでURL指定
2. **接続成功**: `onopen` イベント発火
3. **同期開始**: 500ms間隔で `sync` メッセージ送信
4. **ACK受信**: サーバーから `sync_ack` 受信
5. **切断**: `onclose` イベント → 自動再接続 (リトライ3回)

### メッセージ形式

#### Client → Server (同期メッセージ)

```json
{
  "type": "sync",
  "state": "play",
  "time": 45.2,
  "currentTime": 45.2,
  "duration": 120.0,
  "ts": 1731571200000
}
```

**フィールド説明**:
- `type`: メッセージタイプ (固定値: `"sync"`)
- `state`: 再生状態 (`"play"` | `"pause"` | `"seeking"` | `"seeked"`)
- `time`: 現在の再生位置 (秒、小数点以下2桁)
- `currentTime`: 同上 (互換性のため)
- `duration`: 動画総尺 (秒)
- `ts`: 送信時刻 (UNIXタイムスタンプ、ミリ秒)

#### Server → Client (同期ACK)

```json
{
  "type": "sync_ack",
  "session_id": "demo1",
  "received_state": "play",
  "server_time": "2025-11-14T12:00:00.789Z",
  "relayed_to_devices": true
}
```

#### Client → Server (ストップ信号) **[NEW]**

```json
{
  "type": "stop_signal",
  "session_id": "demo1",
  "timestamp": 1731571200000
}
```

#### Server → Client (ストップACK) **[NEW]**

```json
{
  "type": "stop_signal_ack",
  "session_id": "demo1",
  "success": true,
  "sent_to_devices": 2,
  "message": "ストップ信号を2台のデバイスに送信しました"
}
```

---

## REST API統合

### APIクライアント構成 (endpoints.ts)

```typescript
import axios from 'axios';

const BACKEND_API_URL = import.meta.env.VITE_BACKEND_API_URL;

const apiClient = axios.create({
  baseURL: BACKEND_API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// デバイス管理API
export const deviceApi = {
  register: (productCode: string) =>
    apiClient.post<DeviceRegistrationResponse>('/api/device/register', {
      product_code: productCode,
    }),
  getInfo: (productCode: string) =>
    apiClient.get<DeviceInfo>(`/api/device/info/${productCode}`),
  getCapabilities: () =>
    apiClient.get<CapabilitiesResponse>('/api/device/capabilities'),
};

// 動画管理API
export const videoApi = {
  getAvailable: () =>
    apiClient.get<AvailableVideosResponse>('/api/videos/available'),
  getDetail: (videoId: string) =>
    apiClient.get<VideoDetail>(`/api/videos/${videoId}`),
  select: (videoId: string, deviceId: string) =>
    apiClient.post<VideoSelectResponse>('/api/videos/select', {
      video_id: videoId,
      device_id: deviceId,
    }),
};

// 準備処理API
export const preparationApi = {
  start: (sessionId: string) =>
    apiClient.post<PreparationStartResponse>(`/api/preparation/start/${sessionId}`, {}),
  getStatus: (sessionId: string) =>
    apiClient.get<PreparationStatus>(`/api/preparation/status/${sessionId}`),
  stop: (sessionId: string) =>
    apiClient.delete<PreparationStopResponse>(`/api/preparation/stop/${sessionId}`),
};

// 再生制御API [NEW - AwardDay]
export const playbackApi = {
  sendStartSignal: (sessionId: string) =>
    apiClient.post<any>(`/api/playback/start/${sessionId}`, {}),
  sendStopSignal: (sessionId: string) =>
    apiClient.post<any>(`/api/playback/stop/${sessionId}`, {}),
  getStatus: () =>
    apiClient.get<any>('/api/playback/status'),
  getConnections: () =>
    apiClient.get<any>('/api/playback/connections'),
};
```

---

## セッションID管理

### 2種類のID

4DX@HOMEシステムでは、以下2種類のIDを使い分けます:

#### 1. デバイスハブ製品コード (大文字)

**用途**: 物理的なデバイスハブを識別

**形式**: `DH001`, `DH002`, `DH003`

**使用箇所**:
- `/api/device/register` エンドポイント
- PairingPage での入力フィールド

#### 2. 本番フロー用セッションID (小文字)

**用途**: WebSocket接続・タイムライン管理

**形式**: `demo1`, `demo2`, `session_xyz789` 等

**使用箇所**:
- `/api/playback/ws/sync/{sessionId}` エンドポイント
- `/api/preparation/upload-timeline/{sessionId}` エンドポイント
- 環境変数 `VITE_PRODUCTION_SESSION_ID`

### セッションID取得方法

```typescript
const sessionId = import.meta.env.VITE_PRODUCTION_SESSION_ID || 'demo1';
```

---

## エラーハンドリング

### ネットワークエラー

```typescript
try {
  const response = await axios.post('/api/device/register', data);
} catch (error) {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      // サーバーエラー (4xx, 5xx)
      console.error('サーバーエラー:', error.response.status, error.response.data);
      alert(`エラー: ${error.response.data.detail || error.response.data.message}`);
    } else if (error.request) {
      // ネットワークエラー (タイムアウト等)
      console.error('ネットワークエラー:', error.message);
      alert('サーバーに接続できません。ネットワーク接続を確認してください。');
    }
  }
}
```

### WebSocketエラー

```typescript
wsClient.on('error', (error) => {
  console.error('WebSocketエラー:', error);
  setWsStatus('error');
});

wsClient.on('close', (code, reason) => {
  console.warn(`WebSocket切断: code=${code}, reason=${reason}`);
  setWsStatus('disconnected');
  
  // 自動再接続 (最大3回)
  if (reconnectAttempts < 3) {
    setTimeout(() => {
      reconnectWebSocket();
    }, 2000 * (reconnectAttempts + 1)); // 指数バックオフ
  }
});
```

---

## パフォーマンス最適化

### 1. WebSocket送信間隔

**目標**: 500ms固定

**実装**:
```typescript
useEffect(() => {
  if (isPlaying) {
    const interval = setInterval(() => {
      sendSyncMessage();
    }, 500); // 500ms固定
    
    return () => clearInterval(interval);
  }
}, [isPlaying, currentTime]);
```

### 2. 動画プリロード

```typescript
<video
  ref={videoRef}
  preload="metadata" // メタデータのみプリロード
  onCanPlay={() => setVideoReady(true)}
>
  <source src={videoUrl} type="video/mp4" />
</video>
```

### 3. 状態管理最適化

```typescript
// React.memoでコンポーネント再レンダリング抑制
const VideoControls = React.memo(({ isPlaying, onPlayPause }) => {
  return (
    <button onClick={onPlayPause}>
      {isPlaying ? '⏸️ 一時停止' : '▶️ 再生'}
    </button>
  );
});

// useMemoで計算結果をキャッシュ
const formattedTime = useMemo(() => {
  return formatTime(currentTime);
}, [currentTime]);
```

---

## ビルド・デプロイ

### ローカル開発

```bash
# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
# http://localhost:5173 でアクセス
```

### プロダクションビルド

```bash
# ビルド実行
npm run build
# dist/ ディレクトリに成果物生成

# プレビュー
npm run preview
# http://localhost:4173 でプレビュー
```

### Renderデプロイ

**自動デプロイ**: GitHub連携でmainブランチへのpushで自動ビルド・デプロイ

**手動デプロイ**: Renderダッシュボードから「Manual Deploy」実行

**環境変数設定**: Renderダッシュボード → Environment → 環境変数追加

---

## デバッグツール

### debug_frontend

**URL**: http://localhost:5173 (ローカル起動時)

**用途**: Cloud Run API動作確認・WebSocketテスト

**主要機能**:
- **動画選択画面**: サンプル動画一覧表示
- **動画準備画面**: 4ステップ準備プロセス
  1. デバイス接続 (製品コード入力)
  2. 動画読み込み (自動)
  3. タイムライン送信 (JSON読み込み→API送信)
  4. デバイステスト (アクチュエーター動作確認)
- **再生画面**: WebSocket同期テスト

**起動方法**:
```bash
cd debug_frontend
npm install
npm run dev
```

---

## トラブルシューティング

### 1. 動画再生されない

**症状**: 黒い画面のまま

**原因**: 動画ファイル未配置

**解決策**:
```bash
# FFmpegでテスト動画生成
ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=120 \
  -c:v libx264 -pix_fmt yuv420p public/videos/demo1.mp4
```

### 2. WebSocket接続失敗

**症状**: `WebSocket: ❌ 未接続`

**原因**: セッションID不一致、Cloud Run未起動

**確認項目**:
- `.env`の`VITE_PRODUCTION_SESSION_ID`が設定されているか
- Cloud Run APIが稼働しているか (`/health` にアクセス)
- ブラウザコンソールでWebSocketエラーログを確認

### 3. デバイス登録失敗

**症状**: `デバイス接続失敗: 404`

**原因**: 製品コード間違い、API未起動

**解決策**:
- 製品コードを確認 (`DH001`, `DH002`, `DH003`)
- Cloud Run APIの `/api/device/register` エンドポイントが有効か確認

### 4. CORS エラー

**症状**: `Access to fetch at '...' has been blocked by CORS policy`

**原因**: Cloud Run側のCORS設定にフロントエンドURLが未登録

**解決策**:
1. `backend/app/config/settings.py` の `cors_origins` を確認
2. `.env` に `https://kz-2504.onrender.com` を追加
3. Cloud Runを再デプロイ

---

## AwardDay以降の変更点

### 追加機能

1. **ストップ処理統合**
   - 一時停止時: REST API + WebSocket で二重送信
   - 動画終了時: 全アクチュエーター自動停止
   - 2秒待機後、動画選択画面へ自動遷移

2. **セッションID分離管理**
   - デバイスハブ製品コード (大文字)
   - 本番フロー用セッションID (小文字)
   - `.env`ファイルで設定可能

3. **エラーハンドリング強化**
   - ネットワークエラー検出・表示
   - WebSocket自動再接続 (最大3回)
   - ユーザーフレンドリーなエラーメッセージ

### 改善点

- WebSocket再接続ロジック: 指数バックオフ採用
- 動画終了時の自動遷移: UX向上
- デバッグログ: コンソール出力強化

---

## 今後の拡張予定

- [ ] ユーザー認証 (JWT)
- [ ] 視聴履歴・お気に入り
- [ ] レスポンシブデザイン (モバイル最適化)
- [ ] 動画評価・コメント機能
- [ ] 検索機能 (タイトル・カテゴリ)
- [ ] 倍速再生対応
- [ ] ストリーミング再生 (HLS/DASH)
- [ ] PWA対応 (オフライン視聴)

---

## 関連ドキュメント

- [バックエンド仕様書](./backend-specification-awardday.md)
- [ハードウェア仕様書](./hardware-specification-awardday.md)
- [本番フロー仕様](../debug_frontend/PRODUCTION_FLOW_SETUP.md)
- [ストップ処理仕様](../debug_frontend/STOP_SIGNAL_SPEC.md)

---

**変更履歴**:

| 日付 | バージョン | 変更内容 |
|-----|----------|---------|
| 2025-11-14 | 2.0.0 | AwardDay後の実装を反映した仕様書作成 |
