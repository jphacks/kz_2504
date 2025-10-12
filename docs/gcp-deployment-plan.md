# 🚀 GCP デプロイメント計画書

## 📋 **概要**
FastAPI WebSocketサーバーをGCP Cloud Runにデプロイし、ローカル開発環境から本番環境への移行を実現する。

## 🎯 **デプロイメント目標**
- **現在**: `http://127.0.0.1:8001` (ローカルのみ)
- **目標**: `https://fourdk-home-backend.run.app` (グローバルアクセス)

## 📅 **実装スケジュール（2日間）**

### **Day 1: GCP基盤構築**
#### ⏰ **午前 (9:00-12:00)**
- [ ] GCPプロジェクト作成・設定
- [ ] 料金アラート設定（無料枠監視）
- [ ] 必要なAPIの有効化
  - Cloud Run API
  - Container Registry API
  - Cloud Build API

#### ⏰ **午後 (13:00-17:00)**
- [ ] Dockerファイル作成・テスト
- [ ] ローカルでのコンテナ動作確認
- [ ] Container Registry への初回プッシュ

### **Day 2: デプロイ・CI/CD**
#### ⏰ **午前 (9:00-12:00)**
- [ ] Cloud Run サービス作成
- [ ] カスタムドメイン設定
- [ ] HTTPS・WebSocket動作確認

#### ⏰ **午後 (13:00-17:00)**
- [ ] GitHub Actions CI/CD設定
- [ ] 本番環境テスト
- [ ] ドキュメント更新（新URL配布）

## 🏗️ **技術アーキテクチャ**

### **使用するGCPサービス**
```
GitHub (ソースコード)
    ↓ push
GitHub Actions (CI/CD)
    ↓ build & deploy
Container Registry (イメージ保存)
    ↓ deploy
Cloud Run (FastAPIサーバー実行)
    ↓ expose
HTTPS URL (フロント・ハードウェア接続)
```

### **コスト見積もり（無料枠内）**
- **Cloud Run**: 月200万リクエスト無料
- **Container Registry**: 0.5GB無料
- **Cloud Build**: 1日120分無料
- **予想コスト**: 月額 0-500円程度

## 🐳 **Docker設定**

### **Dockerfile構成**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイル
COPY app/ ./app/
COPY data/ ./data/

# Cloud Run用設定
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### **docker-compose.yml（開発用）**
```yaml
version: '3.8'
services:
  fastapi:
    build: .
    ports:
      - "8001:8080"
    environment:
      - ENVIRONMENT=development
    volumes:
      - ./data:/app/data
```

## � **課金設定（必須）**

### **GCPコンソールでの設定**
1. https://console.cloud.google.com にアクセス
2. プロジェクト「fourdk-home-2024」を選択
3. 「請求」→「請求アカウントをリンク」
4. クレジットカード情報を登録
5. 無料枠（$300クレジット）が利用可能

### **⚠️ 課金設定完了後に実行**
```bash
# 必要なAPIを有効化
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com  
gcloud services enable cloudbuild.googleapis.com
```

## �🔧 **環境変数管理**

### **本番環境設定**
```bash
# Cloud Run環境変数
ENVIRONMENT=production
PORT=8080
CORS_ORIGINS=https://your-frontend-domain.com
LOG_LEVEL=INFO
```

### **開発環境設定**
```bash
# ローカル環境変数
ENVIRONMENT=development  
PORT=8001
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
LOG_LEVEL=DEBUG
```

## 📤 **GitHub Actions CI/CD**

### **デプロイフロー**
```yaml
# .github/workflows/deploy-cloud-run.yml
name: Deploy to Cloud Run

on:
  push:
    branches: [develop, main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v0
      - name: Build and Deploy
        run: |
          gcloud builds submit --tag gcr.io/$PROJECT_ID/fourdk-home
          gcloud run deploy fourdk-home --image gcr.io/$PROJECT_ID/fourdk-home
```

## 🔗 **URL・エンドポイント計画**

### **本番環境URL**
- **API Base**: `https://fourdk-home-backend.run.app`
- **WebSocket**: `wss://fourdk-home-backend.run.app/ws/{client_id}`
- **ヘルスチェック**: `https://fourdk-home-backend.run.app/health`
- **テストページ**: `https://fourdk-home-backend.run.app/test`

### **フロントエンド統合**
```javascript
// 本番環境用設定
const API_BASE_URL = 'https://fourdk-home-backend.run.app';
const WEBSOCKET_URL = 'wss://fourdk-home-backend.run.app/ws';
```

### **ハードウェア統合**
```python
# Raspberry Pi用設定
BACKEND_URL = "wss://fourdk-home-backend.run.app/ws"
```

## 🧪 **テスト戦略**

### **デプロイ後テストリスト**
- [ ] HTTPSアクセス確認
- [ ] WebSocket接続テスト
- [ ] セッション作成・参加テスト
- [ ] マルチクライアント動作確認
- [ ] レスポンス時間測定
- [ ] エラーログ確認

### **負荷テスト**
```bash
# WebSocket負荷テスト
wscat -c wss://fourdk-home-backend.run.app/ws/test-client-1
wscat -c wss://fourdk-home-backend.run.app/ws/test-client-2
# ... 同時接続数テスト
```

## 📊 **監視・ログ**

### **Cloud Logging設定**
- リクエストログ
- WebSocket接続ログ  
- エラーログ
- パフォーマンスメトリクス

### **アラート設定**
- エラー率 > 5%
- レスポンス時間 > 5秒
- 同時接続数 > 100

## 🔄 **ロールバック計画**

### **緊急時対応**
1. **即座にローカル環境に戻す**
   ```bash
   # フロントエンド・ハードウェアの接続先をローカルに変更
   API_BASE_URL = 'http://127.0.0.1:8001'
   ```

2. **前バージョンにロールバック**
   ```bash
   gcloud run deploy fourdk-home --image gcr.io/$PROJECT_ID/fourdk-home:previous
   ```

## 📚 **参考資料・次のステップ**

### **完了後の展開**
1. **フロントエンド連携**: 新URLでの接続テスト
2. **ハードウェア連携**: Raspberry Pi設定更新
3. **チームシェア**: 本番環境URLの配布
4. **負荷対応**: 必要に応じてスケーリング設定

### **将来の拡張**
- Cloud SQL (データベース永続化)
- Redis (セッション管理高速化)  
- Load Balancer (高可用性)
- CDN (静的ファイル配信)

---

## 📞 **サポート・質問**
**担当**: 久米（バックエンド開発者）
**完了予定**: 2日以内
**ステータス**: 🔄 進行中