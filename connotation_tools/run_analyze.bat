@echo off
chcp 65001 > nul
echo ==========================================
echo 解析モード - 動画解析＆JSON生成
echo ==========================================
echo.

set /p VIDEO_FILE="動画ファイル名を入力 (例: my_video.mp4): "

if "%VIDEO_FILE%"=="" (
    echo エラー: ファイル名が入力されていません
    pause
    exit /b 1
)

python analyze_video.py "%VIDEO_FILE%"

echo.
if %ERRORLEVEL% EQU 0 (
    echo [成功] 解析が完了しました！
    echo 次に run_playback.bat を実行してください。
) else (
    echo [エラー] 解析中にエラーが発生しました。
)
echo.
pause

