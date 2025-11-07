# Backend Configuration for Raspberry Pi Clients

このファイルは、Raspberry Piクライアントから接続するバックエンドURLを管理します。

## 環境変数の設定

各スクリプトで以下の環境変数を使用してURLを設定できます:

```bash
# .env ファイルまたは環境変数として設定
export BACKEND_API_URL="https://your-backend-url.run.app/api"
export BACKEND_WS_URL="wss://your-backend-url.run.app"
```

## Pythonスクリプトでの使用例

```python
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

api_base_url = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")
ws_base_url = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")
```

## デプロイ後の設定手順

1. Cloud Runにデプロイ後、URLを取得:
```bash
gcloud run services describe 4dx-home-backend-api --region=asia-northeast1 --format="value(status.url)"
```

2. 取得したURLを `.env` ファイルに設定:
```bash
BACKEND_API_URL="https://4dx-home-backend-api-XXXXXXXXXX.asia-northeast1.run.app/api"
BACKEND_WS_URL="wss://4dx-home-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
```

3. Raspberry Piに `.env` ファイルをコピー

## セキュリティ注意事項

- `.env` ファイルは `.gitignore` に登録されており、Gitにコミットされません
- 本番環境のURLは必要な人にのみ共有してください
- 公開リポジトリにはURL情報を含めないでください
