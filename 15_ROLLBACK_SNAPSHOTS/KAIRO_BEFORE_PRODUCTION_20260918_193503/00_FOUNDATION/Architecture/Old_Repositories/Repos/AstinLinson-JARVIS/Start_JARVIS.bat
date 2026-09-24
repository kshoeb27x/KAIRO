@echo off
:: ============================================================
:: Start_JARVIS.bat — Production launcher for JARVIS
:: ============================================================
:: Resolves paths dynamically. Never hardcodes usernames.
:: Writes all errors to logs\startup.log for diagnosis.
:: ============================================================

:: Resolve the directory this script lives in
set "SCRIPT_DIR=%~dp0"

:: The project root is the parent of JARVIS\ (this bat lives next to JARVIS\)
set "PROJECT_ROOT=%SCRIPT_DIR%"

:: Change to project root so JARVIS finds config\config.yaml
cd /d "%PROJECT_ROOT%"

:: Ensure the logs directory exists
if not exist "JARVIS\logs" mkdir "JARVIS\logs"

:: Timestamp for the startup log
echo. >> "JARVIS\logs\startup.log"
echo ============================================ >> "JARVIS\logs\startup.log"
echo JARVIS Startup: %date% %time% >> "JARVIS\logs\startup.log"
echo Working Directory: %PROJECT_ROOT% >> "JARVIS\logs\startup.log"
echo ============================================ >> "JARVIS\logs\startup.log"

:: Detect Python — prefer the venv if it exists
if exist "%PROJECT_ROOT%JARVIS\.venv\Scripts\python.exe" (
    set "PYTHON=%PROJECT_ROOT%JARVIS\.venv\Scripts\python.exe"
    echo Using venv Python: %PYTHON% >> "JARVIS\logs\startup.log"
) else (
    set "PYTHON=python"
    echo Using system Python >> "JARVIS\logs\startup.log"
)

:: Launch JARVIS
echo Starting JARVIS... >> "JARVIS\logs\startup.log"
"%PYTHON%" -m JARVIS.main >> "JARVIS\logs\startup.log" 2>&1

:: If we get here, JARVIS exited
echo JARVIS exited with code %ERRORLEVEL% at %date% %time% >> "JARVIS\logs\startup.log"
