"""
4DX@HOME Flask HTTP Server
デバイスハブのステータス確認とローカル制御用のHTTPサーバー
"""

import logging
import json
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class FlaskServer:
    """Flask HTTPサーバー"""
    
    def __init__(
        self,
        device_manager=None,
        timeline_processor=None,
        mqtt_client=None
    ):
        self.app = Flask(__name__, template_folder='../../templates', static_folder='../../static')
        CORS(self.app)
        
        self.device_manager = device_manager
        self.timeline_processor = timeline_processor
        self.mqtt_client = mqtt_client
        
        # ルート設定
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """HTTPエンドポイントを設定"""
        
        @self.app.route('/')
        def index():
            """コントローラーページ"""
            return render_template('controller.html')
        
        @self.app.route('/health')
        def health():
            """ヘルスチェック"""
            from config import Config
            
            status = {
                "status": "healthy",
                "device_id": Config.DEVICE_HUB_ID,
                "mqtt_connected": self.mqtt_client.is_connected if self.mqtt_client else False,
                "timeline_loaded": len(self.timeline_processor.timeline) > 0 if self.timeline_processor else False
            }
            
            return jsonify(status)
        
        @self.app.route('/api/status')
        def get_status():
            """デバイスハブのステータスを取得"""
            from config import Config
            
            status = {
                "device_id": Config.DEVICE_HUB_ID,
                "device_name": Config.DEVICE_NAME,
                "mqtt": {
                    "connected": self.mqtt_client.is_connected if self.mqtt_client else False,
                    "broker": f"{Config.MQTT_BROKER_HOST}:{Config.MQTT_BROKER_PORT}"
                },
                "devices": self.device_manager.get_status_summary() if self.device_manager else {},
                "timeline": self.timeline_processor.get_stats() if self.timeline_processor else {}
            }
            
            return jsonify(status)
        
        @self.app.route('/api/devices')
        def get_devices():
            """接続中のデバイス一覧を取得"""
            if not self.device_manager:
                return jsonify({"error": "Device manager not available"}), 503
            
            devices = [
                {
                    "device_id": d.device_id,
                    "device_type": d.device_type,
                    "is_online": d.is_online,
                    "last_heartbeat": d.last_heartbeat
                }
                for d in self.device_manager.get_all_devices()
            ]
            
            return jsonify({"devices": devices})
        
        @self.app.route('/api/timeline/stats')
        def get_timeline_stats():
            """タイムライン統計を取得"""
            if not self.timeline_processor:
                return jsonify({"error": "Timeline processor not available"}), 503
            
            stats = self.timeline_processor.get_stats()
            return jsonify(stats)
        
        @self.app.route('/api/mqtt/publish', methods=['POST'])
        def mqtt_publish():
            """MQTTメッセージを手動で配信（テスト用）"""
            if not self.mqtt_client:
                return jsonify({"error": "MQTT client not available"}), 503
            
            data = request.get_json()
            topic = data.get('topic')
            payload = data.get('payload')
            
            if not topic or not payload:
                return jsonify({"error": "topic and payload are required"}), 400
            
            try:
                self.mqtt_client.publish(topic, payload)
                return jsonify({"success": True, "topic": topic, "payload": payload})
            except Exception as e:
                logger.error(f"MQTT配信エラー: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/playback/control', methods=['POST'])
        def playback_control():
            """再生制御（開始/停止/リセット）"""
            if not self.timeline_processor:
                return jsonify({"error": "Timeline processor not available"}), 503
            
            data = request.get_json()
            command = data.get('command')
            
            if command == 'start':
                self.timeline_processor.start_playback()
                return jsonify({"success": True, "command": "start"})
            
            elif command == 'stop':
                self.timeline_processor.stop_playback()
                return jsonify({"success": True, "command": "stop"})
            
            elif command == 'reset':
                self.timeline_processor.reset()
                return jsonify({"success": True, "command": "reset"})
            
            else:
                return jsonify({"error": f"Unknown command: {command}"}), 400
        
        @self.app.route('/api/debug/logs', methods=['GET'])
        def get_debug_logs():
            """デバッグログ（最新のMQTT通信ログ）を取得"""
            try:
                from config import Config
                
                # 通信ログディレクトリを確認
                log_dir = Path(Config.COMMUNICATION_LOG_DIR)
                if not log_dir.exists():
                    return jsonify({"logs": [], "message": "ログディレクトリが存在しません"})
                
                # 最新のログファイルを取得
                log_files = sorted(log_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
                
                logs = []
                max_logs = 20
                
                for log_file in log_files[:5]:  # 最新5ファイルから取得
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if len(logs) >= max_logs:
                                    break
                                try:
                                    log_entry = json.loads(line.strip())
                                    logs.append(log_entry)
                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        logger.error(f"ログファイル読み込みエラー: {e}")
                        continue
                    
                    if len(logs) >= max_logs:
                        break
                
                return jsonify({"logs": logs[:max_logs]})
            
            except Exception as e:
                logger.error(f"ログ取得エラー: {e}", exc_info=True)
                return jsonify({"error": str(e), "logs": []}), 500
        
        @self.app.route('/api/debug/system-info', methods=['GET'])
        def get_system_info():
            """システム情報を取得"""
            try:
                from config import Config
                import platform
                import psutil
                
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # メモリ使用率
                memory = psutil.virtual_memory()
                
                # ディスク使用率
                disk = psutil.disk_usage('/')
                
                system_info = {
                    "platform": platform.system(),
                    "platform_release": platform.release(),
                    "python_version": platform.python_version(),
                    "cpu_percent": cpu_percent,
                    "memory": {
                        "total_gb": round(memory.total / (1024**3), 2),
                        "used_gb": round(memory.used / (1024**3), 2),
                        "percent": memory.percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024**3), 2),
                        "used_gb": round(disk.used / (1024**3), 2),
                        "percent": disk.percent
                    },
                    "config": {
                        "device_hub_id": Config.DEVICE_HUB_ID,
                        "mqtt_broker": f"{Config.MQTT_BROKER_HOST}:{Config.MQTT_BROKER_PORT}",
                        "sync_tolerance_ms": Config.SYNC_TOLERANCE_MS
                    }
                }
                
                return jsonify(system_info)
            
            except ImportError:
                # psutilがインストールされていない場合
                from config import Config
                import platform
                
                system_info = {
                    "platform": platform.system(),
                    "platform_release": platform.release(),
                    "python_version": platform.python_version(),
                    "config": {
                        "device_hub_id": Config.DEVICE_HUB_ID,
                        "mqtt_broker": f"{Config.MQTT_BROKER_HOST}:{Config.MQTT_BROKER_PORT}",
                        "sync_tolerance_ms": Config.SYNC_TOLERANCE_MS
                    },
                    "note": "詳細なシステム情報を取得するには psutil をインストールしてください"
                }
                
                return jsonify(system_info)
            
            except Exception as e:
                logger.error(f"システム情報取得エラー: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/debug/mqtt-test', methods=['POST'])
        def mqtt_connection_test():
            """MQTT接続テスト"""
            if not self.mqtt_client:
                return jsonify({"success": False, "error": "MQTT client not available"}), 503
            
            try:
                is_connected = self.mqtt_client.is_connected
                
                # テストメッセージを送信
                test_topic = "/4dx/debug/test"
                test_payload = f"test_{datetime.now().timestamp()}"
                
                if is_connected:
                    self.mqtt_client.publish(test_topic, test_payload)
                
                return jsonify({
                    "success": True,
                    "connected": is_connected,
                    "test_sent": is_connected,
                    "topic": test_topic,
                    "payload": test_payload
                })
            
            except Exception as e:
                logger.error(f"MQTT接続テストエラー: {e}", exc_info=True)
                return jsonify({"success": False, "error": str(e)}), 500
    
    def run(self, host: str = '0.0.0.0', port: int = 8000, debug: bool = False) -> None:
        """Flaskサーバーを起動
        
        Args:
            host: ホストアドレス
            port: ポート番号
            debug: デバッグモード
        """
        logger.info(f"Flaskサーバー起動: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)
