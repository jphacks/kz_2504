# 🐳 4DX@HOME FastAPI Backend Dockerfile
# マルチステージビルドで軽量なプロダクション環境を構築

# ===============================
# Stage 1: 開発・ビルドステージ
# ===============================
FROM python:3.12-slim as builder

# メタデータ
LABEL maintainer="kume@4dxathome"
LABEL version="1.0"
LABEL description="4DX@HOME WebSocket FastAPI Backend"

# 作業ディレクトリ設定
WORKDIR /app

# システムの依存関係をインストール（キャッシュ効率化）
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係をインストール（レイヤーキャッシュ最適化）
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ===============================
# Stage 2: プロダクションステージ 
# ===============================
FROM python:3.12-slim

# 非rootユーザー作成（セキュリティ強化）
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 作業ディレクトリ設定
WORKDIR /app

# 必要最小限のシステム依存関係
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Stage1からPython依存関係をコピー
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションファイルをコピー
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser data/ ./data/

# 環境変数設定
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Cloud Run用ポート公開
EXPOSE 8080

# ヘルスチェック設定
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 非rootユーザーに切り替え
USER appuser

# アプリケーション起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]