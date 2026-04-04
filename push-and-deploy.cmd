@echo off
setlocal
REM Deploy: GitHub push + SSH server-update.sh. Run from Explorer or any CMD.
REM Example: push-and-deploy.cmd -SshTarget root@YOUR_IP
cd /d "%~dp0"
where powershell >nul 2>&1
if errorlevel 1 (
  echo ERROR: powershell.exe not in PATH.
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\push-and-update-server.ps1" %*
exit /b %ERRORLEVEL%
