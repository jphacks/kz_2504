import React from "react";

// 超シンプル版 ErrorBoundary
// ・UIライブラリ/複雑なスタイル不使用
// ・フォールバックも最低限のDOMのみ
// ・自動再試行なし（無限ループ/二次崩壊防止）

type Props = { children: React.ReactNode };
type State = { hasError: boolean; error?: unknown };

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: unknown): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: unknown, errorInfo: unknown) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] caught", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 16, fontFamily: 'monospace', color: '#fff', background: '#222', minHeight: '100vh' }}>
          <h1 style={{ fontSize: 16, margin: '0 0 12px', fontWeight: 700 }}>表示エラー</h1>
          <p style={{ margin: '4px 0 12px' }}>UI の描画中に例外が発生しました。最小フォールバックです。</p>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.4, background: '#111', padding: 8, borderRadius: 4, maxHeight: 240, overflow: 'auto' }}>
            {String(this.state.error instanceof Error ? this.state.error.stack || this.state.error.message : this.state.error)}
          </pre>
          <button onClick={this.handleRetry} style={{ marginTop: 12, padding: '6px 12px', cursor: 'pointer' }}>再試行</button>
        </div>
      );
    }
    return this.props.children;
  }
}
