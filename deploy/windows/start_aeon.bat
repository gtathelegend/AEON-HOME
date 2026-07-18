@echo off
setlocal
echo ====================================================
echo Starting ÆON Home - Edge AI Engine (Bare Metal)
echo ====================================================

REM Navigate to repository root
cd /d "%~dp0\..\.."

REM Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found. Copying .env.example...
    copy .env.example .env
    echo Please edit .env before running again.
    pause
    exit /b 1
)

REM Parse .env and export variables (simple batch parser)
for /f "tokens=1,2 delims==" %%A in (.env) do (
    if not "%%A"=="" if not "%%A"==" " if not "%%A:~0,1" == "#" (
        set %%A=%%B
    )
)

echo [INFO] Starting Backend (FastAPI)...
start "AEON Backend" cmd /c "cd backend && python -m aeon.main"

echo [INFO] Waiting 3 seconds for Backend to initialize...
timeout /t 3 /nobreak >nul

echo [INFO] Starting Frontend (Nitro SSR)...
start "AEON Frontend" cmd /c "cd frontend && node .output/server/index.mjs"

echo [SUCCESS] ÆON Home is running.
echo - Dashboard: http://localhost:%NITRO_PORT%
echo - API:       http://localhost:%AEON_API_PORT%
echo - Metrics:   http://localhost:%AEON_METRICS_PORT%
echo Close these windows to stop the services.
endlocal
pause
