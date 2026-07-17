@echo off
cd /d "%~dp0"

:: 强制清理 Python 字节码缓存，防止更新代码后仍运行旧版逻辑
for /d %%x in (__pycache__) do rd /s /q "%%x" 2>nul
del /s /q "*.pyc" 2>nul

if exist "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe" (
  start "" "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe" launcher.py
) else (
  "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" launcher.py
)
