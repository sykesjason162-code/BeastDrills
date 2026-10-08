<#
    Start Beast Drills' local dashboard.

    This is the SHIPPED launcher -- it lives in the release bundle, not in
    the dev tree, and knows nothing about the repo. tools/start_beast_drills.ps1
    is the development one and stays behind; it resolves paths inside a
    checkout that a player will not have.

    Two processes, and both are needed:

      beast_drills.service    owns the drill database and does all the
                              grading and scheduling. The game talks to it
                              through files, so the game does nothing
                              useful while this is down.
      beast_drills.dashboard  the web UI, on whatever address
                              beast_drills.ini says (8765 by default)

    SETTINGS COME FROM beast_drills.ini, not from here. This used to pass
    --port 8765 on every launch, which silently OVERRODE the settings
    file -- a player could edit the port, restart, and watch nothing
    happen. Nothing is passed unless you ask for it on the command line,
    so the dashboard reads its own settings and there is one authority
    rather than two that can disagree.

    Nothing here reaches the internet by itself. The dashboard is a local
    server so the game and your browser can share one database -- though
    it CAN be reached from another machine if you set host in the
    settings file, which is how you run it on a different computer.
#>
param(
    # Only for a one-off. Leave it alone and the settings file decides.
    [int]$Port = 0,
    [switch]$NoBrowser,
    # Stop both processes and exit. "Stop Beast Drills.bat" passes this.
    [switch]$Stop
)
$ErrorActionPreference = 'Stop'

# STOPPING, which used to be impossible. Both processes start hidden, and
# this script told players to "close the windows to stop it" -- there are
# no windows. Only processes running Beast Drills' own modules are
# touched, matched on the module name in their command line.
if ($Stop) {
    $ours = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -match 'beast_drills\.(service|dashboard)' })
    $ours | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    if ($ours.Count) { Write-Host "Beast Drills stopped." -ForegroundColor Green }
    else { Write-Host "Beast Drills was not running." -ForegroundColor DarkGray }
    exit 0
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dash = Join-Path $here 'dashboard'
if (-not (Test-Path (Join-Path $dash 'beast_drills'))) {
    throw "Cannot find the dashboard next to this script. Keep start_dashboard.ps1 in the folder it shipped in."
}

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Host "Python 3 is required and was not found on PATH." -ForegroundColor Red
    Write-Host "Install it from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'."
    exit 1
}

# OLD ENOUGH TO RUN IT. The code uses 3.10 syntax, and an older Python
# fails at import -- which surfaced only as "did not start" below.
& $python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    $have = (& $python --version) 2>&1
    Write-Host "Beast Drills needs Python 3.10 or newer; this is $have." -ForegroundColor Red
    Write-Host "Install a newer one from https://www.python.org/downloads/"
    exit 1
}

# FLASK, the one package the dashboard needs. Found in the pre-beta
# audit: it was never installed by anything and the player README never
# mentioned it, so every fresh install stopped at "did not start".
#
# ASKED, NOT DONE QUIETLY. Installing it fetches from PyPI, and Beast
# Drills promises it does not talk to the internet on its own. So the
# player is told what is missing and chooses; a "no" says how to do it by
# hand. Once installed this never asks again.
& $python -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "The dashboard needs one Python package, Flask, which is not installed." -ForegroundColor Yellow
    $answer = Read-Host "Install it now from the Python Package Index (pip install flask)? [Y/n]"
    if ($answer -match '^\s*(n|no)\s*$') {
        Write-Host "Not installed. To do it yourself:  $python -m pip install flask"
        exit 1
    }
    & $python -m pip install flask
    & $python -c "import flask" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Flask still cannot be imported. Try:  $python -m pip install --user flask" -ForegroundColor Red
        exit 1
    }
    Write-Host "Flask installed." -ForegroundColor Green
}

function Running($pattern) {
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match $pattern }).Count
}

# Started one at a time with a check after each. Launching both at once
# has produced duplicate processes on this platform before, and a second
# copy of the service writing the same database is worth avoiding.
foreach ($mod in 'beast_drills.service', 'beast_drills.dashboard') {
    if ((Running ([regex]::Escape($mod))) -gt 0) {
        Write-Host "$mod is already running." -ForegroundColor DarkGray
        continue
    }
    # -B: no __pycache__ folders. This runs from inside the game folder,
    # which Fluffy and Vortex manage, and bytecode caches written there are
    # files no manager installed -- left behind on uninstall, and flagged
    # as outside changes. The two processes start once a session, so the
    # cache saved nothing worth that.
    $args = @('-B', '-m', $mod)
    # Only when explicitly asked. Otherwise the dashboard reads
    # beast_drills.ini itself.
    if ($mod -eq 'beast_drills.dashboard' -and $Port -gt 0) {
        $args += @('--port', "$Port")
    }
    Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $dash -WindowStyle Hidden
    Start-Sleep -Seconds 3
    if ((Running ([regex]::Escape($mod))) -eq 0) {
        Write-Host "$mod did not start." -ForegroundColor Red
        Write-Host "Run it by hand to see why:  cd `"$dash`"; python -m $mod"
        exit 1
    }
    Write-Host "$mod started." -ForegroundColor Green
}

# WHERE IT ACTUALLY IS, asked of the same code the service uses -- so this
# message and the in-game menu agree by construction. This used to read
# the inbox back from the game folder, where it has not lived since the
# player's data moved to Documents; it always missed and fell back to
# 8765, so a player who changed the port was sent to the wrong address.
$url = "http://localhost:8765"
try {
    Push-Location $dash
    $asked = & $python -B -c "from beast_drills import service, settings; print(settings.dashboard_url(settings.load(service.DEFAULT_DATA_DIR)))" 2>$null
    if ($LASTEXITCODE -eq 0 -and $asked) { $url = "$asked".Trim() }
} catch { } finally { Pop-Location }
if ($Port -gt 0) { $url = "http://localhost:$Port" }

Write-Host ""
Write-Host "Beast Drills is running at $url" -ForegroundColor Cyan
Write-Host "It runs in the background. Leave it running while you play; to stop it, run Stop Beast Drills.bat."
Write-Host "Settings: reframework\data\BeastDrills_data\beast_drills.ini" -ForegroundColor DarkGray
if (-not $NoBrowser) { Start-Process $url }
