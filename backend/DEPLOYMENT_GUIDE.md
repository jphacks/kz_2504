# 4DX@HOME Backend デプロイガイド

## 環境変数の設定

### 1. 環境変数ファイルの作成

```bash
# backend ディレクトリで実行
cp .env.example .env
```

### 2. .env ファイルの編集

デプロイ後に生成されるCloud RunのURLを `.env` ファイルに設定します:

```bash
# 本番環境のURL（デプロイ後に設定）
BACKEND_API_URL="https://4dx-home-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
BACKEND_WS_URL="wss://4dx-home-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
```

### 3. 機密情報の管理

**重要**: 以下のファイルは `.gitignore` に登録されており、Gitにコミットされません:

- `.env` - 環境変数ファイル
- `docs/backend-report/current-status-handover.md` - デプロイURLを含むドキュメント
- `docs/backend-report/deployment-urls.md` - URLリスト

## Cloud Runへのデプロイ

### サービス名

Cloud Runサービス名: **4dx-home-backend-api**

これにより、デプロイ後のURLは以下の形式になります:
```
https://4dx-home-backend-api-[PROJECT_NUMBER].asia-northeast1.run.app
```

### デプロイスクリプトの実行

```powershell
# docs/backend-report ディレクトリから実行
.\deploy-to-cloudrun.ps1
```

### デプロイ後の確認

```bash
# サービス情報の確認
gcloud run services describe 4dx-home-backend-api --region=asia-northeast1

# URLの取得
gcloud run services describe 4dx-home-backend-api --region=asia-northeast1 --format="value(status.url)"
```

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
gcloud run services update 4dx-home-backend-api \
  --region=asia-northeast1 \
  --set-env-vars="ENVIRONMENT=production,DEBUG=false"
```
