
@echo off
setlocal EnableDelayedExpansion

title SupportIQ Startup

echo ========================================
echo          SupportIQ Startup
echo ========================================
echo.

cd /d "%~dp0"

where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Conda was not found.
    echo Install Miniconda first:
    echo https://docs.anaconda.com/miniconda/install/
    pause
    exit /b 1
)

set "ENV_NAME=supportiq"

conda env list | findstr /R /C:"^[ ]*%ENV_NAME%[ ]" >nul 2>&1

if %errorlevel% neq 0 (
    echo [INFO] Creating Conda environment: %ENV_NAME%
    call conda create -n %ENV_NAME% python=3.10 -y

    if not exist "%USERPROFILE%\miniconda3\envs\%ENV_NAME%\python.exe" (
        echo [ERROR] Conda environment creation failed.
        pause
        exit /b 1
    )

    echo [INFO] Conda environment created successfully.
) else (
    echo [INFO] Conda environment already exists: %ENV_NAME%
)

echo [INFO] Activating environment...
call conda activate %ENV_NAME%

if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate Conda environment.
    pause
    exit /b 1
)

if exist "requirements.txt" (
    echo.
    echo [INFO] Installing dependencies...
    python -m pip install -r requirements.txt

    if %errorlevel% neq 0 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
) else (
    echo [ERROR] requirements.txt was not found.
    pause
    exit /b 1
)

REM Create .env automatically without requiring an API key.
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [INFO] .env created.
        echo [INFO] Gemini API key can be configured in the UI.
    ) else (
        echo [WARNING] .env.example was not found.
    )
)

echo.
echo ========================================
echo       Starting SupportIQ
echo ========================================
echo.
echo Open http://localhost:8000
echo Configure the Gemini API key from the UI.
echo Press CTRL+C to stop the application.
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
endlocal