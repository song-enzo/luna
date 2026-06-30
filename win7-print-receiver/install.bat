@echo off
setlocal

set INSTALL_DIR=C:\LunaPrint
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set PY_EXE=

if exist "C:\Python38\python.exe" set PY_EXE=C:\Python38\python.exe
if exist "C:\Python37\python.exe" set PY_EXE=C:\Python37\python.exe
if exist "C:\Python27\python.exe" set PY_EXE=C:\Python27\python.exe

if "%PY_EXE%"=="" (
  echo Python not found. Please install Python 3.8 for Windows 7 first.
  pause
  exit /b 1
)

mkdir "%INSTALL_DIR%" 2>nul
mkdir "%INSTALL_DIR%\templates" 2>nul
mkdir "%INSTALL_DIR%\data" 2>nul
mkdir "%INSTALL_DIR%\logs" 2>nul

copy /Y "%~dp0receiver.py" "%INSTALL_DIR%\receiver.py" >nul
copy /Y "%~dp0config.ini" "%INSTALL_DIR%\config.ini" >nul
copy /Y "%~dp0templates\scuba.btw" "%INSTALL_DIR%\templates\scuba.btw" >nul
copy /Y "%~dp0test_send.py" "%INSTALL_DIR%\test_send.py" >nul

(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo "%PY_EXE%" "%INSTALL_DIR%\receiver.py"
) > "%INSTALL_DIR%\start_receiver.bat"

copy /Y "%INSTALL_DIR%\start_receiver.bat" "%STARTUP_DIR%\LunaPrintReceiver.bat" >nul

netsh firewall add portopening TCP 9876 "Luna Print Receiver" ENABLE >nul 2>nul

echo Installed Luna Print Receiver to %INSTALL_DIR%.
echo It will start automatically after Windows login.
echo Starting receiver now...
start "" /MIN "%INSTALL_DIR%\start_receiver.bat"
pause
