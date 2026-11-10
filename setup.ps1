$ErrorActionPreference = 'Stop'

Write-Host 'Orbit local setup' -ForegroundColor Green
Write-Host 'This creates a private .env file in this folder. The database password is read as a secure prompt.'

$dbHost = Read-Host 'PostgreSQL host [localhost]'
if ([string]::IsNullOrWhiteSpace($dbHost)) { $dbHost = 'localhost' }
$portText = Read-Host 'PostgreSQL port [5433]'
if ([string]::IsNullOrWhiteSpace($portText)) { $portText = '5433' }
$dbName = Read-Host 'Orbit database name [orbit_intelligence]'
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = 'orbit_intelligence' }
$dbUser = Read-Host 'PostgreSQL login [postgres]'
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = 'postgres' }
$securePassword = Read-Host 'PostgreSQL password' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try { $dbPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }

$neoEnabled = Read-Host 'Configure the local Neo4j graph mirror? [Y/n]'
$neoUser = 'neo4j'
$neoPassword = ''
if ([string]::IsNullOrWhiteSpace($neoEnabled) -or $neoEnabled -match '^(y|yes)$') {
  $neoUserInput = Read-Host 'Neo4j username [neo4j]'
  if (-not [string]::IsNullOrWhiteSpace($neoUserInput)) { $neoUser = $neoUserInput }
  $neoSecurePassword = Read-Host 'Neo4j password' -AsSecureString
  $neoPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($neoSecurePassword)
  try { $neoPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($neoPtr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($neoPtr) }
  $neoSecurePassword.Dispose()
}

$uri = [UriBuilder]::new('postgres', $dbHost, [int]$portText, "/$dbName")
$uri.UserName = $dbUser
$uri.Password = $dbPassword
$databaseUrl = $uri.Uri.AbsoluteUri
$sessionSecret = (& node -e "console.log(require('crypto').randomBytes(48).toString('hex'))").Trim()
$encryptionKey = (& node -e "console.log(require('crypto').randomBytes(32).toString('hex'))").Trim()
$envText = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'server/.env.example') -Raw
$envText = $envText -replace '(?m)^DATABASE_URL=.*$', "DATABASE_URL=$databaseUrl"
$envText = $envText -replace '(?m)^SESSION_SECRET=.*$', "SESSION_SECRET=$sessionSecret"
$envText = $envText -replace '(?m)^ENCRYPTION_KEY=.*$', "ENCRYPTION_KEY=$encryptionKey"
$envText = $envText -replace '(?m)^GITHUB_TOKEN=.*$', 'GITHUB_TOKEN='
$envText = $envText -replace '(?m)^NEO4J_URI=.*$', "NEO4J_URI=$(if ($neoPassword) { 'bolt://localhost:7687' } else { '' })"
$envText = $envText -replace '(?m)^NEO4J_USER=.*$', "NEO4J_USER=$neoUser"
$neoPasswordEscaped = $neoPassword.Replace('\', '\\').Replace('"', '\"')
$envText = $envText -replace '(?m)^NEO4J_PASSWORD=.*$', "NEO4J_PASSWORD=`"$neoPasswordEscaped`""
Set-Content -LiteralPath (Join-Path $PSScriptRoot '.env') -Value $envText -Encoding utf8
$dbPassword = $null
$neoPassword = $null
$securePassword.Dispose()

Write-Host 'Private .env created. Installing dependencies and starting Orbit…' -ForegroundColor Green
Push-Location $PSScriptRoot
try {
  if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'node_modules'))) {
    npm install
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
  }
  npm start
} finally { Pop-Location }
