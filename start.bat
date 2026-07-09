@echo off
setlocal enabledelayedexpansion
title Factorio Server Manager Launcher

set "ROOT=%~dp0"
set "PORT=8199"
set "URL=http://127.0.0.1:%PORT%"

rem ---- Resolve python: prefer venv, then system ----
set "PY_CMD="
if exist "%ROOT%backend\venv\Scripts\python.exe" (
    set "PY_CMD=%ROOT%backend\venv\Scripts\python.exe"
)
if not defined PY_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python --version >nul 2>nul
        if not errorlevel 1 set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo ERROR: python not found.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Or create a venv: python -m venv backend\venv
    pause
    exit /b 1
)

echo ============================================
echo   Factorio Server Manager Launcher
echo   Frontend + backend: %URL%
echo ============================================
echo Using python: %PY_CMD%
echo.

rem ---- Check and free port ----
echo [preflight] Checking port %PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%kill_stale_port.ps1" -Port %PORT%
set "PS_EXIT=%errorlevel%"
if "%PS_EXIT%"=="1" (
    echo ERROR: failed to release port %PORT% from an old process.
    pause
    exit /b 1
) else if "%PS_EXIT%"=="2" (
    echo ERROR: port %PORT% is held by another program. Close it and retry.
    pause
    exit /b 1
)

rem ---- Install backend dependencies ----
echo [1/3] Checking backend dependencies...
if not exist "%ROOT%backend\requirements.txt" (
    echo ERROR: backend\requirements.txt not found.
    pause
    exit /b 1
)

"%PY_CMD%" -c "import fastapi" >nul 2>nul
if errorlevel 1 (
    echo Installing backend dependencies...
    "%PY_CMD%" -m pip install -r "%ROOT%backend\requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

rem ---- Resolve npm ----
set "TRAE_NODE=%APPDATA%\TRAE SOLO CN\ModularData\ai-agent\vm\tools\node"
where npm >nul 2>nul
if errorlevel 1 if exist "%TRAE_NODE%\npm.cmd" set "PATH=%TRAE_NODE%;%PATH%"

where npm >nul 2>nul
if errorlevel 1 (
    echo WARNING: npm not found. Frontend build will be skipped.
    echo If you need the frontend, install Node.js from https://nodejs.org/
    goto :skip_frontend
)

rem ---- Build frontend if dist/ does not exist ----
if not exist "%ROOT%frontend\dist\index.html" (
    echo [2/3] Building frontend...
    pushd "%ROOT%frontend"
    call npm install
    if errorlevel 1 (
        echo ERROR: npm install failed.
        popd
        pause
        exit /b 1
    )
    call npm run build
    if errorlevel 1 (
        echo ERROR: Frontend build failed.
        popd
        pause
        exit /b 1
    )
    popd
    echo Frontend built successfully.
) else (
    echo [2/3] Frontend dist/ already exists, skipping build.
    echo ^(Delete frontend\dist\ to force rebuild^)
)

:skip_frontend
echo [3/3] Starting server on %URL% ...
echo.
echo Open in browser:
echo   Local:   http://127.0.0.1:%PORT%
echo.
echo Press Ctrl+C to stop.
echo.

cd /d "%ROOT%backend"
"%PY_CMD%" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

endlocal
