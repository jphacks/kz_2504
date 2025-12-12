@echo off
chcp 65001 > nul
echo ==========================================
echo 視聴用再生モード - 動画再生＆効果信号送信
echo ==========================================
echo.

set /p VIDEO_FILE="動画ファイル名を入力 (例: my_video.mp4): "

if "%VIDEO_FILE%"=="" (
    echo エラー: ファイル名が入力されていません
    pause
    exit /b 1
)

python playback_video.py "%VIDEO_FILE%"

echo.
if %ERRORLEVEL% EQU 0 (
    echo [成功] 再生が完了しました！
) else (
    echo [エラー] 再生中にエラーが発生しました。
)
echo.
pause

