$ErrorActionPreference = "Stop"

$kaggleDir = Join-Path $HOME ".kaggle"
$tokenPath = Join-Path $kaggleDir "access_token"

$secureToken = Read-Host "Cole o KAGGLE_API_TOKEN" -AsSecureString
$tokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)

try {
    $plainToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPtr)
    New-Item -ItemType Directory -Force $kaggleDir | Out-Null
    Set-Content -NoNewline -Path $tokenPath -Value $plainToken
    Write-Host "Token Kaggle salvo em $tokenPath"
}
finally {
    if ($tokenPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPtr)
    }
}
