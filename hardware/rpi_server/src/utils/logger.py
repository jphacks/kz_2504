"""
4DX@HOME Logger Configuration
アプリケーション全体で使用するロガーの設定
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from config import Config


def setup_logger(name: str = None) -> logging.Logger:
    """ロガーをセットアップ
    
    Args:
        name: ロガー名（Noneの場合はルートロガー）
    
    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)
    
    # 既に設定済みの場合はスキップ
    if logger.handlers:
        return logger
    
    # ログレベル設定
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # フォーマッター
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（ローテーション）
    try:
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"ファイルハンドラー設定エラー: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """ロガーを取得
    
    Args:
        name: ロガー名
    
    Returns:
        ロガー
    """
    return logging.getLogger(name)
