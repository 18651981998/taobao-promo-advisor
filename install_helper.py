#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""淘系推广参谋 · 一键安装助手

流程：
1) 启动本地服务（若未运行）
2) 弹出窗口让用户选择浏览器（Chrome / Edge / 360）
3) 若所选浏览器未安装 → 弹窗提示并停止
4) 关闭所选浏览器（必须完全关闭才能写书签 + 加载扩展）
5) 把「导入推广参谋」书签写入该浏览器书签栏（永久）
6) 用 --load-extension 加载浏览器扩展（工具栏图标）
7) 在该浏览器中打开工具页

说明：Chrome / Edge 的 --load-extension 只对“全新浏览器进程”生效，
因此若浏览器正在运行，会先关闭再带参数重启。书签写入也必须在
浏览器关闭时进行，否则会被内存中的状态覆盖。
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
SERVER = os.path.join(HERE, "promo_server.py")
PORT = 8123
EXT_DIR = os.path.join(HERE, "extension")

BOOKMARK_NAME = "导入推广参谋"

# 候选浏览器配置（按推荐顺序）
BROWSERS = [
    {
        "name": "Google Chrome",
        "exes": [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\Google\\Chrome\\User Data",
        "note": "推荐，扩展加载最稳定",
    },
    {
        "name": "Microsoft Edge",
        "exes": [
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\Microsoft\\Edge\\User Data",
        "note": "推荐，扩展加载最稳定",
    },
    {
        "name": "360安全浏览器",
        "exes": [
            "C:/Program Files (x86)/360/360se6/360se.exe",
            "C:/Program Files/360/360se6/360se.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\360\\360se6\\User Data",
        "note": "360 对 MV3 扩展支持有限，可能无法自动加载",
    },
    {
        "name": "360极速浏览器",
        "exes": [
            "C:/Program Files (x86)/360Chrome/Chrome/Application/360chrome.exe",
            "C:/Program Files/360Chrome/Chrome/Application/360chrome.exe",
        ],
        "user_data": "%LOCALAPPDATA%\\360Chrome\\Chrome\\User Data",
        "note": "360 对 MV3 扩展支持有限，可能无法自动加载",
    },
]


def port_free(p):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", p))
        return True
    except OSError:
        return False
    finally:
        s.close()


def server_up():
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2)
        return True
    except Exception:
        return False


def start_server():
    """若服务未起则后台启动，等待就绪"""
    if server_up():
        return True
    if not os.path.isfile(PY):
        return False
    subprocess.Popen([PY, SERVER], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, cwd=HERE,
                     creationflags=0x08000000)
    for _ in range(30):
        time.sleep(0.3)
        if server_up():
            return True
    return False


def bookmarklet_code(port):
    """生成书签 javascript 代码（跳转端口随服务实际端口）"""
    return ("javascript:(function(){"
            "function t(){var r='';try{r=document.querySelector('h1').innerText.trim();}catch(e){}"
            "if(!r)try{r=document.querySelector('meta[property=\"og:title\"]').content.trim();}catch(e){}"
            "if(!r)try{r=g_config.title;}catch(e){}return r;}"
            "function p(){var r='';try{r=g_config.defaultItemPrice;}catch(e){}"
            "if(!r)try{r=document.querySelector('[class*=\"Price\"]').innerText.match(/[\\d.]+/)[0];}catch(e){}"
            "if(!r){var m=document.body.innerText.match(/[¥￥]\\s*([\\d.]+)/);if(m)r=m[1];}return r;}"
            "function c(){var r='';try{r=document.querySelector('meta[property=\"og:image\"]').content.trim();}catch(e){}"
            "if(!r)try{r=g_config.pic;}catch(e){}"
            "if(!r){var imgs=document.querySelectorAll('img');for(var i=0;i<imgs.length;i++){if(imgs[i].src.indexOf('alicdn.com')>-1){r=imgs[i].src;break;}}}return r;}"
            "var title=t(),price=p(),pic=c(),url=location.href;"
            "var u='http://127.0.0.1:" + str(port) + "/?title='+encodeURIComponent(title)"
            "+'&price='+encodeURIComponent(price)+'&pic='+encodeURIComponent(pic)"
            "+'&url='+encodeURIComponent(url);"
            "window.open(u,'_blank');})();")


def is_installed(browser):
    """检查浏览器是否已安装（任一路径存在即可）"""
    for p in browser.get("exes", []):
        if p and os.path.isfile(p):
            return True
    return False


def resolve_exe(browser):
    """返回实际存在的可执行文件路径"""
    for p in browser.get("exes", []):
        if p and os.path.isfile(p):
            return p
    return browser.get("exes", [None])[0]


def resolve_user_data(browser):
    """返回展开后的用户数据目录，若不存在则返回 None"""
    ud = os.path.expandvars(browser.get("user_data", ""))
    return ud if os.path.isdir(ud) else None


def choose_browser():
    """弹出浏览器选择窗口，返回选中的浏览器配置；取消/关闭返回 None"""
    root = tk.Tk()
    root.title("淘系推广参谋 · 选择浏览器")
    root.geometry("440x360")
    root.resizable(False, False)

    tk.Label(root,
             text="请选择要安装书签和扩展的浏览器：",
             font=("Microsoft YaHei", 11)).pack(pady=14)

    selected = tk.StringVar()
    installed = [b for b in BROWSERS if is_installed(b)]
    if installed:
        selected.set(installed[0]["name"])
    else:
        selected.set(BROWSERS[0]["name"])

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


def is_running(exe):
    """检查浏览器主进程是否仍在运行（同时过滤 tasklist 表头里的镜像名）"""
    name = os.path.basename(exe).lower()
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV"],
                             capture_output=True, text=True)
        # CSV 第一行是表头，后面每行是一个进程；统计真正以该镜像名开头的行数
        lines = [l.strip() for l in out.stdout.strip().splitlines() if l.strip()]
        count = 0
        for line in lines[1:]:
            parts = [p.strip('"') for p in line.split(",")]
            if parts and parts[0].lower() == name:
                count += 1
        return count > 0
    except Exception:
        return False


def kill_browser(exe):
    """强制结束浏览器所有进程，包括子进程和后台应用进程"""
    name = os.path.basename(exe)
    base = os.path.splitext(name)[0]
    # taskkill 多种方式清干净
    cmds = [
        ["taskkill", "/F", "/IM", name],
        ["taskkill", "/F", "/IM", name, "/T"],
        ["taskkill", "/F", "/IM", name, "/FI",
         "USERNAME eq " + os.environ.get("USERNAME", "")],
    ]
    for c in cmds:
        subprocess.run(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # PowerShell 兜底强制停止
    try:
        ps = (
            f"Get-Process -Name '{base}' -ErrorAction SilentlyContinue "
            f"| Stop-Process -Force -ErrorAction SilentlyContinue"
        )
        subprocess.run(["powershell", "-Command", ps],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def wait_browser_dead(exe, timeout=15):
    """循环等待浏览器进程彻底退出，返回是否成功"""
    for _ in range(timeout):
        if not is_running(exe):
            return True
        time.sleep(1)
    return not is_running(exe)


def inject_bookmark(browser, code):
    """把书签写入该浏览器所有 Profile 的书签栏（关闭态调用才安全）"""
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
        # 去重：已存在同 URL 则跳过
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


MANUAL_STEPS = (
    "请手动执行以下操作后重试：\n"
    "1) 关闭所有浏览器窗口；\n"
    "2) 右键系统托盘（右下角）的浏览器图标，选择「退出」；\n"
    "3) 浏览器设置 → 系统 → 关闭「关闭浏览器后继续运行后台应用」；\n"
    "4) 重新运行本工具。"
)

LAST_BROWSER_FILE = os.path.join(HERE, "last_browser.txt")


def save_browser(name):
    try:
        with open(LAST_BROWSER_FILE, "w", encoding="utf-8") as f:
            f.write(name)
    except Exception:
        pass


def load_browser():
    try:
        with open(LAST_BROWSER_FILE, encoding="utf-8") as f:
            n = f.read().strip()
        return next((x for x in BROWSERS if x["name"] == n and is_installed(x)), None)
    except Exception:
        return None


def pick_browser():
    """优先使用上次选择且仍安装的浏览器（免弹窗）；否则弹窗选择"""
    saved = load_browser()
    if saved:
        return saved
    return choose_browser()


def open_tool_page(browser):
    """启动服务后：关掉浏览器 → 装书签 → 带扩展重启并打开工具页。

    Chrome / Edge 的 --load-extension 只对“全新进程”生效，因此必须先把
    浏览器完全关掉再带参数启动。若用户拒绝关闭，则退而求其次只打开页面。
    """
    exe = resolve_exe(browser)
    if not exe or not os.path.isfile(exe):
        messagebox.showwarning("浏览器未安装",
            f"「{browser['name']}」未安装。\n请先安装该浏览器，或选择其他已安装的浏览器。")
        return

    if is_running(exe):
        ok = messagebox.askyesno("需要关闭浏览器",
            f"要加载扩展，需先完全关闭「{browser['name']}」\n"
            "（包括所有窗口和系统托盘里的后台应用）。\n\n现在关闭并继续吗？")
        if ok:
            kill_browser(exe)
            if not wait_browser_dead(exe, timeout=20):
                messagebox.showerror("浏览器未能完全关闭",
                    f"「{browser['name']}」仍有残留进程，扩展无法加载。\n\n" + MANUAL_STEPS)
                # 退而求其次：直接打开页面（无扩展）
                subprocess.Popen([exe, f"http://127.0.0.1:{PORT}/"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        else:
            # 用户不想关：直接打开页面，并提示扩展需经本工具加载
            subprocess.Popen([exe, f"http://127.0.0.1:{PORT}/"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            messagebox.showinfo("已打开（未加载扩展）",
                "本次未关闭浏览器，扩展未加载。\n"
                "如需使用扩展/书签，请通过本工具「启动并打开工具页」，并确保浏览器已完全关闭。")
            return

    # 到此处浏览器已关闭（或本来就没开）：写书签安全
    inject_bookmark(browser, bookmarklet_code(PORT))

    # 用原生路径（反斜杠）加载扩展并打开工具页
    ext = EXT_DIR
    try:
        subprocess.Popen([exe, f"--load-extension={ext}",
                         f"http://127.0.0.1:{PORT}/"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        messagebox.showerror("启动浏览器失败",
            f"无法启动 {browser['name']}：\n{str(e)}\n\n请检查浏览器是否损坏。")
        return

    messagebox.showinfo("已打开工具页",
        f"已用 {browser['name']} 打开工具页并加载扩展（本次会话有效）。\n\n"
        "导入商品：打开淘宝/天猫商品页 → 点书签栏「导入推广参谋」或工具栏扩展图标。\n\n"
        "提示：扩展为开发者模式，下次需通过本工具「启动并打开工具页」重新加载；"
        "书签为永久方式，两种都可导入。")


def install_bookmark_only(browser):
    """仅把书签写入浏览器书签栏（需关闭浏览器才能写入）"""
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
        wait_browser_dead(exe, timeout=15)
    inject_bookmark(browser, bookmarklet_code(PORT))
    try:
        subprocess.Popen([exe, f"http://127.0.0.1:{PORT}/"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    messagebox.showinfo("书签已安装",
        f"已将「{BOOKMARK_NAME}」写入 {browser['name']} 书签栏（永久有效）。\n"
        "打开淘宝/天猫商品页，点书签栏「导入推广参谋」即可把商品导入工具。")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true",
                        help="启动服务 + 装书签 + 带扩展打开工具页")
    parser.add_argument("--install-bookmark", action="store_true",
                        help="仅安装书签到浏览器")
    args = parser.parse_args()

    # 1. 启动服务
    if not start_server():
        messagebox.showerror("启动失败",
            "本地服务未能启动，请确认 Python 环境存在：\n" + PY)
        return

    mode = "bookmark" if args.install_bookmark else "open"
    browser = pick_browser()
    if not browser:
        return
    save_browser(browser["name"])

    if mode == "bookmark":
        install_bookmark_only(browser)
    else:
        open_tool_page(browser)


if __name__ == "__main__":
    main()
