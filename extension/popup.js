// 淘系推广参谋 · 扩展弹窗：在当前商品页提取 title / price / pic 并打开本地工具
function extract() {
  function t() {
    var r = '';
    try { r = document.querySelector('h1').innerText.trim(); } catch (e) {}
    if (!r) try { r = document.querySelector('meta[property="og:title"]').content.trim(); } catch (e) {}
    if (!r) r = document.title;
    return r;
  }
  function p() {
    var r = '';
    var sels = ['.Price--realSales', '.Price--actualValue', '#J_PromoPrice .tm-price', '#J_PromoPriceNum', '#J_StrPrice .tb-rmb-num', '.tb-rmb-num', '[class*="Price"]'];
    for (var i = 0; i < sels.length; i++) {
      try { var m = document.querySelector(sels[i]).innerText.match(/[\d,]+\.?\d*/); if (m) { r = m[0].replace(/,/g, ''); break; } } catch (e) {}
    }
    if (!r) { var m = document.body.innerText.match(/[¥￥]\s*([\d,]+\.?\d*)/); if (m) r = m[1].replace(/,/g, ''); }
    return r;
  }
  function c() {
    var r = '';
    try { r = document.querySelector('meta[property="og:image"]').content.trim(); } catch (e) {}
    if (!r) try { r = document.querySelector('#J_ImgBooth').src.trim(); } catch (e) {}
    if (!r) try { r = document.querySelector('#J_ImageWrap img').src.trim(); } catch (e) {}
    if (!r) {
      var imgs = document.querySelectorAll('img');
      for (var i = 0; i < imgs.length; i++) {
        if (imgs[i].src.indexOf('alicdn.com') > -1 || imgs[i].src.indexOf('taobaocdn') > -1) { r = imgs[i].src; break; }
      }
    }
    return r;
  }
  return { title: t(), price: p(), pic: c() };
}

document.getElementById('btn').onclick = async function () {
  var tip = document.getElementById('tip');
  var tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  var tab = tabs[0];
  if (!tab || !/taobao|tmall/.test(tab.url || '')) {
    tip.textContent = '请先打开一个淘宝/天猫商品详情页，再点此按钮。';
    return;
  }
  var res = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: extract });
  var d = (res && res[0] && res[0].result) || {};
  var u = 'http://127.0.0.1:8123/?title=' + encodeURIComponent(d.title || '')
    + '&price=' + encodeURIComponent(d.price || '')
    + '&pic=' + encodeURIComponent(d.pic || '')
    + '&url=' + encodeURIComponent(tab.url || '');
  chrome.tabs.create({ url: u });
  window.close();
};
