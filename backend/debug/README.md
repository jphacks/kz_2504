# Backend Debug Tools - Raspberry Pi Development

このディレクトリには、Raspberry Pi通信システムのデバッグとテスト用ファイルが含まれています。

## 📁 ファイル一覧

### 🚀 **新規追加 - CloudRun対応版**
- **`raspberry-pi-cloudrun.py`** - **Raspberry Pi本番用**
  - 既存コード(`rasberry-pi-code.py`)ベースのCloudRun対応版
  - 実際のGPIO/Serial/MQTT制御
  - WebSocket通信でCloudRunと連携
  - JSON同期データ + リアルタイム同期対応

- **`raspberry-pi-pc-debug.py`** - **PC環境デバッグ用**
  - Windows/macOS対応のクロスプラットフォーム版
  - ハードウェアをモック化（視覚的フィードバック）
  - CloudRun通信ロジックは本番と同じ
  - 開発・テスト用

- **`rasberry-pi-code.py`** - **参考用**
  - オリジナルのSocket通信ベースコード
  - ハードウェア制御ロジックの参考実装

### メインアプリケーション（既存）
- **`raspberry-pi-main-pc.py`** - PC環境対応のRaspberry Piメインアプリケーション
  - 本番バックエンドとの通信テスト用
  - Windows環境での文字化け対策済み
  - ハードウェアシミュレーション機能付き

### テストツール
- **`test_websocket_client.py`** - WebSocket通信テスト用クライアント
  - バックエンドとの通信確認用
  - 同期データ送受信テスト

### 運用ファイル (実際のRaspberry Pi用)
- **`start-4dx-home.sh`** - 起動スクリプト
- **`4dx-home.service`** - systemdサービス設定
- **`RASPBERRY_PI_SETUP.md`** - セットアップガイド

## 🛠️ 使用方法

### **🚀 CloudRun対応版（推奨）**

#### Raspberry Pi本番環境
```bash
# 必要ライブラリインストール
pip install websockets aiohttp RPi.GPIO pyserial paho-mqtt

# セッションIDを指定して実行
python raspberry-pi-cloudrun.py test_session_01

# デフォルトセッションで実行
python raspberry-pi-cloudrun.py
```

#### PC環境デバッグ
```bash
# WebSocketライブラリのみ
pip install websockets aiohttp

# PC環境でデバッグ実行
python raspberry-pi-pc-debug.py pc_debug_session

# Windows PowerShell
python raspberry-pi-pc-debug.py test_session_pc
```

### **📡 CloudRun APIテスト**
```bash
# タイムライン読み込みテスト
curl -X POST "https://fourdk-backend-333203798555.asia-northeast1.run.app/api/playback/debug/timeline/test_session?video_id=demo1"

# 連続同期開始テスト
curl -X POST "https://fourdk-backend-333203798555.asia-northeast1.run.app/api/playback/debug/sync/test_session/start?interval=0.5"
```

### **🔧 既存システム**

#### PC環境でのテスト実行
```bash
# バックエンドディレクトリで実行
cd C:\Users\kumes\Documents\kz_2504\backend
python debug/raspberry-pi-main-pc.py test_session_debug
```

#### WebSocket通信テスト
```bash
python debug/test_websocket_client.py
```

## 🎯 開発用途

### **CloudRun対応版**
- **フロントエンド連携**: Web画面からの動画同期データ受信
- **リアルタイム同期**: 0.5秒間隔の時間同期処理
- **JSON同期データ**: demo1.jsonなどのタイムライン一括受信
- **クロスプラットフォーム**: PC環境でのハードウェアロジックデバッグ

### **既存システム**
- バックエンドのWebSocket通信機能デバッグ
- Raspberry Pi通信プロトコルのテスト  
- 本番環境での動作確認

## ⚡ パフォーマンス比較

| 項目 | 既存システム | CloudRun対応版 |
|------|-------------|---------------|
| 通信方式 | Socket | WebSocket (WSS) |
| 認証 | なし | デバイス登録 |
| 同期精度 | 手動送信 | 自動連続同期 |
| エラー処理 | 基本的 | 自動再接続 |
| PC対応 | 限定的 | 完全対応 |

## 📋 注意事項

### **CloudRun対応版**
- **Raspberry Pi**: 実際のハードウェア制御（GPIO/Serial/MQTT）
- **PC**: ハードウェアをモック化、ログ出力でエフェクト確認
- **元コード**: ハードウェア制御ロジックを完全保持

### **既存システム**
このディレクトリのファイルは開発・デバッグ専用です。
実際のRaspberry Pi展開時は、適切な環境に合わせて設定を調整してください。

## 🔄 移行方法

**既存 → CloudRun対応版**
1. 依存関係追加: `pip install websockets aiohttp`
2. 実行: `python raspberry-pi-cloudrun.py {session_id}`
3. ハードウェア制御ロジックはそのまま利用可能

**🎯 元のSocket通信コードの完全な機能を保持しつつ、CloudRunとの統合を実現**