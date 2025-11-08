#!/bin/bash
# 4DX@HOME Raspberry Pi Server - 再起動スクリプト
# 既存プロセスを停止して新しいサーバーを起動

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" || exit 1

echo "=========================================="
echo "4DX@HOME Server Restart"
echo "=========================================="

# 1. 既存プロセスを停止
echo ""
echo "ステップ1: 既存プロセスを停止中..."
bash "$SCRIPT_DIR/stop_server.sh"

# 2. 少し待つ
sleep 2

# 3. セッションIDを引数から取得（デフォルト: demo1）
SESSION_ID="${1:-demo1}"

echo ""
echo "ステップ2: サーバーを起動中..."
echo "Session ID: $SESSION_ID"
echo ""

# 4. 仮想環境を有効化（存在する場合）
if [ -d "venv" ]; then
    echo "仮想環境を有効化します..."
    source venv/bin/activate
fi

# 5. サーバー起動
python main.py "$SESSION_ID"
