# 🔧 バックエンド本番用コード変更仕様書

**最終更新**: 2025年10月12日 10:15 JST  
**対象**: マイコン統合に向けた本番用コード変更  
**重要度**: ★★★ **必須変更事項**

## 🎯 **変更が必要な箇所**

### **1. 準備処理サービス WebSocket URL変更**

**ファイル**: `backend/app/services/preparation_service.py`  
**行数**: 614

#### **現在（ローカル開発用）**
```python
device_hub_ws_url = f"ws://localhost:8002/device-hub/sync/{device_id}"
```

#### **変更後（本番環境用）**
```python
# マイコンとの統合では本番WebSocketエンドポイントを使用
device_hub_ws_url = f"wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/preparation/ws/{session_id}"
```

**変更理由**:
- 現在はローカル開発用URL（localhost:8002）を使用
- マイコン統合では本番環境のWebSocketエンドポイントが必要
- 正しいセッションベースのURLパターンに変更

---

### **2. Mock WebSocket実装の実装化**

**ファイル**: `backend/app/services/preparation_service.py`  
**行数**: 631-632

#### **現在（Mock実装）**
```python
# 実際のWebSocket送信（今回はMock実装）
success = await self._mock_websocket_transmission(device_hub_ws_url, transmission_payload)
```

#### **変更後（実装版）**
```python
# マイコンへの実際のWebSocket送信
success = await self._production_websocket_transmission(session_id, device_id, transmission_payload)
```

**新規メソッド実装が必要**:
```python
async def _production_websocket_transmission(self, session_id: str, device_id: str, payload: Dict[str, Any]) -> bool:
    """本番環境WebSocket送信実装（マイコン統合用）"""
    try:
        # マイコンが準備処理APIから同期データを事前送信する新しいフロー
        from app.api.playback_control import ws_manager
        
        # セッション内のデバイス接続を確認
        device_connections = await self._get_device_connections(session_id)
        
        if not device_connections:
            logger.warning(f"セッション {session_id} にアクティブなデバイス接続がありません")
            return False
        
        # アクティブなマイコンに同期データ送信
        success_count = 0
        for connection_id in device_connections:
            if connection_id.startswith("device_"):
                websocket = ws_manager.active_connections.get(connection_id)
                if websocket:
                    try:
                        # sync_data_bulk_transmission メッセージとして送信
                        bulk_message = {
                            "type": "sync_data_bulk_transmission",
                            "session_id": session_id,
                            "video_id": payload.get("video_id", "demo1"),
                            "transmission_metadata": payload.get("metadata", {}),
                            "sync_data": payload.get("sync_data", {})
                        }
                        
                        await websocket.send_text(json.dumps(bulk_message))
                        success_count += 1
                        logger.info(f"マイコンへ同期データ送信成功: {connection_id}")
                        
                    except Exception as e:
                        logger.error(f"マイコン送信エラー ({connection_id}): {e}")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"本番WebSocket送信エラー: {e}")
        return False

async def _get_device_connections(self, session_id: str) -> List[str]:
    """セッション内のマイコン接続一覧取得"""
    from app.api.playback_control import ws_manager
    
    device_connections = []
    if session_id in ws_manager.session_connections:
        for connection_id in ws_manager.session_connections[session_id]:
            if connection_id.startswith("device_"):
                if connection_id in ws_manager.active_connections:
                    device_connections.append(connection_id)
    
    return device_connections
```

---

### **3. SSL証明書検証設定の本番化**

**ファイル**: `backend/app/services/preparation_service.py`  
**行数**: 673-675

#### **現在（開発環境用・セキュリティ無効）**
```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False  # ❌ 本番環境では危険
ssl_context.verify_mode = ssl.CERT_NONE  # ❌ 本番環境では危険
```

#### **変更後（本番環境用・セキュリティ有効）**
```python
# 本番環境では適切なSSL証明書検証を実行
ssl_context = ssl.create_default_context()
# ssl_context.check_hostname = True  # デフォルト値（明示的設定不要）
# ssl_context.verify_mode = ssl.CERT_REQUIRED  # デフォルト値（明示的設定不要）

# 本番環境のCloud Run証明書は自動的に信頼される
logger.info("本番環境SSL証明書検証: 有効")
```

**重要**: マイコン統合では本番環境WSS接続を使用するため、SSL証明書検証を必ず有効化

---

### **4. 環境判定による動的URL設定**

**新規実装推奨**: 環境変数による動的URL設定

```python
# backend/app/config/settings.py に追加
class Settings(BaseSettings):
    # ... 既存設定 ...
    
    # WebSocket URL設定（マイコン統合用）
    DEVICE_WEBSOCKET_BASE_URL: str = Field(
        default="wss://fourdk-backend-333203798555.asia-northeast1.run.app",
        description="マイコンWebSocket接続ベースURL"
    )
    
    ENVIRONMENT: str = Field(default="production", description="実行環境")
    
    def get_device_websocket_url(self, session_id: str) -> str:
        """マイコンWebSocket URL生成"""
        return f"{self.DEVICE_WEBSOCKET_BASE_URL}/api/preparation/ws/{session_id}"
```

**準備処理サービスでの使用**:
```python
# backend/app/services/preparation_service.py
from app.config.settings import settings

async def _transmit_sync_data_to_device(self, device_id: str, processed_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """デバイスハブへの同期データ送信"""
    try:
        # 本番環境対応のWebSocket URL使用
        device_hub_ws_url = settings.get_device_websocket_url(session_id)
        
        # ... 送信処理 ...
```

---

## 🚀 **変更による効果**

### **統合前（現在）**
- ❌ ローカルホストURL使用
- ❌ Mock送信実装
- ❌ SSL証明書検証無効

### **統合後（変更実装後）**
- ✅ 本番環境WSS URL使用
- ✅ 実際のマイコンWebSocket送信
- ✅ SSL証明書検証有効
- ✅ セッション管理統合
- ✅ エラーハンドリング強化

---

## 📋 **実装順序**

### **Phase 1**: 緊急変更（1時間）
1. **SSL証明書検証有効化**: セキュリティ確保
2. **WebSocket URL変更**: 本番環境URL使用

### **Phase 2**: 統合実装（2-3時間）  
1. **実装WebSocket送信メソッド作成**: Mock→実装変換
2. **セッション管理統合**: playback_control連携
3. **エラーハンドリング強化**: 本番運用対応

### **Phase 3**: 検証・最適化（1-2時間）
1. **統合テスト実行**: 実際のマイコン接続テスト
2. **パフォーマンス最適化**: 並列送信・タイムアウト調整
3. **ログ・メトリクス強化**: 運用監視対応

---

**最重要**: これらの変更により、マイコン統合で実際のWebSocket通信が可能になります！🎯