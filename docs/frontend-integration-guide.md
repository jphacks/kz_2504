# フロントエンド実装ガイド

## 必要な依存関係
```bash
npm install
# WebSocket通信は標準のWebSocket APIを使用
# 追加ライブラリ不要
```

## WebSocket接続実装例

### 1. WebSocket接続クラス
```typescript
class FourDXWebSocket {
  private ws: WebSocket | null = null;
  private clientId: string;
  private sessionCode: string | null = null;

  constructor(clientId: string) {
    this.clientId = clientId;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`ws://127.0.0.1:8001/ws/${this.clientId}`);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        resolve();
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };
      
      this.ws.onerror = (error) => {
        reject(error);
      };
    });
  }

  joinSession(sessionCode: string): void {
    this.sessionCode = sessionCode;
    this.send({
      type: 'join_session',
      session_code: sessionCode
    });
  }

  sendSyncData(syncData: any): void {
    this.send({
      type: 'sync_data',
      session_code: this.sessionCode,
      data: syncData
    });
  }

  private send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private handleMessage(data: any): void {
    switch (data.type) {
      case 'session_joined':
        console.log('セッション参加完了:', data.session_code);
        break;
      case 'sync_data':
        // 同期データを受信時の処理
        this.onSyncDataReceived(data.data);
        break;
    }
  }

  private onSyncDataReceived(data: any): void {
    // 映像同期処理をここに実装
    console.log('同期データ受信:', data);
  }
}
```

### 2. React Hook実装例
```typescript
import { useState, useEffect, useRef } from 'react';

export function useFourDXConnection(clientId: string) {
  const [connected, setConnected] = useState(false);
  const [sessionCode, setSessionCode] = useState<string | null>(null);
  const wsRef = useRef<FourDXWebSocket | null>(null);

  useEffect(() => {
    wsRef.current = new FourDXWebSocket(clientId);
    
    wsRef.current.connect()
      .then(() => setConnected(true))
      .catch(console.error);

    return () => {
      wsRef.current?.disconnect();
    };
  }, [clientId]);

  const joinSession = async (code: string) => {
    wsRef.current?.joinSession(code);
    setSessionCode(code);
  };

  const createSession = async () => {
    const response = await fetch('http://127.0.0.1:8001/api/session/create', {
      method: 'POST'
    });
    const data = await response.json();
    return data.session_code;
  };

  return { connected, sessionCode, joinSession, createSession };
}
```

## セッション管理の流れ
1. **セッション作成**: `POST /api/session/create` でコード取得
2. **WebSocket接続**: `/ws/{client_id}` に接続
3. **セッション参加**: `join_session` メッセージ送信
4. **同期データ送受信**: `sync_data` でリアルタイム通信