@echo off
cd /d "%~dp0"
if exist "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe" (
  start "" "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe" launcher.py
) else (
  "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" launcher.py
)
