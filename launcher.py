#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""淘系推广参谋 · 图形化启动菜单（无控制台黑窗口）

现在只负责：
  1. 启动本地服务并用浏览器打开工具页
  2. 安装「导入推广参谋」书签到浏览器书签栏
  3. 停止本地服务
  4. 退出

商品导入统一使用浏览器书签（Bookmarklet）：
  在商品页点一下书签栏「导入推广参谋」，即可把标题/价格/主图导入本地工具。
  不再依赖 Chrome 扩展或 Tampermonkey，安装更稳。
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
        self.geometry("520x420")
        self.resizable(False, False)
        try:
            self.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass

        tk.Label(self, text="淘系推广参谋",
                 font=("Microsoft YaHei", 18, "bold"), fg="#ff5000").pack(pady=(18, 2))
        tk.Label(self, text="作者：A0_0 涛声依旧    版本：V26.0717",
                 font=("Microsoft YaHei", 10), fg="#999999").pack(pady=(0, 16))

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
        group("导入")
        add_btn("②   安装导入书签", lambda: self.do_action("bookmark"))
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
