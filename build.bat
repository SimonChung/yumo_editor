@echo off
setlocal enabledelayedexpansion

:: Windows Build Script (converted from Makefile.win)
set BINARY_NAME=yumo_editor.exe

:: Detect task executable
where task >nul 2>nul
if %errorlevel% equ 0 (
    set TASK_CMD=task
) else if exist "%USERPROFILE%\go\bin\task.exe" (
    set TASK_CMD="%USERPROFILE%\go\bin\task.exe"
) else (
    echo [WARNING] 'task' command not found on PATH or in %%USERPROFILE%%\go\bin.
    echo Please install it via: go install github.com/go-task/task/v3/cmd/task@latest
    set TASK_CMD=task
)

:: Detect wails3 executable
where wails3 >nul 2>nul
if %errorlevel% equ 0 (
    set WAILS_CMD=wails3
) else if exist "%USERPROFILE%\go\bin\wails3.exe" (
    set WAILS_CMD="%USERPROFILE%\go\bin\wails3.exe"
) else (
    echo [WARNING] 'wails3' command not found on PATH or in %%USERPROFILE%%\go\bin.
    set WAILS_CMD=wails3
)

:: Handle arguments
set TARGET=%~1
if "%TARGET%"=="" set TARGET=build

if /i "%TARGET%"=="all" goto do_build
if /i "%TARGET%"=="build" goto do_build
if /i "%TARGET%"=="build_installer" goto do_build_installer
if /i "%TARGET%"=="build-installer" goto do_build_installer
if /i "%TARGET%"=="dev" goto do_dev
if /i "%TARGET%"=="clean" goto do_clean
if /i "%TARGET%"=="clean_all" goto do_clean_all
if /i "%TARGET%"=="clean-all" goto do_clean_all

echo Unknown target: %TARGET%
echo Usage: %~nx0 [build ^| build_installer ^| dev ^| clean ^| clean_all]
exit /b 1

:do_build
echo [build] Running: %TASK_CMD% build
%TASK_CMD% build
if %errorlevel% neq 0 (
    echo [ERROR] Build failed!
    exit /b %errorlevel%
)
goto end

:do_dev
echo [dev] Running: %WAILS_CMD% dev
%WAILS_CMD% dev
if %errorlevel% neq 0 (
    echo [ERROR] Dev mode failed to start!
    exit /b %errorlevel%
)
goto end

:do_clean
echo [clean] Running: %TASK_CMD% clean
%TASK_CMD% clean
if %errorlevel% neq 0 (
    echo [ERROR] Clean failed!
    exit /b %errorlevel%
)
goto end

:do_clean_all
echo [clean_all] Running: %TASK_CMD% clean:all
%TASK_CMD% clean:all
if %errorlevel% neq 0 (
    echo [ERROR] Clean all failed!
    exit /b %errorlevel%
)
:do_build_installer
echo [build_installer] Running: %TASK_CMD% package
%TASK_CMD% package
if %errorlevel% neq 0 (
    echo [ERROR] Installer build failed!
    exit /b %errorlevel%
)
goto end

:end
echo Execution completed successfully.
exit /b 0
