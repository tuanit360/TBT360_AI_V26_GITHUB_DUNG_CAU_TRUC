$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path 'SHA256SUMS.txt')) { throw 'SHA256SUMS.txt not found' }
$errors = 0
Get-Content 'SHA256SUMS.txt' | ForEach-Object {
  if ($_ -match '^([a-fA-F0-9]{64})  (.+)$') {
    $wanted = $Matches[1].ToUpperInvariant()
    $relative = $Matches[2].Replace('/', [IO.Path]::DirectorySeparatorChar)
    $path = Join-Path $PSScriptRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      Write-Host "[MISSING] $relative"
      $errors++
    } elseif ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $wanted) {
      Write-Host "[MISMATCH] $relative"
      $errors++
    }
  }
}
if ($errors -gt 0) { Write-Host "[FAIL] $errors files mismatched"; exit 1 }
Write-Host '[OK] SHA256 integrity verified'
exit 0
