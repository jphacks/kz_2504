export default function AppHeader() {
  return (
    <header className="sticky top-0 z-40 h-12 border-b border-white/10 bg-black text-white">
      <div className="mx-auto flex h-full max-w-[1280px] items-center justify-between px-4">
        {/* 左：黒ロゴ + 赤アクセント */}
        <div className="flex items-center gap-6">
          <a href="/" className="flex items-center">
            <img
              src="/logo.svg"
              alt="4DX@HOME"
              className="h-7 w-auto"
              loading="eager"
            />
          </a>
          <nav className="hidden sm:flex items-center gap-6 text-sm text-white/90">
            <a className="hover:text-white" href="#">映画</a>
            <a className="hover:text-white" href="#">ドキュメンタリー</a>
          </nav>
        </div>

        {/* 右：アイコン */}
        <div className="flex items-center gap-3 text-white/90">
          <button className="rounded-md p-2 hover:bg-white/10" title="アカウント">👤</button>
          <button className="rounded-md p-2 hover:bg-white/10" title="通知">🔔</button>
          <div className="h-6 w-6 rounded-full bg-white/30" title="プロフィール" />
        </div>
      </div>
    </header>
  );
}
