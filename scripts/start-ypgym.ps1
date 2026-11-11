[CmdletBinding()]
param(
    [switch] $NoBuild,
    [switch] $Seed
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendEnv = Join-Path $repoRoot 'backend\.env'
$memberDir = Join-Path $repoRoot 'mobile'
$scannerDir = Join-Path $repoRoot 'scanner-mobile'

if (-not (Test-Path -LiteralPath $backendEnv)) {
    throw 'backend/.env is required. Copy backend/.env.example and configure it before starting YPGym.'
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI was not found. Install and start Docker Desktop.'
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw 'npm was not found. Install the supported Node.js version first.'
}

$callbackLine = Get-Content -LiteralPath $backendEnv |
    Where-Object { $_ -match '^\s*OAUTH_CALLBACK_BASE_URL=' } |
    Select-Object -Last 1
if (-not $callbackLine) {
    throw 'OAUTH_CALLBACK_BASE_URL is missing from backend/.env.'
}
$publicApiUrl = (($callbackLine -split '=', 2)[1]).Trim().Trim('"').Trim("'").TrimEnd('/')
$parsedApiUrl = $null
if (-not [Uri]::TryCreate($publicApiUrl, [UriKind]::Absolute, [ref]$parsedApiUrl) -or
    $parsedApiUrl.Scheme -ne 'https' -or
    $parsedApiUrl.Host -in @('localhost', '127.0.0.1', '::1')) {
    throw 'OAUTH_CALLBACK_BASE_URL must be the public HTTPS API base used by the mobile apps.'
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $Default
    )
    $line = Get-Content -LiteralPath $backendEnv |
        Where-Object { $_ -match ('^\s*' + $Name + '=') } |
        Select-Object -Last 1
    if (-not $line) { return $Default }
    $value = (($line -split '=', 2)[1]).Trim().Trim('"').Trim("'")
    if ($value) { return $value }
    return $Default
}
$pgUser = Get-EnvValue -Name 'POSTGRES_USER' -Default 'ypgym'
$pgDatabase = Get-EnvValue -Name 'POSTGRES_DB' -Default 'ypgym'
$frontendPort = Get-EnvValue -Name 'FRONTEND_HOST_PORT' -Default '5174'

docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Desktop is not running.'
}

$cloudflared = Get-Service -Name 'cloudflared' -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    throw 'The cloudflared Windows service is not installed.'
}
if ($cloudflared.Status -ne 'Running') {
    try {
        Start-Service -Name 'cloudflared'
        (Get-Service -Name 'cloudflared').WaitForStatus('Running', [TimeSpan]::FromSeconds(15))
    } catch {
        throw 'cloudflared is stopped. Open PowerShell as Administrator, run Start-Service cloudflared, then retry.'
    }
}

# Always build the images from the latest Dockerfiles and dependency files, so the stack never runs an older
# build. Docker's layer cache makes this fast when nothing changed. Pass -NoBuild to skip it for a quick restart.
# Application code is mounted into the containers, so the processes are restarted below to load it.
Push-Location $repoRoot
try {
    $composeArgs = @('compose', '--env-file', $backendEnv, '--profile', 'app', 'up', '-d')
    if (-not $NoBuild) {
        # --renew-anon-volumes replaces the frontend's cached node_modules volume, which would otherwise
        # keep serving the old dependencies after package.json or package-lock.json changed. Named volumes
        # (PostgreSQL, Redis) are not touched.
        $composeArgs += @('--build', '--renew-anon-volumes')
    }
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose failed to start YPGym.' }

    # The Celery worker and beat have no auto-reload, and the API reloader and the Vite dev server can miss
    # file changes on Docker Desktop bind mounts, so they keep serving the code they loaded at their last
    # start. Restart them all so they always run the latest code in the working folder.
    docker compose --env-file $backendEnv restart backend-api celery-worker celery-beat frontend-web
    if ($LASTEXITCODE -ne 0) { throw 'Could not restart the app containers.' }

    # Apply every migration up to the newest one. Two heads mean a branched migration history; stop early.
    $heads = @(docker compose --env-file $backendEnv exec -T backend-api alembic heads)
    if ($LASTEXITCODE -ne 0) { throw 'Could not read the Alembic migration heads.' }
    if (@($heads | Where-Object { $_ -match '\(head\)' }).Count -gt 1) {
        throw "Multiple Alembic heads found: $($heads -join '; '). Merge them before starting."
    }
    docker compose --env-file $backendEnv exec -T backend-api alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Alembic failed to upgrade the database.' }
    $current = @(docker compose --env-file $backendEnv exec -T backend-api alembic current)
    Write-Host "Database is at: $($current -join ' ')"

    # Seed the development data (gyms, District 1 and District 11 staff, managers and members, scanner
    # simulators) when the multi-gym demo accounts are missing, or when -Seed is passed. The seed is
    # repeatable and keeps existing passwords and history.
    $needsSeed = $Seed.IsPresent
    if (-not $needsSeed) {
        $probe = $null
        try {
            $probe = "SELECT count(*) FROM users WHERE email = 'memberdist11@ypgym.dev';" |
                docker compose --env-file $backendEnv exec -T postgres-db psql -U $pgUser -d $pgDatabase -tA 2>$null
        } catch {
            $probe = $null
        }
        $alreadySeeded = ($LASTEXITCODE -eq 0) -and ((($probe | Out-String).Trim()) -eq '1')
        if (-not $alreadySeeded) {
            $needsSeed = $true
            Write-Host 'The multi-gym demo accounts were not found: seeding development data.'
        }
    }
    if ($needsSeed) {
        docker compose --env-file $backendEnv exec -T backend-api python -m app.db.seed
        if ($LASTEXITCODE -ne 0) { throw 'The development seed failed.' }
    }
} finally {
    Pop-Location
}

$health = $null
$healthError = $null
for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "$publicApiUrl/health" -TimeoutSec 5
        if ($health.status -eq 'success') {
            break
        }
        $healthError = "Health endpoint returned status '$($health.status)'."
    } catch {
        $healthError = $_.Exception.Message
    }
    Start-Sleep -Seconds 2
}
if ($health.status -ne 'success') {
    throw "The public API did not become ready at $publicApiUrl/health. Last error: $healthError"
}

# The web app runs the Vite dev server from the frontend folder and was restarted above, so once it answers it
# is serving the latest source. Warn instead of failing: a restart can take a while to re-optimise dependencies.
$webReady = $false
for ($attempt = 1; $attempt -le 30 -and -not $webReady; $attempt++) {
    try {
        $webReady = (Invoke-WebRequest -Uri "http://localhost:$frontendPort" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $webReady) {
    Write-Warning "The web app did not answer on http://localhost:$frontendPort yet. Check: docker compose logs frontend-web"
}

# Install mobile dependencies when they are missing or when package-lock.json changed since the last install.
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

function Start-ExpoTerminal {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $Directory,
        [Parameter(Mandatory)] [int] $Port
    )

    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "$Name Expo was not started because port $Port is already in use."
        return $false
    }

    $escapedApiUrl = $publicApiUrl.Replace("'", "''")
    $command = "`$Host.UI.RawUI.WindowTitle = 'YPGym $Name'; `$env:EXPO_PUBLIC_API_URL = '$escapedApiUrl'; npm run start:tunnel -- --port $Port --clear"
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $powerShellPath = (Get-Process -Id $PID).Path
    Start-Process -FilePath $powerShellPath -WorkingDirectory $Directory -ArgumentList @('-NoExit', '-EncodedCommand', $encodedCommand)
    return $true
}

# These terminals stay visible because Expo displays interactive QR codes and controls.
# Newly started servers use --clear so Metro never serves a cached bundle from an older build.
$memberStarted = Start-ExpoTerminal -Name 'Member' -Directory $memberDir -Port 8081
$scannerStarted = Start-ExpoTerminal -Name 'Scanner' -Directory $scannerDir -Port 8082

Write-Host ''
Write-Host 'YPGym backend is ready.' -ForegroundColor Green
if (Get-Command git -ErrorAction SilentlyContinue) {
    try {
        $commit = (git -C $repoRoot rev-parse --short HEAD 2>$null)
        $dirty = @(git -C $repoRoot status --porcelain 2>$null).Count
        if ($commit) { Write-Host "Running:    commit $commit plus $dirty changed or new files (the working folder is what runs)" }
    } catch {
        # The commit line is informational only.
    }
}
Write-Host "Web:        http://localhost:$frontendPort"
Write-Host "Public API: $publicApiUrl"
Write-Host 'If the browser still shows an older UI, hard refresh (Ctrl+Shift+R). If it persists, open DevTools > Application > Service Workers > Unregister, then reload.'
Write-Host ''
Write-Host 'Multi-gym test logins (local seed; password is DEVELOPMENT_SEED_PASSWORD, default YPGymDemo123!):'
Write-Host '  Owner (all gyms):  owner@ypgym.dev'
Write-Host '  District 1:        managerdist1@ypgym.dev, staffdist1@ypgym.dev, memberdist1@ypgym.dev'
Write-Host '  District 11:       managerdist11@ypgym.dev, staffdist11@ypgym.dev, memberdist11@ypgym.dev'
Write-Host 'Seeded scanner devices (key is IOT_DEVICE_API_KEY in backend/.env):'
Write-Host '  local-simulator-1 = District 1, local-simulator-dist11 = District 11'
if ($memberStarted -or $scannerStarted) {
    Write-Host 'Any missing Expo tunnels are starting in separate terminals.'
} else {
    Write-Host 'Existing Expo servers on ports 8081 and 8082 were reused. To load a fully clean bundle, close them and run this script again.'
}
