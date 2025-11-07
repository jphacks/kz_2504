# 時間信号の許容範囲仕様 (Time Tolerance Specification)

**作成日**: 2025年11月8日  
**対象**: Raspberry Pi デバイスハブ  
**バージョン**: 1.0.0

---

## 📌 概要

Raspberry Piのタイムライン処理において、**受信した時間信号に対して±0.1秒の許容範囲**を設けることで、ネットワーク遅延による影響を最小限に抑え、確実にイベントを実行します。

### 目的

- ネットワーク遅延による時間信号のずれを吸収
- イベントの取りこぼしを防止
- より柔軟なタイムライン同期

---

## ⏱️ 許容範囲の仕組み

### 基本ルール

タイムライン上のイベント時刻 `t` に対して、現在時刻 `current_time` が以下の範囲内にある場合、イベントを実行します:

```
t - tolerance <= current_time <= t + tolerance
```

### デフォルト設定

- **許容範囲**: ±100ms (0.1秒)
- **設定場所**: `SYNC_TOLERANCE_MS` 環境変数
- **単位**: ミリ秒 (ms)

### 実行例

#### 例1: 1.0秒のイベント

```
イベント時刻: t = 1.0秒
許容範囲: ±0.1秒
実行範囲: 0.9秒 ~ 1.1秒

現在時刻が以下の場合、イベントが実行されます:
- 0.90秒 ✅ (境界内)
- 0.95秒 ✅ (範囲内)
- 1.00秒 ✅ (ちょうど)
- 1.05秒 ✅ (範囲内)
- 1.10秒 ✅ (境界内)

以下の場合は実行されません:
- 0.89秒 ❌ (範囲外)
- 1.11秒 ❌ (範囲外)
```

#### 例2: 複数イベント

```
タイムライン:
  - t=1.0秒: 振動開始
  - t=1.5秒: 風エフェクト
  - t=2.0秒: フラッシュ

現在時刻 = 1.05秒 の場合:
  - 1.0秒イベント: 実行 ✅ (1.0 ± 0.1 = 0.9~1.1)
  - 1.5秒イベント: 未実行 ⏳ (まだ範囲外)
  - 2.0秒イベント: 未実行 ⏳ (まだ範囲外)

現在時刻 = 1.55秒 の場合:
  - 1.0秒イベント: 処理済み (last_processed_time で管理)
  - 1.5秒イベント: 実行 ✅ (1.5 ± 0.1 = 1.4~1.6)
  - 2.0秒イベント: 未実行 ⏳ (まだ範囲外)
```

---

## 🔧 設定方法

### 環境変数

`.env` ファイルで設定:

```properties
# 同期許容誤差（ミリ秒）
SYNC_TOLERANCE_MS=100  # デフォルト: ±100ms (0.1秒)
```

### カスタマイズ例

#### より厳密な同期（±50ms）

```properties
SYNC_TOLERANCE_MS=50
```

- 使用ケース: ネットワークが安定している環境
- イベント実行範囲: t ± 0.05秒

#### より緩い同期（±200ms）

```properties
SYNC_TOLERANCE_MS=200
```

- 使用ケース: ネットワーク遅延が大きい環境
- イベント実行範囲: t ± 0.2秒

#### 許容範囲なし（厳密一致）

```properties
SYNC_TOLERANCE_MS=0
```

- 使用ケース: テスト環境
- ⚠️ 注意: イベントの取りこぼしが発生する可能性があります

---

## 💻 実装詳細

### processor.py の処理ロジック

```python
def _process_events_at_time(self, current_time: float) -> None:
    """指定時刻のイベントを処理
    
    現在時刻から±tolerance_sec（デフォルト0.1秒）の範囲内にあるイベントを実行します。
    例: イベント時刻が1.0秒の場合、現在時刻が0.9~1.1秒の範囲で実行されます。
    
    Args:
        current_time: 現在時刻（秒）
    """
    tolerance_sec = self.sync_tolerance_ms / 1000.0  # msを秒に変換
    
    # 処理対象イベントを抽出
    events_to_process = []
    
    for event in self.timeline:
        event_time = event.get("t", 0)
        
        # 既に処理済みの時刻より前のイベントはスキップ
        if event_time <= self.last_processed_time:
            continue
        
        # 現在時刻±tolerance内のイベントを処理
        # 例: event_time=1.0, tolerance=0.1の場合、current_time=0.9~1.1で実行
        time_diff = abs(event_time - current_time)
        
        if time_diff <= tolerance_sec:
            events_to_process.append(event)
            logger.debug(
                f"⏱️  イベント実行範囲内: event_time={event_time:.2f}s, "
                f"current_time={current_time:.2f}s, diff={time_diff:.3f}s, "
                f"tolerance=±{tolerance_sec:.3f}s"
            )
        
        # 現在時刻を過ぎたイベントは次回以降
        if event_time > current_time + tolerance_sec:
            break
    
    # イベント実行
    for event in events_to_process:
        self._execute_event(event)
    
    # 処理済み時刻を更新
    if events_to_process:
        self.last_processed_time = current_time
```

### キーポイント

1. **許容範囲の計算**
   ```python
   tolerance_sec = self.sync_tolerance_ms / 1000.0  # 100ms → 0.1秒
   ```

2. **時間差の判定**
   ```python
   time_diff = abs(event_time - current_time)
   if time_diff <= tolerance_sec:  # ±0.1秒以内
       # イベント実行
   ```

3. **処理済みチェック**
   ```python
   if event_time <= self.last_processed_time:
       continue  # 重複実行を防止
   ```

---

## 📊 タイミング図

### 通常ケース（tolerance = 0.1秒）

```
タイムライン:
0.0s    1.0s    2.0s    3.0s
 |       |       |       |
        [振動]  [風]   [光]

受信時刻:
0.0s    0.95s   2.05s   2.98s
 |       |       |       |
        ↓       ↓       ↓
       実行    実行    実行

説明:
- 1.0秒イベント: 0.95秒で受信 → 0.9~1.1秒の範囲内 → 実行 ✅
- 2.0秒イベント: 2.05秒で受信 → 1.9~2.1秒の範囲内 → 実行 ✅
- 3.0秒イベント: 2.98秒で受信 → 2.9~3.1秒の範囲内 → 実行 ✅
```

### 許容範囲外のケース

```
タイムライン:
0.0s    1.0s    2.0s
 |       |       |
        [振動]  [風]

受信時刻:
0.0s    0.85s   2.15s
 |       |       |
        ↓       ↓
       実行    実行
       ❌      ❌

説明:
- 1.0秒イベント: 0.85秒で受信 → 0.9~1.1秒の範囲外 → 未実行 ❌
- 2.0秒イベント: 2.15秒で受信 → 1.9~2.1秒の範囲外 → 未実行 ❌

※ tolerance=0.1秒の場合、±0.15秒のずれには対応できません
```

---

## 🧪 テスト方法

### 1. ログ出力で確認

デバッグログを有効化:

```properties
# .env
LOG_LEVEL=DEBUG
```

実行時のログ例:

```
⏱️  イベント実行範囲内: event_time=1.00s, current_time=1.05s, diff=0.050s, tolerance=±0.100s
イベント実行: t=1.0, effect=vibration, mode=strong, action=start
```

### 2. 許容範囲のテスト

#### テストシナリオ1: 境界値テスト

```python
# タイムライン
events = [
    {"t": 1.0, "effect": "vibration", "mode": "strong"}
]

# テストケース
test_cases = [
    (0.89, False),  # 範囲外
    (0.90, True),   # 境界 (OK)
    (1.00, True),   # ちょうど
    (1.10, True),   # 境界 (OK)
    (1.11, False),  # 範囲外
]
```

#### テストシナリオ2: 連続イベント

```python
# タイムライン（0.5秒間隔）
events = [
    {"t": 1.0, "effect": "vibration"},
    {"t": 1.5, "effect": "wind"},
    {"t": 2.0, "effect": "flash"},
]

# 0.5秒ごとに時間信号を送信
for t in [0.5, 1.0, 1.5, 2.0, 2.5]:
    processor.update_current_time(t)
```

---

## ⚠️ 注意事項

### 1. 重複実行の防止

同じイベントが複数回実行されないよう、`last_processed_time` で管理しています:

```python
if event_time <= self.last_processed_time:
    continue  # 既に処理済み
```

### 2. 時間信号の順序

時間信号は**単調増加**することを前提としています:

```
✅ 正常: 0.5秒 → 1.0秒 → 1.5秒 → 2.0秒
❌ 異常: 1.5秒 → 1.0秒 → 2.0秒 (逆戻り)
```

時間が逆戻りする場合は、`reset()` メソッドで処理状態をリセットしてください。

### 3. ネットワーク遅延

許容範囲は**ネットワーク遅延を吸収するため**のものです:

- 通常のネットワーク遅延: ~50ms
- Wi-Fi環境: ~100ms
- 4G/LTE環境: ~200ms

環境に応じて `SYNC_TOLERANCE_MS` を調整してください。

### 4. イベント密度

イベント間隔が許容範囲より小さい場合、複数イベントが同時に実行される可能性があります:

```
イベント1: t=1.0秒
イベント2: t=1.1秒
tolerance: ±0.1秒

現在時刻=1.0秒の場合:
- イベント1: 実行 ✅ (1.0 ± 0.1)
- イベント2: 実行 ✅ (1.1 ± 0.1 → 1.0~1.2)
```

推奨: イベント間隔は `tolerance の2倍` 以上（デフォルトでは0.2秒以上）

---

## 📈 パフォーマンス

### 処理コスト

- **O(n)**: タイムライン内の全イベントをチェック
- **最適化**: `event_time > current_time + tolerance` で早期終了

### メモリ使用量

- タイムラインサイズに比例
- 典型的な動画（120秒、100イベント）: ~10KB

---

## 🔧 トラブルシューティング

### イベントが実行されない

**原因**: 許容範囲が狭すぎる

**解決策**:
```properties
# .envで許容範囲を広げる
SYNC_TOLERANCE_MS=200  # ±0.2秒
```

### イベントが重複実行される

**原因**: 時間信号が重複送信されている

**解決策**: バックエンド側の送信間隔を確認（推奨: 500ms間隔）

### イベントが早すぎる/遅すぎる

**原因**: システム時刻のずれ

**解決策**: NTPで時刻同期を確認
```bash
sudo timedatectl status
```

---

## 📚 関連ドキュメント

- [Raspberry Pi Server README](./README.md)
- [Timeline Processor実装](./src/timeline/processor.py)
- [Stop Signal Specification](../../debug_frontend/STOP_SIGNAL_SPEC.md)

---

## 🆕 変更履歴

| 日付 | バージョン | 変更内容 |
|-----|----------|---------|
| 2025-11-08 | 1.0.0 | 初版作成 - 時間許容範囲仕様の明確化 |

---

**まとめ**: デフォルト設定（±0.1秒）で、ネットワーク遅延を考慮した柔軟なタイムライン同期が実現されています。
