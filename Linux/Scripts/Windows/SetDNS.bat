@echo off
setlocal enabledelayedexpansion

REM === Check Admin Rights ===
NET SESSION >nul 2>&1 || (
    echo ERROR: Run as Administrator!
    pause
    exit /b
)

REM === New Interface Parsing Method ===
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
  echo Run these commands manually:
  echo 1. netsh interface show interface
  echo 2. ipconfig /all
  pause
  exit /b
)

REM === Interface Selection ===
:retry
set /p INTERFACE_INDEX="Select interface (1-!counter!): "
echo !INTERFACE_INDEX!|findstr /R "^[1-9][0-9]*$" >nul || goto retry
if !INTERFACE_INDEX! gtr !counter! goto retry

REM === Get Interface Name ===
set INTERFACE_NAME=!name[%INTERFACE_INDEX%]!
echo Selected interface: "!INTERFACE_NAME!"

REM === DNS Configuration ===
SET PREFERRED_DNS=185.51.200.2
SET ALTERNATE_DNS=178.22.122.100

netsh interface ip set dns name="!INTERFACE_NAME!" source=static addr=%PREFERRED_DNS% validate=no
netsh interface ip add dns name="!INTERFACE_NAME!" addr=%ALTERNATE_DNS% index=2 validate=no

echo Success! Press any key...
pause