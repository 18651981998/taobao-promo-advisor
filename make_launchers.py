#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 GBK 编码的 Windows 启动器，统一使用 Chrome 浏览器。"""
import os

ROOT = r"C:\Users\Administrator\WorkBuddy\2026-07-17-08-30-54"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 8123

def write(name, content):
    p = os.path.join(ROOT, name)
    with open(p, "w", encoding="gbk") as f:
        f.write(content)
    print(f"已生成 {name} ({os.path.getsize(p)} bytes)")

# 1. 启动.bat：起服务 + 用 Chrome 打开工具页
bat_start = (
    '@echo off\n'
    'chcp 936 >nul\n'
    'cd /d "%~dp0"\n'
    'if not exist "' + PY + '" (\n'
    '    echo 找不到 Python：' + PY + '\n'
    '    echo 请检查 .workbuddy 是否安装\n'
    '    pause\n'
    '    exit /b 1\n'
    ')\n'
    'if not exist "' + CHROME + '" (\n'
    '    echo 未检测到 Google Chrome，请安装 Chrome 后使用。\n'
    '    echo 360浏览器会导致页面卡加载，不推荐使用。\n'
    '    pause\n'
    '    exit /b 1\n'
    ')\n'
    'echo 正在启动淘系推广参谋...\n'
    'start /b "" "' + PY + '" promo_server.py\n'
    'timeout /t 2 /nobreak >nul\n'
    'echo 正在使用 Chrome 打开工具...\n'
    'start "" "' + CHROME + '" "http://127.0.0.1:' + str(PORT) + '/"\n'
    'echo 服务已启动，Chrome 正在打开...\n'
    'echo 按任意键关闭此窗口（服务仍在后台运行）\n'
    'pause >nul\n'
)
write("启动.bat", bat_start)

# 2. start.vbs：无黑窗启动 + 用 Chrome 打开
vbs = (
    'Set ws = CreateObject("WScript.Shell")\n'
    'Set fso = CreateObject("Scripting.FileSystemObject")\n'
    'thisDir = fso.GetParentFolderName(WScript.ScriptFullName)\n'
    'pyPath = "' + PY + '"\n'
    'chromePath = "' + CHROME + '"\n'
    'port = ' + str(PORT) + '\n'
    '\n'
    'If Not fso.FileExists(pyPath) Then\n'
    '    MsgBox "找不到 Python：" & pyPath & vbCrLf & "请检查 .workbuddy 是否安装", vbCritical, "启动失败"\n'
    '    WScript.Quit\n'
    'End If\n'
    'If Not fso.FileExists(chromePath) Then\n'
    '    MsgBox "未检测到 Google Chrome。" & vbCrLf & "360浏览器会导致页面卡加载，请安装 Chrome 后使用。", vbCritical, "启动失败"\n'
    '    WScript.Quit\n'
    'End If\n'
    '\n'
    "' 启动后台服务（0 = 隐藏窗口，不阻塞）\n"
    'cmd = "\"" & pyPath & "\" \"" & thisDir & "\\promo_server.py\""\n'
    'ws.Run cmd, 0, False\n'
    '\n'
    'WScript.Sleep 2500\n'
    '\n'
    "' 用 Chrome 打开本地工具\n"
    'ws.Run "\"" & chromePath & "\" \"http://127.0.0.1:" & port & "/\"", 1, False\n'
)
write("start.vbs", vbs)

# 3. 加载扩展.bat：用 Chrome 加载 extension 目录
bat_ext = (
    '@echo off\n'
    'chcp 936 >nul\n'
    'cd /d "%~dp0"\n'
    'if not exist "' + PY + '" (\n'
    '    echo 找不到 Python，请检查 WorkBuddy 环境。\n'
    '    pause\n'
    '    exit /b 1\n'
    ')\n'
    'if not exist "' + CHROME + '" (\n'
    '    echo 未检测到 Chrome，请安装 Google Chrome 后使用。\n'
    '    pause\n'
    '    exit /b 1\n'
    ')\n'
    'if not exist "extension\\manifest.json" (\n'
    '    echo 未找到扩展目录，请确认 extension 文件夹存在。\n'
    '    pause\n'
    '    exit /b 1\n'
    ')\n'
    'echo 正在启动本地服务...\n'
    'start "" /b "' + PY + '" promo_server.py\n'
    'timeout /t 2 /nobreak >nul\n'
    'echo 正在关闭已运行的 Chrome 以加载扩展...\n'
    'taskkill /F /IM chrome.exe 2>nul\n'
    'timeout /t 2 /nobreak >nul\n'
    'echo 正在使用 Chrome 加载扩展...\n'
    'start "" "' + CHROME + '" --load-extension="%~dp0extension" "http://127.0.0.1:' + str(PORT) + '/"\n'
    'echo.\n'
    'echo 已打开 Chrome 并加载「淘系推广参谋」扩展。\n'
    'echo 在浏览器右上角工具栏点击扩展图标，即可在商品页一键导入。\n'
    'echo （注意：用此方式加载的扩展为开发者模式，关闭 Chrome 后下次需重新运行本文件）\n'
    'pause\n'
)
write("加载扩展.bat", bat_ext)

# 4. 停止服务.bat
bat_stop = (
    '@echo off\n'
    'chcp 936 >nul\n'
    'echo 正在停止淘系推广参谋...\n'
    'taskkill /F /IM python.exe /FI "WINDOWTITLE eq promo_server.py" 2>nul\n'
    'taskkill /F /IM python.exe 2>nul\n'
    'echo 已停止（如果提示找不到进程，说明服务未运行）\n'
    'pause\n'
)
write("停止服务.bat", bat_stop)

print("所有启动器已生成，统一使用 Chrome。")
