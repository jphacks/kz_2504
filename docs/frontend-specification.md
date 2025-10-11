# 4DX@HOME フロントエンド仕様書

## 1. フロントエンド概要

### 1.1 技術スタック
- **フレームワーク**: React 18.2+
- **言語**: TypeScript 5.0+
- **ビルドツール**: Vite 4.0+
- **スタイリング**: CSS Modules + Tailwind CSS
- **状態管理**: React Hooks (useState, useContext, useReducer)
- **通信**: WebSocket API (native browser API)

### 1.2 ブラウザサポート
- **Chrome**: 100+
- **Firefox**: 100+
- **Safari**: 15+
- **Edge**: 100+
- **モバイル**: iOS Safari 15+, Chrome Mobile 100+

### 1.3 レスポンシブ設計
- **デスクトップ**: 1024px以上（メイン対象）
- **タブレット**: 768px - 1023px
- **モバイル**: 320px - 767px（縦持ち想定）

## 2. アプリケーション構造

### 2.1 画面構成
```
App
├── WaitingScreen (待機画面)
│   ├── SessionCodeInput (セッションコード入力)
│   ├── ExperienceSelector (体験選択)
│   ├── ConnectionStatus (接続状態)
│   └── StartButton (開始ボタン)
└── PlayerScreen (再生画面)
    ├── VideoPlayer (動画プレイヤー)
    ├── PlaybackControls (再生制御)
    ├── SyncIndicator (同期状態表示)
    └── EmergencyStop (緊急停止)
```

### 2.2 状態管理
```typescript
// アプリケーション全体の状態
interface AppState {
  // 接続状態
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'error';
  websocket: WebSocket | null;
  
  // セッション情報
  sessionCode: string;
  sessionId: string | null;
  deviceStatus: DeviceStatus;
  
  // 体験設定
  experienceSettings: ExperienceSettings;
  
  // 動画・再生状態
  videoState: VideoState;
  syncState: SyncState;
  
  // UI状態
  currentScreen: 'waiting' | 'player';
  errorMessage: string | null;
}
```

## 3. 待機画面 (WaitingScreen)

### 3.1 画面レイアウト
```
┌─────────────────────────────────┐
│          4DX@HOME              │
│                                │
│  [セッションコード入力]         │
│  ┌─────────┐  [接続]          │
│  │  A4B7   │   ●接続中        │
│  └─────────┘                  │
│                                │
│  体験設定:                     │
│  ☑ 振動   ☐ 香り   ☐ 温度    │
│  ├─────────────────────┤      │
│  │ 強度: ████████░░ 80%  │      │
│  └─────────────────────┘      │
│                                │
│  デバイス状態:                 │
│  ● ハブ接続済み                │
│  ● 動画準備完了                │
│                                │
│     [スタート] (無効)          │
└─────────────────────────────────┘
```

### 3.2 SessionCodeInput コンポーネント
```typescript
interface SessionCodeInputProps {
  value: string;
  onChange: (code: string) -> void;
  onSubmit: () -> void;
  isLoading: boolean;
  error: string | null;
}

const SessionCodeInput: React.FC<SessionCodeInputProps> = ({
  value, onChange, onSubmit, isLoading, error
}) => {
  // 4文字の英数字コード入力
  // リアルタイム入力検証
  // Enter キーでの送信対応
};
```

### 3.3 ExperienceSelector コンポーネント
```typescript
interface ExperienceSettings {
  vibration: {
    enabled: boolean;
    intensity: number; // 0.0 - 1.0
  };
  scent: {
    enabled: boolean;
    type: 'floral' | 'citrus' | 'mint';
  };
  temperature: {
    enabled: boolean;
    range: 'cool' | 'warm';
  };
}

const ExperienceSelector: React.FC<{
  settings: ExperienceSettings;
  onChange: (settings: ExperienceSettings) -> void;
}> = ({ settings, onChange }) => {
  // チェックボックスによる体験ON/OFF
  // スライダーによる強度調整
  // 体験プレビュー機能
};
```

### 3.4 ConnectionStatus コンポーネント
```typescript
interface DeviceStatus {
  hub: 'disconnected' | 'connected' | 'error';
  actuators: {
    vibration: 'disconnected' | 'connected' | 'error';
    scent: 'disconnected' | 'connected' | 'error';
  };
  video: 'loading' | 'ready' | 'error';
}

const ConnectionStatus: React.FC<{
  status: DeviceStatus;
}> = ({ status }) => {
  // リアルタイムステータス表示
  // アイコン + テキストでの状態表現
  // エラー時の詳細情報表示
};
```

## 4. 再生画面 (PlayerScreen)

### 4.1 画面レイアウト
```
┌─────────────────────────────────┐
│  ┌─────────────────────────┐    │
│  │                         │    │
│  │       動画エリア        │    │
│  │                         │    │
│  └─────────────────────────┘    │
│                                │
│  ●─────○────────────── 02:34    │
│  [⏸] [⏭] 🔊 ████████░░         │
│                                │
│  同期状態: ●良好 (±15ms)        │
│  体験: 振動●  香り○            │
│                                │
│  [緊急停止]           [終了]    │
└─────────────────────────────────┘
```

### 4.2 VideoPlayer コンポーネント
```typescript
interface VideoPlayerProps {
  src: string;
  onTimeUpdate: (currentTime: number) -> void;
  onPlay: () -> void;
  onPause: () -> void;
  onSeek: (time: number) -> void;
  onError: (error: string) -> void;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src, onTimeUpdate, onPlay, onPause, onSeek, onError
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    
    // timeupdate イベントでリアルタイム同期
    const handleTimeUpdate = () => {
      onTimeUpdate(video.currentTime);
    };
    
    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [onTimeUpdate]);
};
```

### 4.3 PlaybackControls コンポーネント
```typescript
const PlaybackControls: React.FC<{
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  onPlayPause: () -> void;
  onSeek: (time: number) -> void;
  onVolumeChange: (volume: number) -> void;
}> = ({ isPlaying, currentTime, duration, volume, ...handlers }) => {
  // 再生/一時停止ボタン
  // シークバー（ドラッグ対応）
  // 音量調整スライダー
  // 全画面表示ボタン
};
```

### 4.4 SyncIndicator コンポーネント
```typescript
interface SyncStatus {
  quality: 'excellent' | 'good' | 'poor' | 'critical';
  latency: number; // ms
  lastSyncTime: number;
  packetsLost: number;
}

const SyncIndicator: React.FC<{
  syncStatus: SyncStatus;
  experienceStatus: Record<string, boolean>;
}> = ({ syncStatus, experienceStatus }) => {
  // 同期品質のビジュアル表示
  // 体験デバイスの動作状況
  // ネットワーク遅延情報
};
```

## 5. WebSocket通信

### 5.1 WebSocketService クラス
```typescript
class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  
  constructor(private url: string) {}
  
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.startHeartbeat();
        resolve();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket closed');
        this.scheduleReconnect();
      };
      
      this.ws.onmessage = (event) => {
        this.handleMessage(JSON.parse(event.data));
      };
    });
  }
  
  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(console.error);
    }, 3000);
  }
  
  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({ event: 'ping', data: {} });
    }, 30000);
  }
  
  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        ...message,
        timestamp: new Date().toISOString()
      }));
    }
  }
}
```

### 5.2 カスタムフック - useWebSocket
```typescript
const useWebSocket = (url: string) => {
  const [connectionState, setConnectionState] = 
    useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);
  const wsService = useRef<WebSocketService | null>(null);
  
  const connect = useCallback(async () => {
    setConnectionState('connecting');
    try {
      wsService.current = new WebSocketService(url);
      await wsService.current.connect();
      setConnectionState('connected');
    } catch (error) {
      setConnectionState('error');
      throw error;
    }
  }, [url]);
  
  const sendMessage = useCallback((message: any) => {
    wsService.current?.send(message);
  }, []);
  
  return {
    connectionState,
    connect,
    sendMessage,
    lastMessage
  };
};
```

## 6. 同期処理

### 6.1 同期送信ロジック
```typescript
const useSyncSender = (websocket: WebSocketService | null) => {
  const syncIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const startSync = useCallback((videoElement: HTMLVideoElement) => {
    if (syncIntervalRef.current) return;
    
    syncIntervalRef.current = setInterval(() => {
      if (websocket && !videoElement.paused) {
        websocket.send({
          event: 'playback_sync',
          data: {
            current_time: videoElement.currentTime,
            playback_rate: videoElement.playbackRate,
            state: videoElement.paused ? 'paused' : 'playing',
            buffer_health: getBufferHealth(videoElement)
          }
        });
      }
    }, 100); // 100ms間隔での送信
  }, [websocket]);
  
  const stopSync = useCallback(() => {
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }
  }, []);
  
  return { startSync, stopSync };
};
```

### 6.2 バッファヘルス計算
```typescript
const getBufferHealth = (video: HTMLVideoElement): number => {
  if (video.buffered.length === 0) return 0;
  
  const currentTime = video.currentTime;
  const bufferedEnd = video.buffered.end(video.buffered.length - 1);
  const duration = video.duration;
  
  if (duration === 0) return 0;
  
  const remainingTime = duration - currentTime;
  const bufferedAhead = bufferedEnd - currentTime;
  
  return Math.min(bufferedAhead / Math.min(remainingTime, 30), 1);
};
```

## 7. エラーハンドリング

### 7.1 エラー境界コンポーネント
```typescript
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<
  React.PropsWithChildren<{}>,
  ErrorBoundaryState
> {
  constructor(props: React.PropsWithChildren<{}>) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('React Error Boundary caught error:', error, errorInfo);
    // エラーレポート送信
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <ErrorScreen 
          error={this.state.error} 
          onReload={() => window.location.reload()} 
        />
      );
    }
    
    return this.props.children;
  }
}
```

### 7.2 エラー表示コンポーネント
```typescript
const ErrorScreen: React.FC<{
  error: Error | null;
  onReload: () -> void;
  onRetry?: () -> void;
}> = ({ error, onReload, onRetry }) => {
  const getErrorMessage = (error: Error | null) => {
    if (!error) return '予期しないエラーが発生しました';
    
    // エラーメッセージの日本語化
    const errorMap: Record<string, string> = {
      'NetworkError': 'ネットワークエラーが発生しました',
      'SecurityError': 'セキュリティエラーです',
      'NotAllowedError': 'アクセスが許可されていません'
    };
    
    return errorMap[error.name] || error.message;
  };
  
  return (
    <div className="error-screen">
      <h2>エラーが発生しました</h2>
      <p>{getErrorMessage(error)}</p>
      <div className="error-actions">
        {onRetry && <button onClick={onRetry}>再試行</button>}
        <button onClick={onReload}>ページを再読み込み</button>
      </div>
    </div>
  );
};
```

## 8. パフォーマンス最適化

### 8.1 メモ化戦略
```typescript
// 重い計算のメモ化
const MemoizedVideoPlayer = React.memo(VideoPlayer, (prevProps, nextProps) => {
  return prevProps.src === nextProps.src &&
         prevProps.isPlaying === nextProps.isPlaying;
});

// コールバック関数のメモ化
const PlayerScreen = () => {
  const handleTimeUpdate = useCallback((currentTime: number) => {
    // 同期送信処理
  }, []);
  
  const handlePlayPause = useCallback(() => {
    // 再生制御処理
  }, []);
};
```

### 8.2 遅延ローディング
```typescript
// 画面コンポーネントの遅延読み込み
const WaitingScreen = lazy(() => import('./components/WaitingScreen'));
const PlayerScreen = lazy(() => import('./components/PlayerScreen'));

const App = () => {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Router>
        <Routes>
          <Route path="/" element={<WaitingScreen />} />
          <Route path="/player" element={<PlayerScreen />} />
        </Routes>
      </Router>
    </Suspense>
  );
};
```

## 9. テスト戦略

### 9.1 ユニットテスト (Jest + Testing Library)
```typescript
// WebSocketService のテスト
describe('WebSocketService', () => {
  let wsService: WebSocketService;
  let mockWebSocket: jest.Mocked<WebSocket>;
  
  beforeEach(() => {
    mockWebSocket = createMockWebSocket();
    global.WebSocket = jest.fn(() => mockWebSocket);
    wsService = new WebSocketService('ws://localhost');
  });
  
  test('should connect successfully', async () => {
    const connectPromise = wsService.connect();
    mockWebSocket.onopen?.(new Event('open'));
    
    await expect(connectPromise).resolves.toBeUndefined();
  });
});
```

### 9.2 統合テスト
```typescript
// 同��処理の統合テスト
describe('Sync Integration', () => {
  test('should send sync data at correct intervals', async () => {
    const { result } = renderHook(() => useSyncSender(mockWebSocket));
    const mockVideo = createMockVideoElement();
    
    act(() => {
      result.current.startSync(mockVideo);
    });
    
    await waitFor(() => {
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        expect.objectContaining({
          event: 'playback_sync',
          data: expect.objectContaining({
            current_time: expect.any(Number)
          })
        })
      );
    });
  });
});
```

## 10. ビルド・デプロイ

### 10.1 Vite設定 (vite.config.ts)
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'es2020',
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          websocket: ['./src/services/WebSocketService']
        }
      }
    }
  },
  server: {
    host: true,
    port: 3000
  }
});
```

### 10.2 環境変数管理
```typescript
// src/config/env.ts
interface Config {
  websocketUrl: string;
  videoBaseUrl: string;
  syncInterval: number;
  heartbeatInterval: number;
}

const config: Config = {
  websocketUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
  videoBaseUrl: import.meta.env.VITE_VIDEO_BASE_URL || '/videos',
  syncInterval: 100,
  heartbeatInterval: 30000
};

export default config;
```

---

**更新日**: 2025年10月11日  
**バージョン**: 1.0  
**フロントエンド仕様策定者**: 4DX@HOME開発チーム