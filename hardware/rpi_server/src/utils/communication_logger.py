"""
4DX@HOME Communication Logger
WebSocket通信ログをJSON形式で記録
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class CommunicationLogger:
    """通信ログ記録"""
    
    def __init__(self):
        self.log_dir = Config.COMMUNICATION_LOG_DIR
        self.enabled = Config.ENABLE_COMMUNICATION_LOG
        
        # ログディレクトリを作成
        if self.enabled:
            os.makedirs(self.log_dir, exist_ok=True)
    
    def log_received_message(
        self,
        message_type: str,
        data: Dict[str, Any],
        session_id: str = None
    ) -> None:
        """受信メッセージをログに記録
        
        Args:
            message_type: メッセージタイプ
            data: メッセージデータ
            session_id: セッションID（オプション）
        """
        if not self.enabled:
            return
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "direction": "received",
                "type": message_type,
                "session_id": session_id,
                "data": data
            }
            
            self._write_log(log_entry, message_type)
        
        except Exception as e:
            logger.error(f"通信ログ記録エラー: {e}", exc_info=True)
    
    def log_sent_message(
        self,
        message_type: str,
        data: Dict[str, Any],
        session_id: str = None
    ) -> None:
        """送信メッセージをログに記録
        
        Args:
            message_type: メッセージタイプ
            data: メッセージデータ
            session_id: セッションID（オプション）
        """
        if not self.enabled:
            return
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "direction": "sent",
                "type": message_type,
                "session_id": session_id,
                "data": data
            }
            
            self._write_log(log_entry, message_type)
        
        except Exception as e:
            logger.error(f"通信ログ記録エラー: {e}", exc_info=True)
    
    def _write_log(self, log_entry: Dict, message_type: str) -> None:
        """ログをファイルに書き込み
        
        Args:
            log_entry: ログエントリ
            message_type: メッセージタイプ
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{message_type}_{timestamp}.json"
            filepath = os.path.join(self.log_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"通信ログ保存: {filename}")
        
        except Exception as e:
            logger.error(f"ログファイル書き込みエラー: {e}", exc_info=True)
