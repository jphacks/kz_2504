import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

/** Select：ヘッダー固定 / ヒーロー全幅 / グリッド */
export default function SelectPage() {
  const navigate = useNavigate();

  const sections = useMemo(() => [
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

  const goPlayer = (id: string) => navigate(`/player?content=${encodeURIComponent(id)}`);

  return (
    <>
      <style>{`
        :root{
          --xh-h: clamp(52px, 7vw, 64px);
          --pad: clamp(12px, 3vw, 18px);
          --ico: clamp(28px, 5vw, 34px);
          --gap: clamp(10px, 2.4vw, 16px);
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

        .xh-top{
          position:fixed; inset:0 0 auto 0; height:var(--xh-h);
          background:#000; border-bottom:1px solid rgba(255,255,255,.08);
          padding:0 var(--pad); z-index:20;
          display:grid; grid-template-columns:auto 1fr auto; align-items:center; column-gap:12px;
        }
        .xh-left{ min-width:0; display:flex; align-items:center; }
        .xh-right{ display:flex; align-items:center; gap:var(--gap); }

        .xh-logoBox{ width:var(--logo-w); height:var(--logo-h); border-radius:8px;
          overflow:hidden; border:1px solid rgba(255,255,255,.12);
          display:grid; place-items:center; background:transparent; }
        .xh-logoImg{ width:100%; height:100%; object-fit:contain; display:block; }

        .xh-ico{ width:var(--ico); height:var(--ico); border-radius:999px; background:#e9e9e9;
          display:grid; place-items:center; box-shadow:0 1px 0 rgba(0,0,0,.5) inset; }
        .xh-ico img{ width:60%; height:60%; object-fit:contain; display:block; filter:saturate(0); }

        .xh-content-pad{ padding-top: var(--xh-h); }

        /* Hero */
        .xh-bleed{ width:100vw; margin-left: calc(50% - 50vw); }
        .xh-hero{ position:relative; aspect-ratio:16/7.5; background: radial-gradient(60% 60% at 50% 40%, #1a1a1a 0%, #000 100%); overflow:hidden; }
        .xh-hero img{ width:100%; height:100%; object-fit:cover; display:block; filter:brightness(.96); }
        .xh-play{ position:absolute; inset:0; display:grid; place-items:center; }
        .xh-play button{ width:clamp(64px,8vw,88px); height:clamp(64px,8vw,88px); border-radius:999px; border:none; background:rgba(255,255,255,.22); cursor:pointer; }
        .xh-play svg{ width:clamp(28px,3.6vw,38px); height:clamp(28px,3.6vw,38px); fill:#fff; margin-left:2px; }

        /* Sections */
        .xh-section{ padding: clamp(18px,3vw,24px) 0; }
        .xh-container{ width:min(1280px, 92vw); margin-inline:auto; }
        .xh-section h2{ margin:0 0 clamp(10px,2vw,14px); font-weight:700; font-size:clamp(18px,2.2vw,22px); }

        .xh-grid{ display:grid; gap: clamp(12px,2.2vw,22px); grid-template-columns: repeat(4, minmax(160px,1fr)); }
        @media (max-width: 900px){ .xh-grid{ grid-template-columns: repeat(3,1fr); } }
        @media (max-width: 640px){ .xh-grid{ grid-template-columns: repeat(2,1fr); } }

        .xh-tile{ position:relative; background:#111; border:1px solid rgba(255,255,255,.06); border-radius:6px; overflow:visible; padding:0; cursor:pointer; box-shadow:0 8px 22px rgba(0,0,0,.25); }
        .xh-thumb{ position:relative; z-index:1; width:100%; aspect-ratio:16/9; object-fit:cover; display:block; border-radius:6px; }
        .xh-rank{ position:absolute; left:-18px; top:-6px; z-index:0; font-family:'Impact','Anton',system-ui,sans-serif; font-size:clamp(48px,7vw,84px); color:transparent; -webkit-text-stroke:3px #fff; text-stroke:3px #fff; line-height:1; opacity:.9; transform:rotate(-2deg); pointer-events:none; }
        .xh-ph{ width:100%; aspect-ratio:16/9; display:grid; place-items:center; background:#151515; color:#9aa3b2; border-radius:6px; }
      `}</style>

      <div className="xh-pg">
        <header className="xh-top" role="banner">
          <div className="xh-left">
            <div className="xh-logoBox" title="Home">
              <img src="/logg.jpeg" alt="Logo" className="xh-logoImg"
                   onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
            </div>
          </div>
          <div aria-hidden="true" />
          <div className="xh-right">
            <div className="xh-ico" title="System">
              <img src="/system.jpeg" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
            </div>
            <div className="xh-ico" title="Notifications">
              <img src="/bell.jpeg" alt="" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
            </div>
          </div>
        </header>

        <div className="xh-content-pad">
          <section className="xh-bleed" aria-label="Featured">
            <div className="xh-hero">
              <img src="/hero/main.jpeg" alt="Featured" onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }} />
              <div className="xh-play">
                <button type="button" aria-label="再生" onClick={()=>goPlayer("featured-main")}>
                  <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                </button>
              </div>
            </div>
          </section>

          {sections.map(sec => (
            <section key={sec.title} className="xh-section">
              <div className="xh-container">
                <h2>{sec.title}</h2>
                <div className="xh-grid">
                  {sec.items.map(it => (
                    <button key={it.id} type="button" className="xh-tile" onClick={()=>goPlayer(it.id)} aria-label={`${sec.title} - ${it.title}`}>
                      <span className="xh-rank">{it.rank}</span>
                      <img className="xh-thumb" src={it.thumb} alt={it.title}
                           onError={(e)=>{ (e.currentTarget as HTMLImageElement).replaceWith(Object.assign(document.createElement('div'),{className:'xh-ph',textContent:'No Image'})); }} />
                    </button>
                  ))}
                </div>
              </div>
            </section>
          ))}
        </div>
      </div>
    </>
  );
}
