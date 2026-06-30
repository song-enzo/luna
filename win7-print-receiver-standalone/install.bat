@echo off
setlocal

set INSTALL_DIR=C:\LunaPrint
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set BT_ROOT=D:\BarTender_Print

wmic process where "name='powershell.exe' and commandline like '%%receiver.ps1%%'" call terminate >nul 2>nul
wmic process where "name='powershell.exe' and commandline like '%%manager.ps1%%'" call terminate >nul 2>nul

mkdir "%INSTALL_DIR%" 2>nul
mkdir "%INSTALL_DIR%\templates" 2>nul
mkdir "%INSTALL_DIR%\data" 2>nul
mkdir "%INSTALL_DIR%\logs" 2>nul
mkdir "%BT_ROOT%" 2>nul
mkdir "%BT_ROOT%\Input" 2>nul
mkdir "%BT_ROOT%\Processing" 2>nul
mkdir "%BT_ROOT%\Archive" 2>nul
mkdir "%BT_ROOT%\Error" 2>nul

copy /Y "%~dp0receiver.ps1" "%INSTALL_DIR%\receiver.ps1" >nul
copy /Y "%~dp0manager.ps1" "%INSTALL_DIR%\manager.ps1" >nul
copy /Y "%~dp0config.ini" "%INSTALL_DIR%\config.ini" >nul
copy /Y "%~dp0start-hidden.vbs" "%INSTALL_DIR%\start-hidden.vbs" >nul
copy /Y "%~dp0start-manager.vbs" "%INSTALL_DIR%\start-manager.vbs" >nul
copy /Y "%~dp0test_send.bat" "%INSTALL_DIR%\test_send.bat" >nul
copy /Y "%~dp0send-test.ps1" "%INSTALL_DIR%\send-test.ps1" >nul
copy /Y "%~dp0templates\scuba.btw" "%INSTALL_DIR%\templates\scuba.btw" >nul
copy /Y "%~dp0templates\scuba.btw" "%BT_ROOT%\composition_label.btw" >nul
copy /Y "%~dp0template_data.csv" "%BT_ROOT%\template_data.csv" >nul

del "%STARTUP_DIR%\LunaPrintReceiver.vbs" 2>nul
copy /Y "%INSTALL_DIR%\start-manager.vbs" "%STARTUP_DIR%\LunaPrintManager.vbs" >nul

echo Checking default printer...
wmic printer where Default=True get Name
echo BarTender queue folders:
echo   %BT_ROOT%\Input
echo   %BT_ROOT%\Processing
echo   %BT_ROOT%\Archive
echo   %BT_ROOT%\Error

netsh http delete urlacl url=http://+:9876/ >nul 2>nul
netsh http add urlacl url=http://+:9876/ user=Everyone >nul 2>nul
netsh http add urlacl url=http://+:9876/ sddl=D:(A;;GX;;;WD) >nul 2>nul

netsh advfirewall firewall delete rule name="Luna Print Receiver" >nul 2>nul
netsh advfirewall firewall add rule name="Luna Print Receiver" dir=in action=allow protocol=TCP localport=9876 >nul 2>nul
netsh firewall delete portopening TCP 9876 >nul 2>nul
netsh firewall add portopening TCP 9876 "Luna Print Receiver" ENABLE >nul 2>nul

echo Installed Luna Print Receiver to %INSTALL_DIR%.
echo It will start automatically after Windows login.
echo Starting manager now...
wscript.exe "%INSTALL_DIR%\start-manager.vbs"
echo Done. Test with: %INSTALL_DIR%\test_send.bat
pause
