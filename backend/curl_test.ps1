# curl_test.ps1 - APIテスト用PowerShellスクリプト

# 1. ルートエンドポイントテスト
Write-Host "=== 4DX@HOME Backend API 動作確認 ==="
Write-Host ""

Write-Host "1. ルートエンドポイント"
$response1 = Invoke-RestMethod -Uri "http://localhost:8001/" -Method GET
$response1 | ConvertTo-Json
Write-Host ""

# 2. ヘルスチェック
Write-Host "2. ヘルスチェック"
$response2 = Invoke-RestMethod -Uri "http://localhost:8001/api/health" -Method GET
$response2 | ConvertTo-Json
Write-Host ""

# 3. セッション作成
Write-Host "3. セッション作成"
$sessionData = @{
    product_code = "DH001"
    capabilities = @("vibration", "scent")
    device_info = @{
        version = "1.0.0"
        ip_address = "192.168.1.100"
    }
}

$response3 = Invoke-RestMethod -Uri "http://localhost:8001/api/sessions" -Method POST -Body ($sessionData | ConvertTo-Json) -ContentType "application/json"
$sessionId = $response3.session_id
Write-Host "セッションID: $sessionId"
Write-Host ""

# 4. セッション情報取得
Write-Host "4. セッション情報取得"
$response4 = Invoke-RestMethod -Uri "http://localhost:8001/api/sessions/$sessionId" -Method GET
$response4 | ConvertTo-Json
Write-Host ""

# 5. 動画リスト取得
Write-Host "5. 動画リスト取得"
$response5 = Invoke-RestMethod -Uri "http://localhost:8001/api/videos" -Method GET
$response5 | ConvertTo-Json
Write-Host ""

# 6. 同期データ取得
Write-Host "6. 同期データ取得 (sample1)"
try {
    $response6 = Invoke-RestMethod -Uri "http://localhost:8001/api/sync-data/sample1" -Method GET
    Write-Host "同期イベント数: $($response6.sync_events.Count)"
}
catch {
    Write-Host "エラー: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "=== テスト完了 ===