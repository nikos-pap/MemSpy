@echo off

set SCRIPT_DIR=%~dp0\.githooks
set HOOK_DIR=.git\hooks

REM Ensure hooks directory exists
if not exist "%HOOK_DIR%" mkdir "%HOOK_DIR%"

REM Copy all scripts into hooks
xcopy "%SCRIPT_DIR%\*" "%HOOK_DIR%\" /Y /Q

echo Git hooks installed from "%SCRIPT_DIR%".