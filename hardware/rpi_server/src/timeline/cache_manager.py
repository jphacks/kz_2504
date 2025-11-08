"""
4DX@HOME Timeline Cache Manager
タイムラインデータをJSONファイルとしてキャッシュ
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from config import Config

logger = logging.getLogger(__name__)


class TimelineCacheManager:
    """タイムラインキャッシュ管理"""
    
    def __init__(self):
        self.cache_dir = Config.TIMELINE_CACHE_DIR
        
        # キャッシュディレクトリを作成
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def save_timeline(self, session_id: str, timeline_data: Dict) -> str:
        """タイムラインデータを保存
        
        Args:
            session_id: セッションID
            timeline_data: タイムラインデータ
        
        Returns:
            保存したファイルパス
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{session_id}_{timestamp}.json"
            filepath = os.path.join(self.cache_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(timeline_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"タイムライン保存: {filepath}")
            
            return filepath
        
        except Exception as e:
            logger.error(f"タイムライン保存エラー: {e}", exc_info=True)
            raise
    
    def load_timeline(self, filepath: str) -> Optional[Dict]:
        """タイムラインデータを読み込み
        
        Args:
            filepath: ファイルパス
        
        Returns:
            タイムラインデータ（エラー時はNone）
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"ファイルが存在しません: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"タイムライン読み込み: {filepath}")
            
            return data
        
        except Exception as e:
            logger.error(f"タイムライン読み込みエラー: {e}", exc_info=True)
            return None
    
    def load_latest_timeline(self, session_id: str) -> Optional[Dict]:
        """最新のタイムラインデータを読み込み
        
        Args:
            session_id: セッションID
        
        Returns:
            タイムラインデータ（存在しない場合はNone）
        """
        try:
            # セッションIDで始まるファイルを検索
            files = [
                f for f in os.listdir(self.cache_dir)
                if f.startswith(session_id) and f.endswith('.json')
            ]
            
            if not files:
                logger.warning(f"タイムラインキャッシュが見つかりません: {session_id}")
                return None
            
            # 最新ファイルを選択
            latest_file = sorted(files)[-1]
            filepath = os.path.join(self.cache_dir, latest_file)
            
            return self.load_timeline(filepath)
        
        except Exception as e:
            logger.error(f"最新タイムライン読み込みエラー: {e}", exc_info=True)
            return None
    
    def delete_old_caches(self, keep_count: int = 10) -> None:
        """古いキャッシュファイルを削除
        
        Args:
            keep_count: 保持するファイル数
        """
        try:
            files = [
                f for f in os.listdir(self.cache_dir)
                if f.endswith('.json')
            ]
            
            # ファイル数が閾値以下なら削除不要
            if len(files) <= keep_count:
                return
            
            # 古いファイルから削除
            sorted_files = sorted(files)
            delete_count = len(files) - keep_count
            
            for filename in sorted_files[:delete_count]:
                filepath = os.path.join(self.cache_dir, filename)
                os.remove(filepath)
                logger.info(f"古いキャッシュを削除: {filename}")
        
        except Exception as e:
            logger.error(f"キャッシュ削除エラー: {e}", exc_info=True)
    
    def get_cache_stats(self) -> Dict:
        """キャッシュ統計情報を取得"""
        try:
            files = [
                f for f in os.listdir(self.cache_dir)
                if f.endswith('.json')
            ]
            
            total_size = sum(
                os.path.getsize(os.path.join(self.cache_dir, f))
                for f in files
            )
            
            return {
                "total_files": len(files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_dir": self.cache_dir
            }
        
        except Exception as e:
            logger.error(f"キャッシュ統計取得エラー: {e}", exc_info=True)
            return {}
