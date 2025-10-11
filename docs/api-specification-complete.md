# 4DX@HOME API 仕様書

## API エンドポイント一覧

### Base URL
```
Production: https://fourdk-backend-333203798555.asia-northeast1.run.app
Development: http://localhost:8001
```

---

## セッション管理 API

### 1. セッション作成
**POST** `/api/session/create`

デバイス登録またはユーザー主導でのセッション作成

#### Request Headers
```
Content-Type: application/json
User-Agent: RaspberryPi-4DX/{device_id} | 4DX-WebApp/{user_id}
```

#### Request Body (デバイス登録時)
```json
{
  "product_code": "DH001",
  "capabilities": ["vibration", "motion", "scent", "audio", "lighting"],
  "device_info": {
    "version": "2.1.0",
    "ip_address": "192.168.1.100", 
    "device_id": "raspi-4dx-hub-001",
    "hardware_type": "raspberry_pi_4b",
    "serial_number": "RPI4B8G2024001",
    "firmware_version": "1.4.2"
  }
}
```

#### Request Body (フロントエンド主導時)
```json
{
  "user_initiated": true,
  "user_info": {
    "user_id": "user_12345",
    "device_type": "web_browser",
    "browser": "Chrome 120.0",
    "screen_resolution": "1920x1080"
  }
}
```

#### Response (Success - 200)
```json
{
  "session_code": "A7JZKG",
  "message": "Session A7JZKG created successfully"
}
```

#### Response (Error - 400/500)
```json
{
  "detail": "Invalid request data"
}
```

---

### 2. セッション情報取得
**GET** `/api/session/{session_code}`

セッションの詳細情報を取得

#### Path Parameters
- `session_code` (string): 6文字の英数字セッションコード

#### Request Headers
```
User-Agent: RaspberryPi-4DX/{device_id} | 4DX-WebApp/{user_id}
```

#### Response (Success - 200)
```json
{
  "session_code": "A7JZKG",
  "session_data": {
    "created_at": "2025-10-11T12:07:16.138447",
    "clients": [],
    "status": "waiting",
    "device_connected": true,
    "last_activity": "2025-10-11T12:10:30.000000"
  }
}
```

#### Response (Error - 404)
```json
{
  "detail": "Session not found"
}
```

---

## システム情報 API

### 3. ヘルスチェック
**GET** `/health`

API サーバーの稼働状態確認

#### Response (Success - 200)
```json
{
  "status": "healthy",
  "service": "4DX@HOME Backend API", 
  "version": "1.0.0",
  "timestamp": "2025-10-11T12:07:15.294495"
}
```

---

### 4. システム情報
**GET** `/`

システムの基本情報と稼働状況

#### Response (Success - 200)
```json
{
  "service": "4DX@HOME Backend API",
  "status": "running",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2025-10-11T12:07:15.503808",
  "active_sessions": 3,
  "endpoints": {
    "api_docs": "/docs",
    "sessions": "/api/sessions", 
    "health": "/api/health"
  }
}
```

---

### 5. API仕様書
**GET** `/docs`

Swagger UI による対話的API仕様書

#### Response
HTML形式のSwagger UIページ

---

## 通信プロトコル詳細

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|--------|
| 200 | OK | 正常な応答 |
| 400 | Bad Request | 不正なリクエストデータ |
| 404 | Not Found | リソースが見つからない |
| 500 | Internal Server Error | サーバー内部エラー |
| 503 | Service Unavailable | サービス利用不可 |

### Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/session/create` | 10 requests | 1 minute |
| `/api/session/{code}` | 60 requests | 1 minute |
| `/health` | 120 requests | 1 minute |

### Authentication

現在の実装では認証は不要ですが、将来的にAPI Keyまたはセッションベース認証を導入予定。

---

## WebSocket 通信仕様（将来実装）

### 接続エンドポイント

#### デバイス側
```
wss://api-domain/ws/device/{session_code}
```

#### フロントエンド側  
```
wss://api-domain/ws/webapp/{session_code}
```

### メッセージ形式

#### 接続確立
```json
{
  "type": "connection_established",
  "client_type": "device" | "webapp",
  "session_code": "A7JZKG", 
  "message": "接続確立",
  "timestamp": "2025-10-11T12:07:15.000000"
}
```

#### 同期コマンド (Frontend → Device)
```json
{
  "type": "sync_command",
  "command": {
    "command_type": "vibration",
    "intensity": 75,
    "duration": 2000,
    "video_time": 45.2
  },
  "timestamp": "2025-10-11T12:07:15.000000"
}
```

#### 実行フィードバック (Device → Frontend)
```json
{
  "type": "execution_feedback", 
  "command_id": "sync_cmd_001",
  "status": "completed",
  "actual_intensity": 75,
  "actual_duration": 2000,
  "timestamp": "2025-10-11T12:07:17.500000"
}
```

#### デバイス状態更新
```json
{
  "type": "device_status",
  "device_id": "raspi-4dx-hub-001",
  "status": "ready",
  "actuators": {
    "vibration": {"status": "ready", "last_intensity": 0},
    "motion": {"status": "ready", "position": 0},
    "scent": {"status": "ready", "active_cartridge": null},
    "audio": {"status": "ready", "volume": 50}
  },
  "system": {
    "cpu_temp": 45.2,
    "memory_usage": 65.3,
    "uptime": "2d 14h 23m"
  },
  "timestamp": "2025-10-11T12:07:15.000000"
}
```

---

## エラーレスポンス形式

### 標準エラーレスポンス
```json
{
  "detail": "Error description",
  "error_code": "SESSION_NOT_FOUND",
  "timestamp": "2025-10-11T12:07:15.000000",
  "request_id": "req_12345abcde"
}
```

### バリデーションエラー
```json
{
  "detail": [
    {
      "loc": ["body", "device_info", "ip_address"],
      "msg": "invalid IP address format",
      "type": "value_error"
    }
  ]
}
```

---

## セッションライフサイクル

```
1. [Device] POST /api/session/create
   └─→ Session Created (status: "waiting")

2. [Frontend] GET /api/session/{code}  
   └─→ Session Joined (status: "active")

3. [Frontend] Send sync commands
   [Device] Execute actuator commands
   [Device] Send execution feedback

4. [Both] Periodic status monitoring
   └─→ GET /api/session/{code}

5. Session Timeout or Explicit End
   └─→ Session Ended (status: "ended")
```

---

## 実装例

### TypeScript (Frontend)

```typescript
// セッション参加
const response = await fetch(`${BASE_URL}/api/session/${sessionCode}`, {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'User-Agent': '4DX-WebApp/1.0.0'
  }
});

if (response.ok) {
  const sessionInfo = await response.json();
  console.log('セッション参加成功:', sessionInfo);
} else {
  console.error('セッション参加失敗:', response.status);
}
```

### Python (Raspberry Pi)

```python
# デバイス登録
import aiohttp

async def register_device():
    device_data = {
        "product_code": "DH001",
        "capabilities": ["vibration", "motion", "scent", "audio"],
        "device_info": {
            "version": "2.1.0",
            "ip_address": "192.168.1.100",
            "device_id": "raspi-4dx-hub-001",
            "hardware_type": "raspberry_pi_4b"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/session/create",
            json=device_data,
            headers={"User-Agent": "RaspberryPi-4DX/hub-001"}
        ) as response:
            
            if response.status == 200:
                data = await response.json()
                session_code = data["session_code"]
                print(f"デバイス登録成功: {session_code}")
                return session_code
            else:
                print(f"デバイス登録失敗: {response.status}")
                return None
```

---

## モニタリング・ログ

### ログ形式
```
[2025-10-11 12:07:15] INFO: セッション作成: A7JZKG (device: raspi-4dx-hub-001)
[2025-10-11 12:07:16] INFO: フロントエンド接続: A7JZKG (user: user_12345)
[2025-10-11 12:07:20] INFO: 同期コマンド: A7JZKG vibration(75%, 2000ms)
[2025-10-11 12:07:22] INFO: 実行完了: A7JZKG vibration → success
```

### パフォーマンスメトリクス
- API レスポンス時間: < 300ms (95%ile)
- セッション作成成功率: > 99%
- 同時接続セッション数: < 1000
- メモリ使用量: < 512MB

---

## セキュリティ

### HTTPS強制
- 本番環境では全通信がHTTPS/WSS
- 開発環境でのHTTP通信のみ許可

### CORS設定
```json
{
  "allow_origins": ["*"],
  "allow_methods": ["GET", "POST", "PUT", "DELETE"],
  "allow_headers": ["*"],
  "allow_credentials": true
}
```

### セッション管理
- セッションコードは6文字の英数字
- 1時間の無活動で自動タイムアウト
- 最大同時セッション数制限

この仕様書により、フロントエンド（TypeScript）とラズベリーパイ（Python）の両方で統一された実装が可能になります。