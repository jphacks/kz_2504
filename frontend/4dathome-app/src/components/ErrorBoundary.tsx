import React from "react";

type Props = { children: React.ReactNode };
type State = { hasError: boolean; error?: unknown; autoTried: boolean };

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
  this.state = { hasError: false, autoTried: false };
  }

  static getDerivedStateFromError(error: unknown): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: unknown, errorInfo: unknown) {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught:", error, errorInfo);
    // 1回だけ自動再試行（短いバックオフ）
    if (!this.state.autoTried) {
      setTimeout(() => {
        this.setState({ hasError: false, error: undefined, autoTried: true });
      }, 60);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, autoTried: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{position:"fixed", inset:0, display:"grid", placeItems:"center", background:"#0e1324", color:"#fff", fontFamily:"system-ui,-apple-system,Segoe UI,Roboto,\"Noto Sans JP\",sans-serif"}}>
          <div style={{maxWidth:520, width:"92%", textAlign:"center"}}>
            <div style={{fontWeight:800, fontSize:"18px", marginBottom:10}}>表示に失敗しました</div>
            <div style={{opacity:.9, marginBottom:14}}>一時的な不整合が発生しました。再試行してください。</div>
            <button onClick={this.handleRetry} style={{padding:"10px 16px", borderRadius:8, border:"none", fontWeight:700, cursor:"pointer"}}>再試行</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
