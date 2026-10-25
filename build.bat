@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem Always run relative to this script, including when called from another folder.
pushd "%~dp0" || exit /b 1
set "RESULT=0"
set "TARGET=%~1"
if not defined TARGET set "TARGET=build_installer"

if /i "%TARGET%"=="help" goto usage
if /i "%TARGET%"=="--help" goto usage
if /i "%TARGET%"=="all" set "TARGET=build_installer"
if /i "%TARGET%"=="build-installer" set "TARGET=build_installer"
if /i "%TARGET%"=="clean-all" set "TARGET=clean_all"
if /i "%TARGET%"=="build" goto prepare
if /i "%TARGET%"=="build_installer" goto prepare
if /i "%TARGET%"=="dev" goto prepare
if /i "%TARGET%"=="clean" goto prepare
if /i "%TARGET%"=="clean_all" goto prepare
echo [ERROR] Unknown target: "%TARGET%"
set "RESULT=1"
goto usage

:prepare
rem Make fallback tools available to child Task processes as well.
set "PATH=%PATH%;%USERPROFILE%\go\bin;%ProgramFiles(x86)%\NSIS;%ProgramFiles(x86)%\NSIS\Bin;%ProgramFiles%\NSIS;%ProgramFiles%\NSIS\Bin"
where task >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Task is missing. Install: go install github.com/go-task/task/v3/cmd/task@latest
    set "RESULT=1"
    goto end
)
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is missing. Install Node.js 22.12+ or 24 LTS.
    set "RESULT=1"
    goto end
)
if /i "%TARGET%"=="clean" goto do_clean
if /i "%TARGET%"=="clean_all" goto do_clean_all
for %%T in (go npm wails3) do (
    where %%T >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Required tool %%T is missing. See README.md for setup.
        set "RESULT=1"
        goto end
    )
)
if /i "%TARGET%"=="dev" goto do_dev
if /i "%TARGET%"=="build" goto do_build
where makensis >nul 2>nul
if errorlevel 1 (
    echo [ERROR] NSIS 3 is missing. Install NSIS and retry.
    set "RESULT=1"
    goto end
)
echo [installer] Building Windows amd64 application and installer...
task windows:package
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto end
if not exist "build\bin\yumo_editor-amd64-installer.exe" (
    echo [ERROR] Installer output is missing.
    set "RESULT=1"
    goto end
)
echo [OK] Installer: %~dp0build\bin\yumo_editor-amd64-installer.exe
goto end

:do_build
task build
set "RESULT=%ERRORLEVEL%"
goto end

:do_dev
wails3 dev
set "RESULT=%ERRORLEVEL%"
goto end

:do_clean
task clean
set "RESULT=%ERRORLEVEL%"
goto end

:do_clean_all
task clean:all
set "RESULT=%ERRORLEVEL%"
goto end

:usage
echo Usage: %~nx0 [build_installer ^| build ^| dev ^| clean ^| clean_all]
echo Default / all: build the application and Windows NSIS installer.
echo build: executable only. clean_all: also remove node_modules; keep the lockfile.

:end
popd
exit /b %RESULT%
