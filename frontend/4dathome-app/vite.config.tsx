import { useState } from "react";

export default function App() {
  const [count, setCount] = useState(0);     // ← 状態（ステート）

  return (
    <main style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1>React はじめの一歩</h1>
      <p>今のカウント: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        クリックで +1
      </button>
    </main>
  );
}
