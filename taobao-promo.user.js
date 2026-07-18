// ==UserScript==
// @name         淘系推广参谋 · 一键导入（悬浮按钮）
// @namespace    http://127.0.0.1:8123
// @version      2.2
// @description  在淘宝/天猫商品页注入悬浮按钮，点击一键抓取标题/价格/主图并传入本地「淘系推广参谋」工具，无需 F12。
// @author       A0_0 涛声依旧
// @match        *://*taobao.com/*
// @match        *://*tmall.com/*
// @match        *://*tmall.hk/*
// @match        http://127.0.0.1:8123/*
// @connect      127.0.0.1
// @updateURL    https://raw.githubusercontent.com/18651981998/taobao-promo-advisor/main/taobao-promo.user.js
// @downloadURL  https://raw.githubusercontent.com/18651981998/taobao-promo-advisor/main/taobao-promo.user.js
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function () {
  'use strict';

  const TOOL = 'http://127.0.0.1:8123';

  // 在本地工具页注入标记，让页面知道脚本已安装
  if (location.origin === TOOL) {
    window.__TAOBAO_PROMO_USERSCRIPT_INSTALLED__ = true;
    return;
  }

  // 判断当前是否为商品详情页（淘宝/天猫详情页地址规律性较强）
  function isItemPage() {
    const u = location.href;
    if (/item\.htm|detail\.tmall|item\.taobao|world\.taobao|m\.tb\.cn/.test(u)) return true;
    const host = location.hostname;
    if (/\b(taobao|tmall)\b/.test(host) && /\d{8,}/.test(u)) return true;
    return !!document.querySelector('#J_Title, #detail, .tb-detail, .tb-main, [data-spm*="d"], [data-spm*="item"], .item-title, h1');
  }

  const onItem = isItemPage();
  console.log('[淘系推广参谋] 脚本已激活。当前页面是否商品页：', onItem, location.href);

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
      t.style.cssText = 'position:fixed;right:20px;bottom:160px;z-index:9999999;max-width:260px;padding:10px 14px;'
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
      GM_xmlhttpRequest({
        method: 'POST',
        url: TOOL + '/api/browser-parse',
        headers: { 'Content-Type': 'application/json' },
        data: JSON.stringify(d),
        timeout: 4000,
        onload: function (resp) {
          let ok = false;
          try { ok = JSON.parse(resp.responseText).ok; } catch (e) {}
          showToast(ok ? '已导入 ✓ 正在打开工具页…' : '已抓取，正在打开工具页', true);
          fallback();
        },
        onerror: function () { showToast('本地服务未启动？已用链接打开', false); fallback(); },
        ontimeout: function () { showToast('连接超时，已用链接打开', false); fallback(); }
      });
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
      'position:fixed', 'right:20px', 'top:120px', 'z-index:9999999',
      'padding:11px 16px', 'background:linear-gradient(135deg,#ff5000,#ff7300)', 'color:#fff',
      'border-radius:24px', 'font-size:14px', 'font-weight:600', 'cursor:pointer',
      'box-shadow:0 6px 18px rgba(255,80,0,.4)', 'font-family:-apple-system,"Microsoft YaHei",sans-serif',
      'line-height:1', 'user-select:none', 'border:2px solid #fff'
    ].join(';');
    let busy = false;
    btn.addEventListener('click', function () {
      if (busy) return;
      if (!onItem) {
        showToast('请在商品详情页（item.taobao.com / detail.tmall.com）使用此按钮', false);
        return;
      }
      busy = true; btn.style.opacity = '.7';
      const d = extract();
      if (!d.title && !d.price && !d.pic) {
        showToast('未能自动提取，请手动填写', false);
        busy = false; btn.style.opacity = '1'; return;
      }
      sendData(d);
      setTimeout(function () { busy = false; btn.style.opacity = '1'; }, 1500);
    });
    btn.addEventListener('mouseenter', function () { btn.style.transform = 'scale(1.05)'; });
    btn.addEventListener('mouseleave', function () { btn.style.transform = 'scale(1)'; });

    // 按住按钮可拖动，避免被页面固定栏遮挡
    let dragging = false, startX, startY, startLeft, startTop;
    btn.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      dragging = true;
      startX = e.clientX; startY = e.clientY;
      const rect = btn.getBoundingClientRect();
      startLeft = rect.left; startTop = rect.top;
      btn.style.transition = 'none';
      e.preventDefault();
    });
    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      const dx = e.clientX - startX, dy = e.clientY - startY;
      btn.style.left = Math.max(0, Math.min(window.innerWidth - btn.offsetWidth, startLeft + dx)) + 'px';
      btn.style.top = Math.max(0, Math.min(window.innerHeight - btn.offsetHeight, startTop + dy)) + 'px';
      btn.style.right = 'auto';
    });
    document.addEventListener('mouseup', function () { dragging = false; btn.style.transition = 'transform .15s'; });

    document.body.appendChild(btn);
    console.log('[淘系推广参谋] 悬浮按钮已注入', location.href);
  }

  if (document.body) addButton();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addButton);

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
