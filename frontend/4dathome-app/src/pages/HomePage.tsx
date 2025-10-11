// src/pages/HomePage.tsx
import { useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";

export default function HomePage() {
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);        // 連打防止
  const [playing, setPlaying] = useState(false);  // クリック後に true → video を初生成
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // playing になったら、video がマウントされた直後に再生
  useEffect(() => {
    if (!playing) return;
    const playAfterMount = () => {
      const v = videoRef.current;
      if (!v) return;
      try {
        v.currentTime = 0;
        const p = v.play();
        if (p && typeof p.then === "function") {
          p.catch(() => navigate("/session")); // 再生不可は救済遷移
        }
      } catch {
        navigate("/session");
      }
    };
    const id = requestAnimationFrame(playAfterMount);
    return () => cancelAnimationFrame(id);
  }, [playing, navigate]);

  const handleLogin = () => {
    if (busy) return;
    setBusy(true);
    setPlaying(true); // ← このタイミングで <video> が初めてレンダリングされる
  };

  const handleEnded = () => {
    if (busy) navigate("/session");
  };

  const handleWaitingOrStalled = () => {
    // 稀なスタック対策：軽く再生を促す
    const v = videoRef.current;
    if (!v || !busy) return;
    try {
      const p = v.play();
      if (p && typeof p.then === "function") p.catch(() => {});
    } catch {}
  };

  const handleError = () => {
    if (busy) navigate("/session");
  };

  return (
    <>
      <style>{`
        :root{
          --pad: clamp(12px, 3vw, 18px);
          --title-shift: -8vh; /* タイトル群を少し上へ（調整OK） */
        }
        html, body, #root { margin:0; background:#000; color:#fff; }

        /* ページ全体（フル画面） */
        .xh-page{
          position:fixed; inset:0; width:100vw; height:100svh; /* svhでモバイルUIに強い */
          overflow:hidden;
        }

        /* 初期背景（home.jpeg）。黒文字が読めるようグラデ無効、画像をはっきり見せる */
        .xh-bgImg{
          position:absolute; inset:0;
          width:100%; height:100%; object-fit:cover; display:block;
          opacity:.85;
        }

        /* 中央テキスト（playing でフェードアウト） */
        .xh-center{
          position:relative; z-index:2; width:100%; height:100%;
          display:grid; place-items:center; text-align:center; padding:var(--pad);
        }
        .xh-hero{
          transform: translateY(var(--title-shift));  /* ← 上寄せ */
          transition: opacity .45s ease, transform .45s ease;
        }
        .xh-page.playing .xh-hero{
          opacity:0; transform: translateY(calc(var(--title-shift) + 8px)) scale(.98);
          pointer-events:none;
        }

        /* タイトル＆サブコピー：黒でシンプル、適度な縦間隔 */
        .xh-title{
          font-size: clamp(26px, 6.4vw, 88px); /* 小さめに */
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

        /* ★ ボタンを下寄せするドック（playing でフェードアウト） */
        .xh-btnDock{
          position:absolute; left:0; right:0;
          bottom: max(clamp(36px, 10vh, 120px), env(safe-area-inset-bottom)); /* かなり下寄せ */
          z-index:2;
          display:flex; justify-content:center;
          padding: 0 var(--pad);
          transition: opacity .45s ease, transform .45s ease;
        }
        .xh-page.playing .xh-btnDock{
          opacity:0; transform: translateY(10px);
          pointer-events:none;
        }

        /* CTA（REGISTERは反転配色） */
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

        .xh-btn--primary{ /* LOG IN：白背景×黒文字 */
          background:#fff; color:#000; border:1px solid rgba(0,0,0,.18);
        }
        .xh-btn--primary:hover{ filter:brightness(0.98); }

        .xh-btn--inverted{ /* REGISTER：黒背景×白文字（反転） */
          background:#000; color:#fff; border:1px solid rgba(255,255,255,.28);
        }
        .xh-btn--inverted:hover{ filter:brightness(1.06); }

        /* 動画：画面いっぱい（クリック後に初生成＆フェードイン） */
        .xh-videoWrap{
          position:absolute; inset:0; z-index:3;
          opacity:0; transition: opacity .45s ease;
        }
        .xh-page.playing .xh-videoWrap{ opacity:1; }
        .xh-vid{
          position:absolute; inset:0; width:100%; height:100%;
          object-fit: cover; object-position:center;  /* 画面いっぱい */
          background:#000;
          border:none; border-radius:0; filter:none;
          pointer-events:auto;
        }
      `}</style>

      <div className={`xh-page ${playing ? "playing" : ""}`}>
        {/* 背景（home.jpeg 必須） */}
        <img
          src="/home.jpeg"
          alt=""
          className="xh-bgImg"
          onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }}
        />

        {/* 中央テキスト（黒・シンプル、上寄せ） */}
        <div className="xh-center">
          <div className="xh-hero">
            <h1 className="xh-title">4DX@HOME</h1>
            <p className="xh-sub">小さな画面に大きな迫力</p>
          </div>
        </div>

        {/* ★ 下寄せボタンドック（REGISTERは反転配色） */}
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
              onClick={()=>navigate("/selectpage")}
              disabled={busy}
              aria-disabled={busy}
            >
              REGISTER
            </button>
          </div>
        </div>

        {/* 動画は LOG IN 後にだけ生成して再生（全画面） */}
        {playing && (
          <div className="xh-videoWrap" aria-hidden={!playing}>
            <video
              ref={videoRef}
              className="xh-vid"
              preload="auto"
              playsInline
              muted
              controls={false}
              disablePictureInPicture
              controlsList="nodownload noplaybackrate nofullscreen noremoteplayback"
              onEnded={handleEnded}
              onWaiting={handleWaitingOrStalled}
              onStalled={handleWaitingOrStalled}
              onError={handleError}
            >
              <source src="/logo.mp4" type="video/mp4" />
              {/* WebM があれば追記
              <source src="/logo.webm" type="video/webm" />
              */}
            </video>
          </div>
        )}
      </div>
    </>
  );
}
