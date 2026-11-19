[CmdletBinding()]
param(
    # Public API base the apps call. Defaults to OAUTH_CALLBACK_BASE_URL from backend/.env.
    [string] $ApiUrl
)

# Starts the latest member app (mobile/, port 8081) and scanner app (scanner-mobile/, port 8082) in Expo tunnels.
# Old Expo servers on those ports are stopped, dependencies are refreshed when package-lock.json changed, and
# Metro starts with --clear, so Expo Go always loads a fresh bundle built from the current working folder.

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendEnv = Join-Path $repoRoot 'backend\.env'
$memberDir = Join-Path $repoRoot 'mobile'
$scannerDir = Join-Path $repoRoot 'scanner-mobile'

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'npm was not found. Install the supported Node.js version first.'
}

if (-not $ApiUrl) {
    if (-not (Test-Path -LiteralPath $backendEnv)) {
        throw 'backend/.env is required, or pass -ApiUrl https://your-public-api/api/v1.'
    }
    $callbackLine = Get-Content -LiteralPath $backendEnv |
        Where-Object { $_ -match '^\s*OAUTH_CALLBACK_BASE_URL=' } |
        Select-Object -Last 1
    if (-not $callbackLine) {
        throw 'OAUTH_CALLBACK_BASE_URL is missing from backend/.env. Add it or pass -ApiUrl.'
    }
    $ApiUrl = ($callbackLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
}
$ApiUrl = $ApiUrl.TrimEnd('/')
$parsedApiUrl = $null
if (-not [Uri]::TryCreate($ApiUrl, [UriKind]::Absolute, [ref]$parsedApiUrl) -or
    $parsedApiUrl.Scheme -notin @('http', 'https')) {
    throw "API URL '$ApiUrl' must be an absolute http or https URL."
}

# The apps can start without the API, so only warn when it does not answer.
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/health" -TimeoutSec 5
    if ($health.status -ne 'success') { Write-Warning "API health at $ApiUrl/health returned '$($health.status)'." }
} catch {
    Write-Warning "API did not answer at $ApiUrl/health. Start the backend with .\scripts\start-ypgym.ps1 if the apps cannot sign in."
}

# Install dependencies when they are missing or when package-lock.json changed since the last install.
# An existing install is trusted once, then its lock file hash is recorded inside node_modules.
foreach ($appDir in @($memberDir, $scannerDir)) {
    $lockPath = Join-Path $appDir 'package-lock.json'
    $lockStampPath = Join-Path $appDir 'node_modules\.ypgym-lock-hash'
    $installed = Test-Path -LiteralPath (Join-Path $appDir 'node_modules\.bin\expo.cmd')
    $lockHash = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
    $stampedHash = $null
    if (Test-Path -LiteralPath $lockStampPath) {
        $lockStampText = Get-Content -LiteralPath $lockStampPath -Raw
        if ($lockStampText) { $stampedHash = $lockStampText.Trim() }
    }
    if ($installed -and -not $stampedHash) {
        Set-Content -LiteralPath $lockStampPath -Value $lockHash -Encoding ASCII
    } elseif (-not $installed -or $stampedHash -ne $lockHash) {
        Write-Host "Installing dependencies in $appDir."
        Push-Location $appDir
        try {
            npm ci
            if ($LASTEXITCODE -ne 0) { throw "npm ci failed in $appDir." }
        } finally {
            Pop-Location
        }
        Set-Content -LiteralPath $lockStampPath -Value $lockHash -Encoding ASCII
    }
}

function Stop-OldExpo {
    param(
        [Parameter(Mandatory)] [string] $Title,
        [Parameter(Mandatory)] [int] $Port
    )

    # Close the terminal a previous run opened (found by its title) together with its Expo child processes.
    Get-Process -Name powershell, pwsh -ErrorAction SilentlyContinue |
        Where-Object { $_.Id -ne $PID -and $_.MainWindowTitle -eq $Title } |
        ForEach-Object { taskkill /PID $_.Id /T /F *> $null }

    # A terminal hosted in Windows Terminal has no window title to match, so also stop whatever Node process
    # still listens on the port. Anything else on the port is left alone.
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($processId in $listeners) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq 'node') {
            Write-Host "Stopping the old Expo server on port $Port (PID $processId)."
            taskkill /PID $processId /T /F *> $null
        }
    }

    for ($attempt = 1; $attempt -le 10; $attempt++) {
        if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "Port $Port is still in use by another program. Free it and run this script again."
}

function Start-ExpoTerminal {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $Directory,
        [Parameter(Mandatory)] [int] $Port
    )

    $title = "YPGym $Name"
    Stop-OldExpo -Title $title -Port $Port

    # The terminal stays visible because Expo displays the interactive QR code and controls.
    $escapedApiUrl = $ApiUrl.Replace("'", "''")
    $command = "`$Host.UI.RawUI.WindowTitle = '$title'; `$env:EXPO_PUBLIC_API_URL = '$escapedApiUrl'; npm run start:tunnel -- --port $Port --clear"
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $powerShellPath = (Get-Process -Id $PID).Path
    Start-Process -FilePath $powerShellPath -WorkingDirectory $Directory -ArgumentList @('-NoExit', '-EncodedCommand', $encodedCommand)
}

Start-ExpoTerminal -Name 'Member' -Directory $memberDir -Port 8081
Start-ExpoTerminal -Name 'Scanner' -Directory $scannerDir -Port 8082

Write-Host ''
Write-Host 'Member app (port 8081) and scanner app (port 8082) are starting in separate terminals.' -ForegroundColor Green
Write-Host "API:     $ApiUrl"
if (Get-Command git -ErrorAction SilentlyContinue) {
    $commit = git -C $repoRoot rev-parse --short HEAD 2>$null
    if ($commit) { Write-Host "Running: commit $commit plus any uncommitted changes (the working folder is what runs)" }
}
Write-Host 'Scan each QR code with Expo Go. If a phone still shows the old app, shake it and choose Reload.'
