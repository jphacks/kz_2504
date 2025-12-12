@echo off
chcp 65001 > nul
echo ==========================================
echo セットアップスクリプト
echo ==========================================
echo.

echo 必要なパッケージをインストール中...
pip install -r requirements.txt

echo.
if %ERRORLEVEL% EQU 0 (
    echo [成功] セットアップが完了しました！
    echo.
    echo 次のステップ:
    echo 1. analyze_video.py の HARD_CODED_OPENAI_API_KEY にAPIキーを設定
    echo 2. videos/ ディレクトリに .mp4 動画を配置
    echo 3. run_analyze.bat を実行
) else (
    echo [エラー] セットアップ中にエラーが発生しました。
)
echo.
pause

