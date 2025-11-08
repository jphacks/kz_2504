import { useMemo, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

/** Select：ヘッダー固定 / ヒーロー全幅 / グリッド */
export default function SelectPage() {
  // デモ用：認証ガード回避（auth=1を自動セット）
  if (typeof window !== "undefined") {
    try { sessionStorage.setItem("auth", "1"); } catch {}
  }
  const navigate = useNavigate();
  const [isHotSectionVisible, setHotSectionVisible] = useState(false);

  const sections = useMemo(() => [
    {
      title: "今熱い！",
      items: [
        { id: "demo2", rank: 1, thumb: "/thumbs/demo2.jpeg", title: "Demo 1" },
        { id: "demo3", rank: 2, thumb: "/thumbs/demo3.jpeg", title: "Demo 2" },
        { id: "action-3", rank: 3, thumb: "/thumbs/action-3.jpeg", title: "Action 3" },
        { id: "horror-1", rank: 4, thumb: "/thumbs/horror-1.jpeg", title: "Horror 1" },
      ],
    },
    {
      title: "アクション映画",
      items: [
        { id: "action-1", rank: 1, thumb: "/thumbs/action-1.jpeg", title: "Action 1" },
        { id: "action-2", rank: 2, thumb: "/thumbs/action-2.jpeg", title: "Action 2" },
        { id: "action-3", rank: 3, thumb: "/thumbs/action-3.jpeg", title: "Action 3" },
        { id: "action-4", rank: 4, thumb: "/thumbs/action-4.jpeg", title: "Action 4" },
      ],
    },
    {
      title: "ホラー映画",
      items: [
        { id: "horror-1", rank: 1, thumb: "/thumbs/horror-1.jpeg", title: "Horror 1" },
        { id: "horror-2", rank: 2, thumb: "/thumbs/horror-2.jpeg", title: "Horror 2" },
        { id: "horror-3", rank: 3, thumb: "/thumbs/horror-3.jpeg", title: "Horror 3" },
        { id: "horror-4", rank: 4, thumb: "/thumbs/horror-4.jpeg", title: "Horror 4" },
      ],
    },
  ], []);

  // 「今熱い！」セクションのサムネイル画像を事前チェック
  useEffect(() => {
    const hotSection = sections.find(sec => sec.title === "今熱い！");
    if (!hotSection || !hotSection.items.length) {
      setHotSectionVisible(false);
      return;
    }

    const thumbnails = hotSection.items.map(item => item.thumb);
    let cancelled = false;
    let remaining = thumbnails.length;
    let hasError = false;

    thumbnails.forEach((url) => {
      const img = new Image();
      img.onload = () => {
        remaining -= 1;
        if (!cancelled && remaining === 0 && !hasError) {
          setHotSectionVisible(true);
        }
      };
      img.onerror = () => {
        if (!cancelled) {
          hasError = true;
          setHotSectionVisible(false);
        }
      };
      img.src = url;
    });

    return () => {
      cancelled = true;
    };
  }, [sections]);

  // 動画IDとメタデータを取得して準備画面へ遷移
  const goPlayer = (id: string, title?: string, thumb?: string) => {
    // 動画情報をsessionStorageに保存
    const selectedVideo = {
      id,
      title: title || id.toUpperCase(),
      thumbnailUrl: thumb || `/thumbs/${id}.jpeg`,
    };
    try {
      sessionStorage.setItem("selectedVideo", JSON.stringify(selectedVideo));
    } catch (e) {
      console.error("Failed to save selectedVideo:", e);
    }
    navigate(`/prepare?content=${encodeURIComponent(id)}`);
  };

  return (
    <>
      <style>{`
        :root{
          --xh-h: clamp(52px, 7vw, 64px);
          --pad: clamp(12px, 3vw, 18px);
          --ico: clamp(28px, 4.8vw, 36px);  
          --gap: clamp(14px, 3vw, 22px);     
          --logo-h: clamp(32px, 5vw, 44px);
          --logo-w-base: calc(var(--logo-h) * 2);
          --logo-w: max(80px, min(
            var(--logo-w-base),
            calc(100vw - (var(--pad) * 2) - (var(--ico) * 2) - var(--gap) - 12px)
          ));
          --xh-text:#f2f2f2;
        }
        html, body, #root { background:#0e1324; }
        .xh-pg{ min-height:100vh; color:var(--xh-text); font-family: system-ui,-apple-system,Segoe UI,Roboto,"Noto Sans JP",sans-serif; }

        /* ====== Header（本文幅に揃える） ====== */
        .xh-top{
          position:fixed; inset:0 0 auto 0; height:var(--xh-h);
          background:#000; border-bottom:1px solid rgba(255,255,255,.08);
          z-index:20; padding:0;
        }
        .xh-head{
          width:min(1280px, 92vw);
          margin:0 auto; height:100%;
          display:grid; grid-template-columns:auto 1fr auto; align-items:center; column-gap:12px;
          padding:0 var(--pad);                   /* ← Pairing と同じ左右パディング */
        }
        .xh-left{ min-width:0; display:flex; align-items:center; gap: clamp(18px, 3.2vw, 32px); }
        .xh-right{
          display:flex; align-items:center;
          gap: calc(var(--gap) + 6px);            /* ← アイコン間少し広め */
          padding-right: calc(var(--pad) * .6);   /* ← 右端との余白も少し */
        }

        .xh-logoBox{ width:var(--logo-w); height:var(--logo-h); border-radius:8px;
          overflow:hidden; border:1px solid rgba(255,255,255,.12);
          display:grid; place-items:center; background:transparent; }
        .xh-logoImg{ width:100%; height:100%; object-fit:contain; display:block; }

        /* ロゴ右のカテゴリ（左詰め） */
        .xh-nav{ display:flex; align-items:center; gap: clamp(14px,2.4vw,22px); font-weight:700; letter-spacing:.02em; }
        .xh-nav .dot::before{ content:"・"; margin:0 .5em; opacity:.9; }

        /* 右側アイコン：PNG / 白塗り / 丸囲みなし */
        .xh-ico{ display:flex; align-items:center; justify-content:center; width:auto; height:auto; background:transparent; border:none; padding:0; }
        .xh-ico img{ width:var(--ico); height:auto; display:block; filter: brightness(0) invert(1); }

        .xh-content-pad{ padding-top: var(--xh-h); }

        /* ====== Hero（縦低め + 下部グラデ + △のみ + PR文を左下に） ====== */
        .xh-bleed{ width:100vw; margin-left: calc(50% - 50vw); }
        .xh-hero{ position:relative; aspect-ratio:16/5.5; background:#000; overflow:hidden; cursor:pointer; }
        .xh-hero img{ width:100%; height:100%; object-fit:cover; display:block; filter:brightness(.96); }
        .xh-hero .xh-grad{ position:absolute; left:0; right:0; bottom:0; height:46%;
          background:linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,.75) 100%); }

        .xh-play{ position:absolute; inset:0; display:grid; place-items:center; }
        .xh-play button{ background:transparent; border:none; padding: clamp(6px,1vw,10px); cursor:pointer; }
        .xh-play svg{ width:clamp(28px,3.6vw,38px); height:clamp(28px,3.6vw,38px); fill:#fff; margin-left:2px; }

        /* PR文：左下（背景なし・大きめ） */
        .xh-heroCopy{
          position:absolute;
          left: clamp(16px, 5vw, 48px);
          bottom: clamp(14px, 4vw, 48px);
          z-index:2;
          display:grid;
          gap: clamp(6px, 1.2vw, 10px);
          pointer-events:none;
          color:#fff;
          text-shadow: 0 2px 14px rgba(0,0,0,.6);
        }
        .xh-pill{ background: transparent; border: none; padding: 0; font-weight: 900; letter-spacing: .16em; font-size: clamp(18px, 3.2vw, 28px); }
        .xh-kv{ font-weight: 900; line-height: 1.1; font-size: clamp(22px, 5vw, 56px); }

        /* ====== Sections ====== */
        .xh-section{ padding: clamp(18px,3vw,24px) 0; }
        .xh-container{ width:min(1280px, 92vw); margin-inline:auto; }
        .xh-section h2{ margin:0 0 clamp(10px,2vw,14px); font-weight:700; font-size:clamp(18px,2.2vw,22px); }

        .xh-grid{ display:grid; gap: clamp(12px,2.2vw,22px); grid-template-columns: repeat(4, minmax(160px,1fr)); }
        @media (max-width: 900px){ .xh-grid{ grid-template-columns: repeat(3,1fr); } }
        @media (max-width: 640px){ .xh-grid{ grid-template-columns: repeat(2,1fr); } }

        /* タイル：ランキング背景は黒、数字は画像の後ろ（溢れ可） */
        .xh-tile{
          position:relative; background:#000;
          border:1px solid rgba(255,255,255,.06); border-radius:6px;
          overflow:visible; padding:0; cursor:pointer; box-shadow:0 8px 22px rgba(0,0,0,.25);
        }
        .xh-thumb{
          position:relative; z-index:1; width:100%;
          aspect-ratio:16/9;
          object-fit:cover;
          object-position: top center; /* 上側優先 */
          display:block; border-radius:6px;
        }
        .xh-tile .xh-grad{
          position:absolute; left:0; right:0; bottom:0; height:46%;
          background:linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,.75) 100%);
          z-index:2; border-bottom-left-radius:6px; border-bottom-right-radius:6px;
        }

        /* ★ ランキング数字：少し“多めに”左へ突き出す（かつ画像の後ろ） */
        .xh-rank{
          position:absolute;
          left: clamp(-22px, -2.5vw, -22px); 
          top: clamp(10px,  10px);
          z-index:0;                          /* ← 画像(xh-thumb: z-index:1)の“後ろ”に置く */
          font-family:'Impact','Anton',system-ui,sans-serif;
          font-size:clamp(44px,7vw,84px);
          color:transparent; -webkit-text-stroke:3px #fff; text-stroke:3px #fff;
          line-height:1; opacity:.9; transform:rotate(-2deg); pointer-events:none;
        }

        .xh-ph{ width:100%; aspect-ratio:16/9; display:grid; place-items:center; background:#151515; color:#9aa3b2; border-radius:6px; }
      `}</style>

      <div className="xh-pg">
        <header className="xh-top" role="banner">
          <div className="xh-head">
            <div className="xh-left">
              <div className="xh-logoBox" title="Home">
                <img src="/logg.jpeg" alt="Logo" className="xh-logoImg"
                     onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              </div>
              <nav className="xh-nav" aria-label="カテゴリ">
                <span>映画</span><span className="dot"></span>
                <span>アニメ</span><span className="dot"></span>
                <span>ヒューマンドラマ</span>
              </nav>
            </div>
            <div aria-hidden="true" />
            <div className="xh-right">
              <div className="xh-ico" title="System">
                <img src="/system.png" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              </div>
              <div className="xh-ico" title="Notifications">
                <img src="/bell.png" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              </div>
            </div>
          </div>
        </header>

        <div className="xh-content-pad">
          <section className="xh-bleed" aria-label="Featured">
            {/* 画像クリックで main 再生 */}
            <div className="xh-hero" onClick={()=>goPlayer("main", "WILDCARD - 世界を揺らす、没入型ホームシネマ。", "/hero/main.gif")} role="button" tabIndex={0}>
              <img src="/hero/main.gif" alt="Featured"
                   onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              <div className="xh-grad" aria-hidden="true"></div>

              {/* PRコピー：左下、背景なし、文字大きめ */}
              <div className="xh-heroCopy" aria-hidden="true">
                <span className="xh-pill">WIRLDC@RD</span>
                <div className="xh-kv">世界を揺らす、没入型ホームシネマ。</div>
              </div>

              <div className="xh-play">
                {/* △のみ（丸なし） */}
                <button type="button" aria-label="再生" onClick={(e)=>{ e.stopPropagation(); goPlayer("main", "WILDCARD - 世界を揺らす、没入型ホームシネマ。", "/hero/main.gif"); }}>
                  <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                </button>
              </div>
            </div>
          </section>

          {sections.map(sec => {
            // 「今熱い！」セクションは画像が全て正常に読み込めた場合のみ表示
            if (sec.title === "今熱い！" && !isHotSectionVisible) {
              return null;
            }
            
            return (
              <section key={sec.title} className="xh-section">
                <div className="xh-container">
                  <h2>{sec.title}</h2>
                  <div className="xh-grid">
                    {sec.items.map(it => (
                      <button key={it.id} type="button" className="xh-tile" onClick={()=>goPlayer(it.id, it.title, it.thumb)} aria-label={`${sec.title} - ${it.title}`}>
                        <span className="xh-rank">{it.rank}</span>
                        <img
                          className="xh-thumb"
                          src={it.thumb}
                          alt={it.title}
                          onError={(e)=>{ (e.currentTarget as HTMLImageElement).replaceWith(Object.assign(document.createElement('div'),{className:'xh-ph',textContent:'No Image'})); }}
                        />
                        <div className="xh-grad" aria-hidden="true"></div>
                      </button>
                    ))}
                  </div>
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </>
  );
}
