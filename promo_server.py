#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘系推广参谋 · 本地后端
- 提供网页服务（自动打开浏览器）
- 提供 /api/parse 接口：粘贴淘宝/天猫链接，自动解析 标题/价格/主图
  解析优先级：① 若配置了淘宝客APPKEY → 走官方API（最稳）
             ② 否则服务端抓取商品页解析（依赖淘宝是否返回真实HTML）
"""
import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import re
import subprocess
import webbrowser
import threading
import hashlib
import time
import argparse

PORT = 8123
HERE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(HERE, "taobao-promo-advisor.html")

# 浏览器扩展抓取后 POST 回来的数据临时存放（按 IP 隔离，避免多用户串数据）
_last_parse = {"title": "", "price": "", "pic": "", "sales": "", "reviews": "", "url": "", "ts": 0, "ip": ""}


def find_free_port(start=PORT, end=PORT+20):
    """如果默认端口被占用，尝试附近端口"""
    for p in range(start, end+1):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            continue
    return start


def open_browser(port, delay=1.5):
    """启动后自动打开浏览器，优先 Chrome / Edge，避免默认浏览器是 360 时跳到 360"""
    def _open():
        time.sleep(delay)
        url = f"http://127.0.0.1:{port}/"
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        for exe in candidates:
            if os.path.isfile(exe):
                try:
                    subprocess.Popen([exe, url],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    pass
        try:
            webbrowser.open(url, new=2)
        except Exception:
            pass
    t = threading.Thread(target=_open, daemon=True)
    t.start()


# ===== 可选：淘宝客（阿里妈妈）开放平台凭证，填了就用官方API，最稳 =====
# 用法：设置环境变量 APPKEY / APPSECRET / ADZONE_ID 后启动，或在下方直接填写
APPKEY = os.environ.get("APPKEY", "")
APPSECRET = os.environ.get("APPSECRET", "")
ADZONE_ID = os.environ.get("ADZONE_ID", "")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def extract_item_id(url):
    """从各种淘宝/天猫链接里抠出商品数字ID"""
    if not url:
        return None
    # 短链 m.tb.cn 会让 urllib 自动跟随重定向，这里直接匹配数字ID
    patterns = [
        r'(?:id|num_iid|item_id|auctionId)=(\d{10,})',
        r'/(\d{10,})(?:[.?#]|$)',
        r'(\d{10,})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def parse_html(html, item_id):
    """多策略解析淘宝/天猫商品页：标题、价格、主图"""
    out = {}

    # 标题候选池（按优先级）
    title_candidates = []

    def add_title(t, source=""):
        t = t.strip() if t else ""
        # 过滤掉常见占位/无意义标题
        if not t or len(t) < 4:
            return
        bad = ["商品详情页", "淘宝网", "天猫", "taobao", "tmall", "手机淘宝", "阿里1688",
               "商品搜索", "宝贝详情", "detail", "tb", "页面"]
        if any(b in t.lower() for b in bad) and len(t) < 12:
            return
        title_candidates.append({"text": t, "source": source, "len": len(t)})

    # 1. og:title 多顺序兼容
    for pat in [r'<meta\s+property="og:title"\s+content="([^"]+)"',
                r'<meta\s+content="([^"]+)"\s+property="og:title"',
                r'<meta\s+property=\'og:title\'\s+content=\'([^\']+)\'',
                r'<meta\s+name="og:title"\s+content="([^"]+)"']:
        m = re.search(pat, html, re.I)
        if m:
            add_title(m.group(1), "og:title")

    # 2. <title> 标签（通常有平台后缀，但可能直接就是真实标题）
    m = re.search(r'<title>([^<]+)</title>', html)
    if m:
        t = m.group(1)
        t = re.sub(r'\s*[-|]\s*(淘宝网|天猫|tmall|Taobao|手机淘宝).*$', '', t, flags=re.I)
        add_title(t, "<title>")

    # 3. g_config / TShop.Setup 常见配置对象
    for pat in [r'g_config\s*=\s*\{[\s\S]*?"title"\s*:\s*"([^"]+)"',
                r'g_config\s*=\s*\{[\s\S]*?title\s*:\s*["\']([^"\']+)["\']',
                r'TShop\.Setup\([\s\S]*?"title"\s*:\s*"([^"]+)"',
                r'defaultItemTitle\s*[:=]\s*["\']([^"\']+)["\']',
                r'itemTitle\s*[:=]\s*["\']([^"\']+)["\']']:
        m = re.search(pat, html, re.I)
        if m:
            add_title(m.group(1), "script")

    # 4. 大块 JSON 里找 title（window.__INITIAL_STATE__ / _INIT_NANO_PUB_DATA / api 数据）
    for pat in [r'window\.__INITIAL_STATE__\s*=\s*([\s\S]*?);</script>',
                r'window\._INIT_NANO_PUB_DATA\s*=\s*([\s\S]*?);</script>',
                r'window\.__DATA__\s*=\s*([\s\S]*?);</script>',
                r'var\s+_DATA_\s*=\s*([\s\S]*?);</script>']:
        m = re.search(pat, html, re.I)
        if m:
            try:
                js = json.loads(m.group(1).strip().rstrip(';'))
                # 递归找标题
                def find_title(obj, depth=0):
                    if depth > 8:
                        return None
                    if isinstance(obj, dict):
                        for k in ['title', 'itemTitle', 'itemTitle', 'zhName', 'itemTitle']:
                            v = obj.get(k)
                            if isinstance(v, str) and len(v.strip()) > 4:
                                return v.strip()
                        # 天猫详情常见 key
                        for k in ['item', 'itemDO', 'data', 'result', 'itemInfo']:
                            if k in obj:
                                r = find_title(obj[k], depth+1)
                                if r:
                                    return r
                    return None
                tt = find_title(js)
                if tt:
                    add_title(tt, "json")
            except Exception:
                pass

    # 5. 通用 title 字段（兜底）
    for pat in [r'"title"\s*:\s*"([^"]{4,120})"',
                r'"itemTitle"\s*:\s*"([^"]{4,120})"']:
        for m in re.finditer(pat, html):
            add_title(m.group(1), "generic")

    # 选择最佳标题：优先 og:title / script，长度适中
    best_title = None
    best_score = -1
    for c in title_candidates:
        score = 0
        if c["source"] == "og:title":
            score += 100
        if c["source"] == "script":
            score += 80
        if c["source"] == "json":
            score += 70
        score += min(len(c["text"]), 80)  # 长度适中加分
        if score > best_score:
            best_score = score
            best_title = c["text"]
    if best_title:
        out["title"] = best_title

    # 价格
    price_candidates = []
    for pat in [r'"price"\s*:\s*"?([\d.]+)"?',
                r'"viewPrice"\s*:\s*"([\d.]+)"',
                r'"zkFinalPrice"\s*:\s*"([\d.]+)"',
                r'"skuPrice"\s*:\s*"([\d.]+)"',
                r'"defaultItemPrice"\s*:\s*"?([\d.]+)"?',
                r'"priceNow"\s*:\s*"?([\d.]+)"?',
                r'priceBold[^\d]*([\d.]+)',
                r'[\u4ef7][\u683c]\s*[:=]\s*"?([\d.]+)"?']:
        for m in re.finditer(pat, html):
            price_candidates.append(m.group(1))
    # 选出现频率最高的价格，避免解析到促销价/区间价
    if price_candidates:
        from collections import Counter
        cnt = Counter(price_candidates)
        out["price"] = cnt.most_common(1)[0][0]

    # 主图候选池
    pic_candidates = []

    def add_pic(src, source=""):
        if not src:
            return
        src = src.strip()
        if src.startswith("//"):
            src = "https:" + src
        if not src.startswith("http"):
            return
        # 过滤小图、logo
        if any(x in src.lower() for x in ["40x40", "60x60", "80x80", "pngicon", "logo"]):
            return
        pic_candidates.append({"url": src, "source": source})

    for pat in [r'<meta\s+property="og:image"\s+content="([^"]+)"',
                r'<meta\s+content="([^"]+)"\s+property="og:image"',
                r'"pic"\s*:\s*"([^"]+)"',
                r'"picUrl"\s*:\s*"([^"]+)"',
                r'"img"\s*:\s*"([^"]+)"',
                r'"itemPic"\s*:\s*"([^"]+)"',
                r'"mainPic"\s*:\s*"([^"]+)"',
                r'"image"\s*:\s*"([^"]+)"']:
        for m in re.finditer(pat, html, re.I):
            add_pic(m.group(1), "regex")

    # 从 JSON 主图字段里取
    if not pic_candidates:
        for pat in [r'"images"\s*:\s*\[\s*"([^"]+)"',
                    r'"itemImages"\s*:\s*\[\s*"([^"]+)"']:
            m = re.search(pat, html, re.I)
            if m:
                add_pic(m.group(1), "json")

    # 取第一个（按优先级 og:image > 其他）
    if pic_candidates:
        out["pic"] = pic_candidates[0]["url"]

    return out


def is_generic_title(t):
    if not t:
        return True
    bad = ["商品详情页", "宝贝详情", "淘宝网", "天猫", "tmall", "taobao", "手机淘宝", "阿里1688",
           "商品搜索", "detail", "page", "页面", "tb"]
    t2 = t.lower()
    return len(t.strip()) < 5 or any(b in t2 for b in bad)


def fetch_page(url):
    """服务端抓取商品页并解析（多域名尝试，结果合并）"""
    item_id = extract_item_id(url)
    if not item_id:
        return {"ok": False, "msg": "未能从链接中识别商品ID（请确认是商品详情页链接）"}

    candidates = [
        ("https://detail.tmall.com/item.htm", "tmall"),
        ("https://h5.m.taobao.com/awp/core/detail.htm", "m_taobao"),
        ("https://item.taobao.com/item.htm", "taobao"),
    ]

    best = {"title": "", "price": "", "pic": ""}
    merged_from = []
    last_err = None

    for base, domain in candidates:
        u = f"{base}?id={item_id}"
        try:
            # Referer 与目标域名一致，减少反爬
            referer = "https://www.tmall.com/" if "tmall" in domain else "https://www.taobao.com/"
            req = urllib.request.Request(u, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": referer,
                "Connection": "keep-alive",
            })
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode("utf-8", "ignore")
            data = parse_html(html, item_id)
            merged_from.append({"domain": domain, "data": data})

            # 合并最佳字段
            if not best["title"] and not is_generic_title(data.get("title")):
                best["title"] = data.get("title")
            if not best["price"] and data.get("price"):
                best["price"] = data.get("price")
            if not best["pic"] and data.get("pic"):
                best["pic"] = data.get("pic")

        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
        except Exception as e:
            last_err = str(e)

    # 只要拿到 title/price/pic 中任意真实字段，就返回部分成功
    if best["title"] or best["price"] or best["pic"]:
        result = {"ok": True, "item_id": item_id, "source": "page_parse"}
        result.update(best)
        # 标记哪些字段没拿到
        missing = []
        if not best["title"]:
            missing.append("标题")
        if not best["price"]:
            missing.append("价格")
        if not best["pic"]:
            missing.append("主图")
        if missing:
            result["warning"] = f"未解析到：{', '.join(missing)}；建议提供淘宝客 API 凭证或手动补全。"
        return result

    return {"ok": False, "msg": last_err or "页面未返回商品数据（淘宝可能返回了验证页）"}


def tbk_sign(params, secret):
    """淘宝开放平台 TOP 签名（MD5）"""
    ks = sorted(params.keys())
    s = secret
    for k in ks:
        s += k + str(params[k])
    s += secret
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


def tbk_item_info(item_id):
    """走淘宝客官方API：taobao.tbk.item.info.get"""
    if not (APPKEY and APPSECRET and ADZONE_ID):
        return None
    params = {
        "method": "taobao.tbk.item.info.get",
        "app_key": APPKEY,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "2.0",
        "sign_method": "md5",
        "num_iids": item_id,
        "adzone_id": ADZONE_ID,
        "platform": "1",
    }
    params["sign"] = tbk_sign(params, APPSECRET)
    url = "https://gw.api.taobao.com/router/rest?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            js = json.loads(r.read().decode("utf-8", "ignore"))
        item = js["tbk_item_info_get_response"]["results"]["n_tbk_item"][0]
        return {
            "ok": True,
            "item_id": item_id,
            "title": item.get("title", ""),
            "price": item.get("zk_final_price", ""),
            "pic": "https:" + item.get("pict_url", "") if item.get("pict_url") else "",
            "cat": item.get("cat_name", ""),
            "source": "tbk_api",
        }
    except Exception as e:
        return {"ok": False, "msg": "淘宝客API调用失败：" + str(e), "source": "tbk_api"}


def parse_url(url):
    item_id = extract_item_id(url)
    if not item_id:
        return {"ok": False, "msg": "未能从链接中识别商品ID"}
    # 优先官方API（若配置了凭证）
    if APPKEY and APPSECRET:
        api = tbk_item_info(item_id)
        if api:
            return api
    # 否则服务端抓页
    return fetch_page(url)


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra_headers=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Requested-With")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body.encode("utf-8") if isinstance(body, str) else body)

    def do_OPTIONS(self):
        self._send(204, "")

    def do_GET(self):
        path = self.path
        if path == "/api/last-parse":
            # 返回最近一次浏览器抓取的数据（如果 30 秒内有）
            global _last_parse
            age = time.time() - _last_parse["ts"]
            data = {"ok": _last_parse["ts"] > 0 and age < 30, "data": _last_parse}
            if not data["ok"]:
                data["data"] = {}
            self._send(200, json.dumps(data, ensure_ascii=False))
            return
        # 把 URL 路径和查询参数分开，避免 /foo.html?a=1 被当成含 ? 的文件名
        full_path = self.path
        path = full_path
        if "?" in full_path:
            path = full_path[:full_path.find("?")]
        if path in ("/", "/index.html"):
            path = "/taobao-promo-advisor.html"
        # 安全路径：只允许当前目录下的静态文件
        local_path = os.path.normpath(os.path.join(HERE, path.lstrip("/")))
        if not local_path.startswith(HERE) or not os.path.isfile(local_path):
            self._send(404, "not found")
            return
        # 根据扩展名推断 content-type
        ext = os.path.splitext(local_path)[1].lower()
        ctype_map = {".html": "text/html; charset=utf-8", ".js": "application/javascript",
                     ".css": "text/css", ".json": "application/json", ".png": "image/png",
                     ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                     ".svg": "image/svg+xml", ".ico": "image/x-icon"}
        ctype = ctype_map.get(ext, "application/octet-stream")
        try:
            with open(local_path, "rb") as f:
                self._send(200, f.read(), ctype)
        except Exception as e:
            self._send(500, "read error: " + str(e))

    def do_POST(self):
        if self.path == "/api/parse":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8", "ignore")
                payload = json.loads(raw) if raw else {}
                url = payload.get("url", "")
                result = parse_url(url)
                self._send(200, json.dumps(result, ensure_ascii=False))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "msg": str(e)}, ensure_ascii=False))
        elif self.path == "/api/browser-parse":
            # 浏览器扩展在淘宝页面抓取后 POST 数据回来
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8", "ignore")
                payload = json.loads(raw) if raw else {}
                global _last_parse
                _last_parse = {
                    "title": payload.get("title", ""),
                    "price": payload.get("price", ""),
                    "pic": payload.get("pic", ""),
                    "sales": payload.get("sales", ""),
                    "reviews": payload.get("reviews", ""),
                    "url": payload.get("url", ""),
                    "ts": time.time(),
                    "ip": self.client_address[0],
                }
                self._send(200, json.dumps({"ok": True, "msg": "已接收"}, ensure_ascii=False))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "msg": str(e)}, ensure_ascii=False))
        else:
            self._send(404, "not found")

    def log_message(self, *args):
        pass  # 静默日志


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true",
                        help="启动服务后不自动打开浏览器（由启动器控制）")
    args = parser.parse_args()

    os.chdir(HERE)
    port = PORT
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/"
        print("淘系推广参谋已启动：", url)
        print("链接自动解析：", "已启用（淘宝客API）" if (APPKEY and APPSECRET) else "已启用（服务端抓页，受淘宝反爬影响）")
        if not args.no_open:
            open_browser(port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("已停止")


if __name__ == "__main__":
    main()
