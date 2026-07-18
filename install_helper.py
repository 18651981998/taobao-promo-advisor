#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""淘系推广参谋 · 浏览器选择 / 安装助手

说明：
- 普通扩展（Manifest V3，不走 Tampermonkey）是目前最可靠的「装一次、所有商品页自动出按钮」方案。
- Chrome 138+ 默认会停用「未打包扩展」，必须先在浏览器配置里打开「开发者模式」。
- 本助手只负责：
  1) 选择要打开的浏览器；
  2) 在浏览器配置文件里预开启「开发者模式」；
  3) 用选中的浏览器打开本地工具页。
"""
import os
import sys
sys.dont_write_bytecode = True  # 禁止生成 .pyc，避免缓存导致旧代码被加载
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
            # 新版 360 安全浏览器常见路径
            "C:/Program Files (x86)/360/360se13/360se.exe",
            "C:/Program Files/360/360se13/360se.exe",
            "C:/Program Files (x86)/360/360se14/360se.exe",
            "C:/Program Files/360/360se14/360se.exe",
            # 旧版 360se6
            "C:/Program Files (x86)/360/360se6/360se.exe",
            "C:/Program Files/360/360se6/360se.exe",
            # 用户实际安装路径：AppData\Roaming\360se6\Application
            os.path.expandvars("%APPDATA%/360se6/Application/360se.exe"),
            # 企业/其他命名
            "C:/Program Files (x86)/360/360SafeBrowser/360se.exe",
            "C:/Program Files/360/360SafeBrowser/360se.exe",
            "C:/Program Files (x86)/360/360se/360se.exe",
            "C:/Program Files/360/360se/360se.exe",
            # 64 位版本
            "C:/Program Files/360/360se13/360se.exe",
        ],
        "user_data": "%APPDATA%\\360se6\\Application",
        "note": "兼容性一般",
    },
    {
        "name": "360极速浏览器",
        "exes": [
            "C:/Program Files (x86)/360ChromeX/Chrome/Application/360chrome.exe",
            "C:/Program Files/360ChromeX/Chrome/Application/360chrome.exe",
            "C:/Program Files (x86)/360Chrome/Chrome/Application/360chrome.exe",
            "C:/Program Files/360Chrome/Chrome/Application/360chrome.exe",
            "C:/Program Files (x86)/360ChromeX/Chrome/Application/chrome.exe",
            "C:/Program Files/360ChromeX/Chrome/Application/chrome.exe",
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
    # 先检查硬编码路径
    for p in browser.get("exes", []):
        if p and os.path.isfile(p):
            return True
    # 对 360 浏览器做动态扫描（新版安装路径多变）
    name = browser.get("name", "")
    if "360" in name:
        return bool(scan_for_360(name))
    return False


def resolve_exe(browser):
    # 先检查硬编码路径
    for p in browser.get("exes", []):
        if p and os.path.isfile(p):
            return p
    # 对 360 浏览器做动态扫描
    name = browser.get("name", "")
    if "360" in name:
        found = scan_for_360(name)
        if found:
            return found
    return browser.get("exes", [None])[0]


def scan_for_360(name):
    """动态扫描 360 浏览器可执行文件。新版 360 安装路径经常变化，硬编码路径容易失效。"""
    import glob
    candidates = []
    if "安全" in name:
        # 360 安全浏览器：主程序可能是 360se.exe 或 360SafeBrowser.exe
        keywords = [("360se", "360se.exe"), ("360SafeBrowser", "360SafeBrowser.exe")]
    elif "极速" in name:
        # 360 极速浏览器：主程序可能是 360chrome.exe 或 chrome.exe 在 360Chrome 目录下
        keywords = [("360Chrome", "360chrome.exe"), ("360ChromeX", "360chrome.exe"), ("360Chrome", "chrome.exe")]
    else:
        return None

    search_roots = [
        "C:/Program Files",
        "C:/Program Files (x86)",
        os.path.expandvars("%LOCALAPPDATA%"),
        os.path.expandvars("%APPDATA%"),
    ]

    for root in search_roots:
        if not os.path.isdir(root):
            continue
        for folder_keyword, exe_name in keywords:
            # 扫描 folder_keyword 开头的目录
            pattern = os.path.join(root, folder_keyword + "*", "**", exe_name).replace("\\", "/")
            try:
                for path in glob.glob(pattern, recursive=True):
                    if os.path.isfile(path):
                        # 排除 installer 目录下的更新程序/安装程序
                        parts = path.replace("\\", "/").lower().split("/")
                        if "installer" in parts:
                            continue
                        candidates.append(path)
            except Exception:
                pass
            # 也扫描直接子目录
            pattern2 = os.path.join(root, "360", folder_keyword + "*", "**", exe_name).replace("\\", "/")
            try:
                for path in glob.glob(pattern2, recursive=True):
                    if os.path.isfile(path):
                        parts = path.replace("\\", "/").lower().split("/")
                        if "installer" in parts:
                            continue
                        candidates.append(path)
            except Exception:
                pass

    if not candidates:
        return None
    # 优先选择路径最短的（更接近根目录），避免选到更新程序之类
    candidates.sort(key=lambda x: len(x))
    return candidates[0]


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
    root.geometry("440x420")
    root.resizable(False, False)

    tk.Label(root,
             text="请选择要使用的浏览器：",
             font=("Microsoft YaHei", 11)).pack(pady=14)

    # 用 Listbox 替代 Radiobutton，避免旧缓存/变量绑定导致的多选问题
    listbox = tk.Listbox(root, font=("Microsoft YaHei", 11), height=6,
                         selectmode="single", activestyle="none")
    for b in BROWSERS:
        listbox.insert("end", b["name"])
    listbox.pack(fill="x", padx=40, pady=5)

    result = [None]

    def on_ok():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning("未选择浏览器",
                                   "请先点选要使用的浏览器，再点「确定」。")
            return
        browser = next((b for b in BROWSERS if b["name"] == listbox.get(sel[0])), None)
        if not browser:
            return
        if not is_installed(browser):
            messagebox.showwarning("浏览器未安装",
                                   f"「{listbox.get(sel[0])}」未安装。\n请先安装该浏览器，或选择其他已安装的浏览器。")
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


def enable_developer_mode(browser):
    """在浏览器所有配置文件的 Preferences 里预开启「开发者模式」。

    Chrome 138+ 默认会停用未打包扩展（--load-extension 加载的扩展），
    只有开发者模式打开时，这些扩展才会保持启用。我们必须在浏览器完全关闭时
    修改 Preferences 才安全。返回是否成功修改了至少一个 profile。
    """
    ud = resolve_user_data(browser)
    if not ud:
        return False
    # 收集所有含 Preferences 的 profile 目录
    profiles = []
    if os.path.isfile(os.path.join(ud, "Default", "Preferences")):
        profiles.append(os.path.join(ud, "Default"))
    try:
        for d in os.listdir(ud):
            pdir = os.path.join(ud, d)
            pref = os.path.join(pdir, "Preferences")
            if os.path.isdir(pdir) and os.path.isfile(pref) and pdir not in profiles:
                profiles.append(pdir)
    except Exception:
        pass
    if not profiles:
        return False
    ok = False
    for pdir in profiles:
        pref = os.path.join(pdir, "Preferences")
        try:
            with open(pref, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        ext = data.setdefault("extensions", {}).setdefault("ui", {})
        if ext.get("developer_mode") is True:
            ok = True
            continue
        ext["developer_mode"] = True
        try:
            with open(pref, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            ok = True
        except Exception:
            continue
    return ok


def _open_ext_folder(ext_dir):
    """打开 extension 文件夹。优先用 os.startfile（最快），失败再用 explorer.exe。"""
    if not os.path.isdir(ext_dir):
        return
    try:
        os.startfile(ext_dir)
    except Exception:
        try:
            subprocess.Popen(["explorer.exe", ext_dir],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def _extensions_url(browser):
    """返回该浏览器可能支持的扩展程序页 URL 列表（按优先顺序）。"""
    name = browser.get("name", "")
    if "360安全" in name:
        return ["se://extensions", "chrome://extensions"]
    if "360极速" in name:
        return ["chrome://extensions", "se://extensions"]
    if "Edge" in name:
        return ["edge://extensions"]
    return ["chrome://extensions"]


def _open_extensions_page(browser):
    """在浏览器中打开扩展程序页（不关闭浏览器）。按优先顺序尝试多个 URL。"""
    exe = resolve_exe(browser)
    if not exe or not os.path.isfile(exe):
        return False
    urls = _extensions_url(browser)
    for url in urls:
        try:
            subprocess.Popen([exe, url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return url
        except Exception:
            continue
    return False


def auto_install_extension(browser, ext_dir, log_fn=None, debug_port=9333):
    """打开扩展程序页和 extension 文件夹，让用户手动加载已解压扩展。

    说明：Chrome 138+ 不再允许外部程序直接静默安装未打包扩展，因此最稳的做法是
    自动帮你打开扩展管理页 + extension 文件夹，你只需点两下「加载已解压的扩展程序」。
    本函数不关闭、不重启浏览器，速度最快。
    """
    def log(msg):
        if log_fn:
            log_fn(msg)

    log("正在预开启开发者模式…")
    enable_developer_mode(browser)

    log("正在打开扩展程序页…")
    opened_url = _open_extensions_page(browser)
    if opened_url:
        log("已打开扩展程序页：%s" % opened_url)
    else:
        log("未能自动打开扩展程序页，请手动打开 chrome://extensions 或 se://extensions")

    log("正在打开 extension 文件夹…")
    _open_ext_folder(ext_dir)

    log("\n" +
        "【请按下面 3 步手动加载扩展】\n" +
        "1) 在打开的「扩展程序」页面右上角，确认「开发者模式」是【开】的；\n" +
        "2) 点左上角「加载已解压的扩展程序」；\n" +
        "3) 在打开的文件夹中，选中「extension」文件夹，点「选择文件夹」。\n" +
        "列表出现「淘系推广参谋·商品导入」即成功。")
    return True


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
    args = parser.parse_args()

    if not start_server():
        messagebox.showerror("启动失败",
            "本地服务未能启动，请确认 Python 环境存在：\n" + PY)
        return

    browser = pick_browser()
    if not browser:
        return
    save_browser(browser["name"])

    open_tool_page(browser)


if __name__ == "__main__":
    main()
