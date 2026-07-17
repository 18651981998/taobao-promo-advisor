#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""淘系推广参谋 · 浏览器选择 / 书签安装助手

说明：
- 由于 Chrome 的单实例机制 + 新版 Chrome 对本地扩展自动加载的限制，
  命令行 --load-extension 自动安装扩展极不稳定，已彻底弃用。
- 本助手现在只负责两件事：
  1) 选择要打开的浏览器；
  2) 把书签写入浏览器书签栏（永久有效）。
- 商品导入统一使用书签（Bookmarklet）：在商品页点一下书签栏「导入推广参谋」，
  自动抓取标题/价格/主图并打开本地工具，无需安装任何扩展。
"""
import os
import sys
import json
import time
import argparse
import subprocess
import tkinter as tk
from tkinter import messagebox

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
PYW = r"C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"
SERVER = os.path.join(HERE, "promo_server.py")
PORT = 8123
BOOKMARK_NAME = "导入推广参谋"

BROWSERS = [
    {
        "name": "Google Chrome",
        "exes": [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\Google\\Chrome\\User Data",
        "note": "推荐",
    },
    {
        "name": "Microsoft Edge",
        "exes": [
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data",
        "note": "推荐",
    },
    {
        "name": "360安全浏览器",
        "exes": [
            "C:/Program Files (x86)/360/360se6/360se.exe",
            "C:/Program Files/360/360se6/360se.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\360\\360se6\\User Data",
        "note": "兼容性一般",
    },
    {
        "name": "360极速浏览器",
        "exes": [
            "C:/Program Files (x86)/360Chrome/Chrome/Application/360chrome.exe",
            "C:/Program Files/360Chrome/Chrome/Application/360chrome.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\360Chrome\\Chrome\\User Data",
        "note": "兼容性一般",
    },
]

LAST_BROWSER_FILE = os.path.join(HERE, "last_browser.txt")


def server_up():
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2)
        return True
    except Exception:
        return False


def start_server():
    if server_up():
        return True
    pyw = PYW if os.path.isfile(PYW) else PY
    if not os.path.isfile(pyw):
        return False
    subprocess.Popen([pyw, SERVER, "--no-open"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=HERE,
                     creationflags=0x08000000)
    for _ in range(30):
        time.sleep(0.3)
        if server_up():
            return True
    return False


def is_installed(browser):
    for p in browser.get("exes", []):
        if p and os.path.isfile(p):
            return True
    return False


def resolve_exe(browser):
    for p in browser.get("exes", []):
        if p and os.path.isfile(p):
            return p
    return browser.get("exes", [None])[0]


def resolve_user_data(browser):
    ud = os.path.expandvars(browser.get("user_data", ""))
    if os.path.isdir(ud):
        return ud
    # 360安全浏览器实际数据目录在 %APPDATA%\360se6\Application\<版本>
    if browser.get("name") == "360安全浏览器":
        base = os.path.expandvars("%APPDATA%\\360se6\\Application")
        if os.path.isdir(base):
            # 找版本号最大的目录
            try:
                dirs = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and d[0].isdigit()]
                if dirs:
                    dirs.sort(key=lambda x: [int(n) for n in x.split(".")], reverse=True)
                    return os.path.join(base, dirs[0])
            except Exception:
                pass
    return None


def choose_browser():
    root = tk.Tk()
    root.title("淘系推广参谋 · 选择浏览器")
    root.geometry("440x320")
    root.resizable(False, False)

    tk.Label(root,
             text="请选择要使用的浏览器：",
             font=("Microsoft YaHei", 11)).pack(pady=14)

    selected = tk.StringVar()
    installed = [b for b in BROWSERS if is_installed(b)]
    selected.set(installed[0]["name"] if installed else BROWSERS[0]["name"])

    for b in BROWSERS:
        status = "已安装" if is_installed(b) else "未安装"
        text = f"{b['name']}  ({status})"
        tk.Radiobutton(root, text=text, variable=selected, value=b["name"],
                       font=("Microsoft YaHei", 10)).pack(anchor="w", padx=40, pady=2)
        if b.get("note"):
            tk.Label(root, text=f"   {b['note']}", fg="gray",
                     font=("Microsoft YaHei", 9)).pack(anchor="w", padx=60)

    result = [None]

    def on_ok():
        name = selected.get()
        browser = next((b for b in BROWSERS if b["name"] == name), None)
        if not browser:
            return
        if not is_installed(browser):
            messagebox.showwarning("浏览器未安装",
                                   f"「{name}」未安装。\n请先安装该浏览器，或选择其他已安装的浏览器。")
            return
        result[0] = browser
        root.destroy()

    def on_cancel():
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=18)
    tk.Button(btn_frame, text="确定", width=10, command=on_ok).pack(side="left", padx=10)
    tk.Button(btn_frame, text="取消", width=10, command=on_cancel).pack(side="left", padx=10)

    root.mainloop()
    return result[0]


def load_browser():
    try:
        with open(LAST_BROWSER_FILE, encoding="utf-8") as f:
            n = f.read().strip()
        return next((x for x in BROWSERS if x["name"] == n and is_installed(x)), None)
    except Exception:
        return None


def save_browser(name):
    try:
        with open(LAST_BROWSER_FILE, "w", encoding="utf-8") as f:
            f.write(name)
    except Exception:
        pass


def pick_browser():
    saved = load_browser()
    if saved:
        return saved
    return choose_browser()


def bookmarklet_code(port):
    return ("javascript:(function(){"
            "function t(){var r='';try{r=document.querySelector('h1').innerText.trim();}catch(e){}"
            "if(!r)try{r=document.querySelector('meta[property=\"og:title\"]').content.trim();}catch(e){}"
            "if(!r)try{r=g_config.title;}catch(e){}return r;}"
            "function p(){var r='';try{r=g_config.defaultItemPrice;}catch(e){}"
            "if(!r)try{r=document.querySelector('[class*=\"Price\"]').innerText.match(/[\\d.]+/)[0];}catch(e){}"
            "if(!r){var m=document.body.innerText.match(/[¥￥]\\s*([\\d.]+)/);if(m)r=m[1];}return r;}"
            "function c(){var r='';try{r=document.querySelector('meta[property=\"og:image\"]').content.trim();}catch(e){}"
            "if(!r)try{r=g_config.pic;}catch(e){}"
            "if(!r){var imgs=document.querySelectorAll('img');for(var i=0;i<imgs.length;i++){if(imgs[i].src.indexOf('alicdn.com')>-1){r=imgs[i].src;break;}}return r;}"
            "var title=t(),price=p(),pic=c(),url=location.href;"
            "var u='http://127.0.0.1:" + str(port) + "/?title='+encodeURIComponent(title)"
            "+'&price='+encodeURIComponent(price)+'&pic='+encodeURIComponent(pic)"
            "+'&url='+encodeURIComponent(url);window.open(u,'_blank');})();")


def inject_bookmark(browser, code):
    ud = resolve_user_data(browser)
    if not ud:
        return []
    profiles = set()
    bm = os.path.join(ud, "Bookmarks")
    if os.path.isfile(bm):
        profiles.add(bm)
    try:
        for d in os.listdir(ud):
            p = os.path.join(ud, d, "Bookmarks")
            if os.path.isfile(p):
                profiles.add(p)
    except Exception:
        pass
    done = []
    for prof in profiles:
        try:
            with open(prof, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        bar = data.get("roots", {}).get("bookmark_bar")
        if not bar:
            continue
        children = bar.setdefault("children", [])
        if any(c.get("url") == code for c in children if c.get("type") == "url"):
            done.append(prof)
            continue
        now = str(int(time.time() * 1000000) + 11644473600000000)
        children.append({"type": "url", "name": BOOKMARK_NAME,
                         "url": code, "date_added": now})
        with open(prof, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        done.append(prof)
    return done


def is_running(exe):
    name = os.path.basename(exe).lower()
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV"],
                             capture_output=True, text=True)
        lines = [l.strip() for l in out.stdout.strip().splitlines() if l.strip()]
        for line in lines[1:]:
            parts = [p.strip('"') for p in line.split(",")]
            if parts and parts[0].lower() == name:
                return True
    except Exception:
        pass
    return False


def kill_browser(exe):
    name = os.path.basename(exe)
    subprocess.run(["taskkill", "/F", "/IM", name, "/T"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_browser_dead(exe, timeout=10):
    for _ in range(timeout):
        if not is_running(exe):
            return True
        time.sleep(1)
    return not is_running(exe)


def install_bookmark(browser):
    """关闭浏览器后写入书签，再重新打开"""
    exe = resolve_exe(browser)
    if not exe or not os.path.isfile(exe):
        messagebox.showwarning("浏览器未安装",
            f"「{browser['name']}」未安装。\n请先安装该浏览器，或选择其他已安装的浏览器。")
        return
    if is_running(exe):
        ok = messagebox.askyesno("需要关闭浏览器",
            f"把书签写入「{browser['name']}」需要先完全关闭它。\n现在关闭并继续吗？")
        if not ok:
            messagebox.showinfo("已取消", "未做任何改动。")
            return
        kill_browser(exe)
        wait_browser_dead(exe)
    inject_bookmark(browser, bookmarklet_code(PORT))
    try:
        subprocess.Popen([exe, f"http://127.0.0.1:{PORT}/"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    messagebox.showinfo("书签已安装",
        f"已将「{BOOKMARK_NAME}」写入 {browser['name']} 书签栏。\n"
        "打开淘宝/天猫商品页，点书签栏「导入推广参谋」即可把商品导入工具。")


def open_tool_page(browser):
    """直接用选中的浏览器打开工具页，不杀进程"""
    exe = resolve_exe(browser)
    if not exe or not os.path.isfile(exe):
        messagebox.showwarning("浏览器未安装",
            f"「{browser['name']}」未安装。\n请先安装该浏览器，或选择其他已安装的浏览器。")
        return
    try:
        subprocess.Popen([exe, f"http://127.0.0.1:{PORT}/"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        messagebox.showerror("启动浏览器失败", str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true",
                        help="选择浏览器并打开工具页")
    parser.add_argument("--install-bookmark", action="store_true",
                        help="安装书签到浏览器书签栏")
    args = parser.parse_args()

    if not start_server():
        messagebox.showerror("启动失败",
            "本地服务未能启动，请确认 Python 环境存在：\n" + PY)
        return

    browser = pick_browser()
    if not browser:
        return
    save_browser(browser["name"])

    if args.install_bookmark:
        install_bookmark(browser)
    else:
        open_tool_page(browser)


if __name__ == "__main__":
    main()
