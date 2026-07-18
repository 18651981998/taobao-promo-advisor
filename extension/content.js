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
  function attr(sel, a) {
    try { const e = document.querySelector(sel); return e ? (e.getAttribute(a) || e[a] || '').trim() : ''; } catch (e) { return ''; }
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

    let pic = attr('meta[property="og:image"]', 'content')
      || attr('#J_ImgBooth', 'src')
      || attr('#J_ImageWrap img', 'src');
    if (!pic) {
      const imgs = document.querySelectorAll('#J_ImgBooth, #J_ImageWrap img, img');
      for (const im of imgs) {
        const src = im.src || im.getAttribute('data-src') || '';
        if (src && (src.indexOf('alicdn.com') > -1 || src.indexOf('taobaocdn') > -1)) { pic = src; break; }
      }
    }

    return { title: title || '', price: price || '', pic: pic || '', url: location.href };
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
      + '&url=' + encodeURIComponent(d.url || '');
    window.open(TOOL + '/' + q, '_blank');
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
      'position:fixed', 'left:20px', 'top:150px', 'z-index:2147483647',
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

  function init() {
    if (document.body) addButton();
    else {
      const t = setInterval(function () {
        if (document.body) { clearInterval(t); addButton(); }
      }, 300);
    }
  }
  init();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addButton);
  }
  window.addEventListener('load', addButton);

  // SPA 路由切换或页面异步渲染后，若按钮丢失则重建
  try {
    const mo = new MutationObserver(function () {
      if (!document.getElementById('tb-promo-import-btn')) addButton();
    });
    if (document.body) mo.observe(document.body, { childList: true, subtree: true });
  } catch (e) {}

  // 每隔 2 秒兜底检查一次，确保按钮始终存在
  setInterval(function () {
    if (!document.getElementById('tb-promo-import-btn')) addButton();
  }, 2000);
})();
