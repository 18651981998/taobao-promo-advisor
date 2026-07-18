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


def bookmarklet_code(port):
    """书签代码：点击后向当前商品页注入一个悬浮按钮（与油猴/扩展效果一致），
    再点按钮即可抓取并导入。不依赖任何扩展或油猴，所有浏览器可用。"""
    p = str(port)
    return (
        "javascript:(function(){"
        "if(document.getElementById('tb-promo-import-btn'))return;"
        "var TOOL='http://127.0.0.1:" + p + "';"
        "function tx(s){try{var e=document.querySelector(s);return e?e.innerText.trim():''}catch(e){return''}}"
        "function at(s,a){try{var e=document.querySelector(s);return e?((e.getAttribute(a)||e[a]||'').trim()):''}catch(e){return''}}"
        "function ex(){"
        "var t=tx('h1')||at('meta[property=\"og:title\"]','content')||document.title;"
        "t=(t||'').replace(/\\s*-\\s*(淘宝网|天猫|tmall|Taobao).*$/i,'').trim();"
        "var pr='';"
        "var ps=['.Price--realSales','.Price--actualValue','#J_PromoPrice .tm-price','#J_PromoPriceNum','#J_StrPrice .tb-rmb-num','.tb-rmb-num','[class*=\"Price\"]'];"
        "for(var i=0;i<ps.length;i++){var m=tx(ps[i]).match(/[\\d,]+\\.?\\d*/);if(m){pr=m[0].replace(/,/g,'');break;}}"
        "if(!pr){var b=document.body.innerText.match(/[¥￥]\\s*([\\d,]+\\.?\\d*)/);if(b)pr=b[1].replace(/,/g,'');}"
        "var pic=at('meta[property=\"og:image\"]','content')||at('#J_ImgBooth','src')||at('#J_ImageWrap img','src');"
        "if(!pic){var im=document.querySelectorAll('img');for(var j=0;j<im.length;j++){var s=im[j].src||im[j].getAttribute('data-src')||'';if(s.indexOf('alicdn.com')>-1){pic=s;break;}}}"
        "return{title:t||'',price:pr||'',pic:pic||'',url:location.href};"
        "}"
        "function toast(m,ok){var n=document.getElementById('tb-promo-toast');if(!n){n=document.createElement('div');n.id='tb-promo-toast';n.style.cssText='position:fixed;right:20px;bottom:160px;z-index:2147483647;max-width:260px;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:500;box-shadow:0 6px 18px rgba(0,0,0,.2);font-family:-apple-system,\"Microsoft YaHei\",sans-serif;transition:opacity .3s';document.body.appendChild(n);}n.style.background=ok?'#0f6e56':'#c0451d';n.style.color='#fff';n.textContent=m;n.style.opacity='1';clearTimeout(n._timer);n._timer=setTimeout(function(){n.style.opacity='0';},2600);}"
        "function openTool(d){var q='?title='+encodeURIComponent(d.title||'')+'&price='+encodeURIComponent(d.price||'')+'&pic='+encodeURIComponent(d.pic||'')+'&url='+encodeURIComponent(d.url||'');window.open(TOOL+'/'+q,'_blank');}"
        "function send(d){try{fetch(TOOL+'/api/browser-parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(j){toast('已导入',true);openTool(d)}).catch(function(){openTool(d)})}catch(e){openTool(d)}}"
        "var btn=document.createElement('div');btn.id='tb-promo-import-btn';btn.innerHTML='🛒 导入推广参谋';"
        "btn.style.cssText='position:fixed;left:20px;top:150px;z-index:2147483647;padding:11px 16px;background:linear-gradient(135deg,#ff5000,#ff7300);color:#fff;border-radius:24px;font-size:14px;font-weight:600;cursor:pointer;display:block!important;visibility:visible!important;opacity:1!important;box-shadow:0 6px 18px rgba(255,80,0,.4);font-family:-apple-system,\"Microsoft YaHei\",sans-serif;line-height:1;user-select:none;border:2px solid #fff';"
        "btn.onclick=function(){var d=ex();if(!d.title&&!d.price&&!d.pic){toast('未抓取到商品信息',false);openTool(d);return;}toast('正在抓取',true);send(d);};"
        "document.body.appendChild(btn);"
        "})();"
    )


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
