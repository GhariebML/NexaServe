# MCIT Enterprise Customer Service - Interactive Terminal Client
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "MCIT AI Customer Service Client"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  MCIT Enterprise AI Customer Service - Local Interactive CLI" -ForegroundColor Green
Write-Host "  Endpoint: http://localhost:5678/webhook/customer-service" -ForegroundColor Gray
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Type 'exit' or 'quit' to end session.`n" -ForegroundColor DarkGray

$channel = "webchat"
$customerName = "Noura Al-Qahtani"
$phone = "+966501234567"

while ($true) {
    Write-Host "Enter your message (Arabic or English): " -ForegroundColor Yellow -NoNewline
    $msg = Read-Host
    if ([string]::IsNullOrWhiteSpace($msg) -or $msg -in @('exit', 'quit')) {
        break
    }

    $payload = @{
        channel = $channel
        customer_name = $customerName
        phone = $phone
        message = $msg
    } | ConvertTo-Json -Compress

    Write-Host "`n[Processing with local Ollama & PostgreSQL Knowledge Base...]" -ForegroundColor DarkGray
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
        $resp = Invoke-RestMethod -Uri "http://localhost:5678/webhook/customer-service" -Method Post -ContentType "application/json; charset=utf-8" -Body $bytes
        $sw.Stop()

        Write-Host "`n------------------------ Response ------------------------" -ForegroundColor Cyan
        Write-Host "Intent:      $($resp.intent) (Confidence: $([math]::Round($resp.confidence * 100))%)" -ForegroundColor Magenta
        Write-Host "Channel:     $($resp.channel) | Locale: $($resp.locale)" -ForegroundColor DarkCyan
        if ($resp.ticket_number) {
            Write-Host "SLA Ticket:  $($resp.ticket_number) [ESCALATED TO SPECIALIST]" -ForegroundColor Red
        }
        if ($resp.pii_masked) {
            Write-Host "PDPL Shield: Saudi PII was automatically masked" -ForegroundColor Yellow
        }
        Write-Host "`nReply:" -ForegroundColor Green
        Write-Host "$($resp.response)" -ForegroundColor White
        Write-Host "`nLatency:     $($sw.ElapsedMilliseconds) ms" -ForegroundColor DarkGray
        Write-Host "----------------------------------------------------------`n" -ForegroundColor Cyan
    } catch {
        Write-Host "Error communicating with workflow: $_" -ForegroundColor Red
    }
}
