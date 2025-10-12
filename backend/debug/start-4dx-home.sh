#!/bin/bash
# 4DX@HOME Raspberry Pi 起動スクリプト
# 
# 使用方法:
#   ./start-4dx-home.sh [セッションID]
#
# 例:
#   ./start-4dx-home.sh session_demo123

set -e

# =====================================
# 設定
# =====================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${SCRIPT_DIR}"
PYTHON_APP="raspberry-pi-main.py"
LOG_DIR="/var/log/4dx-home"
PID_FILE="/tmp/4dx-home.pid"

# デフォルト設定
DEFAULT_SESSION_ID="session_demo123"
SESSION_ID="${1:-$DEFAULT_SESSION_ID}"

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# =====================================
# 前処理チェック
# =====================================

check_environment() {
    log_info "🔍 環境チェック開始"
    
    # Python存在確認
    if ! command -v python3 &> /dev/null; then
        log_error "Python3が見つかりません"
        exit 1
    fi
    
    python_version=$(python3 --version)
    log_info "✅ Python: $python_version"
    
    # 必要ディレクトリ作成
    sudo mkdir -p "$LOG_DIR"
    sudo chown pi:pi "$LOG_DIR" 2>/dev/null || log_warn "ログディレクトリ権限設定スキップ"
    
    mkdir -p "/tmp/4dx_sync_data"
    
    log_info "✅ ディレクトリ準備完了"
    
    # ネットワーク接続確認
    if ping -c 1 -W 5 8.8.8.8 &> /dev/null; then
        log_info "✅ ネットワーク接続: OK"
    else
        log_warn "⚠️ ネットワーク接続に問題があります"
    fi
    
    # 必要パッケージ確認
    check_python_packages
}

check_python_packages() {
    log_info "📦 Pythonパッケージ確認"
    
    required_packages=(
        "websockets"
        "aiohttp"
    )
    
    missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            log_debug "✅ $package"
        else
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_warn "⚠️ 不足パッケージ: ${missing_packages[*]}"
        log_info "📥 パッケージインストール実行中..."
        
        # パッケージインストール試行
        if command -v pip3 &> /dev/null; then
            for package in "${missing_packages[@]}"; do
                log_info "インストール中: $package"
                pip3 install --user "$package" || log_warn "インストール失敗: $package"
            done
        else
            log_error "pip3が見つかりません。手動でパッケージをインストールしてください:"
            printf '%s\n' "${missing_packages[@]}"
            exit 1
        fi
    else
        log_info "✅ 必要パッケージ: すべて利用可能"
    fi
}

# =====================================
# プロセス管理
# =====================================

check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # 実行中
        else
            rm -f "$PID_FILE"
            return 1  # 停止中
        fi
    fi
    return 1  # 停止中
}

stop_app() {
    log_info "🛑 4DX@HOME アプリケーション停止"
    
    if check_running; then
        PID=$(cat "$PID_FILE")
        log_info "プロセス終了: PID=$PID"
        
        # graceful shutdown
        kill -TERM "$PID" 2>/dev/null || true
        sleep 3
        
        # 強制終了（必要な場合）
        if ps -p "$PID" > /dev/null 2>&1; then
            log_warn "強制終了実行"
            kill -KILL "$PID" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
        log_info "✅ 停止完了"
    else
        log_info "ℹ️ アプリケーションは実行されていません"
    fi
}

# =====================================
# メイン起動処理
# =====================================

start_app() {
    log_info "🚀 4DX@HOME Raspberry Pi システム起動"
    log_info "📱 セッションID: $SESSION_ID"
    
    # 重複起動チェック
    if check_running; then
        log_error "❌ アプリケーションは既に実行中です (PID: $(cat $PID_FILE))"
        log_info "停止してから再起動する場合は: $0 stop"
        exit 1
    fi
    
    # 環境チェック
    check_environment
    
    # アプリケーションファイル確認
    if [ ! -f "$APP_DIR/$PYTHON_APP" ]; then
        log_error "❌ アプリケーションファイルが見つかりません: $APP_DIR/$PYTHON_APP"
        exit 1
    fi
    
    # 起動
    log_info "🎬 アプリケーション開始..."
    
    cd "$APP_DIR"
    
    # バックグラウンド実行でPIDファイル作成
    nohup python3 "$PYTHON_APP" "$SESSION_ID" > "$LOG_DIR/app-output.log" 2>&1 &
    APP_PID=$!
    echo $APP_PID > "$PID_FILE"
    
    # 起動確認
    sleep 2
    if ps -p "$APP_PID" > /dev/null 2>&1; then
        log_info "✅ 起動成功 (PID: $APP_PID)"
        log_info "📄 ログファイル: $LOG_DIR/4dx-app.log"
        log_info "📄 出力ログ: $LOG_DIR/app-output.log"
        
        # 最初の数行を表示
        log_info "--- 起動ログ (最初の10行) ---"
        tail -n 10 "$LOG_DIR/app-output.log" 2>/dev/null || echo "ログファイル読み込み待機中..."
        log_info "--- ログ終了 ---"
        
    else
        log_error "❌ 起動に失敗しました"
        rm -f "$PID_FILE"
        
        # エラーログ表示
        if [ -f "$LOG_DIR/app-output.log" ]; then
            log_error "--- エラーログ ---"
            tail -n 20 "$LOG_DIR/app-output.log"
            log_error "--- エラーログ終了 ---"
        fi
        
        exit 1
    fi
}

show_status() {
    log_info "📊 4DX@HOME システム状態"
    
    if check_running; then
        PID=$(cat "$PID_FILE")
        
        # プロセス情報
        echo "🟢 実行中"
        echo "PID: $PID"
        echo "起動時刻: $(ps -p $PID -o lstart= 2>/dev/null | xargs)"
        
        # メモリ使用量
        if command -v ps &> /dev/null; then
            memory_info=$(ps -p $PID -o pid,ppid,pcpu,pmem,cmd --no-headers 2>/dev/null || echo "情報取得不可")
            echo "メモリ情報: $memory_info"
        fi
        
        # ログファイルサイズ
        if [ -f "$LOG_DIR/4dx-app.log" ]; then
            log_size=$(du -h "$LOG_DIR/4dx-app.log" | cut -f1)
            echo "ログサイズ: $log_size"
        fi
        
    else
        echo "🔴 停止中"
    fi
    
    # 最新ログ表示
    if [ -f "$LOG_DIR/4dx-app.log" ]; then
        echo ""
        echo "--- 最新ログ (最後の5行) ---"
        tail -n 5 "$LOG_DIR/4dx-app.log"
        echo "--- ログ終了 ---"
    fi
}

show_logs() {
    local lines="${1:-50}"
    log_info "📄 ログ表示 (最新${lines}行)"
    
    if [ -f "$LOG_DIR/4dx-app.log" ]; then
        tail -n "$lines" "$LOG_DIR/4dx-app.log"
    else
        log_warn "ログファイルが見つかりません: $LOG_DIR/4dx-app.log"
    fi
}

# =====================================
# コマンドライン処理
# =====================================

show_usage() {
    echo "4DX@HOME Raspberry Pi 管理スクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0 [start|stop|restart|status|logs] [セッションID]"
    echo ""
    echo "コマンド:"
    echo "  start    アプリケーション開始 (デフォルト)"
    echo "  stop     アプリケーション停止"
    echo "  restart  アプリケーション再起動"
    echo "  status   実行状態確認"
    echo "  logs     ログ表示"
    echo ""
    echo "例:"
    echo "  $0 start session_demo123"
    echo "  $0 stop"
    echo "  $0 logs"
}

# メイン処理
COMMAND="${1:-start}"

# コマンド処理
case "$COMMAND" in
    "start")
        start_app
        ;;
    "stop")
        stop_app
        ;;
    "restart")
        stop_app
        sleep 2
        start_app
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "${2:-50}"
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        # 第一引数がセッションIDの場合（後方互換性）
        if [[ ! "$COMMAND" =~ ^(start|stop|restart|status|logs|help)$ ]]; then
            SESSION_ID="$COMMAND"
            start_app
        else
            log_error "❌ 不明なコマンド: $COMMAND"
            show_usage
            exit 1
        fi
        ;;
esac