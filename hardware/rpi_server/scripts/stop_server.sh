#!/bin/bash
# 4DX@HOME Raspberry Pi Server - 停止スクリプト
# ポート8000を使用しているプロセスを停止

echo "ポート8000を使用しているプロセスを検索中..."

# ポート8000を使用しているプロセスIDを取得
PID=$(lsof -ti:8000)

if [ -z "$PID" ]; then
    echo "✓ ポート8000を使用しているプロセスはありません"
else
    echo "プロセスID $PID を停止します..."
    kill -9 $PID
    
    # 停止確認
    sleep 1
    
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo "✗ プロセスの停止に失敗しました"
        exit 1
    else
        echo "✓ プロセスを停止しました"
    fi
fi

# Pythonプロセス（main.py）も確認
echo ""
echo "main.pyプロセスを検索中..."
PYTHON_PID=$(pgrep -f "python.*main.py")

if [ -z "$PYTHON_PID" ]; then
    echo "✓ main.pyプロセスは実行されていません"
else
    echo "Python プロセスID $PYTHON_PID を停止します..."
    kill -9 $PYTHON_PID
    sleep 1
    echo "✓ Pythonプロセスを停止しました"
fi

echo ""
echo "サーバー停止完了"
