#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""淘系推广参谋 · 图形化启动菜单（无控制台黑窗口）

功能菜单：
  使用
    ① 启动并打开工具页
    ② 安装悬浮按钮（一键引导）—— 自动弹出 Tampermonkey 商店页 + 本地脚本安装页
  导入
    安装 Tampermonkey 扩展         —— 打开正版 Tampermonkey 商店页
    安装悬浮按钮脚本               —— 打开 GitHub 上的用户脚本安装页（HTTPS，更易弹出安装按钮）
    安装导入书签（备选）           —— 旧方案，浏览器书签导入
  管理
    ③ 停止本地服务
    ④ 退出

说明：
  浏览器（Chrome/Edge）出于安全策略，禁止任何程序自动把扩展静默装进浏览器，
  必须用户在弹出的商店页点一次「添加」。因此「一键引导」= 自动帮你把安装页弹出来，
  你只需点确认。这是目前最接近「启动后自动安装」的做法。

  商品导入主方案 = Tampermonkey 用户脚本（悬浮按钮）：在商品页点一下「🛒 导入推广参谋」，
  即把标题/价格/主图自动传入本地工具。无需 F12、无需复制代码。
"""
import os
import sys
sys.dont_write_bytecode = True  # 禁止生成 .pyc 缓存，避免更新后仍运行旧代码

# 启动前强制清理本目录下的所有 .pyc / __pycache__，防止旧缓存导致选择窗口等逻辑不生效
try:
    import pathlib
    _here = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
    for _pyc in _here.rglob("*.pyc"):
        try:
            _pyc.unlink(missing_ok=True)
        except Exception:
            pass
    for _cache in _here.rglob("__pycache__"):
        try:
            if _cache.is_dir():
                _cache.rmdir()
        except Exception:
            pass
except Exception:
    pass

import time
import webbrowser
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, scrolledtext

import install_helper as ih

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
PYW = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"
SERVER = os.path.join(HERE, "promo_server.py")
INSTALL_HELPER = os.path.join(HERE, "install_helper.py")
PORT = 8123

# Tampermonkey 官方商店地址（正版，推荐）
TM_CHROME = "https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojimpmpbldmpobfkfo"
TM_EDGE = "https://microsoftedge.microsoft.com/addons/detail/tampermonkey/iikmkjmpaadaofnihnnoafoofjgjencj"
# Tampermonkey 扩展 ID（用于直接打开其详情页）
TM_CHROME_ID = "dhdgffkkebhmkfjojimpmpbldmpobfkfo"
TM_EDGE_ID = "iikmkjmpaadaofnihnnoafoofjgjencj"
# GitHub 上用户脚本的 raw HTTPS 地址（Chrome 138 对本地 HTTP userscript 安装页限制很严，
# 改成受信任的 HTTPS 公共域名后 Tampermonkey 更容易弹出安装按钮）
USERSCRIPT_GITHUB_URL = "https://raw.githubusercontent.com/18651981998/taobao-promo-advisor/main/taobao-promo.user.js"
# 本地用户脚本安装页（备用）
USERSCRIPT_LOCAL_URL = f"http://127.0.0.1:{PORT}/taobao-promo.user.js"
USERSCRIPT_URL = USERSCRIPT_GITHUB_URL


def tm_settings_url(browser):
    """根据所选浏览器，返回 Tampermonkey 详情页地址（带 ID 直达，省去手动查找）。"""
    name = browser.get("name", "") if isinstance(browser, dict) else str(browser)
    if "Edge" in name:
        return f"edge://extensions/?id={TM_EDGE_ID}"
    return f"chrome://extensions/?id={TM_CHROME_ID}"


def tm_dashboard_url(browser):
    """返回 Tampermonkey 脚本管理面板地址（已安装脚本在这里查看）。"""
    name = browser.get("name", "") if isinstance(browser, dict) else str(browser)
    if "Edge" in name:
        return f"edge-extension://{TM_EDGE_ID}/options.html"
    return f"chrome-extension://{TM_CHROME_ID}/options.html"


def server_up():
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
        return True
    except Exception:
        return False


def open_url(url, browser=None):
    """用指定浏览器打开 URL；未指定或浏览器不存在时回退到系统默认浏览器。"""
    if browser and ih.is_installed(browser):
        exe = ih.resolve_exe(browser)
        try:
            subprocess.Popen([exe, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            pass
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass


def stop_server():
    ps_cmd = (
        "Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%promo_server.py%'\" "
        "| Select-Object -ExpandProperty ProcessId "
        "| ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-Command", ps_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if server_up():
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return not server_up()


def start_server():
    stop_server()
    pyw = PYW if os.path.isfile(PYW) else PY
    if not os.path.isfile(pyw):
        return False
    # pythonw + CREATE_NO_WINDOW：彻底隐藏黑色控制台窗口
    subprocess.Popen([pyw, SERVER, "--no-open"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=HERE,
                     creationflags=0x08000000)
    for _ in range(30):
        time.sleep(0.3)
        if server_up():
            return True
    return False


def run_install_helper(extra_arg):
    if not os.path.isfile(PYW) and not os.path.isfile(PY):
        messagebox.showerror("错误", "找不到 Python 运行环境。")
        return
    cmd = [PYW if os.path.isfile(PYW) else PY, INSTALL_HELPER]
    if extra_arg:
        cmd.append(extra_arg)
    subprocess.run(cmd, cwd=HERE)


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("淘系推广参谋 · 启动菜单   |   A0_0 涛声依旧  V26.0717")
        self.geometry("540x470")
        self.resizable(False, False)
        try:
            self.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass

        tk.Label(self, text="淘系推广参谋",
                 font=("Microsoft YaHei", 18, "bold"), fg="#ff5000").pack(pady=(18, 2))
        tk.Label(self, text=f"作者：A0_0 涛声依旧    版本：V26.0717    路径：{HERE}",
                 font=("Microsoft YaHei", 9), fg="#999999").pack(pady=(0, 16))

        self.btn_frame = tk.Frame(self)
        self.btn_frame.pack(fill="x", padx=32)
        self.buttons = []
        self.running = False

        def group(title):
            tk.Label(self.btn_frame, text=title, font=("Microsoft YaHei", 10, "bold"),
                     fg="#bbbbbb", anchor="w").pack(fill="x", pady=(10, 4))

        def add_btn(label, cb, primary=False):
            b = tk.Button(self.btn_frame, text=label, font=("Microsoft YaHei", 12),
                          height=1, relief="flat", command=cb, anchor="w", padx=14)
            if primary:
                b.configure(bg="#ff5000", fg="#ffffff", activebackground="#e04600")
            else:
                b.configure(bg="#ffffff", fg="#333333", activebackground="#f2f2f2")
            b.pack(fill="x", pady=4, ipady=4)
            self.buttons.append(b)

        group("使用")
        add_btn("①   启动并打开工具页", lambda: self.do_action("open"), primary=True)
        add_btn("②   安装悬浮按钮（一键引导）", lambda: self.do_action("guide"), primary=True)
        group("导入")
        add_btn("   安装 Tampermonkey 扩展（正版）", lambda: self.do_action("tm"))
        add_btn("   安装悬浮按钮脚本", lambda: self.do_action("script"))
        add_btn("   安装导入书签（备选）", lambda: self.do_action("bookmark"))
        group("管理")
        add_btn("   打开帮助页（脚本查看/使用说明）", lambda: self.do_action("dashboard"))
        add_btn("③   停止本地服务", lambda: self.do_action("stop"))
        add_btn("④   退出", lambda: self.do_action("exit"))

        tk.Label(self, text="运行日志", font=("Microsoft YaHei", 10),
                 fg="#666666").pack(anchor="w", padx=32, pady=(10, 0))
        self.log = scrolledtext.ScrolledText(self, height=7, font=("Consolas", 9),
                                             bg="#fafafa", fg="#333333", state="disabled")
        self.log.pack(fill="both", expand=True, padx=32, pady=(2, 14))

        self._startup()

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_running(self, running):
        self.running = running
        state = "disabled" if running else "normal"
        for b in self.buttons:
            b.configure(state=state)

    def _startup(self):
        self._set_running(True)
        self._log("正在启动本地服务，请稍候...")
        def work():
            ok = start_server()
            self.after(0, lambda: self._log(
                "OK 本地服务已启动：http://127.0.0.1:8123/" if ok else
                "ERROR 本地服务启动失败，请检查 promo_server.py"))
            self.after(0, lambda: self._set_running(False))
        threading.Thread(target=work, daemon=True).start()

    def do_action(self, kind):
        if kind == "exit":
            self.destroy()
            return
        if self.running:
            return
        if kind == "stop":
            self._set_running(True)
            self._log("正在停止本地服务...")
            def w():
                ok = stop_server()
                self.after(0, lambda: self._log("OK 本地服务已停止。" if ok else
                                                 "ERROR 停止失败，请手动结束 python.exe"))
                self.after(0, lambda: self._set_running(False))
            threading.Thread(target=w, daemon=True).start()
            return

        if kind == "dashboard":
            self._set_running(True)
            self._log("请选择浏览器，随后将打开油猴脚本帮助页...")
            def w():
                browser = ih.choose_browser()
                if not browser:
                    self.after(0, lambda: self._log("已取消，未选择浏览器。"))
                    self.after(0, lambda: self._set_running(False))
                    return
                ih.save_browser(browser["name"])
                help_url = os.path.join(HERE, "tampermonkey-help.html")
                # 如果浏览器能打开本地文件路径，就直接用 file:// 本地地址
                file_url = "file://" + help_url.replace("\\", "/")
                self.after(0, lambda: self._log(f"正在用 {browser['name']} 打开帮助页..."))
                open_url(file_url, browser)
                self.after(0, lambda: self._log(
                    "OK 已打开帮助页。\n"
                    "Chrome 禁止外部程序直接打开油猴管理面板（会出现 ERR_BLOCKED_BY_CLIENT），\n"
                    "请按帮助页步骤：点击浏览器工具栏的油猴图标 → 管理面板查看脚本。"))
                self.after(0, lambda: self._set_running(False))
            threading.Thread(target=w, daemon=True).start()
            return

        if kind == "guide":
            # 一键引导：先选择浏览器，再自动弹出 Tampermonkey 商店页 + 本地脚本安装页
            self._set_running(True)
            self._log("请选择浏览器，随后将打开 Tampermonkey 安装页与脚本页...")
            def w():
                browser = ih.choose_browser()
                if not browser:
                    self.after(0, lambda: self._log("已取消，未选择浏览器。"))
                    self.after(0, lambda: self._set_running(False))
                    return
                ih.save_browser(browser["name"])
                if not server_up():
                    start_server()
                time.sleep(0.6)
                self.after(0, lambda: self._log(f"正在用 {browser['name']} 打开安装页..."))
                # 先打开 Tampermonkey 设置页（直达开关），再打开商店页与脚本页
                open_url(tm_settings_url(browser), browser)
                open_url(TM_CHROME, browser)
                open_url(USERSCRIPT_URL, browser)
                self.after(0, lambda: self._log(
                    f"OK 已用 {browser['name']} 打开三个页面：\n"
                    "1) Tampermonkey 详情页（开「允许用户脚本」开关）\n"
                    "2) Tampermonkey 商店页 → 点「添加」安装扩展\n"
                    "3) 悬浮按钮脚本页 → 点「安装」安装脚本。若未弹安装框，回工具页点「复制脚本代码（手动安装）」\n"
                    f"Edge 用户商店链接：{TM_EDGE}"))
                self.after(0, lambda: self._set_running(False))
            threading.Thread(target=w, daemon=True).start()
            return

        if kind == "tm":
            self._set_running(True)
            self._log("请选择浏览器，随后打开 Tampermonkey 商店页...")
            def w():
                browser = ih.choose_browser()
                if not browser:
                    self.after(0, lambda: self._log("已取消，未选择浏览器。"))
                    self.after(0, lambda: self._set_running(False))
                    return
                ih.save_browser(browser["name"])
                self.after(0, lambda: self._log(f"正在用 {browser['name']} 打开 Tampermonkey 商店页..."))
                open_url(TM_CHROME, browser)
                self.after(0, lambda: self._log(
                    f"OK 已用 {browser['name']} 打开 Tampermonkey 商店页，点「添加」安装扩展。\n"
                    "安装完后回到本工具点「安装悬浮按钮脚本」即可。\n"
                    f"Edge 用户请访问：{TM_EDGE}"))
                self.after(0, lambda: self._set_running(False))
            threading.Thread(target=w, daemon=True).start()
            return

        if kind == "script":
            self._set_running(True)
            self._log("请选择浏览器，随后将打开 Tampermonkey 设置页（开用户脚本开关）...")
            def w():
                browser = ih.choose_browser()
                if not browser:
                    self.after(0, lambda: self._log("已取消，未选择浏览器。"))
                    self.after(0, lambda: self._set_running(False))
                    return
                ih.save_browser(browser["name"])
                if not server_up():
                    start_server()
                time.sleep(0.6)
                # 第一步：先打开 Tampermonkey 详情页（带 ID 直达，省去手动查找）
                self.after(0, lambda: self._log(f"正在用 {browser['name']} 打开 Tampermonkey 设置页..."))
                open_url(tm_settings_url(browser), browser)
                # 第二步：直接打开脚本安装页，不再弹窗阻断；提示写到日志栏
                self.after(0, lambda: self._log(
                    "已打开 Tampermonkey 详情页，请确认「允许用户脚本」开关已开启。\n"
                    "现在打开脚本安装页..."))
                open_url(USERSCRIPT_URL, browser)
                self.after(0, lambda: self._log(
                    "OK 已打开悬浮按钮脚本安装页。\n"
                    "Tampermonkey 应该会弹出安装确认框，点「安装」即可。\n"
                    "若未弹框，回工具页点「复制脚本代码（手动安装）」手动粘贴。"))
                self.after(0, lambda: self._set_running(False))
            threading.Thread(target=w, daemon=True).start()
            return

        # open / bookmark：走 install_helper
        arg = {"open": "--open", "bookmark": "--install-bookmark"}.get(kind)
        label = {"open": "启动并打开工具页",
                 "bookmark": "安装导入书签"}[kind]
        self._set_running(True)
        self._log("正在执行：" + label + " ...")
        def w():
            try:
                run_install_helper(arg)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("执行出错", str(e)))
            finally:
                self.after(0, lambda: self._log("OK 完成：" + label))
                self.after(0, lambda: self._set_running(False))
        threading.Thread(target=w, daemon=True).start()


def main():
    try:
        app = Launcher()
        app.mainloop()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        try:
            messagebox.showerror("启动器出错", tb)
        except Exception:
            pass
        try:
            with open(os.path.join(HERE, "launcher_error.log"), "w", encoding="utf-8") as f:
                f.write(tb)
        except Exception:
            pass


if __name__ == "__main__":
    main()
