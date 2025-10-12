# Backend Debug Tools - Raspberry Pi Development

このディレクトリには、Raspberry Pi通信システムのデバッグとテスト用ファイルが含まれています。

## ファイル一覧

### メインアプリケーション
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

## 使用方法

### PC環境でのテスト実行
```bash
# バックエンドディレクトリで実行
cd C:\Users\kumes\Documents\kz_2504\backend
python debug/raspberry-pi-main-pc.py test_session_debug
```

### WebSocket通信テスト
```bash
python debug/test_websocket_client.py
```

## 開発用途
- バックエンドのWebSocket通信機能デバッグ
- Raspberry Pi通信プロトコルのテスト
- 本番環境での動作確認

## 注意事項
このディレクトリのファイルは開発・デバッグ専用です。
実際のRaspberry Pi展開時は、適切な環境に合わせて設定を調整してください。