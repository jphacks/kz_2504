# 4DX@HOME システム設計図・シーケンス図詳細

## 1. 詳細シーケンス図集

### 1.1 完全システム初期化シーケンス

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant V as Video要素
    participant W as Webアプリ (JS)
    participant S as サーバー (GCP)
    participant H as デバイスハブ (ラズパイ)
    participant A as Arduino
    participant M as 振動モーター
    
    Note over U, M: フェーズ1: ハードウェア起動
    
    U->>H: デバイス電源ON
    activate H
    H->>H: OS起動 & Pythonスクリプト自動実行
    H->>A: USB経由でシリアルポートを開く
    activate A
    A->>A: setup()実行 (シリアル通信とGPIOピンを初期化)
    A-->>H: シリアル接続確立 (Ready信号)
    
    H->>S: WSS接続を要求
    activate S
    S->>S: ユニークなセッションコード生成 (例: A4B7)
    S-->>H: コードを通知 ("code": "A4B7")
    H->>H: コンソールにコードを出力 (`print("コード: A4B7")`)
    
    Note over U, M: フェーズ2: Webアプリ準備
    
    par
        U->>W: ページにアクセス
        activate W
        W->>V: <video>要素を生成し、プリロード開始
        activate V
        W->>W: video.addEventListener('canplaythrough', ...) 登録
    and
        H->>H: セッションコード待機状態
    end
    
    Note over U, M: フェーズ3: ペアリング
    
    U->>W: コンソールを見てコード「A4B7」を入力
    W->>S: WSS接続 & ペアリング要求 ("sessionCode": "A4B7")
    S->>S: コードを検証し、WebAppとHubを紐付け
    S-->>W: ペアリング成功 & デバイス接続完了を通知
    S-->>H: Webアプリ接続完了通知
    
    V-->>W: 準備完了イベント発行 (canplaythrough)
    deactivate V
    
    Note over U, M: フェーズ4: セッション開始準備完了
    
    W-->>U: スタートボタンを有効化
    U->>W: 体験を選択し、スタートボタンをクリック
    W->>S: "start_session" イベント送信 (選択体験設定を含む)
    S->>S: セッション状態を"active"に更新
    S-->>H: セッション開始通知
    S-->>W: 開始確認応答
    W-->>U: プレイヤー画面に遷移
    
    deactivate W
    deactivate S
    deactivate H
    deactivate A
```

### 1.2 動画再生中のリアルタイム同期詳細

```mermaid
sequenceDiagram
    participant Timer as JS Timer (100ms)
    participant W as Webアプリ (player.js)
    participant S as サーバー (main.py)
    participant H as ハブ (hub.py)
    participant A as Arduino (actuator.ino)
    participant M as 振動モーター
    
    Note over Timer, M: 継続的同期処理 (100ms間隔)
    
    loop 動画再生中の同期ループ
        Timer->>W: setInterval callback実行
        W->>W: video.currentTime取得 (例: 10.484秒)
        W->>S: ws.send('{"event":"playback_sync", "data":{"current_time":10.484}}')
        
        activate S
        S->>S: セッション特定 & 同期データ照合
        S->>S: check_sync_events(time=10.484)
        
        Note right of S: 10.5秒地点の振動イベント発見<br/>if event and user_settings["vibration"]:
        
        alt 同期イベント発見 & ユーザー設定有効
            S->>H: ws.send('{"event":"actuator_command", "data":{"action":"vibrate", "intensity":0.8, "duration":500}}')
            deactivate S
            
            activate H
            H->>H: data = json.loads(message)
            H->>H: action = data["data"]["action"] # "vibrate"
            H->>H: intensity = int(data["data"]["intensity"] * 100) # 80
            H->>H: duration = data["data"]["duration"] # 500
            H->>H: command = f"{action[0]},{intensity},{duration}\n" # "v,80,500\n"
            
            H->>A: serial.write(command.encode('utf-8'))
            deactivate H
            
            activate A
            Note over A: loop()内で Serial.available() > 0 検知
            A->>A: commandString = Serial.readStringUntil('\n') # "v,80,500"
            A->>A: sscanf(commandString, "v,%d,%d", &intensity, &duration)
            A->>A: pwmValue = map(intensity, 0, 100, 0, 255) # 204
            A->>A: vibrationStartTime = millis()
            A->>A: motorActive = true
            
            A->>M: analogWrite(MOTOR_PIN, pwmValue)
            activate M
            M-->>A: 振動開始
            
            Note over A, M: duration (500ms) 経過まで継続
            
            loop モーター制御ループ
                A->>A: if (millis() - vibrationStartTime >= duration)
                alt 時間経過
                    A->>M: analogWrite(MOTOR_PIN, 0)
                    deactivate M
                    A->>A: motorActive = false
                else 継続中
                    Note right of A: 振動継続
                end
            end
            deactivate A
            
        else 同期イベントなし
            Note right of S: 何も送信しない
            deactivate S
        end
        
        Note over Timer, M: 100ms待機後、次の同期処理へ
    end
```

### 1.3 エラー発生・復旧シーケンス

```mermaid
sequenceDiagram
    participant W as Webアプリ
    participant S as サーバー
    participant H as ラズパイ
    participant N as ネットワーク
    
    Note over W, N: 正常運用中
    
    W->>S: 同期データ送信
    S->>H: 制御コマンド
    H-->>S: 実行確認
    S-->>W: ステータス応答
    
    Note over W, N: ❌ ネットワーク障害発生
    
    W-xN: 接続断
    S-xN: 接続断
    
    Note over W, N: エラー検知・処理
    
    par Webアプリ側
        W->>W: WebSocket.onclose イベント発火
        W->>W: connectionState = 'disconnected'
        W->>W: showConnectionError() 実行
        W->>W: 自動再接続タイマー開始 (3秒)
        
        loop 再接続ループ
            Note right of W: 3秒後
            W->>N: WebSocket再接続試行
            alt 接続成功
                N->>S: 接続確立
                S-->>W: 接続完了
                W->>S: セッション復旧要求
                S->>S: セッション状態確認
                alt セッション有効
                    S-->>W: セッション復旧完了
                    W->>W: hideConnectionError()
                    W->>W: 正常状態復帰
                else セッション無効
                    S-->>W: セッション無効通知
                    W->>W: 初期画面に戻る
                end
            else 接続失敗
                W->>W: 3秒待機 → リトライ
            end
        end
        
    and ラズパイ側
        H->>H: WebSocket.onclose イベント発火
        H->>H: connection_lost = True
        H->>H: LED点滅でエラー状態表示
        
        loop 再接続ループ
            Note right H: 3秒後
            H->>N: WebSocket再接続試行
            alt 接続成功
                N->>S: 接続確立
                S-->>H: 接続完了
                H->>S: デバイス再登録要求
                S->>S: デバイス情報復旧
                S-->>H: 登録完了 + セッション情報
                H->>H: connection_lost = False
                H->>H: 正常LED表示復帰
            else 接続失敗
                H->>H: 3秒待機 → リトライ
            end
        end
    end
    
    Note over W, N: ✅ 双方向復旧完了
    
    S-->>W: device_reconnected 通知
    S-->>H: webapp_reconnected 通知
    
    Note over W, N: 正常運用再開
    
    W->>S: 同期データ送信再開
    S->>H: 制御コマンド再開
```

## 2. システム状態遷移図

### 2.1 システム全体状態遷移

```mermaid
stateDiagram-v2
    [*] --> SystemOff: 電源OFF
    
    SystemOff --> DeviceBooting: ハードウェア電源ON
    note right of DeviceBooting
        ラズパイ起動
        Arduino初期化
        ネットワーク接続
    end note
    
    DeviceBooting --> WaitingForPairing: デバイス登録完了
    note right of WaitingForPairing
        セッションコード発行済み
        Webアプリ接続待ち
    end note
    
    WaitingForPairing --> SessionEstablished: ペアリング成功
    note right of SessionEstablished
        Webアプリ接続完了
        体験設定受信済み
    end note
    
    SessionEstablished --> ActiveSync: セッション開始
    note right of ActiveSync
        動画再生中
        リアルタイム同期実行中
        物理フィードバック動作中
    end note
    
    ActiveSync --> SessionPaused: 一時停止
    SessionPaused --> ActiveSync: 再生再開
    
    state ErrorStates {
        NetworkError: ネットワーク切断
        DeviceError: デバイス異常
        SyncError: 同期エラー
    }
    
    SessionEstablished --> NetworkError: 接続切断
    ActiveSync --> NetworkError: 接続切断
    ActiveSync --> DeviceError: ハードウェア異常
    ActiveSync --> SyncError: 同期精度劣化
    
    NetworkError --> SessionEstablished: 再接続成功
    NetworkError --> WaitingForPairing: セッション失効
    DeviceError --> DeviceBooting: システム再起動
    SyncError --> ActiveSync: 自動補正完了
    
    ActiveSync --> SessionEstablished: セッション終了
    SessionPaused --> SessionEstablished: セッション終了
    SessionEstablished --> WaitingForPairing: タイムアウト
    WaitingForPairing --> SystemOff: 電源OFF
```

### 2.2 WebSocket接続状態詳細

```mermaid
stateDiagram-v2
    [*] --> Disconnected: 初期状態
    
    Disconnected --> Connecting: connect() 呼び出し
    note right of Connecting
        WebSocket生成
        接続試行中
        タイムアウト監視
    end note
    
    Connecting --> Connected: onopen イベント
    Connecting --> Disconnected: onerror / タイムアウト
    
    Connected --> Authenticating: 接続確立
    note right of Authenticating
        デバイス登録 or
        セッション参加
    end note
    
    Authenticating --> Authenticated: 認証成功
    Authenticating --> Disconnected: 認証失敗
    
    Authenticated --> Authenticated: メッセージ送受信
    note right of Authenticated
        Ping/Pong ヘルスチェック
        データ送受信
        正常運用状態
    end note
    
    state ReconnectionStates {
        Reconnecting: 再接続中
        BackoffWait: 待機中
    }
    
    Connected --> Reconnecting: onclose イベント
    Authenticated --> Reconnecting: 予期しない切断
    
    Reconnecting --> Connected: 再接続成功
    Reconnecting --> BackoffWait: 再接続失敗
    
    BackoffWait --> Reconnecting: 待機時間経過
    note right of BackoffWait
        指数バックオフ
        最大30秒待機
    end note
    
    Authenticated --> Disconnected: 正常切断
```

## 3. データフロー・アーキテクチャ図

### 3.1 システム全体データフロー

```mermaid
flowchart TB
    subgraph "Input Layer"
        VideoFile[動画ファイル<br/>MP4/WebM]
        SyncData[同期データ<br/>JSON]
        UserInput[ユーザー入力<br/>設定・操作]
    end
    
    subgraph "Presentation Layer"
        Browser[Webブラウザ]
        ReactApp[React アプリケーション]
        VideoPlayer[HTML5 Video Player]
    end
    
    subgraph "Communication Layer"
        WSClient[WebSocket Client]
        WSS[WSS Connection<br/>TLS 1.3]
        APIGateway[API Gateway<br/>Load Balancer]
    end
    
    subgraph "Business Logic Layer"
        FastAPI[FastAPI Server]
        SessionMgr[セッション管理]
        SyncEngine[同期エンジン]
        EventProcessor[イベント処理]
    end
    
    subgraph "Device Layer"
        DeviceHub[デバイスハブ<br/>Raspberry Pi]
        SerialComm[シリアル通信<br/>USB]
        MCU[マイクロコントローラー<br/>Arduino]
    end
    
    subgraph "Physical Layer"
        VibrationMotor[振動モーター]
        ScentDiffuser[香り拡散装置]
        LEDIndicator[ステータスLED]
    end
    
    VideoFile --> VideoPlayer
    SyncData --> SyncEngine
    UserInput --> ReactApp
    
    ReactApp --> WSClient
    VideoPlayer --> WSClient
    
    WSClient -.-> WSS
    WSS --> APIGateway
    APIGateway --> FastAPI
    
    FastAPI --> SessionMgr
    FastAPI --> SyncEngine
    SyncEngine --> EventProcessor
    
    EventProcessor -.-> WSS
    WSS -.-> DeviceHub
    
    DeviceHub --> SerialComm
    SerialComm --> MCU
    
    MCU --> VibrationMotor
    MCU --> ScentDiffuser
    MCU --> LEDIndicator
    
    VibrationMotor -.物理フィードバック.-> Browser
    ScentDiffuser -.物理フィードバック.-> Browser
```

### 3.2 メッセージキューイングシステム

```mermaid
flowchart LR
    subgraph "Message Sources"
        WebApp[Webアプリ<br/>同期メッセージ]
        DeviceHub[デバイスハブ<br/>ステータス更新]
        Timer[タイマー<br/>ヘルスチェック]
    end
    
    subgraph "Message Processing"
        Ingress[メッセージ受信]
        Validator[形式検証]
        RateLimiter[レート制限]
        Router[ルーティング]
    end
    
    subgraph "Message Handlers"
        SyncHandler[同期処理<br/>ハンドラー]
        SessionHandler[セッション管理<br/>ハンドラー]
        DeviceHandler[デバイス制御<br/>ハンドラー]
    end
    
    subgraph "Message Outputs"
        DeviceQueue[デバイス<br/>コマンドキュー]
        WebQueue[Webアプリ<br/>レスポンスキュー]
        LogQueue[ログ<br/>出力キュー]
    end
    
    WebApp --> Ingress
    DeviceHub --> Ingress
    Timer --> Ingress
    
    Ingress --> Validator
    Validator --> RateLimiter
    RateLimiter --> Router
    
    Router --> SyncHandler
    Router --> SessionHandler  
    Router --> DeviceHandler
    
    SyncHandler --> DeviceQueue
    SessionHandler --> WebQueue
    DeviceHandler --> DeviceQueue
    
    SyncHandler --> LogQueue
    SessionHandler --> LogQueue
    DeviceHandler --> LogQueue
```

## 4. 物理アーキテクチャ図

### 4.1 ハードウェア接続図

```mermaid
flowchart TB
    subgraph "Power Supply"
        PSU[USB-C 電源アダプター<br/>5V/3A]
        ExtPower[外部電源<br/>6V/1A]
    end
    
    subgraph "Raspberry Pi 4"
        RPI[Raspberry Pi 4<br/>4GB RAM]
        GPIO[GPIO ピン]
        USB[USB ポート]
        WiFi[WiFi モジュール<br/>2.4/5GHz]
    end
    
    subgraph "Arduino Uno"
        MCU[ATmega328P<br/>マイクロコントローラー]
        DigitalPins[デジタルピン<br/>0-13]
        PWMPins[PWM ピン<br/>3,5,6,9,10,11]
        USBSerial[USB Serial<br/>通信]
    end
    
    subgraph "Motor Driver"
        L293D[L293D<br/>モータードライバーIC]
        MotorOut[モーター出力]
    end
    
    subgraph "Actuators"
        VibMotor[振動モーター<br/>10mm コイン型]
        StatusLED[ステータスLED]
        EmergencyBtn[緊急停止<br/>ボタン]
    end
    
    subgraph "Network"
        Router[WiFiルーター]
        Internet[インターネット]
        GCP[GCP サーバー]
    end
    
    PSU --> RPI
    ExtPower --> L293D
    
    RPI --> GPIO
    RPI --> USB
    RPI --> WiFi
    
    USB --> USBSerial
    USBSerial --> MCU
    MCU --> DigitalPins
    MCU --> PWMPins
    
    PWMPins --> L293D
    L293D --> MotorOut
    MotorOut --> VibMotor
    
    GPIO --> StatusLED
    GPIO --> EmergencyBtn
    
    WiFi -.-> Router
    Router --> Internet
    Internet --> GCP
```

### 4.2 信号フロー図

```mermaid
flowchart LR
    subgraph "Digital Domain"
        WebApp[Webアプリ<br/>JavaScript]
        Server[GCPサーバー<br/>Python]
        RaspberryPi[ラズパイ<br/>Python]
    end
    
    subgraph "Serial Communication"
        USBSerial[USB Serial<br/>9600 bps]
        ArduinoSerial[Arduino Serial<br/>受信バッファ]
    end
    
    subgraph "MCU Processing"
        Parser[コマンドパーサー<br/>C/C++]
        PWMGen[PWM生成器<br/>Timer1]
        GPIO[GPIO制御]
    end
    
    subgraph "Analog Domain"
        MotorDriver[L293D<br/>電力増幅]
        Motor[振動モーター<br/>物理出力]
    end
    
    WebApp -.WebSocket.-> Server
    Server -.WebSocket.-> RaspberryPi
    RaspberryPi --> USBSerial
    USBSerial --> ArduinoSerial
    
    ArduinoSerial --> Parser
    Parser --> PWMGen
    Parser --> GPIO
    
    PWMGen --> MotorDriver
    GPIO --> MotorDriver
    MotorDriver --> Motor
    
    Motor -.物理振動.-> WebApp
```

---

**更新日**: 2025年10月11日  
**バージョン**: 1.0  
**システム設計詳細策定者**: 4DX@HOME開発チーム