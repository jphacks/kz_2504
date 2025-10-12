# 🌐 4DX@HOME 通信仕様書 - フロントエンドエンジニア向け（最新版）

**最終更新**: 2025年10月12日 09:47 JST  
**対象**: TypeScript/React フロントエンド実装者  
**システム状況**: ✅ **本番環境稼働中**

## 🚀 **現在のデプロイ状況**

### **バックエンドURL**
- **本番環境**: `https://fourdk-backend-333203798555.asia-northeast1.run.app` ✅ **稼働中**
- **開発環境**: `http://localhost:8004` (ローカル開発用)

### **システム稼働状況**
- ✅ **API稼働**: 15エンドポイント全て正常動作
- ✅ **WebSocket**: `wss://fourdk-backend-333203798555.asia-northeast1.run.app` 対応
- ✅ **CORS設定**: フロントエンド接続準備完了
- ⚠️ **API Docs**: 本番環境では無効化（セキュリティ設定）
- ✅ **SSL/TLS**: 暗号化通信対応

---

## 📋 **実装概要**

### 🎯 **フロントエンド実装要件**
1. **デバイス登録画面**: 製品コード入力（6文字以内）
2. **動画選択画面**: 利用可能動画一覧表示・選択
3. **準備進捗画面**: リアルタイム準備状況表示
4. **動画再生画面**: HTML5プレイヤー + WebSocket同期
5. **エフェクト表示**: 4Dエフェクト状態のビジュアル表示

---

## 🔌 **REST API 仕様**

### **Base URL**
```
本番: https://fourdk-backend-333203798555.asia-northeast1.run.app/api
開発: http://localhost:8004/api
```

### **1. システム情報 API**

#### **API情報取得**
```http
GET /version
```

**レスポンス**:
```json
{
  "api_version": "1.0.0",
  "environment": "production DEBUG=false LOG_LEVEL=INFO",
  "supported_endpoints": [
    "/",
    "/health", 
    "/api/version",
    "/api/device/register",
    "/api/device/info/{product_code}",
    "/api/device/capabilities",
    "/api/videos/available",
    "/api/videos/{video_id}",
    "/api/videos/select",
    "/api/videos/categories/list",
    "/api/preparation/start/{session_id}",
    "/api/preparation/status/{session_id}",
    "/api/preparation/stop/{session_id}",
    "/api/preparation/ws/{session_id}",
    "/api/preparation/health"
  ],
  "documentation": "disabled"
}
```

### **2. デバイス管理 API**

#### **製品コード認証**
```http
POST /device/register
Content-Type: application/json

{
  "product_code": "DH001"
}
```

**⚠️ 重要**: `product_code`は**6文字以内**の制限があります。

**レスポンス**:
```json
{
  "device_id": "device_da7a949e",
  "device_name": "4DX Home Basic",
  "capabilities": ["VIBRATION", "MOTION", "AUDIO"],
  "status": "registered",
  "registered_at": "2025-10-12T00:47:33.589510",
  "session_timeout": 60
}
```

#### **デバイス能力一覧**
```http
GET /device/capabilities
```

**レスポンス**:
```json
{
  "supported_capabilities": ["VIBRATION", "WATER", "WIND", "FLASH", "COLOR"],
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

#### **デバイス情報取得**
```http
GET /device/info/{product_code}
```

**レスポンス例**:
```json
{
  "device_id": "device_da7a949e",
  "device_type": "basic",
  "tier": "Basic",
  "capabilities": ["VIBRATION", "MOTION", "AUDIO"],
  "status": "registered",
  "last_seen": "2025-10-12T00:47:33Z"
}
```

### **3. 動画管理 API**

#### **利用可能動画一覧**
```http
GET /videos/available
```

**現在のレスポンス**:
```json
{
  "videos": [],
  "total_count": 0,
  "available_count": 0,
  "device_id": null,
  "filter_applied": false
}
```

**⚠️ 注意**: 現在動画コンテンツは空です。テスト用動画の追加が必要です。

#### **動画選択・セッション開始**
```http
POST /videos/select
Content-Type: application/json

{
  "video_id": "demo1",
  "session_id": "session_abc123"
}
```

#### **動画カテゴリ一覧**
```http
GET /videos/categories/list
```

### **4. 準備処理 API**

#### **準備開始**
```http
POST /preparation/start/{session_id}
Content-Type: application/json

{
  "force_restart": false
}
```

#### **準備状態取得**
```http
GET /preparation/status/{session_id}
```

#### **準備停止**
```http
DELETE /preparation/stop/{session_id}
```

#### **準備処理ヘルスチェック**
```http
GET /preparation/health
```

---

## 🔄 **WebSocket 通信仕様**

### **接続エンドポイント**

#### **準備進捗監視**
```
wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/preparation/ws/{session_id}
```

#### **動画同期（最重要）**
```
wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/playback/ws/sync/{session_id}
```

### **WebSocket メッセージ形式**

#### **1. 接続確立時**
**受信メッセージ**:
```json
{
  "type": "connection_established",
  "connection_id": "frontend_session_abc123_094733",
  "session_id": "session_abc123",
  "server_time": "2025-10-12T00:47:33.123456",
  "message": "WebSocket接続が確立されました"
}
```

#### **2. 動画同期メッセージ（送信）**
**HTML5動画プレイヤーから100ms間隔で送信**:
```json
{
  "type": "sync",
  "state": "play",              // "play" | "pause" | "seeking" | "seeked"
  "time": 15.234,              // 現在の再生位置（秒）
  "duration": 30.0,            // 動画の総時間（秒）
  "ts": 1728747453123          // クライアント送信タイムスタンプ（ms）
}
```

#### **3. 同期応答（受信）**
```json
{
  "type": "sync_ack",
  "session_id": "session_abc123",
  "received_time": 15.234,
  "received_state": "play",
  "server_time": "2025-10-12T00:47:33.345678",
  "relayed_to_devices": true
}
```

---

## 🎮 **実装例（TypeScript）**

### **本番環境用APIクライアント**
```typescript
interface ApiClient {
  baseUrl: string;
}

class FourDXApiClient implements ApiClient {
  // 本番環境URL使用
  baseUrl = 'https://fourdk-backend-333203798555.asia-northeast1.run.app/api';

  async getSystemInfo() {
    const response = await fetch(`${this.baseUrl}/version`);
    return response.json();
  }

  async registerDevice(productCode: string) {
    // 6文字制限に注意
    if (productCode.length > 6) {
      throw new Error('Product code must be 6 characters or less');
    }

    const response = await fetch(`${this.baseUrl}/device/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_code: productCode })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Registration failed: ${error.detail}`);
    }
    
    return response.json();
  }

  async getDeviceCapabilities() {
    const response = await fetch(`${this.baseUrl}/device/capabilities`);
    return response.json();
  }

  async getAvailableVideos() {
    const response = await fetch(`${this.baseUrl}/videos/available`);
    return response.json();
  }

  async selectVideo(videoId: string, sessionId: string) {
    const response = await fetch(`${this.baseUrl}/videos/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, session_id: sessionId })
    });
    return response.json();
  }

  async startPreparation(sessionId: string, forceRestart = false) {
    const response = await fetch(`${this.baseUrl}/preparation/start/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_restart: forceRestart })
    });
    return response.json();
  }

  async getPreparationStatus(sessionId: string) {
    const response = await fetch(`${this.baseUrl}/preparation/status/${sessionId}`);
    return response.json();
  }
}
```

### **WebSocket同期クライアント（本番環境対応）**
```typescript
class VideoSyncClient {
  private ws: WebSocket | null = null;
  private video: HTMLVideoElement;
  private sessionId: string;
  private syncInterval: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(video: HTMLVideoElement, sessionId: string) {
    this.video = video;
    this.sessionId = sessionId;
  }

  connect(): void {
    // 本番環境WSS使用
    const wsUrl = `wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/playback/ws/sync/${this.sessionId}`;
    
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('✅ WebSocket接続成功（本番環境）');
        this.reconnectAttempts = 0;
        this.startSyncLoop();
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('📨 同期応答:', data);
        
        if (data.type === 'sync_ack') {
          // 同期確認処理
          this.handleSyncAcknowledgment(data);
        }
      };

      this.ws.onclose = (event) => {
        console.log(`🔌 WebSocket接続終了: ${event.code}`);
        this.stopSyncLoop();
        
        // 自動再接続（本番環境では重要）
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          setTimeout(() => {
            console.log(`🔄 再接続試行 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            this.connect();
          }, 1000 * this.reconnectAttempts); // 指数バックオフ
        }
      };

      this.ws.onerror = (error) => {
        console.error('❌ WebSocketエラー:', error);
      };

    } catch (error) {
      console.error('❌ WebSocket接続失敗:', error);
    }
  }

  private startSyncLoop(): void {
    this.syncInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const message = {
          type: 'sync',
          state: this.video.paused ? 'pause' : 'play',
          time: this.video.currentTime,
          duration: this.video.duration || 0,
          ts: Date.now()
        };
        
        this.ws.send(JSON.stringify(message));
      }
    }, 100); // 100ms間隔（重要）
  }

  private stopSyncLoop(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  private handleSyncAcknowledgment(data: any): void {
    // 同期確認データの処理
    console.log(`🎯 同期確認: ${data.received_state} at ${data.received_time}s`);
  }

  disconnect(): void {
    this.stopSyncLoop();
    if (this.ws) {
      this.ws.close(1000, '正常終了');
      this.ws = null;
    }
  }
}
```

---

## ⚡ **重要な実装ポイント**

### **1. 本番環境対応**
- **HTTPS/WSS必須**: 本番環境は暗号化通信のみ
- **エラーハンドリング**: ネットワーク断絶・再接続機能必須
- **製品コード制限**: 6文字以内の制限に注意

### **2. パフォーマンス**
- **WebSocket再接続**: 指数バックオフで自動再接続
- **同期精度**: 100ms間隔送信を維持
- **メモリ管理**: 適切なリソース解放

### **3. セキュリティ**
- **CORS対応**: 本番環境でCORS設定済み
- **入力検証**: 製品コード長などの制限確認
- **エラー情報**: 詳細エラー情報を適切に処理

---

## 🔍 **テスト方法**

### **本番環境での動作確認**
```bash
# システム情報確認
curl https://fourdk-backend-333203798555.asia-northeast1.run.app/api/version

# デバイス登録テスト
curl -X POST -H "Content-Type: application/json" \
  -d '{"product_code": "DH001"}' \
  https://fourdk-backend-333203798555.asia-northeast1.run.app/api/device/register

# 能力確認
curl https://fourdk-backend-333203798555.asia-northeast1.run.app/api/device/capabilities
```

### **統合テストシナリオ**
1. **デバイス登録** → **動画一覧取得** → **動画選択**
2. **準備処理開始** → **WebSocket接続** → **同期テスト**
3. **エラー処理** → **再接続** → **復旧確認**

---

## 📊 **現在の制約事項**

### **⚠️ 注意が必要な点**
1. **動画コンテンツ**: 現在空のため、テスト用動画の追加が必要
2. **製品コード**: 6文字制限の厳格な検証
3. **API Documentation**: 本番環境では無効化済み
4. **セッション管理**: 60秒のタイムアウト設定

### **✅ 正常動作確認済み**
1. **API全エンドポイント**: 15個全て稼働中
2. **デバイス登録**: 正常な登録フロー
3. **WebSocket基盤**: 接続・メッセージ送受信
4. **CORS設定**: フロントエンド接続準備完了

---

**実装完了目標**: 3-5日  
**担当者**: フロントエンドエンジニア  
**サポート**: バックエンドエンジニア（本番環境での通信テスト・デバッグ支援）  
**本番環境**: ✅ **即座利用可能**