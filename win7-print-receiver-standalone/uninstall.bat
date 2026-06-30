@echo off
setlocal

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

del "%STARTUP_DIR%\LunaPrintReceiver.vbs" 2>nul
del "%STARTUP_DIR%\LunaPrintManager.vbs" 2>nul
netsh http delete urlacl url=http://+:9876/ >nul 2>nul
netsh advfirewall firewall delete rule name="Luna Print Receiver" >nul 2>nul
netsh firewall delete portopening TCP 9876 >nul 2>nul

echo Startup entry, HTTP permission, and firewall rule removed.
echo C:\LunaPrint is kept for logs, data, and template backup.
pause
