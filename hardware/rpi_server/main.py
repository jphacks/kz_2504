"""
4DX@HOME Raspberry Pi Server - Main Application
Cloud Run APIと統合したRaspberry Piデバイスハブサーバー
"""

import asyncio
import logging
import signal
import sys
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from config import Config
from src.utils.logger import setup_logger
from src.utils.communication_logger import CommunicationLogger
from src.mqtt.broker import MQTTBrokerClient
from src.mqtt.event_mapper import EventToMQTTMapper
from src.mqtt.device_manager import DeviceManager
from src.api.websocket_client import CloudRunWebSocketClient
from src.api.message_handler import WebSocketMessageHandler
from src.timeline.processor import TimelineProcessor
from src.timeline.cache_manager import TimelineCacheManager
from src.server.app import FlaskServer

# ロガーセットアップ
setup_logger()
logger = logging.getLogger(__name__)


class RaspberryPiServer:
    """Raspberry Pi デバイスハブサーバー"""
    
    def __init__(self, session_id: str):
        """
        Args:
            session_id: 接続するセッションID
        """
        self.session_id = session_id
        
        # コンポーネント初期化
        self.mqtt_client = MQTTBrokerClient()
        self.device_manager = DeviceManager()
        self.timeline_processor = TimelineProcessor(on_event_callback=self._on_timeline_event)
        self.cache_manager = TimelineCacheManager()
        self.comm_logger = CommunicationLogger()
        
        # WebSocketクライアント初期化
        self.ws_client = CloudRunWebSocketClient(
            session_id=session_id,
            on_message_callback=self._on_websocket_message
        )
        
        # Flaskサーバー初期化
        self.flask_server = FlaskServer(
            device_manager=self.device_manager,
            timeline_processor=self.timeline_processor,
            mqtt_client=self.mqtt_client
        )
        
        # Flask用スレッド
        self.flask_thread: Optional[threading.Thread] = None
        
        # 終了フラグ
        self._stop_requested = False
    
    async def start(self) -> None:
        """サーバーを起動"""
        logger.info("=" * 60)
        logger.info("4DX@HOME Raspberry Pi Server 起動")
        logger.info("=" * 60)
        logger.info(f"Device Hub ID: {Config.DEVICE_HUB_ID}")
        logger.info(f"Session ID: {self.session_id}")
        logger.info(f"Cloud Run API: {Config.CLOUD_RUN_API_URL}")
        logger.info("=" * 60)
        
        # 1. MQTTブローカー接続
        try:
            self.mqtt_client.connect()
            self.mqtt_client.subscribe_heartbeat(self._on_device_heartbeat)
            logger.info("✓ MQTT接続完了")
        except Exception as e:
            logger.error(f"✗ MQTT接続失敗: {e}")
            raise
        
        # 2. Flaskサーバー起動（バックグラウンドスレッド）
        self._start_flask_server()
        logger.info("✓ Flaskサーバー起動完了")
        
        # 3. WebSocketクライアント起動
        try:
            logger.info("WebSocket接続開始...")
            await self.ws_client.start_with_reconnect()
        except Exception as e:
            logger.error(f"WebSocketエラー: {e}", exc_info=True)
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """クリーンアップ処理"""
        logger.info("クリーンアップ開始")
        
        # WebSocket切断
        if self.ws_client:
            await self.ws_client.disconnect()
        
        # MQTT切断
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        
        logger.info("クリーンアップ完了")
    
    def _start_flask_server(self) -> None:
        """Flaskサーバーをバックグラウンドスレッドで起動"""
        def run_flask():
            try:
                self.flask_server.run(
                    host=Config.FLASK_HOST,
                    port=Config.FLASK_PORT,
                    debug=Config.FLASK_DEBUG
                )
            except OSError as e:
                if "Address already in use" in str(e):
                    logger.error(
                        f"ポート {Config.FLASK_PORT} は既に使用されています。"
                        f"既存のプロセスを停止するか、.envファイルでFLASK_PORTを変更してください。"
                    )
                    logger.info("停止方法: bash scripts/stop_server.sh")
                else:
                    logger.error(f"Flaskサーバー起動エラー: {e}", exc_info=True)
        
        self.flask_thread = threading.Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
    
    def _on_websocket_message(self, message: Dict[str, Any]) -> None:
        """WebSocketメッセージ受信時のコールバック
        
        Args:
            message: 受信メッセージ
        """
        message_type = message.get("type", "unknown")
        
        # 通信ログ記録
        self.comm_logger.log_received_message(
            message_type=message_type,
            data=message,
            session_id=self.session_id
        )
        
        # メッセージハンドラーで処理
        handler = WebSocketMessageHandler(
            on_sync_data=self._on_sync_data_received,
            on_sync_time=self._on_sync_time_received,
            on_control_command=self._on_control_command_received,
            on_device_test=self._on_device_test_received,
            on_video_sync=self._on_video_sync_received,
            on_stop_signal=self._on_stop_signal_received
        )
        
        handler.handle_message(message)
    
    def _on_sync_data_received(self, data: Dict) -> None:
        """タイムラインデータ受信時の処理
        
        Args:
            data: タイムラインデータ（session_id, video_id, sync_data, transmission_metadataを含む）
        """
        try:
            session_id = data.get("session_id", self.session_id)
            video_id = data.get("video_id", "unknown")
            sync_data = data.get("sync_data", {})
            
            logger.info(f"タイムラインデータ処理開始: video_id={video_id}")
            
            # タイムラインプロセッサーにロード（sync_dataを渡す）
            self.timeline_processor.load_timeline(sync_data)
            
            # キャッシュに保存（完全なデータを保存）
            self.cache_manager.save_timeline(session_id, data)
            
            logger.info("タイムラインデータ処理完了")
        
        except Exception as e:
            logger.error(f"タイムラインデータ処理エラー: {e}", exc_info=True)
    
    def _on_sync_time_received(self, current_time: float) -> None:
        """同期時刻受信時の処理
        
        Args:
            current_time: 現在時刻（秒）
        """
        # タイムラインプロセッサーに時刻を更新
        self.timeline_processor.update_current_time(current_time)
    
    def _on_video_sync_received(self, sync_data: Dict) -> None:
        """動画同期メッセージ受信時の処理
        
        Args:
            sync_data: 動画同期データ（video_time, video_state, video_duration, session_idを含む）
        """
        video_time = sync_data.get("video_time", 0)
        video_state = sync_data.get("video_state", "unknown")
        
        logger.info(f"📺 動画同期処理: state={video_state}, time={video_time:.2f}秒")
        
        # 再生中の場合、タイムラインプロセッサーに時刻を更新
        if video_state == "play":
            # 再生開始時にタイムライン再生も開始
            if not self.timeline_processor.is_playing:
                self.timeline_processor.start_playback()
                logger.info(f"▶️  タイムライン再生開始")
            
            self.timeline_processor.update_current_time(video_time)
            logger.info(f"⏱️  タイムライン時刻更新: {video_time:.2f}秒")
        elif video_state == "pause":
            # 一時停止時はタイムライン処理も停止
            if self.timeline_processor.is_playing:
                self.timeline_processor.stop_playback()
                logger.info(f"⏸️  タイムライン再生一時停止")
        elif video_state == "seeking" or video_state == "seeked":
            # シーク時は現在時刻を更新
            self.timeline_processor.update_current_time(video_time)
            logger.info(f"⏩ シーク完了: {video_time:.2f}秒")
    
    def _on_control_command_received(self, control: Dict) -> None:
        """制御コマンド受信時の処理
        
        Args:
            control: 制御コマンド
        """
        command = control.get("command")
        
        logger.info(f"制御コマンド受信: {command}")
        
        if command == "start_playback":
            self.timeline_processor.start_playback()
        
        elif command == "stop_playback":
            self.timeline_processor.stop_playback()
        
        elif command == "reset":
            self.timeline_processor.reset()
    
    def _on_device_test_received(self, test_data: Dict) -> None:
        """デバイステスト受信時の処理
        
        Args:
            test_data: テストデータ（session_id, test_type, timestampを含む）
        """
        session_id = test_data.get("session_id")
        test_type = test_data.get("test_type", "basic")
        
        logger.info(f"🧪 デバイステスト実行開始: session_id={session_id}, test_type={test_type}")
        
        try:
            # デバイステスト実行（MQTTブローカー接続確認）
            is_mqtt_connected = self.mqtt_client.is_connected if hasattr(self.mqtt_client, 'is_connected') else True
            
            # 接続されているデバイス数を取得
            connected_devices = self.device_manager.get_all_devices()
            device_count = len(connected_devices)
            
            # テスト結果を作成（DeviceStatusオブジェクトを辞書に変換）
            test_result = {
                "type": "device_test_result",
                "session_id": session_id,
                "test_type": test_type,
                "status": "success",
                "mqtt_connected": is_mqtt_connected,
                "device_count": device_count,
                "devices": [
                    {
                        "device_id": d.device_id,
                        "device_type": d.device_type,
                        "is_online": d.is_online,
                        "last_heartbeat": d.last_heartbeat
                    } for d in connected_devices
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ デバイステスト完了: mqtt={is_mqtt_connected}, devices={device_count}")
            
            # WebSocket経由でバックエンドに応答を送信
            asyncio.create_task(self._send_device_test_result(test_result))
        
        except Exception as e:
            logger.error(f"❌ デバイステスト実行エラー: {e}", exc_info=True)
            
            # エラー応答を送信
            error_result = {
                "type": "device_test_result",
                "session_id": session_id,
                "test_type": test_type,
                "status": "error",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            asyncio.create_task(self._send_device_test_result(error_result))
    
    async def _send_device_test_result(self, result: Dict) -> None:
        """デバイステスト結果をバックエンドに送信
        
        Args:
            result: テスト結果
        """
        try:
            await self.ws_client.send_message(result)
            logger.info(f"📤 デバイステスト結果送信完了")
        except Exception as e:
            logger.error(f"❌ デバイステスト結果送信エラー: {e}", exc_info=True)
    
    def _on_stop_signal_received(self, stop_data: Dict) -> None:
        """ストップ信号受信時の処理（全アクチュエータ停止）
        
        Args:
            stop_data: ストップ信号データ（session_id, action, timestamp, sourceを含む）
        """
        session_id = stop_data.get("session_id")
        action = stop_data.get("action", "stop_all")
        source = stop_data.get("source", "unknown")
        
        logger.info(
            f"🛑 ストップ信号処理開始: session_id={session_id}, "
            f"action={action}, source={source}"
        )
        
        try:
            # タイムライン再生を停止
            if self.timeline_processor.is_playing:
                self.timeline_processor.stop_playback()
                logger.info("⏸️  タイムライン再生停止")
            
            # 全アクチュエータ停止MQTTコマンドを取得
            stop_commands = EventToMQTTMapper.get_stop_all_commands()
            
            # MQTTコマンドを送信
            for topic, payload in stop_commands:
                self.mqtt_client.publish(topic, payload)
                logger.debug(f"📤 MQTT送信: {topic} = {payload}")
            
            logger.info(
                f"✅ 全アクチュエータ停止完了: {len(stop_commands)}個のコマンド送信"
            )
        
        except Exception as e:
            logger.error(f"❌ ストップ信号処理エラー: {e}", exc_info=True)
    
    def _on_timeline_event(self, event: Dict) -> None:
        """タイムラインイベント発火時の処理
        
        Args:
            event: タイムラインイベント
        """
        # イベントをMQTTコマンドにマッピング
        mqtt_commands = EventToMQTTMapper.process_timeline_event(event)
        
        # MQTTコマンドを並列配信
        for topic, payload in mqtt_commands:
            self.mqtt_client.publish(topic, payload)
    
    def _on_device_heartbeat(self, device_id: str) -> None:
        """デバイスハートビート受信時の処理
        
        Args:
            device_id: デバイスID
        """
        self.device_manager.register_device(device_id)


def signal_handler(sig, frame):
    """シグナルハンドラー（Ctrl+C対応）"""
    logger.info("終了シグナル受信")
    sys.exit(0)


async def main():
    """メインエントリーポイント"""
    # シグナルハンドラー登録
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # セッションIDを引数から取得（デフォルト: "default_session"）
    session_id = sys.argv[1] if len(sys.argv) > 1 else "default_session"
    
    # サーバー起動
    server = RaspberryPiServer(session_id=session_id)
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("プログラムを終了します")
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        sys.exit(1)
