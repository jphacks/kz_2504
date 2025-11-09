// src/pages/HomePage.tsx
import { useNavigate } from "react-router-dom";
import { useRef, useState } from "react";

export default function HomePage() {
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);          // 連打防止（ボタン用）
  const [playing, setPlaying] = useState(true);     // アクセス時に動画前面表示
  const [showVideo, setShowVideo] = useState(true); // マウント制御（フェード後に外す）
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // LOG IN は即遷移（動画は関与しない）
  const handleLogin = () => {
    if (busy) return;
    setBusy(true);
    navigate("/login");
  };

  // 再生終了：まず不透明度を下げてからアンマウント
  const handleEnded = () => {
    setPlaying(false);                      // .xh-page から playing クラスが外れてフェードアウト
    setTimeout(() => setShowVideo(false), 200); // CSSのtransition時間に合わせて外す
  };

  // 停止・待ち状態になったとき、再度 play を試みる（無音なので大抵OK）
  const handleWaitingOrStalled = () => {
    const v = videoRef.current;
    if (!v) return;
    try {
      const p = v.play();
      if (p && typeof p.then === "function") {
        p.catch((err) => {
          console.warn("[home video] recover play failed", err);
        });
      }
    } catch (err) {
      console.warn("[home video] recover play threw", err);
    }
  };

  const handleError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error("[home video] error", e);
    // エラー時も静かにフェードアウトして非表示
    setPlaying(false);
    setTimeout(() => setShowVideo(false), 500);
  };

  return (
    <>
      <style>{`
        :root{
          --pad: clamp(12px, 3vw, 18px);
          --title-shift: -8vh;
        }
        html, body, #root { margin:0; background:#000; color:#fff; }

        .xh-page{
          position:fixed; inset:0; width:100vw; height:100svh;
          overflow:hidden;
        }

        .xh-bgImg{
          position:absolute; inset:0;
          width:100%; height:100%; object-fit:cover; display:block;
          opacity:.85;
        }

        .xh-center{
          position:relative; z-index:2; width:100%; height:100%;
          display:grid; place-items:center; text-align:center; padding:var(--pad);
        }
        .xh-hero{
          transform: translateY(var(--title-shift));
          transition: opacity .45s ease, transform .45s ease;
        }
        /* アクセス直後は動画が前面なのでテキスト/ボタンは薄くする */
        .xh-page.playing .xh-hero{
          opacity:0; transform: translateY(calc(var(--title-shift) + 8px)) scale(.98);
          pointer-events:none;
        }

        .xh-title{
          font-size: clamp(26px, 6.4vw, 88px);
          font-weight: 900;
          letter-spacing: .04em;
          line-height: 1.08;
          margin: 0 0 clamp(10px, 2.2vw, 18px);
          color: #000;
          text-shadow: none;
        }
        .xh-sub{
          font-size: clamp(16px, 2.6vw, 26px);
          font-weight: 600;
          letter-spacing: .03em;
          margin: 0;
          color: #000;
        }

        .xh-btnDock{
          position:absolute; left:0; right:0;
          bottom: max(clamp(36px, 10vh, 120px), env(safe-area-inset-bottom));
          z-index:2;
          display:flex; justify-content:center;
          padding: 0 var(--pad);
          transition: opacity .45s ease, transform .45s ease;
        }
        .xh-page.playing .xh-btnDock{
          opacity:0; transform: translateY(10px);
          pointer-events:none;
        }

        .xh-ctas{
          display:flex; gap: clamp(16px, 3.2vw, 24px);
          justify-content:center; flex-wrap:wrap; margin:0;
        }
        .xh-btn{
          min-width: clamp(180px, 28vw, 280px);
          padding: 14px 20px; border-radius:10px; font-weight:800; letter-spacing:.04em;
          cursor:pointer; transition: transform .06s ease, filter .2s ease, opacity .2s ease;
        }
        .xh-btn:hover{ transform:translateY(-1px); }
        .xh-btn:active{ transform:translateY(0); }
        .xh-btn[disabled]{ opacity:.6; cursor:not-allowed; }

        .xh-btn--primary{ background:#fff; color:#000; border:1px solid rgba(0,0,0,.18); }
        .xh-btn--primary:hover{ filter:brightness(0.98); }

        .xh-btn--inverted{ background:#000; color:#fff; border:1px solid rgba(255,255,255,.28); }
        .xh-btn--inverted:hover{ filter:brightness(1.06); }

        /* 動画：フェード用。playing クラス中のみ不透明 */
        .xh-videoWrap{
          position:absolute; inset:0; z-index:3;
          opacity:0; transition: opacity .2s ease;
        }
        .xh-page.playing .xh-videoWrap{ opacity:1; }

        .xh-vid{
          position:absolute; inset:0; width:100%; height:100%;
          object-fit: cover; object-position:center;
          background:#000;
          border:none; border-radius:0; filter:none;
          pointer-events:auto;
        }
      `}</style>

      <div className={`xh-page ${playing ? "playing" : ""}`}>
        <img
          src="/home.jpeg"
          alt=""
          className="xh-bgImg"
          onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }}
        />

        <div className="xh-center">
          <div className="xh-hero">
            <h1 className="xh-title">4DX@HOME</h1>
            <p className="xh-sub">小さな画面に大きな迫力</p>
          </div>
        </div>

        <div className="xh-btnDock">
          <div className="xh-ctas">
            <button
              className="xh-btn xh-btn--primary"
              onClick={handleLogin}
              disabled={busy}
              aria-busy={busy}
            >
              {busy ? "LOADING..." : "LOG IN"}
            </button>
            <button
              className="xh-btn xh-btn--inverted"
              onClick={() => {
                try { sessionStorage.setItem("auth", "guest"); } catch {}
                navigate("/selectpage");
              }}
              disabled={busy}
              aria-disabled={busy}
            >
              GUEST
            </button>
          </div>
        </div>

        {/* アクセス時に自動再生 → 終了でフェードアウトしてからアンマウント */}
        {showVideo && (
          <div className="xh-videoWrap" aria-hidden={!playing}>
            <video
              ref={videoRef}
              className="xh-vid"
              preload="auto"
              playsInline
              muted
              autoPlay
              controls={false}
              disablePictureInPicture
              controlsList="nodownload noplaybackrate nofullscreen noremoteplayback"
              onPlay={() => setPlaying(true)}
              onEnded={handleEnded}
              onWaiting={handleWaitingOrStalled}
              onStalled={handleWaitingOrStalled}
              onError={handleError}
            >
              <source src="/logo.mp4" type="video/mp4" />
              {/* 必要なら WebM も追加
              <source src="/logo.webm" type="video/webm" />
              */}
            </video>
          </div>
        )}
      </div>
    </>
  );
}
