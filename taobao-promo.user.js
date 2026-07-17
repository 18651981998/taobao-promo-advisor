// ==UserScript==
// @name         淘系推广参谋 · 商品导入
// @namespace    http://127.0.0.1:8123
// @version      1.0
// @description  在淘宝/天猫商品页一键导入标题、价格、主图到本地「淘系推广参谋」工具
// @author       A0_0 涛声依旧
// @match        https://item.taobao.com/item.htm*
// @match        https://detail.tmall.com/item.htm*
// @match        https://*.tmall.com/*
// @match        https://*.taobao.com/*
// @match        http://127.0.0.1:8123/*
// @grant        unsafeWindow
// ==/UserScript==

(function () {
  'use strict';

  const TOOL_ORIGIN = 'http://127.0.0.1:8123';
  const win = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;

  // 在本地工具页注入标记，让页面知道脚本已安装
  if (location.origin === TOOL_ORIGIN) {
    window.__TAOBAO_PROMO_USERSCRIPT_INSTALLED__ = true;
    return;
  }

  // 仅商品详情页显示按钮（简单判断 URL 或页面特征）
  if (!/item\.htm|detail/.test(location.href)) return;

  function extract() {
    let title = '';
    try { title = document.querySelector('h1').innerText.trim(); } catch (e) {}
    if (!title) try { title = document.querySelector('meta[property="og:title"]').content.trim(); } catch (e) {}
    if (!title) try { title = win.g_config.title; } catch (e) {}

    let price = '';
    try { price = win.g_config.defaultItemPrice; } catch (e) {}
    if (!price) {
      try {
        price = document.querySelector('[class*="Price"]').innerText.match(/[\d.]+/)[0];
      } catch (e) {}
    }
    if (!price) {
      const m = document.body.innerText.match(/[¥￥]\s*([\d.]+)/);
      if (m) price = m[1];
    }

    let pic = '';
    try { pic = document.querySelector('meta[property="og:image"]').content.trim(); } catch (e) {}
    if (!pic) try { pic = win.g_config.pic; } catch (e) {}
    if (!pic) {
      const imgs = document.querySelectorAll('img');
      for (let i = 0; i < imgs.length; i++) {
        if (imgs[i].src && imgs[i].src.indexOf('alicdn.com') > -1) { pic = imgs[i].src; break; }
      }
    }

    return { title, price, pic, url: location.href };
  }

  function openTool(d) {
    const u = TOOL_ORIGIN + '/?title=' + encodeURIComponent(d.title || '')
            + '&price=' + encodeURIComponent(d.price || '')
            + '&pic=' + encodeURIComponent(d.pic || '')
            + '&url=' + encodeURIComponent(d.url || '');
    window.open(u, '_blank');
  }

  function addButton() {
    if (document.getElementById('tb-promo-import-btn')) return;
    const btn = document.createElement('div');
    btn.id = 'tb-promo-import-btn';
    btn.innerText = '导入推广参谋';
    btn.style.cssText = [
      'position:fixed',
      'right:20px',
      'bottom:100px',
      'z-index:999999',
      'padding:10px 14px',
      'background:#ff5000',
      'color:#fff',
      'border-radius:8px',
      'font-size:14px',
      'font-weight:600',
      'cursor:pointer',
      'box-shadow:0 4px 12px rgba(255,80,0,.35)',
      'font-family:-apple-system,"Microsoft YaHei",sans-serif',
      'line-height:1.4'
    ].join(';');
    btn.addEventListener('click', function () {
      const d = extract();
      if (!d.title && !d.price && !d.pic) {
        alert('未能自动提取商品信息，请手动填写。');
        return;
      }
      openTool(d);
    });
    document.body.appendChild(btn);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addButton);
  } else {
    addButton();
  }
})();
