# 🔄 Cloud Run サービス再設定ガイド

## 📋 **サービス削除時に保持されるもの**

### ✅ **保持される要素**
```
✅ Container Registry内のDockerイメージ
✅ GCPプロジェクト設定
✅ 有効化されたAPI
✅ 課金アカウント・予算設定
✅ IAM権限設定
✅ ローカルのDockerイメージとソースコード
```

### ❌ **失われる要素**
```
❌ Cloud Runサービス設定
❌ サービスURL (新しいURLが生成される)
❌ カスタムドメイン設定
❌ 環境変数設定
❌ リソース制限設定
❌ IAM ポリシー (サービス固有)
```

## 🚀 **再デプロイ手順**

### **Step 1: Dockerイメージ確認**
```bash
# ローカルイメージ確認
docker images | grep fourdk-home-backend

# Container Registry確認  
gcloud container images list --repository=gcr.io/fourdk-home-2024
```

### **Step 2: 必要に応じてイメージ再プッシュ**
```bash
# 最新コードでリビルド
docker build -t fourdk-home-backend .
docker tag fourdk-home-backend gcr.io/fourdk-home-2024/fourdk-home-backend:latest
docker push gcr.io/fourdk-home-2024/fourdk-home-backend:latest
```

### **Step 3: Cloud Run再デプロイ**
```bash
# サービス再作成 (同じ設定)
gcloud run deploy fourdk-home-backend \
  --image gcr.io/fourdk-home-2024/fourdk-home-backend:latest \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --max-instances 1
```

## 📊 **再設定時の設定値**

### **リソース設定**
```yaml
CPU: 1 vCPU
メモリ: 512Mi  
最大インスタンス: 1
ポート: 8080
リージョン: asia-northeast1
認証: 未認証を許可
```

### **環境変数 (必要に応じて)**
```bash
ENVIRONMENT=production
PORT=8080
CORS_ORIGINS=*
LOG_LEVEL=INFO
```

## 🔗 **URL変更の影響**

### **新しいURL形式**
```
旧: https://fourdk-home-backend-333203798555.asia-northeast1.run.app
新: https://fourdk-home-backend-[新しいハッシュ].asia-northeast1.run.app
```

### **影響を受けるファイル**
```
docs/frontend-integration-guide.md
docs/hardware-integration-guide.md  
docs/development-roadmap.md
frontend/ 内の設定ファイル
hardware/ 内の設定ファイル
```

## 🛡️ **料金最適化の代替案**

### **Option A: トラフィック0設定**
```bash
# サービス削除ではなくトラフィックを0に
gcloud run services update fourdk-home-backend \
  --region asia-northeast1 \
  --no-traffic

# 再有効化時
gcloud run services update-traffic fourdk-home-backend \
  --region asia-northeast1 \
  --to-latest=100
```

### **Option B: 最小リソース設定**  
```bash
# 最小構成で維持
gcloud run services update fourdk-home-backend \
  --region asia-northeast1 \
  --cpu 0.25 \
  --memory 256Mi \
  --max-instances 1 \
  --concurrency 1
```

### **Option C: 定期起動・停止**
```bash
# Cloud Scheduler + Cloud Functions で自動制御
# 開発時間外は自動停止、開始時は自動起動
```

## 🎯 **推奨アプローチ**

### **開発期間中の運用**
1. **ローカル開発**: Docker環境 (`localhost:8001`)
2. **チーム連携**: Cloud Run一時起動 (必要時のみ)
3. **最終確認**: 本番デプロイ前に完全テスト

### **サービス削除する場合の手順**
```bash
# 1. 現在の設定を保存
gcloud run services describe fourdk-home-backend \
  --region asia-northeast1 \
  --format="export" > backup-service-config.yaml

# 2. サービス削除
gcloud run services delete fourdk-home-backend \
  --region asia-northeast1 \
  --quiet

# 3. 再デプロイ時
gcloud run services replace backup-service-config.yaml
```

## 📞 **緊急時復旧手順**

### **クイック復旧**
```bash
# 最速デプロイ (1分以内)
gcloud run deploy fourdk-home-backend \
  --image gcr.io/fourdk-home-2024/fourdk-home-backend:latest \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### **フル復旧**
```bash
# 完全な設定で復旧
gcloud run deploy fourdk-home-backend \
  --image gcr.io/fourdk-home-2024/fourdk-home-backend:latest \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --max-instances 1 \
  --set-env-vars ENVIRONMENT=production,PORT=8080
```

---

## 💡 **結論**

**推奨**: サービス削除ではなく **トラフィック0設定** または **最小リソース設定** を使用することで、URL変更を避けながら料金を最小化できます。

完全に削除する場合は、上記の手順で簡単に復旧可能ですが、新しいURLが生成されるため、チームメンバーへの通知が必要です。