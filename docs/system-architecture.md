# 4DX@HOME システム設計書

## 1. システム設計概要

### 1.1 アーキテクチャ概要
4DX@HOMEは、Webアプリ、GCPサーバー、デバイスハブ（ラズパイ）、アクチュエーター（Arduino）の4層構成で、WebSocket通信によるリアルタイム同期システムを実現します。

### 1.2 設計原則
- **低遅延**: 50ms以内での同期精度実現
- **可用性**: 自動再接続機能による高可用性
- **拡張性**: モジュラー設計による機能追加容易性
- **セキュリティ**: WSS通信による安全な通信経路
- **運用性**: ログ・監視機能による運用支援

## 2. システム全体構成図

```mermaid
graph TB
    subgraph "User Environment"
        User[ユーザー]
        WebApp[Webアプリ<br/>React/TypeScript]
        Device[4DX@HOMEデバイス]
    end
    
    subgraph "Cloud Infrastructure"
        GCP[GCPサーバー<br/>FastAPI/WebSocket]
        LB[Load Balancer]
        Monitor[監視・ログ]
    end
    
    subgraph "Device Hardware"
        RaspberryPi[ラズパイ<br/>デバイスハブ]
        Arduino[Arduino<br/>制御基板]
        Actuators[アクチュエーター<br/>振動・香り等]
    end
    
    User --> WebApp
    WebApp -.WSS.-> LB
    LB --> GCP
    GCP --> Monitor
    GCP -.WSS.-> RaspberryPi
    RaspberryPi -.USB Serial.-> Arduino
    Arduino --> Actuators
    Actuators -.物理フィードバック.-> User
```

## 3. 詳細シーケンス図

### 3.1 システム初期化・セッション確立

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant W as Webアプリ
    participant S as GCPサーバー
    participant R as ラズパイ
    participant A as Arduino
    
    Note over U, A: システム起動フェーズ
    
    U->>R: デバイス電源ON
    activate R
    R->>R: OS起動・Python実行
    R->>A: USB Serial接続確立
    activate A
    A-->>R: Ready信号応答
    
    R->>S: WebSocket接続要求
    activate S
    S->>S: セッションコード生成(A4B7)
    S-->>R: セッション作成完了 + コード通知
    R->>R: コンソールにコード表示
    deactivate R
    
    Note over U, A: ペアリングフェーズ
    
    U->>W: Webアプリアクセス
    activate W
    W->>W: 待機画面表示
    U->>W: セッションコード入力(A4B7)
    W->>S: WebSocket接続 + ペアリング要求
    
    S->>S: コード照合・クライアント紐付け
    S-->>W: ペアリング成功 + デバイス状態
    S-->>R: Webアプリ接続通知
    
    W->>W: 動画プリロード開始
    W-->>U: 接続完了・体験設定画面表示
    
    Note over U, A: 準備完了フェーズ
    
    U->>W: 体験設定選択(振動:ON, 香り:OFF)
    U->>W: スタートボタンクリック
    W->>S: セッション開始要求 + 設定情報
    S->>S: 同期データ読み込み
    S-->>W: 開始準備完了
    W->>W: 再生画面遷移
    W-->>U: 動画再生開始
    
    deactivate W
    deactivate S
    deactivate A
```

### 3.2 リアルタイム同期処理

```mermaid
sequenceDiagram
    participant W as Webアプリ
    participant V as Video要素
    participant S as GCPサーバー
    participant R as ラズパイ
    participant A as Arduino
    participant M as 振動モーター
    
    Note over W, M: 動画再生中の継続的同期
    
    loop 100ms間隔での同期送信
        V->>W: timeupdate イベント
        W->>W: currentTime取得 (例:10.48s)
        W->>S: 同期データ送信
        Note right of W: {"event":"playback_sync",<br/>"data":{"current_time":10.48}}
        
        S->>S: 同期イベント検索
        Note right of S: 10.5s地点の振動イベント発見
        
        alt 同期イベントが存在し、ユーザー設定ON
            S->>R: アクチュエーター制御コマンド
            Note right of S: {"event":"actuator_command",<br/>"action":"vibrate",<br/>"intensity":0.8, "duration":500}
            
            R->>R: JSONコマンド解析
            R->>A: シリアルコマンド送信
            Note right of R: "v,80,500\n"
            
            A->>A: コマンドパース・実行
            A->>M: PWM信号出力 (80%強度)
            activate M
            M-->>A: 振動実行中
            
            Note over A, M: 500ms経過後
            A->>M: PWM信号停止
            deactivate M
            
            A-->>R: 実行完了応答
            R-->>S: コマンド実行確認
        else 同期イベントなし or 設定OFF
            Note right of S: 何も送信しない
        end
    end
```

### 3.3 エラー処理・再接続シーケンス

```mermaid
sequenceDiagram
    participant W as Webアプリ
    participant S as GCPサーバー
    participant R as ラズパイ
    
    Note over W, R: 正常通信中
    W->>S: 同期データ送信
    S->>R: 制御コマンド
    
    Note over W, R: ネットワーク障害発生
    W-xS: 接続断
    S-xR: 接続断
    
    par Webアプリ側再接続
        W->>W: WebSocket onclose検知
        W->>W: 再接続タイマー開始(3秒)
        Note right of W: 接続エラー画面表示
        
        loop 再接続試行
            W->>S: 再接続試行
            alt 接続成功
                S-->>W: 接続確立
                W->>W: エラー画面解除
                W->>S: セッション復旧要求
            else 接続失敗
                W->>W: 3秒待機後リトライ
            end
        end
    and ラズパイ側再接続
        R->>R: WebSocket onclose検知
        R->>R: 再接続タイマー開始(3秒)
        
        loop 再接続試行
            R->>S: 再接続試行
            alt 接続成功
                S-->>R: 接続確立
                R->>S: デバイス再登録
                S-->>R: セッション復旧
            else 接続失敗
                R->>R: 3秒待機後リトライ
            end
        end
    end
    
    Note over W, R: 双方向接続復旧後
    S-->>W: デバイス接続復旧通知
    S-->>R: Webアプリ接続復旧通知
    W->>W: 正常画面復帰
```

## 4. 状態遷移図

### 4.1 Webアプリケーション状態遷移

```mermaid
stateDiagram-v2
    [*] --> Initializing: アプリ起動
    
    Initializing --> WaitingForCode: 初期化完了
    note right of Initializing
        - React初期化
        - 設定読み込み
        - UI描画
    end note
    
    WaitingForCode --> Connecting: コード入力・送信
    note right of WaitingForCode
        - セッションコード入力待ち
        - 体験設定UI表示
    end note
    
    Connecting --> WaitingForCode: ペアリング失敗
    Connecting --> WaitingForReady: ペアリング成功
    note right of Connecting
        - WebSocket接続中
        - サーバー通信
    end note
    
    WaitingForReady --> ReadyToStart: 全準備完了
    note right of WaitingForReady
        - デバイス接続確認
        - 動画プリロード
        - 体験設定確認
    end note
    
    ReadyToStart --> Playing: スタートボタン
    note right of ReadyToStart
        - スタートボタン有効化
        - 最終設定確認
    end note
    
    Playing --> Paused: 一時停止
    Playing --> Playing: シーク操作
    Paused --> Playing: 再生再開
    note right of Playing
        - 動画再生中
        - リアルタイム同期送信
        - 体験デバイス制御
    end note
    
    state ErrorStates {
        NetworkError: ネットワークエラー
        DeviceError: デバイスエラー
        VideoError: 動画エラー
    }
    
    Connecting --> NetworkError: 接続失敗
    WaitingForReady --> DeviceError: デバイス異常
    Playing --> VideoError: 動画エラー
    Paused --> VideoError: 動画エラー
    
    NetworkError --> Connecting: 再接続
    DeviceError --> WaitingForReady: エラー解決
    VideoError --> ReadyToStart: リロード
    
    Playing --> [*]: セッション終了
    Paused --> [*]: セッション終了
```

### 4.2 デバイスハブ（ラズパイ）状態遷移

```mermaid
stateDiagram-v2
    [*] --> Booting: 電源ON
    
    Booting --> InitializingHardware: OS起動完了
    note right of Booting
        - ラズパイOS起動
        - サービス開始
    end note
    
    InitializingHardware --> ConnectingToServer: ハードウェア初期化完了
    note right of InitializingHardware
        - Arduino接続確立
        - GPIO初期化
        - ステータス確認
    end note
    
    ConnectingToServer --> WaitingForPairing: サーバー接続・登録完了
    note right of ConnectingToServer
        - WebSocket接続
        - デバイス登録
        - セッションコード取得
    end note
    
    WaitingForPairing --> Ready: Webアプリペアリング完了
    note right of WaitingForPairing
        - セッションコード表示
        - ペアリング待機
    end note
    
    Ready --> Active: セッション開始
    note right of Ready
        - 接続確認完了
        - 制御準備完了
    end note
    
    Active --> Active: 制御コマンド受信・実行
    note right of Active
        - リアルタイム制御
        - Arduino通信
        - ステータス監視
    end note
    
    state ErrorStates {
        HardwareError: ハードウェアエラー
        NetworkError: ネットワークエラー
        ArduinoError: Arduino通信エラー
    }
    
    InitializingHardware --> HardwareError: 初期化失敗
    ConnectingToServer --> NetworkError: 接続失敗
    Active --> ArduinoError: Serial通信エラー
    
    HardwareError --> InitializingHardware: 復旧試行
    NetworkError --> ConnectingToServer: 再接続
    ArduinoError --> InitializingHardware: ハードウェア再初期化
    
    Active --> WaitingForPairing: セッション終了
    Ready --> WaitingForPairing: タイムアウト
```

### 4.3 Arduino制御装置状態遷移

```mermaid
stateDiagram-v2
    [*] --> PowerOn: 電源投入
    
    PowerOn --> Initializing: setup()実行
    note right of PowerOn
        - マイコン起動
        - メモリ初期化
    end note
    
    Initializing --> Idle: 初期化完了
    note right of Initializing
        - GPIO設定
        - シリアル通信開始
        - モーター停止状態
    end note
    
    Idle --> ProcessingCommand: コマンド受信
    note right of Idle
        - シリアル監視中
        - モーター停止
        - ステータスLED OFF
    end note
    
    ProcessingCommand --> Vibrating: 振動コマンド
    ProcessingCommand --> Idle: 無効コマンド
    ProcessingCommand --> Idle: stopコマンド
    note right of ProcessingCommand
        - コマンド解析
        - パラメータ検証
    end note
    
    Vibrating --> Idle: 振動時間完了
    Vibrating --> Idle: 緊急停止
    note right of Vibrating
        - PWM出力中
        - タイマー監視
        - ステータスLED ON
    end note
    
    state ErrorStates {
        SerialError: シリアル通信エラー
        MotorError: モーターエラー
    }
    
    ProcessingCommand --> SerialError: 通信異常
    Vibrating --> MotorError: モーター異常
    
    SerialError --> Idle: エラークリア
    MotorError --> Idle: 安全停止
    
    Vibrating --> [*]: システム終了
    Idle --> [*]: システム終了
```

## 5. データフロー図

### 5.1 同期データフロー

```mermaid
flowchart TD
    subgraph "データ生成"
        VideoFile[動画ファイル] --> VideoPlayer[HTML5 Video]
        SyncJSON[同期データJSON] --> SyncEngine[同期エンジン]
    end
    
    subgraph "リアルタイム処理"
        VideoPlayer --> TimerEvent[timeupdate<br/>100ms間隔]
        TimerEvent --> SyncPacket[同期パケット生成]
        SyncPacket --> WebSocket[WebSocket送信]
    end
    
    subgraph "サーバー処理"
        WebSocket --> SessionMgr[セッション管理]
        SessionMgr --> SyncEngine
        SyncEngine --> EventFilter[イベント抽出]
        EventFilter --> UserSettings[ユーザー設定適用]
        UserSettings --> CommandGen[制御コマンド生成]
    end
    
    subgraph "デバイス制御"
        CommandGen --> DeviceWS[デバイスWebSocket]
        DeviceWS --> SerialCmd[シリアルコマンド]
        SerialCmd --> HardwareCtrl[ハードウェア制御]
        HardwareCtrl --> PhysicalOutput[物理出力]
    end
    
    subgraph "フィードバック"
        PhysicalOutput --> UserExperience[ユーザー体験]
        UserExperience --> VideoPlayer
    end
```

### 5.2 メッセージフロー詳細

```mermaid
graph LR
    subgraph "Webアプリ → サーバー"
        A1[timeupdate] --> A2[currentTime: 10.48]
        A2 --> A3[sync message]
        A3 --> A4[WebSocket送信]
    end
    
    subgraph "サーバー処理"
        B1[メッセージ受信] --> B2[セッション特定]
        B2 --> B3[同期データ照合]
        B3 --> B4{イベント存在?}
        B4 -->|Yes| B5[ユーザー設定確認]
        B4 -->|No| B9[何もしない]
        B5 --> B6{設定有効?}
        B6 -->|Yes| B7[制御コマンド生成]
        B6 -->|No| B9
        B7 --> B8[デバイスへ送信]
    end
    
    subgraph "デバイス → Arduino"
        C1[WebSocketメッセージ] --> C2[JSON解析]
        C2 --> C3[シリアル文字列変換]
        C3 --> C4[USB Serial送信]
    end
    
    subgraph "Arduino処理"
        D1[シリアル受信] --> D2[コマンド解析]
        D2 --> D3[PWM制御]
        D3 --> D4[タイマー設定]
        D4 --> D5[モーター駆動]
    end
```

## 6. エラーハンドリング設計

### 6.1 エラー分類と対応戦略

| エラーレベル | エラー種別 | 検出方法 | 対応戦略 | 復旧方法 |
|--------------|------------|----------|----------|----------|
| Critical | サーバーダウン | WebSocket接続失敗 | 即座にエラー表示 | 自動再接続 |
| High | デバイス切断 | ハートビート応答なし | デバイスエラー表示 | 手動再接続 |
| Medium | 同期ずれ | タイムスタンプ比較 | 警告表示・補正 | 自動補正 |
| Low | 一時的通信遅延 | レスポンス遅延 | 内部で吸収 | 自動リトライ |

### 6.2 エラー検出・通知フロー

```mermaid
sequenceDiagram
    participant W as Webアプリ
    participant S as サーバー
    participant R as ラズパイ
    
    Note over W, R: エラー監視・検出
    
    loop ヘルスチェック
        W->>S: Ping送信
        S-->>W: Pong応答
        
        S->>R: Ping送信
        alt 正常応答
            R-->>S: Pong応答
        else タイムアウト
            S->>S: デバイス異常検出
            S-->>W: device_error通知
            W->>W: エラー画面表示
        end
    end
    
    Note over W, R: エラー復旧
    
    R->>S: 再接続試行
    S->>S: セッション復旧
    S-->>W: device_reconnected通知
    W->>W: エラー画面解除
```

## 7. パフォーマンス設計

### 7.1 レスポンス時間要件

| 処理項目 | 目標時間 | 計測ポイント | 最大許容時間 |
|----------|----------|--------------|--------------|
| セッション確立 | < 2秒 | コード入力〜ペアリング完了 | 5秒 |
| 同期精度 | ± 50ms | 動画時刻〜物理出力 | ± 100ms |
| 制御応答 | < 100ms | コマンド送信〜実行開始 | 200ms |
| 再接続時間 | < 3秒 | 切断検出〜再接続完了 | 10秒 |

### 7.2 スループット設計

```
通信頻度設計:
├── Webアプリ → サーバー
│   ├── 同期メッセージ: 10 msg/sec (100ms間隔)
│   ├── 制御イベント: 5 msg/sec (ユーザー操作)
│   └── ヘルスチェック: 0.033 msg/sec (30秒間隔)
├── サーバー → デバイス  
│   ├── 制御コマンド: 最大 5 cmd/sec
│   ├── ステータス要求: 1 req/sec
│   └── ヘルスチェック: 0.033 msg/sec
└── デバイス内部
    ├── Serial通信: 9600 bps
    ├── PWM更新: 1000 Hz
    └── タイマー精度: 1ms
```

## 8. セキュリティ設計

### 8.1 セキュリティ脅威と対策

| 脅威 | リスクレベル | 対策 | 実装方法 |
|------|--------------|------|----------|
| 通信傍受 | High | 暗号化通信 | WSS (TLS 1.3) |
| セッション乗っ取り | Medium | セッションコード | ランダム生成・有効期限 |
| DDoS攻撃 | Medium | レート制限 | API Gateway制限 |
| 物理デバイス悪用 | Low | 緊急停止機能 | ハードウェア安全装置 |

### 8.2 セキュリティ実装詳細

```python
# セッションコード生成（セキュリティ考慮）
import secrets
import string

def generate_session_code(length: int = 4) -> str:
    # 暗号学的に安全な乱数生成
    alphabet = string.ascii_uppercase + string.digits
    # 紛らわしい文字を除外 (0, O, I, 1など)
    alphabet = alphabet.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# レート制限実装
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        client_requests = self.requests[client_id]
        
        # 古いリクエスト削除
        while client_requests and client_requests[0] < now - self.window_seconds:
            client_requests.pop(0)
        
        # レート制限チェック
        if len(client_requests) >= self.max_requests:
            return False
        
        client_requests.append(now)
        return True
```

## 9. 監視・運用設計

### 9.1 監視項目

```yaml
監視カテゴリ:
  システムメトリクス:
    - CPU使用率 (ラズパイ)
    - メモリ使用率
    - ネットワーク遅延
    - WebSocket接続数
  
  アプリケーションメトリクス:
    - セッション成功率
    - 同期精度 (遅延分布)
    - エラー発生率
    - デバイス稼働率
  
  ビジネスメトリクス:
    - アクティブセッション数
    - 平均セッション時間
    - ユーザー体験満足度
    - デバイス利用率
```

### 9.2 ログ設計

```json
// 構造化ログ形式
{
  "timestamp": "2025-10-11T10:30:00.123Z",
  "level": "INFO",
  "service": "device-hub",
  "session_id": "ses_1234567890",
  "event": "actuator_command_executed",
  "data": {
    "command": "vibrate",
    "intensity": 80,
    "duration": 500,
    "execution_time_ms": 23,
    "success": true
  },
  "trace_id": "trace_abcd1234"
}
```

---

**更新日**: 2025年10月11日  
**バージョン**: 1.0  
**システム設計責任者**: 4DX@HOME開発チーム