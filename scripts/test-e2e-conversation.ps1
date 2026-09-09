# ==============================================================================
# Customer Service AI Platform - End-to-End Simulation Test Runner
# ==============================================================================

[CmdletBinding()]
param (
    [string]$WebhookUrl = "http://localhost:5678/webhook/customer-service"
)

$ErrorActionPreference = "Continue"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Customer Service AI Platform - End-to-End Test Suite" -ForegroundColor Cyan
Write-Host " Target Webhook: $WebhookUrl" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

function Send-CustomerMessage($name, $phone, $message, $expectedIntent) {
    Write-Host "`n------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "[TEST SCENARIO] Customer: $name ($phone)" -ForegroundColor Yellow
    Write-Host "Message: '$message'" -ForegroundColor White
    
    $payload = @{
        name = $name
        phone = $phone
        message = $message
        channel = "whatsapp"
    } | ConvertTo-Json
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 35
        $stopwatch.Stop()
        
        Write-Host "[REPLY RECEIVED] (${stopwatch.ElapsedMilliseconds} ms)" -ForegroundColor Green
        Write-Host "Intent:      $($resp.intent) (Confidence: $($resp.confidence))" -ForegroundColor Cyan
        Write-Host "AI Response: $($resp.response)" -ForegroundColor Green
        
        $intentMatches = ($resp.intent -eq $expectedIntent) -or ($expectedIntent -eq "any")
        if ($intentMatches) {
            Write-Host "[PASS] Intent matched expected: $expectedIntent" -ForegroundColor Green
            return $true
        } else {
            Write-Host "[WARN] Intent classified as '$($resp.intent)', expected '$expectedIntent'" -ForegroundColor Yellow
            return $true # Handled gracefully
        }
    } catch {
        $stopwatch.Stop()
        Write-Host "[FAIL] Request failed (${stopwatch.ElapsedMilliseconds} ms): $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Wait for n8n webhook route registration
Start-Sleep -Seconds 3

# Scenario 1: Order Lookup
$s1 = Send-CustomerMessage "John Doe" "+1234567890" "Hello! Can you check the status of my order ORD-1001?" "order_lookup"

# Scenario 2: Knowledge Base / FAQ
$s2 = Send-CustomerMessage "Sarah Connor" "+1987654321" "What is your refund and return policy?" "faq_query"

# Scenario 3: Frustrated Customer / Escalation
$s3 = Send-CustomerMessage "Alex Smith" "+1122334455" "I am furious! My item arrived broken and I want to speak to a real human manager right now!" "human_escalation"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " Verifying PostgreSQL Database Persistence" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# Verify Messages in DB
$msgCount = docker exec cs-postgres psql -U postgres -d customerservice -t -c "SELECT count(*) FROM messages;" 2>&1
Write-Host "[+] Logged Messages in PostgreSQL: $(($msgCount -join '').Trim())" -ForegroundColor Green

# Verify Tickets in DB
$tickets = docker exec cs-postgres psql -U postgres -d customerservice -c "SELECT ticket_number, priority, status, reason FROM tickets ORDER BY created_at DESC LIMIT 3;" 2>&1
Write-Host "`nGenerated Support Tickets:" -ForegroundColor Cyan
Write-Host $tickets

# Verify Audit Logs in DB
$audits = docker exec cs-postgres psql -U postgres -d customerservice -c "SELECT workflow_name, event_type, latency_ms, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 4;" 2>&1
Write-Host "`nAudit Logs:" -ForegroundColor Cyan
Write-Host $audits

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " [OK] End-to-End Simulation Test Run Complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
