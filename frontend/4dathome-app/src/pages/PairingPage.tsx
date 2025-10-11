import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function PairingPage() {
  const [code, setCode] = useState("");
  const nav = useNavigate();

  const normalized = code.trim();
  const isValid = normalized.toLowerCase() === "test" || /^[A-Z0-9]{4}$/.test(normalized);

  const connect = () => {
    if (!isValid) return;
    // 次ページで使えるように保存＋クエリにも付与
    sessionStorage.setItem("sessionCode", normalized);
    nav(`/player?session=${encodeURIComponent(normalized)}`);
  };

  return (
    <section className="mx-auto max-w-xl">
      <h1 className="mb-3 text-2xl font-semibold">🔗 セッション接続</h1>
      <p className="text-sm text-gray-500">
        デバイスのコンソールに表示されたセッションコードを入力してください。
        （開発用ショートカット：<code>test</code>）
      </p>

      <div className="mt-5 rounded-2xl border border-black/5 bg-white p-5 shadow-sm dark:bg-gray-800 dark:border-white/10">
        <label className="block text-sm font-medium mb-2">セッションコード</label>
        <input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="例: A4B7 / test"
          className="w-full rounded-xl border border-black/10 bg-white/80 px-3 py-2 text-lg outline-none placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 dark:bg-gray-900 dark:border-white/10"
        />
        <button
          onClick={connect}
          disabled={!isValid}
          className="mt-4 w-full rounded-xl bg-blue-600 px-4 py-2 text-white disabled:opacity-50 hover:bg-blue-700 transition"
        >
          接続してプレイヤーへ
        </button>
      </div>
    </section>
  );
}
