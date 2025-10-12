# 🐳 4DX@HOME FastAPI Backend Dockerfile
# シンプルなシングルステージビルドでローカル環境と同じ動作を実現

FROM python:3.12-slim

# メタデータ
LABEL maintainer="kume@4dxathome"
LABEL version="2.0"
LABEL description="4DX@HOME WebSocket FastAPI Backend - New Spec"

# 作業ディレクトリ設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー（全ディレクトリ構造を保持）
COPY . .

# 環境変数設定
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Cloud Run用ポート公開
EXPOSE 8080

# ヘルスチェック設定（新しいAPIエンドポイントを使用）
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# アプリケーション起動（本番環境用 - reloadオプション無し）
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]