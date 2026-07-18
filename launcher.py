#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""淘系推广参谋 · 图形化启动菜单（无控制台黑窗口）

功能菜单：
  使用
    ① 启动并打开工具页
    ② 普通安装（悬浮按钮）—— 打开 Chrome 扩展程序页 + extension 文件夹，手动加载一次即可
  管理
    ③ 停止本地服务
    ④ 退出

说明：
  Chrome/Edge 出于安全策略，禁止任何程序自动静默安装扩展。
  因此点击「普通安装」后，工具会帮你打开扩展管理页和 extension 文件夹，
  你只需在扩展管理页点「加载已解压的扩展程序」，然后选中 extension 文件夹即可。
  这是目前最稳定、最不容易被浏览器安全策略拦截的安装方式。
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
        add_btn("②   普通安装（悬浮按钮）", lambda: self.do_action("extension"), primary=True)
        group("管理")
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

        if kind == "extension":
            # 安装普通 Chrome 扩展（手动「加载已解压的扩展程序」）
            # 这是目前最稳定的方式：Chrome 138+ 对自动加载限制很严，手动加载一次即可永久生效。
            self._set_running(True)
            self._log("请选择浏览器，随后将打开扩展程序页和 extension 文件夹...")
            def w():
                browser = ih.choose_browser()
                if not browser:
                    self.after(0, lambda: self._log("已取消，未选择浏览器。"))
                    self.after(0, lambda: self._set_running(False))
                    return
                ih.save_browser(browser["name"])
                ext_dir = os.path.join(HERE, "extension")
                exe = ih.resolve_exe(browser)
                if not exe or not os.path.isfile(exe):
                    self.after(0, lambda: self._log("未检测到「%s」已安装，无法安装扩展。" % browser["name"]))
                    self.after(0, lambda: self._set_running(False))
                    return
                # 尽量预开启开发者模式（Chrome 138+ 必须）
                dm = ih.enable_developer_mode(browser)
                self.after(0, lambda: self._log(
                    "已%s开发者模式。" % ("预开启" if dm else "尝试预开启（若失败请手动开启）")))
                # 打开 extension 文件夹，方便用户选中
                try:
                    os.startfile(ext_dir)
                    self.after(0, lambda: self._log("已打开「extension」文件夹，等下请选它。"))
                except Exception as e:
                    self.after(0, lambda: self._log("打开文件夹失败：%s" % e))
                # 打开扩展程序页
                ext_url = "chrome://extensions"
                if "Edge" in browser.get("name", ""):
                    ext_url = "edge://extensions"
                try:
                    subprocess.Popen([exe, ext_url],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    self.after(0, lambda: self._log("打开扩展程序页失败：%s" % e))
                self.after(0, lambda: self._log(
                    "\n"
                    "【请按下面 3 步手动加载扩展】\n"
                    "1) 在打开的「扩展程序」页面右上角，确认「开发者模式」是【开】的；\n"
                    "2) 点左上角「加载已解压的扩展程序」；\n"
                    "3) 在刚才打开的文件夹中，选中「extension」文件夹，点「选择文件夹」。\n"
                    "列表出现「淘系推广参谋·商品导入」即成功。\n"
                    "之后打开任意淘宝/天猫商品页，右上角都会自动出现「🛒 导入推广参谋」按钮。"))
                self.after(0, lambda: self._set_running(False))
            threading.Thread(target=w, daemon=True).start()
            return

        # open：走 install_helper 选择浏览器并打开工具页
        arg = {"open": "--open"}.get(kind)
        label = {"open": "启动并打开工具页"}[kind]
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
