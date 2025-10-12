"""
Phase B-3 再生モデル定義（簡素化版）

receiver.py + ws_video_sync_sender.htmlパターンに準拠
サーバーは単純な中継役として動作し、フロントエンドが全制御を担当
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# receiver.py + ws_video_sync_sender.html パターンに準拠した単純なモデル

class SyncMessage(BaseModel):
    """
    フロントエンド同期メッセージ（ws_video_sync_sender.html準拠）
    サーバーは受信したデータをそのまま中継
    """
    type: str = "sync"
    state: str = Field(..., description="再生状態 (play, pause, seeking, seeked)")
    time: float = Field(ge=0.0, description="動画再生時刻（秒）")
    duration: float = Field(ge=0.0, description="動画総再生時間（秒）") 
    ts: Optional[int] = Field(None, description="クライアント送信タイムスタンプ（ミリ秒）")

class DeviceStatus(BaseModel):
    """デバイス状態情報（最小限）"""
    type: str = "device_status"
    device_id: str
    status: str = Field(..., description="ready, busy, error, offline")
    json_loaded: bool = Field(False, description="demo1.json読み込み状態")

# WebSocket応答メッセージ（簡素化）
class ConnectionEstablished(BaseModel):
    """WebSocket接続確立応答"""
    type: str = "connection_established"
    connection_id: str
    session_id: str
    server_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    message: str = "WebSocket接続が確立されました"

class SyncAcknowledge(BaseModel):
    """同期確認応答"""
    type: str = "sync_ack"
    session_id: str
    received_time: float
    received_state: str
    server_time: str = Field(default_factory=lambda: datetime.now().isoformat())
    relayed_to_devices: bool = False

class DeviceConnected(BaseModel):
    """デバイス接続確認"""
    type: str = "device_connected"
    connection_id: str
    session_id: str
    server_time: str = Field(default_factory=lambda: datetime.now().isoformat())

# ==========================================
# 簡素化ユーティリティ関数
# ==========================================

def create_sync_message_from_dict(data: dict) -> SyncMessage:
    """辞書からSyncMessageを作成"""
    return SyncMessage(**data)

def validate_sync_message(data: dict) -> tuple[bool, Optional[str]]:
    """同期メッセージの検証"""
    try:
        SyncMessage(**data)
        return True, None
    except Exception as e:
        return False, str(e)

def validate_device_status(data: dict) -> tuple[bool, Optional[str]]:
    """デバイス状態の検証"""
    try:
        DeviceStatus(**data)
        return True, None
    except Exception as e:
        return False, str(e)

# receiver.pyパターンに準拠した中継データ作成
def create_relay_data(session_id: str, sync_data: dict) -> dict:
    """
    フロントエンドから受信した同期データを
    そのままデバイスに中継するための形式に変換
    """
    return {
        "type": "video_sync",
        "session_id": session_id,
        "video_time": sync_data.get("time", 0),
        "video_state": sync_data.get("state", "unknown"),
        "video_duration": sync_data.get("duration"),
        "client_timestamp": sync_data.get("ts"),
        "server_timestamp": int(datetime.now().timestamp() * 1000)
    }