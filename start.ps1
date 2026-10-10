Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $scriptDirectory
try {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -m poker_game @args
    } else {
        & python -m poker_game @args
    }

    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

exit $exitCode
