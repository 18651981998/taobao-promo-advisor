#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 GBK 编码的启动器 bat（Windows CMD 中文兼容）"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EXT = os.path.join(ROOT, "extension")

# ---- 一键安装.bat：起服务 + 选浏览器 + 注入书签到书签栏 ----
install_bat = f"""@echo off
chcp 936 >nul
cd /d "%~dp0"
if not exist "{PY}" (
    echo 找不到 Python，请检查 WorkBuddy 环境。
    pause
    exit /b 1
)
echo 正在启动本地服务并安装书签，请稍候...
"{PY}" install_helper.py
"""

# ---- 加载扩展.bat：起服务 + 关 Chrome + 以扩展方式启动 Chrome ----
load_ext_bat = f"""@echo off
chcp 936 >nul
cd /d "%~dp0"
if not exist "{PY}" (
    echo 找不到 Python，请检查 WorkBuddy 环境。
    pause
    exit /b 1
)
if not exist "{CHROME}" (
    echo 未检测到 Chrome，请安装 Google Chrome 后使用。
    pause
    exit /b 1
)
echo 正在启动本地服务...
start "" /b "{PY}" promo_server.py
timeout /t 2 /nobreak >nul
echo 正在关闭 Chrome 并以扩展方式重新打开...
taskkill /F /IM chrome.exe 2>nul
timeout /t 1 /nobreak >nul
start "" "{CHROME}" --load-extension="{EXT}" http://127.0.0.1:8123/
echo.
echo 已打开 Chrome 并加载「淘系推广参谋」扩展。
echo 在浏览器右上角工具栏点击扩展图标，即可在商品页一键导入。
echo （注意：用此方式打开的扩展为开发者模式，关闭后下次需重新运行本文件）
pause
"""

with open(os.path.join(ROOT, "一键安装.bat"), "w", encoding="gbk") as f:
    f.write(install_bat)
with open(os.path.join(ROOT, "加载扩展.bat"), "w", encoding="gbk") as f:
    f.write(load_ext_bat)

print("已生成：一键安装.bat / 加载扩展.bat")
