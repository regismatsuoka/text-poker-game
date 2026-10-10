@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
    py -m poker_game %*
) else (
    python -m poker_game %*
)

exit /b %errorlevel%
