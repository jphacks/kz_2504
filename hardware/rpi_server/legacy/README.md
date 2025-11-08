# Legacy 4DXHOME Code

このディレクトリには、既存の4DXHOMEコード（ハードウェアエンジニアが開発したMQTTサーバー）を参考用に保存します。

## コピー方法

```bash
# 4DXHOMEディレクトリから必要なファイルをコピー
cp ../../4DXHOME/mqtt_server.py ./mqtt_server.py
cp ../../4DXHOME/controller.html ./controller.html
cp ../../4DXHOME/timeline_player.html ./timeline_player.html
cp ../../4DXHOME/timeline.json ./timeline.json
```

## ファイルの役割

- **mqtt_server.py**: 元のMQTTサーバー実装
- **controller.html**: デバイス制御UI
- **timeline_player.html**: タイムライン再生UI
- **timeline.json**: テスト用タイムラインデータ

## 注意事項

このディレクトリのコードは参考・バックアップ用です。実際の実装は `src/` ディレクトリにあります。

## イベントマッピングの継承

`mqtt_server.py` の `event_map` は `src/mqtt/event_mapper.py` の `EVENT_MAP` として継承されています。
