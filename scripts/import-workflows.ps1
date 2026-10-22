[CmdletBinding()]
param (
    [string]$ProjectDir = "E:\NexaServe"
)

$ErrorActionPreference = "Stop"
$workflowsDir = Join-Path $ProjectDir "infra\n8n\workflows"
$inventoryPath = Join-Path $ProjectDir "deployment\inventory.json"
if (-not (Test-Path $workflowsDir) -or -not (Test-Path $inventoryPath)) {
    throw "Canonical workflow source or deployment inventory is missing."
}

# Preflight every canonical export before any Docker/database operation.
$inventory = Get-Content -Raw $inventoryPath | ConvertFrom-Json
$rows = @($inventory.workflows)
$acceptance = $inventory.n8n_workflows.import_acceptance
if (-not $acceptance -or $acceptance.status -ne "passed" -or -not $acceptance.n8n_version -or -not $acceptance.evidence) {
    throw "Isolated target-like n8n import acceptance evidence is not recorded."
}
$names = @($rows | ForEach-Object { $_.file })
$ids = @($rows | ForEach-Object { $_.id })
if (($names | Select-Object -Unique).Count -ne $names.Count -or
    ($ids | Select-Object -Unique).Count -ne $ids.Count) {
    throw "Inventory contains duplicate workflow filenames or IDs."
}
$workflowFiles = foreach ($row in $rows) {
    $path = Join-Path $workflowsDir $row.file
    if (-not (Test-Path $path)) { throw "Canonical workflow source is missing: $($row.file)" }
    $workflow = Get-Content -Raw $path | ConvertFrom-Json
    if ($workflow.id -ne $row.id) { throw "Inventory ID mismatch: $($row.file)" }
    if ($workflow.PSObject.Properties.Name -contains "active" -and $workflow.active -isnot [bool]) {
        throw "Invalid active metadata type: $($row.file)"
    }
    if ($workflow.active -eq $true) {
        throw "Import blocked by active=true export metadata: $($row.file). Complete isolated import acceptance first."
    }
    Get-Item $path
}

$projectIdQuery = docker exec cs-postgres psql -U postgres -d n8n -t -c "SELECT id FROM project LIMIT 1;" 2>&1
if ($LASTEXITCODE -ne 0) { throw "Could not resolve the n8n project; no workflow imports were attempted." }
$projectId = ($projectIdQuery -join "").Trim()
if (-not $projectId) { throw "n8n project ID is empty; no workflow imports were attempted." }

docker exec cs-n8n mkdir -p /tmp/workflows
if ($LASTEXITCODE -ne 0) { throw "Could not prepare the temporary import directory." }
foreach ($wf in $workflowFiles) {
    $containerDest = "/tmp/workflows/$($wf.Name)"
    docker cp $wf.FullName "cs-n8n:$containerDest"
    if ($LASTEXITCODE -ne 0) { throw "Copy failed for $($wf.Name); import stopped." }
    docker exec cs-n8n n8n import:workflow --input=$containerDest --projectId=$projectId
    if ($LASTEXITCODE -ne 0) { throw "Import failed for $($wf.Name); no activation was attempted." }
    Write-Host "Imported $($wf.Name)."
}

Write-Host "Canonical workflow import completed. No workflow was published or activated by this script."
