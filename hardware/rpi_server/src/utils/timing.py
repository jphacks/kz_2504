"""
4DX@HOME Timing Utilities
タイミング関連のユーティリティ関数
"""

import time
from typing import Optional


def get_current_timestamp() -> float:
    """現在のUnixタイムスタンプを取得（秒）"""
    return time.time()


def get_current_timestamp_ms() -> int:
    """現在のUnixタイムスタンプを取得（ミリ秒）"""
    return int(time.time() * 1000)


def is_within_tolerance(
    target_time: float,
    current_time: float,
    tolerance_ms: int
) -> bool:
    """時刻が許容範囲内かチェック
    
    Args:
        target_time: 目標時刻（秒）
        current_time: 現在時刻（秒）
        tolerance_ms: 許容誤差（ミリ秒）
    
    Returns:
        許容範囲内の場合True
    """
    tolerance_sec = tolerance_ms / 1000.0
    diff = abs(target_time - current_time)
    return diff <= tolerance_sec


def format_duration(seconds: float) -> str:
    """秒数を人間が読みやすい形式にフォーマット
    
    Args:
        seconds: 秒数
    
    Returns:
        フォーマット済み文字列（例: "1m 23s", "45s"）
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if remaining_seconds < 1:
        return f"{minutes}m"
    
    return f"{minutes}m {remaining_seconds:.0f}s"
