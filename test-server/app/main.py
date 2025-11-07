from __future__ import annotations
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="4DX@HOME Sync WS (minimal)")

# CORS（念のため。WSにも効きます）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# セッションID -> 接続セット
SESSIONS: Dict[str, Set[WebSocket]] = {}
# 接続メタ（roleなど）: conn_id -> dict
CONN_META: Dict[str, dict] = {}
# 逆引き: WebSocket -> conn_id
SOCK_TO_ID: Dict[WebSocket, str] = {}

# 送信ヘルパ
async def _safe_send(ws: WebSocket, payload: dict):
    try:
        await ws.send_text(json.dumps(payload))
    except Exception:
        # クライアント切断等は放置（クリーンアップ時に除外される）
        pass

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def register_socket(session_id: str, ws: WebSocket, role: str) -> str:
    await ws.accept()
    conn_id = f"{role}_{uuid.uuid4().hex[:8]}"
    SESSIONS.setdefault(session_id, set()).add(ws)
    CONN_META[conn_id] = {"role": role, "session_id": session_id}
    SOCK_TO_ID[ws] = conn_id

    # 仕様に寄せた初回メッセージ
    await _safe_send(ws, {
        "type": "connection_established",
        "connection_id": conn_id,
        "session_id": session_id,
        "server_time": _now_iso(),
        "message": "WebSocket接続が確立されました",
    })
    print(f"[JOIN] session={session_id} conn={conn_id} role={role} now={_now_iso()}")
    return conn_id

def unregister_socket(ws: WebSocket):
    conn_id = SOCK_TO_ID.get(ws)
    meta = CONN_META.pop(conn_id, None) if conn_id else None
    if meta:
        ses = meta["session_id"]
        if ses in SESSIONS and ws in SESSIONS[ses]:
            SESSIONS[ses].discard(ws)
            if not SESSIONS[ses]:
                SESSIONS.pop(ses, None)
    if ws in SOCK_TO_ID:
        SOCK_TO_ID.pop(ws, None)
    print(f"[LEAVE] conn={conn_id} meta={meta}")

async def broadcast(session_id: str, payload: dict, *, exclude: Optional[WebSocket] = None, to_role: Optional[str] = None):
    # 同じセッションの他クライアントへブロードキャスト
    conns = list(SESSIONS.get(session_id, set()))
    for ws in conns:
        if ws is exclude:
            continue
        target_id = SOCK_TO_ID.get(ws)
        target_meta = CONN_META.get(target_id or "", {})
        if to_role and target_meta.get("role") != to_role:
            continue
        await _safe_send(ws, payload)

@app.get("/health")
async def health():
    return {"ok": True, "sessions": {k: len(v) for k, v in SESSIONS.items()}}

# === コア: Player/Device 双方が同じセッションに繋ぐ ===
# 例）
#  Player:  ws://localhost:8004/api/playback/ws/sync/debug123?role=player
#  Device:  ws://localhost:8004/api/playback/ws/sync/debug123?role=device
@app.websocket("/api/playback/ws/sync/{session_id}")
async def ws_sync(websocket: WebSocket, session_id: str, role: str = Query("player")):
    conn_id = await register_socket(session_id, websocket, role)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            # Player から 0.5s ごとに飛んでくる payload 例:
            # { type:"sync", state:"play|pause|seeking|seeked", time:12.34, duration:120.0, ts: 172... }
            if data.get("type") == "sync":
                # サーバ側にログ出力（time/state を確認用にコンソールへ）
                print(f"[SYNC] ses={session_id} from={conn_id} state={data.get('state')} time={data.get('time'):.3f}")

                # 送信者へ ACK（仕様書の形に寄せる）
                ack = {
                    "type": "sync_ack",
                    "session_id": session_id,
                    "received_time": data.get("time", 0.0),
                    "received_state": data.get("state", "pause"),
                    "server_time": _now_iso(),
                    "relayed_to_devices": True,
                }
                await _safe_send(websocket, ack)

                # 他クライアントへ中継
                relay = {
                    "type": "sync",
                    "from": conn_id,
                    "session_id": session_id,
                    "state": data.get("state"),
                    "time": data.get("time"),
                    "duration": data.get("duration"),
                    "ts": data.get("ts"),
                    "server_time": _now_iso(),
                }

                # 送信元が player のときは device へ、device のときは player へ飛ばす（どちらでも良い）
                from_role = CONN_META.get(conn_id, {}).get("role", "player")
                target_role = "device" if from_role == "player" else "player"
                await broadcast(session_id, relay, exclude=websocket, to_role=target_role)

            else:
                # その他のメッセージはそのまま全員へ（簡易）
                await broadcast(session_id, {"type": "passthrough", "from": conn_id, **data}, exclude=websocket)

    except WebSocketDisconnect:
        pass
    finally:
        unregister_socket(websocket)
