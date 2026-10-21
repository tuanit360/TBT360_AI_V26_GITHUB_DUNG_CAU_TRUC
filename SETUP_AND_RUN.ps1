$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root
$Runtime = Join-Path $Root 'runtime'
$PythonHome = Join-Path $Runtime 'Python311'
$Python = Join-Path $PythonHome 'python.exe'
$Venv = Join-Path $Runtime 'ai_env'
$Py = Join-Path $Venv 'Scripts\python.exe'
$Logs = Join-Path $Root 'logs'
$Cache = Join-Path $Runtime 'downloads'
New-Item -ItemType Directory -Force -Path $Logs,$Cache | Out-Null
$Log = Join-Path $Logs 'bootstrap.log'
function Note([string]$s) {
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $s"
  Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
  Write-Host $line
}
function ValidPython([string]$exe) {
  if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { return $false }
  try {
    $v = & $exe -c 'import sys; print(str(sys.version_info.major) + "." + str(sys.version_info.minor))' 2>$null
    return ($LASTEXITCODE -eq 0 -and ($v -join '').Trim() -eq '3.11')
  } catch { return $false }
}
function Run([string]$exe, [string[]]$arguments) {
  Note ('[RUN] ' + $exe + ' ' + ($arguments -join ' '))
  $saved = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    & $exe @arguments 2>&1 | ForEach-Object {
      $line = "$_"
      Write-Host $line
      Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
    }
    $code = $LASTEXITCODE
  } finally { $ErrorActionPreference = $saved }
  if ($code -ne 0) { throw "Command exited ${code}: $exe" }
}
function FindInstalledPython {
  # First find an existing private installation, then registered per-user/system Python.
  $candidatePaths = New-Object 'System.Collections.Generic.List[string]'
  $candidatePaths.Add($Python)
  $registryPaths = @(
    'HKCU:\Software\Python\PythonCore\3.11\InstallPath',
    'HKLM:\Software\Python\PythonCore\3.11\InstallPath',
    'HKLM:\Software\WOW6432Node\Python\PythonCore\3.11\InstallPath'
  )
  foreach ($key in $registryPaths) {
    try {
      $keyData = Get-Item -LiteralPath $key -ErrorAction Stop
      $directory = $keyData.GetValue('')
      if ($directory) { $candidatePaths.Add((Join-Path $directory 'python.exe')) }
      $executable = $keyData.GetValue('ExecutablePath')
      if ($executable) { $candidatePaths.Add($executable) }
    } catch { }
  }
  $candidatePaths.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'))
  $candidatePaths.Add('C:\Python311\python.exe')
  $candidatePaths.Add('C:\Program Files\Python311\python.exe')
  try {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
      $launcherList = & $launcher.Source -0p 2>$null
      foreach ($entry in $launcherList) {
        if ($entry -match '^\s*-V:3\.11(?:-64)?\s+(.+python\.exe)\s*$') {
          $candidatePaths.Add($Matches[1].Trim('"'))
        }
      }
    }
  } catch { }
  foreach ($commandName in @('python.exe','python3.exe')) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) { $candidatePaths.Add($command.Source) }
  }
  foreach ($candidate in ($candidatePaths | Select-Object -Unique)) {
    if (ValidPython $candidate) {
      # Prevent selecting Windows Store aliases and 32-bit Python.
      $bits = & $candidate -c 'import struct; print(struct.calcsize("P") * 8)' 2>$null
      if ($LASTEXITCODE -eq 0 -and ($bits -join '').Trim() -eq '64') { return $candidate }
    }
  }
  return $null
}

try {
  Note '[START] TBT360 AI V65 Windows repaired bootstrap (Python 3.11 x64).'
  Note ('[ROOT] ' + $Root)
  $found = FindInstalledPython
  if ($found) {
    $Python = $found
    Note ('[FOUND] Existing Python 3.11 x64: ' + $Python)
  } else {
    Note '[INFO] Python 3.11 x64 not found. Downloading official installer.'
    $Installer = Join-Path $Cache 'python-3.11.9-amd64.exe'
    if (!(Test-Path -LiteralPath $Installer) -or (Get-Item $Installer).Length -lt 10000000) {
      $url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
      Note ('[DOWNLOAD] ' + $url)
      Invoke-WebRequest -Uri $url -OutFile $Installer -UseBasicParsing -TimeoutSec 3600
    }
    $signature = Get-AuthenticodeSignature -FilePath $Installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
      throw 'Official Python installer signature verification failed.'
    }
    $InstallerLog = Join-Path $Logs 'python-installer.log'
    $installArgs = '/quiet InstallAllUsers=0 Include_pip=1 Include_launcher=1 PrependPath=0 Shortcuts=0 AssociateFiles=0 Include_test=0 /log "' + $InstallerLog + '"'
    Note '[INSTALL] Installing Python 3.11 for current user.'
    $proc = Start-Process -FilePath $Installer -ArgumentList $installArgs -Wait -PassThru
    Note ('[INSTALL] Python installer exit=' + $proc.ExitCode)
    $found = FindInstalledPython
    if (!$found) {
      throw 'Python is still unavailable. If Python is installed, check its path or logs/python-installer.log.'
    }
    $Python = $found
  }
  Note ('[PYTHON] ' + $Python)
  if (!(ValidPython $Py)) {
    Note '[INSTALL] Creating private virtual environment.'
    Run $Python @('-m','venv',$Venv)
  }
  if (!(ValidPython $Py)) { throw 'Virtual environment creation failed.' }
  Note ('[VENV] ' + $Py)
  Run $Py @('-m','pip','--version')
  & $Py -c 'import torch, torchvision; print(torch.__version__)' *> $null
  if ($LASTEXITCODE -ne 0) {
    Note '[INSTALL] Installing PyTorch 2.5.1 CUDA 12.1 (requires internet and disk space).'
    Run $Py @('-m','pip','install','--disable-pip-version-check','torch==2.5.1','torchvision==0.20.1','--index-url','https://download.pytorch.org/whl/cu121')
  }
  & $Py (Join-Path $Root 'tools\check_runtime.py') *> $null
  if ($LASTEXITCODE -ne 0) {
    Note '[INSTALL] Installing remaining AI dependencies.'
    Run $Py @('-m','pip','install','--disable-pip-version-check','-r',(Join-Path $Root 'requirements.txt'))
  }
  $probeLog = Join-Path $Logs 'check_stdout.json'
  $probe = & $Py (Join-Path $Root 'tools\check_runtime.py') 2>&1
  $probe | Out-File -FilePath $probeLog -Encoding utf8
  if ($LASTEXITCODE -ne 0) { throw ('Dependency validation failed: ' + $probeLog) }
  $data = ($probe -join "`n") | ConvertFrom-Json
  if (!$data.ok) { throw ('Missing AI modules: ' + $probeLog) }
  Note ('[READY] All modules import successfully. CUDA detected=' + $data.cuda)
  $env:HF_HOME = Join-Path $Runtime 'huggingface_cache'
  $env:HF_HUB_DISABLE_TELEMETRY = '1'
  Note '[RUN] Launching TBT360 AI on localhost:7861'
  & $Py (Join-Path $Root 'app\generate.py')
  if ($LASTEXITCODE -ne 0) { throw "App exit code: $LASTEXITCODE" }
} catch {
  Note ('[ERROR] ' + $_.Exception.Message)
  Write-Host 'Send logs/bootstrap.log and logs/python-installer.log for further diagnosis.'
  exit 1
}
