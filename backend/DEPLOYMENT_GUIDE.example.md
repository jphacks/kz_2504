# 4DX@HOME Backend デプロイガイド

> **⚠️ 注意**: このファイルはテンプレートです。実際のデプロイURLは `backend/DEPLOYMENT_GUIDE.md` に記載されていますが、そのファイルは `.gitignore` により除外されています。

## 環境変数の設定

### 1. 環境変数ファイルの作成

```bash
# backend ディレクトリで実行
cp .env.example .env
```

### 2. .env ファイルの編集

デプロイ後に生成されるCloud RunのURLを `.env` ファイルに設定します:

```bash
# 本番環境のURL(デプロイ後に設定)
BACKEND_API_URL="https://your-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
BACKEND_WS_URL="wss://your-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
```

### 3. 機密情報の管理

**重要**: 以下のファイルは `.gitignore` に登録されており、Gitにコミットされません:

- `.env` - 環境変数ファイル
- `docs/backend-report/` - デプロイURLを含むドキュメント
- `backend/DEPLOYMENT_GUIDE.md` - このファイルの実際の版（URLを含む）

## Cloud Runへのデプロイ

### サービス名

Cloud Runサービス名: **fdx-home-backend-api**

これにより、デプロイ後のURLは以下の形式になります:
```
https://fdx-home-backend-api-[PROJECT_NUMBER].asia-northeast1.run.app
```

### デプロイ手順

```bash
# 1. Dockerイメージのビルド
cd backend
docker build -f Dockerfile.cloudrun \
  -t asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest .

# 2. Artifact Registryへのプッシュ
docker push asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest

# 3. Cloud Runへのデプロイ
gcloud run deploy fdx-home-backend-api \
  --image=asia-northeast1-docker.pkg.dev/fourdk-home-2024/my-fastapi-repo/fdx-home-backend-api:latest \
  --region=asia-northeast1 \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300s \
  --concurrency=80 \
  --max-instances=20 \
  --allow-unauthenticated
```

### デプロイ後の確認

```bash
# サービス情報の確認
gcloud run services describe fdx-home-backend-api --region=asia-northeast1

# URLの取得
gcloud run services describe fdx-home-backend-api --region=asia-northeast1 --format="value(status.url)"
```

取得したURLを各環境変数ファイルに設定してください。

## セキュリティ考慮事項

1. **環境変数**: `.env` ファイルは必ず `.gitignore` に含めてください
2. **URL情報**: 本番環境のURLはチーム内でのみ共有し、公開リポジトリには含めないでください
3. **CORS設定**: 本番環境では実際のフロントエンドURLのみを許可してください
4. **API Documentation**: 本番環境では `/docs` を無効化してください（`ENVIRONMENT=production` で自動的に無効化）

## ローカル開発

```bash
# 依存関係のインストール
pip install -r requirements.txt

# ローカルサーバーの起動
python -m app.main
```

デフォルトでは `http://localhost:8000` でサーバーが起動します。

## トラブルシューティング

### URL情報の確認

デプロイ後のURL情報は以下のコマンドで確認できます:

```bash
gcloud run services list --platform=managed --region=asia-northeast1
```

### 環境変数の反映

Cloud Runで環境変数を設定する場合:

```bash
gcloud run services update fdx-home-backend-api \
  --region=asia-northeast1 \
  --set-env-vars="ENVIRONMENT=production,DEBUG=false"
```

### CORS設定の更新

`backend/debug/.env.cloudrun` ファイルを編集してCORS設定を更新:

```bash
cd backend/debug
# .env.cloudrunを編集
gcloud run services update fdx-home-backend-api \
  --region=asia-northeast1 \
  --env-vars-file=.env.cloudrun
```

## デプロイ履歴

デプロイ履歴は実際の `backend/DEPLOYMENT_GUIDE.md` ファイル（Git除外）に記録されています。

---

**最終更新**: 2025年11月7日  
**テンプレートバージョン**: 1.0
