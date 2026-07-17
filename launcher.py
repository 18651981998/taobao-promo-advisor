#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""淘系推广参谋 · 图形化启动菜单（无控制台黑窗口，杜绝双击闪退）

把原来的编号式控制台菜单改为 tkinter 图形界面：
  1. 启动服务并打开工具页
  2. 一键安装书签 + 扩展
  3. 仅加载扩展
  4. 停止本地服务
  5. 退出

用 pythonw.exe 启动本文件时不分配控制台，因此在资源管理器里双击 .bat
不会再出现“黑窗口闪一下”的问题。
"""
import os
import sys
import time
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, scrolledtext

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
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


def start_server():
    # 先停掉任何旧进程，确保代码更新后一定加载最新版
    stop_server()
    if not os.path.isfile(PY):
        return False
    # 启动器自己会控制浏览器打开，所以让服务不要自动弹出默认浏览器
    subprocess.Popen([PY, SERVER, "--no-open"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=HERE,
                     creationflags=0x08000000)
    for _ in range(30):
        time.sleep(0.3)
        if server_up():
            return True
    return False


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


def run_install_helper(extra_arg):
    if not os.path.isfile(PY):
        messagebox.showerror("错误", "找不到 Python 运行环境。")
        return
    cmd = [PY, INSTALL_HELPER]
    if extra_arg:
        cmd.append(extra_arg)
    subprocess.run(cmd, cwd=HERE)


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("淘系推广参谋 · 启动菜单   |   A0_0 涛声依旧  V26.0717")
        self.geometry("560x470")
        self.resizable(False, False)
        try:
            self.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass

        tk.Label(self, text="淘系推广参谋 · 启动菜单",
                 font=("Microsoft YaHei", 16, "bold"), fg="#ff6a00").pack(pady=(14, 2))
        tk.Label(self, text="作者：A0_0 涛声依旧    版本：V26.0717",
                 font=("Microsoft YaHei", 10), fg="#999999").pack(pady=(0, 10))

        self.btn_frame = tk.Frame(self)
        self.btn_frame.pack(fill="x", padx=24)
        actions = [
            ("1.   启动服务并打开工具页", lambda: self.do_action("open")),
            ("2.   一键安装书签 + 扩展", lambda: self.do_action("install")),
            ("3.   仅加载扩展", lambda: self.do_action("ext")),
            ("4.   停止本地服务", lambda: self.do_action("stop")),
            ("5.   退出", lambda: self.do_action("exit")),
        ]
        self.buttons = []
        for label, cb in actions:
            b = tk.Button(self.btn_frame, text=label, font=("Microsoft YaHei", 12),
                          height=1, relief="raised", command=cb, anchor="w", padx=12)
            b.pack(fill="x", pady=4)
            self.buttons.append(b)

        tk.Label(self, text="运行日志", font=("Microsoft YaHei", 10),
                 fg="#666666").pack(anchor="w", padx=24, pady=(6, 0))
        self.log = scrolledtext.ScrolledText(self, height=9, font=("Consolas", 9),
                                             bg="#fafafa", fg="#333333", state="disabled")
        self.log.pack(fill="both", expand=True, padx=24, pady=(2, 12))

        self.running = False
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
        arg = {"open": "--open-only", "install": None, "ext": "--extension-only"}[kind]
        label = {"open": "启动服务并打开工具页", "install": "安装书签 + 扩展",
                 "ext": "加载扩展"}[kind]
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
