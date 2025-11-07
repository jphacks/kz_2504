import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BACKEND_WS_URL } from "../config/backend";
import TimelineUploadButton from "../components/TimelineUploadButton";
import { deviceApi } from "../services/endpoints";

export default function VideoPreparationPage() {
  const { search } = useLocation();
  const q = useMemo(() => new URLSearchParams(search), [search]);
  const navigate = useNavigate();

  const [sessionId, setSessionId] = useState("");
  const [deviceHubId, setDeviceHubId] = useState("");
  const [isDeviceConnecting, setIsDeviceConnecting] = useState(false);
  const [isDeviceConnected, setIsDeviceConnected] = useState(false);
  const [isTimelineSent, setIsTimelineSent] = useState(false);
  const [timelineUploading, setTimelineUploading] = useState(false);
  const [devicesTesting, setDevicesTesting] = useState(false);
  const [isDevicesTested, setIsDevicesTested] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const connInfoRef = useRef<string | null>(null);

  // セッションIDやハブIDは手動入力のみ（URLクエリから自動入力しない）

  const waitWsHandshake = (timeoutMs = 5000): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      if (connInfoRef.current) return resolve(true);
      const ws = wsRef.current;
      let settled = false;
      const done = (ok: boolean) => {
        if (settled) return; settled = true;
        try { ws?.removeEventListener("message", onMsg); } catch {}
        try { ws?.removeEventListener("open", onOpen); } catch {}
        try { ws?.removeEventListener("close", onClose); } catch {}
        clearTimeout(timer);
        resolve(ok);
      };
      const onMsg = (ev: MessageEvent) => {
        try {
          const j = JSON.parse((ev as any).data);
          if (j?.type === "connection_established") {
            connInfoRef.current = j.connection_id;
            done(true);
          }
        } catch {}
      };
      const onOpen = () => setTimeout(() => !settled && done(true), 400);
      const onClose = () => !settled && done(false);
      const timer = setTimeout(() => done(false), timeoutMs);
      wsRef.current?.addEventListener("message", onMsg);
      wsRef.current?.addEventListener("open", onOpen);
      wsRef.current?.addEventListener("close", onClose);
    });
  };

  const connectWS = () => {
    try {
      const sid = (sessionId || "").trim();
      const hub = (deviceHubId || "").trim();
      if (!sid) { setError("セッションIDを入力してください"); return; }
      const url = hub
        ? `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sid)}?hub=${encodeURIComponent(hub)}`
        : `${BACKEND_WS_URL}/api/playback/ws/sync/${encodeURIComponent(sid)}`;

      if (wsRef.current) { try { wsRef.current.close(); } catch {} wsRef.current = null; }
      const ws = new WebSocket(url);
      wsRef.current = ws;

      setIsDeviceConnecting(true);

      ws.onopen = () => {
        if (hub && ws.readyState === WebSocket.OPEN) {
          try { ws.send(JSON.stringify({ type: "identify", hub_id: hub })); } catch {}
        }
        setTimeout(() => {
          if (!isDeviceConnected) setIsDeviceConnected(true);
          setIsDeviceConnecting(false);
        }, 600);
      };
      ws.onmessage = (ev) => {
        try {
          const j = JSON.parse(ev.data);
          if (j?.type === "connection_established") {
            connInfoRef.current = j.connection_id;
            setIsDeviceConnected(true);
            setIsDeviceConnecting(false);
          }
        } catch {}
      };
      ws.onerror = () => { setError("WebSocket error"); };
      ws.onclose = () => { /* no-op */ };
    } catch (e: any) {
      setError(`接続エラー: ${e?.message || String(e)}`);
      setIsDeviceConnecting(false);
    }
  };

  const handleStart = () => {
    // ここまで完了後、playerへ遷移
    const params = new URLSearchParams();
    params.set("session", (sessionId || "").trim());
    if (deviceHubId.trim()) params.set("hub", deviceHubId.trim());
    const content = q.get("content") || "demo1";
    if (content) params.set("content", content);

    // 永続化
    try { sessionStorage.setItem("sessionId", (sessionId || "").trim()); } catch {}
    try { if (deviceHubId) sessionStorage.setItem("deviceHubId", deviceHubId.trim()); } catch {}

    navigate(`/player?${params.toString()}`);
  };

  const onTimelineComplete = () => setIsTimelineSent(true);
  const onTimelineError = (e: Error) => setError(`タイムライン送信に失敗しました: ${e.message || String(e)}`);

  const handleDeviceTest = async () => {
    if (!sessionId) { setError("セッションIDが設定されていません"); return; }
    if (!isTimelineSent) { setError("先にタイムラインを送信してください"); return; }
    if (!isDeviceConnected) { setError("先にデバイスを接続してください"); return; }
    setError(null);
    setDevicesTesting(true);
    try {
      const result = await deviceApi.test("basic", sessionId);
      if (result?.status?.toLowerCase?.() === "success") {
        setIsDevicesTested(true);
      } else {
        throw new Error(result?.message || `status: ${result?.status}`);
      }
    } catch (e: any) {
      setError(`デバイステスト失敗: ${e?.message || String(e)}`);
      setIsDevicesTested(false);
    } finally {
      setDevicesTesting(false);
    }
  };

  const allReady = isDeviceConnected && isTimelineSent && isDevicesTested;

  return (
    <div className="prep-wrapper" style={{minHeight:"100vh",background:"#0b0f1a",display:"grid",placeItems:"center",color:"#fff"}}>
      <div className="prep-card" style={{width:"min(560px,92%)",background:"rgba(16,20,32,.9)",border:"1px solid rgba(255,255,255,.12)",borderRadius:14,padding:"clamp(18px,3.5vw,28px)"}}>
        <h2 style={{fontWeight:800,fontSize:"clamp(18px,3.6vw,22px)",margin:"0 0 14px"}}>再生準備</h2>

        <div style={{padding:"12px 0 14px",borderBottom:"1px solid rgba(255,255,255,.08)"}}>
          <div className="prep-label" style={{fontSize:13,opacity:.9,marginBottom:6}}>セッションID</div>
          <div style={{display:"grid",gridTemplateColumns:"1fr auto",gap:10,alignItems:"center"}}>
            <input className="xh-input" placeholder="例: session01" value={sessionId} onChange={(e)=>setSessionId(e.target.value)} style={{width:"100%",height:"clamp(40px,6.6vw,48px)",background:"#fff",color:"#111",borderRadius:6,border:"2px solid #111",padding:"0 12px"}}/>
            <button className="xh-btn xh-login" onClick={()=>{ if(!sessionId.trim()){setError("セッションIDを入力してください");return;} setError(null); try{sessionStorage.setItem("sessionId",sessionId.trim());}catch{} }} style={{height:"clamp(42px,7vw,48px)",borderRadius:8,fontWeight:700,background:"#fff",color:"#111"}}>適用</button>
          </div>
        </div>

        <div style={{padding:"12px 0 14px",borderBottom:"1px solid rgba(255,255,255,.08)"}}>
          <div className="prep-label" style={{fontSize:13,opacity:.9,marginBottom:6}}>デバイスハブID</div>
          <div style={{display:"grid",gridTemplateColumns:"1fr auto",gap:10,alignItems:"center"}}>
            <input className="xh-input" placeholder="例: DH001" value={deviceHubId} onChange={(e)=>setDeviceHubId(e.target.value)} style={{width:"100%",height:"clamp(40px,6.6vw,48px)",background:"#fff",color:"#111",borderRadius:6,border:"2px solid #111",padding:"0 12px"}}/>
            <button className="xh-btn xh-login" onClick={connectWS} disabled={isDeviceConnected || isDeviceConnecting} style={{height:"clamp(42px,7vw,48px)",borderRadius:8,fontWeight:700,background:"#fff",color:"#111"}}>{isDeviceConnecting?"接続中…":isDeviceConnected?"接続済み":"接続"}</button>
          </div>
          <div style={{marginTop:8,fontSize:12,opacity:.95,color:isDeviceConnected?"#79ff7a":"#fff"}}>{isDeviceConnected?"接続確認完了":(isDeviceConnecting?"接続確認中…":"未接続")}</div>
        </div>

        <div style={{padding:"12px 0 14px",borderBottom:"1px solid rgba(255,255,255,.08)"}}>
          <div className="prep-label" style={{fontSize:13,opacity:.9,marginBottom:6}}>タイムラインJSON送信</div>
          <div>
            {isTimelineSent ? (
              <div style={{fontSize:12,color:"#79ff7a"}}>送信完了</div>
            ) : (
              <TimelineUploadButton
                sessionId={sessionId}
                videoId={q.get("content") || 'demo1'}
                onComplete={onTimelineComplete}
                onError={onTimelineError}
                onUploadingChange={(u)=>setTimelineUploading(u)}
                className="xh-btn xh-login"
              />
            )}
          </div>
        </div>

        <div style={{padding:"12px 0 14px",borderBottom:"1px solid rgba(255,255,255,.08)"}}>
          <div className="prep-label" style={{fontSize:13,opacity:.9,marginBottom:6}}>デバイス動作確認</div>
          <div>
            {isDevicesTested ? (
              <div style={{fontSize:12,color:"#79ff7a"}}>確認完了</div>
            ) : (
              <button className="xh-btn xh-login" onClick={handleDeviceTest} disabled={!isTimelineSent || devicesTesting} style={{height:"clamp(42px,7vw,48px)",borderRadius:8,fontWeight:700,background:"#fff",color:"#111"}}>
                {devicesTesting?"テスト実行中…":"テスト実行"}
              </button>
            )}
          </div>
        </div>

        {error && <div style={{marginTop:8,fontSize:12,color:"#ff9f9f"}}>⚠ {error}</div>}

        <div style={{padding:"12px 0 0"}}>
          <div className="prep-label" style={{fontSize:13,opacity:.9,marginBottom:6}}>準備完了後の開始</div>
          <button className="xh-btn xh-login" onClick={handleStart} disabled={!allReady} style={{width:"100%",height:"clamp(42px,7vw,48px)",borderRadius:8,fontWeight:700,background:"#fff",color:"#111",marginBottom:10}}>
            再生を開始する
          </button>
          <button className="xh-btn" onClick={handleStart} style={{width:"100%",height:"clamp(38px,6vw,42px)",borderRadius:8,fontWeight:600,background:"rgba(74,144,226,0.2)",color:"#4a90e2",border:"1px solid #4a90e2"}}>
            テスト: 準備をスキップして再生画面へ
          </button>
        </div>
      </div>
    </div>
  );
}
