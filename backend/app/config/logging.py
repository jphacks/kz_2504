# app/config/logging.py
import logging
import sys
from datetime import datetime

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """ログ設定のセットアップ"""
    import os
    
    # ログフォーマット設定
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ログレベル設定
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # ハンドラーリスト
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # ファイルログハンドラー（指定された場合）
    if log_file:
        # ログディレクトリ作成
        log_dir = os.path.dirname(log_file) or "."
        os.makedirs(log_dir, exist_ok=True)
        
        handlers.append(
            logging.FileHandler(log_file, encoding='utf-8')
        )
    
    # 基本ログ設定
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers,
        force=True  # 既存設定を上書き
    )
    
    # 外部ライブラリのログレベル調整
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    return logging.getLogger(__name__)