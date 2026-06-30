@echo off
setlocal

set INSTALL_DIR=C:\LunaPrint
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

del "%STARTUP_DIR%\LunaPrintReceiver.bat" 2>nul
netsh firewall delete portopening TCP 9876 >nul 2>nul

echo Startup entry and firewall rule removed.
echo Installed files remain in %INSTALL_DIR% so logs and template are not deleted.
pause
