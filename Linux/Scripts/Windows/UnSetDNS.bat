@echo off
setlocal enabledelayedexpansion

REM === Check Admin Rights ===
NET SESSION >nul 2>&1 || (
    echo ERROR: Run as Administrator!
    pause
    exit /b
)

REM === List Interfaces ===
echo Scanning network interfaces...
echo ==================================

set counter=0
for /f "tokens=3* delims= " %%A in (
  'netsh interface show interface ^| findstr /R /C:"Connected" /C:"Disconnected"'
) do (
  set /a counter+=1
  set "name[!counter!]=%%B"
  echo [!counter!] %%B
)

if !counter! equ 0 (
  echo ERROR: No interfaces found
  pause
  exit /b
)

REM === Interface Selection ===
:retry
set /p INTERFACE_INDEX="Select interface to reset DNS (1-!counter!): "
echo !INTERFACE_INDEX!|findstr /R "^[1-9][0-9]*$" >nul || goto retry
if !INTERFACE_INDEX! gtr !counter! goto retry

REM === Get Interface Name ===
set INTERFACE_NAME=!name[%INTERFACE_INDEX%]!

REM === Reset to DHCP ===
netsh interface ip set dns name="!INTERFACE_NAME!" source=dhcp

echo(
echo SUCCESS: DNS reset to DHCP for "!INTERFACE_NAME!"
echo The interface will now obtain DNS automatically from your network.

REM === Quick Verification ===
echo Current DNS settings:
ipconfig /all | findstr /C:"DNS Servers" /C:"!INTERFACE_NAME!"

pause