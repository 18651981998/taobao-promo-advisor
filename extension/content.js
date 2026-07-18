// 淘系推广参谋 · 普通扩展 Content Script
// 作用：在淘宝/天猫商品页注入悬浮按钮，点击抓取标题/价格/主图并打开本地工具页
// 不走 Tampermonkey，因此不受 Chrome 138+ 对用户脚本的限制
(function () {
  'use strict';

  const TOOL = 'http://127.0.0.1:8123';

  // 在本地工具页注入标记，让页面知道扩展已安装
  if (location.origin === TOOL) {
    window.__TAOBAO_PROMO_EXTENSION_INSTALLED__ = true;
    return;
  }

  function isItemPage() {
    const u = location.href;
    if (/item\.htm|detail\.tmall|item\.taobao|world\.taobao|m\.tb\.cn/.test(u)) return true;
    const host = location.hostname;
    if (/\b(taobao|tmall)\b/.test(host) && /\d{8,}/.test(u)) return true;
    return !!document.querySelector('#J_Title, #detail, .tb-detail, .tb-main, [data-spm*="d"], [data-spm*="item"], .item-title, h1');
  }

  const onItem = isItemPage();
  console.log('[淘系推广参谋] 扩展已激活。当前页面是否商品页：', onItem, location.href);

  function text(sel) {
    try { const e = document.querySelector(sel); return e ? e.innerText.trim() : ''; } catch (e) { return ''; }
  }
  function textAll(sel) {
    try {
      const arr = Array.from(document.querySelectorAll(sel));
      return arr.map(function (el) { return el.innerText.trim(); }).join('\n');
    } catch (e) { return ''; }
  }
  function attr(sel, a) {
    try { const e = document.querySelector(sel); return e ? (e.getAttribute(a) || e[a] || '').trim() : ''; } catch (e) { return ''; }
  }

  function scoreImage(src) {
    if (!src) return -1000;
    let s = 0;
    // 阿里/淘宝 CDN 才有可能是商品主图
    if (/alicdn\.com|taobaocdn\.com/.test(src)) s += 30;
    // 商品图常见上传目录与尺寸标记
    if (/\/uploaded\//.test(src)) s += 120;
    if (/\/imgextra\//.test(src)) s += 120;
    if (/_\d{2,4}x\d{2,4}/.test(src)) s += 80;
    if (/[?&]x-oss-process|imageView|_Q\d/.test(src)) s += 40;
    // 排除 logo/占位/loading
    if (/logo|blank|placeholder|loading|1x1|empty|default|pix\.gif|tfscom/i.test(src)) s -= 500;
    if (/^data:/.test(src)) s -= 300;
    return s;
  }

  function collectImageCandidates() {
    const candidates = [];
    const selectors = [
      '#J_ImgBooth img', '#J_ImgBooth', '#J_ImageWrap img', '#J_ZoomPic img', '#J_ZoomMain img',
      '.tb-main-pic img', '.tb-booth img', '.main-image img', '.tm-gallery img', '.gallery img',
      '.item-pic img', '.img-privilege img', '.module-pic img', '#J_PicPanel img', '.pic img'
    ];
    for (let s of selectors) {
      try {
        const els = document.querySelectorAll(s);
        els.forEach(function (el) {
          if (el.tagName === 'IMG') {
            candidates.push(el.getAttribute('src'));
            candidates.push(el.getAttribute('data-src'));
            if (el.srcset) candidates.push(el.srcset.split(',')[0].trim().split(' ')[0]);
          } else {
            Array.from(el.querySelectorAll('img')).forEach(function (im) {
              candidates.push(im.getAttribute('src'));
              candidates.push(im.getAttribute('data-src'));
            });
          }
        });
      } catch (e) {}
    }
    // 兜底：遍历所有图片，收集看起来像是商品主图的
    try {
      Array.from(document.querySelectorAll('img')).forEach(function (im) {
        if (im.naturalWidth && im.naturalWidth < 100) return;
        candidates.push(im.getAttribute('src'));
        candidates.push(im.getAttribute('data-src'));
        if (im.srcset) candidates.push(im.srcset.split(',')[0].trim().split(' ')[0]);
      });
    } catch (e) {}
    // 去重并评分
    const seen = new Set();
    const scored = [];
    for (let src of candidates) {
      if (!src || seen.has(src)) continue;
      seen.add(src);
      const sc = scoreImage(src);
      if (sc <= 0) continue;
      scored.push({ src: src, score: sc });
    }
    scored.sort(function (a, b) { return b.score - a.score; });
    return scored;
  }

  function extractImage() {
    const imgs = collectImageCandidates();
    if (imgs.length) return imgs[0].src;
    // 最后的兜底：og:image
    const og = attr('meta[property="og:image"]', 'content');
    if (og && !/logo|blank|placeholder/i.test(og)) return og;
    return '';
  }

  function extractNumber(patterns, fallbackPatterns) {
    for (let s of patterns) {
      try {
        const t = textAll(s);
        const m = t.match(/[\d,\.万]+/);
        if (m) return m[0].replace(/,/g, '');
      } catch (e) {}
    }
    if (fallbackPatterns) {
      const body = document.body ? document.body.innerText : '';
      for (let re of fallbackPatterns) {
        const m = body.match(re);
        if (m) return m[1].replace(/,/g, '');
      }
    }
    return '';
  }

  function extract() {
    let title = text('h1')
      || attr('meta[property="og:title"]', 'content')
      || document.title;
    title = (title || '').replace(/\s*-\s*(淘宝网|天猫|tmall|Taobao|TAOBAO).*$/i, '').trim();

    let price = '';
    const priceSels = ['.Price--realSales', '.Price--actualValue', '#J_PromoPrice .tm-price',
      '#J_PromoPriceNum', '#J_StrPrice .tb-rmb-num', '.tb-rmb-num', '[class*="Price"]'];
    for (const s of priceSels) {
      const m = text(s).match(/[\d,]+\.?\d*/);
      if (m) { price = m[0].replace(/,/g, ''); break; }
    }
    if (!price) {
      const m = document.body.innerText.match(/[¥￥]\s*([\d,]+\.?\d*)/);
      if (m) price = m[1].replace(/,/g, '');
    }

    const pic = extractImage();

    const sales = extractNumber(
      ['.tm-ind-sellCount', '.tm-ind-sellCount .tm-count', '[class*="sellCount"]', '[class*="sellCount"] .tm-count',
       '.tb-sell-count', '.sell-count', '#J_SellCounter', '[data-spm*="sell"]'],
      [/(?:月销|月销量|已售|总销量|销量|月成交量|成交)[：:\s]*([\d,\.万]+)\s*(?:件|笔|单)?/i]
    );

    const reviews = extractNumber(
      ['.tm-ind-reviewCount', '.tm-ind-reviewCount .tm-count', '[class*="reviewCount"]', '[class*="reviewCount"] .tm-count',
       '.tb-rate-count', '.rate-count', '#J_ReviewTab', '.rate-counter', '[data-spm*="review"]'],
      [/累计评价[：:\s]*([\d,\.万]+)/i, /(?:评价|评论)[数\s]*[：:\s]*([\d,\.万]+)/i]
    );

    return { title: title || '', price: price || '', pic: pic || '', sales: sales || '', reviews: reviews || '', url: location.href };
  }

  function showToast(msg, ok) {
    let t = document.getElementById('tb-promo-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'tb-promo-toast';
      t.style.cssText = 'position:fixed;right:20px;bottom:160px;z-index:2147483647;max-width:260px;padding:10px 14px;'
        + 'border-radius:8px;font-size:13px;font-weight:500;box-shadow:0 6px 18px rgba(0,0,0,.2);'
        + 'font-family:-apple-system,"Microsoft YaHei",sans-serif;transition:opacity .3s;';
      document.body.appendChild(t);
    }
    t.style.background = ok ? '#0f6e56' : '#c0451d';
    t.style.color = '#fff';
    t.textContent = msg;
    t.style.opacity = '1';
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.style.opacity = '0'; }, 2600);
  }

  function openTool(d) {
    const q = '?title=' + encodeURIComponent(d.title || '')
      + '&price=' + encodeURIComponent(d.price || '')
      + '&pic=' + encodeURIComponent(d.pic || '')
      + '&sales=' + encodeURIComponent(d.sales || '')
      + '&reviews=' + encodeURIComponent(d.reviews || '')
      + '&url=' + encodeURIComponent(d.url || '');
    window.open(TOOL + '/taobao-promo-advisor.html' + q, '_blank');
  }

  function sendData(d) {
    const fallback = function () { openTool(d); };
    try {
      fetch(TOOL + '/api/browser-parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(d)
      }).then(function (r) { return r.json(); }).then(function (j) {
        showToast(j.ok ? '已导入 ✓ 正在打开工具页…' : '已抓取，正在打开工具页', true);
        fallback();
      }).catch(function () { fallback(); });
    } catch (e) {
      fallback();
    }
  }

  function addButton() {
    if (document.getElementById('tb-promo-import-btn')) return;
    const btn = document.createElement('div');
    btn.id = 'tb-promo-import-btn';
    btn.innerHTML = '🛒 导入推广参谋';
    btn.style.cssText = [
      'position:fixed', 'right:20px', 'top:140px', 'z-index:2147483647',
      'padding:11px 16px', 'background:linear-gradient(135deg,#ff5000,#ff7300)', 'color:#fff',
      'border-radius:24px', 'font-size:14px', 'font-weight:600', 'cursor:pointer', 'display:block !important',
      'visibility:visible !important', 'opacity:1 !important',
      'box-shadow:0 6px 18px rgba(255,80,0,.4)', 'font-family:-apple-system,"Microsoft YaHei",sans-serif',
      'line-height:1', 'user-select:none', 'border:2px solid #fff'
    ].join(';');
    let dragging = false, offX = 0, offY = 0;
    btn.addEventListener('mousedown', function (e) {
      dragging = true; offX = e.clientX - btn.offsetLeft; offY = e.clientY - btn.offsetTop;
      e.preventDefault();
    });
    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      btn.style.left = (e.clientX - offX) + 'px';
      btn.style.top = (e.clientY - offY) + 'px';
    });
    document.addEventListener('mouseup', function () { dragging = false; });
    btn.addEventListener('click', function () {
      console.log('[淘系推广参谋] 按钮被点击');
      if (!onItem) { showToast('请在商品详情页使用', false); return; }
      try {
        const d = extract();
        console.log('[淘系推广参谋] 抓取结果', d);
        if (!d.title && !d.price && !d.pic) {
          showToast('未抓取到商品信息，请确认是商品详情页', false);
          openTool(d);
          return;
        }
        showToast('正在抓取…', true);
        sendData(d);
      } catch (e) {
        console.error('[淘系推广参谋] 抓取失败', e);
        showToast('抓取失败：' + e.message, false);
      }
    });
    document.body.appendChild(btn);
    console.log('[淘系推广参谋] 悬浮按钮已注入', location.href);
  }

  function attachObserver() {
    try {
      const mo = new MutationObserver(function () {
        if (!document.getElementById('tb-promo-import-btn')) addButton();
      });
      mo.observe(document.documentElement, { childList: true, subtree: true });
    } catch (e) {}
  }

  function init() {
    if (document.body) {
      addButton();
      attachObserver();
    } else {
      const t = setInterval(function () {
        if (document.body) {
          clearInterval(t);
          addButton();
          attachObserver();
        }
      }, 200);
    }
  }
  init();

  // 兜底：页面各种时机都尝试补一次按钮，确保一定出现
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addButton);
  }
  window.addEventListener('load', addButton);

  // 每隔 2 秒兜底检查一次，确保按钮始终存在
  setInterval(function () {
    if (!document.getElementById('tb-promo-import-btn')) addButton();
  }, 2000);
})();
