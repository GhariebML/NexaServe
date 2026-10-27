# Headers for NexaServe internal endpoints (n8n webhooks and WhatsApp bridge control routes).
# The token comes from $env:WHATSAPP_INGEST_TOKEN, falling back to the project .env file.
function Get-NexaServeServiceHeaders {
    $token = $env:WHATSAPP_INGEST_TOKEN
    if (-not $token) {
        $envFile = Join-Path (Split-Path -Parent $PSScriptRoot) ".env"
        if (Test-Path $envFile) {
            $line = Get-Content $envFile | Where-Object { $_ -match '^\s*WHATSAPP_INGEST_TOKEN\s*=' } | Select-Object -First 1
            if ($line) { $token = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'") }
        }
    }
    if (-not $token) { Write-Warning "WHATSAPP_INGEST_TOKEN is not set; n8n webhooks will reject requests (401)." }
    return @{ "X-NexaServe-Webhook-Token" = $token }
}
