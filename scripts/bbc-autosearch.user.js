// ==UserScript==
// @name         BBC Lightning Leads — Auto-Search from URL hash
// @namespace    https://github.com/timfarr-ai/rt-companion
// @version      1.1
// @description  Auto-fills the BBC Lightning Leads search box when URL contains "#auto:<location>" and triggers Search. Used by the rt-companion daily briefing to deep-link from a deal card into a BBC search.
// @author       Tim Farr
// @match        https://www.buyboxcartel.com/vip/lightning-leads*
// @match        https://buyboxcartel.com/vip/lightning-leads*
// @grant        none
// @run-at       document-idle
// @updateURL    https://raw.githubusercontent.com/timfarr-ai/rt-companion/main/scripts/bbc-autosearch.user.js
// @downloadURL  https://raw.githubusercontent.com/timfarr-ai/rt-companion/main/scripts/bbc-autosearch.user.js
// ==/UserScript==

(function () {
  'use strict';

  const HASH_PREFIX = '#auto:';
  const POLL_INTERVAL_MS = 200;
  const POLL_TIMEOUT_MS = 8000;

  function getAutoQuery() {
    const h = location.hash || '';
    if (!h.startsWith(HASH_PREFIX)) return null;
    try {
      return decodeURIComponent(h.slice(HASH_PREFIX.length));
    } catch (e) {
      return h.slice(HASH_PREFIX.length);
    }
  }

  function findSearchInput() {
    // BBC's Lightning Leads search box — placeholder includes "City" or "address"
    return document.querySelector(
      'input[placeholder*="City" i], input[placeholder*="City, State" i], input[placeholder*="address" i]'
    );
  }

  function findSearchButton() {
    return Array.from(document.querySelectorAll('button')).find(
      (b) => b.innerText && b.innerText.trim().toLowerCase() === 'search'
    );
  }

  function setReactInputValue(input, value) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function showBanner(msg, color) {
    const existing = document.getElementById('rt-autosearch-banner');
    if (existing) existing.remove();
    const div = document.createElement('div');
    div.id = 'rt-autosearch-banner';
    div.style.cssText =
      'position:fixed;top:12px;right:12px;z-index:99999;padding:8px 14px;' +
      'background:' + (color || '#1e2c44') + ';color:#fff;border-radius:8px;' +
      'font:13px -apple-system,BlinkMacSystemFont,sans-serif;box-shadow:0 4px 12px rgba(0,0,0,0.4);';
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 4000);
  }

  function runAutoSearch() {
    const q = getAutoQuery();
    if (!q) return;
    const startTime = Date.now();
    const tryFill = () => {
      const input = findSearchInput();
      const btn = findSearchButton();
      if (input && btn) {
        setReactInputValue(input, q);
        setTimeout(() => {
          btn.click();
          showBanner('🔍 Auto-searched: ' + q, '#1a4d2e');
          // Clear the hash so a manual refresh doesn't re-trigger
          history.replaceState(null, '', location.pathname + location.search);
        }, 250);
        return true;
      }
      return false;
    };

    if (tryFill()) return;
    const poll = setInterval(() => {
      if (tryFill() || Date.now() - startTime > POLL_TIMEOUT_MS) {
        clearInterval(poll);
        if (Date.now() - startTime > POLL_TIMEOUT_MS) {
          showBanner('⚠️ Auto-search: search box not found. Paste manually: ' + q, '#7d4d1a');
        }
      }
    }, POLL_INTERVAL_MS);
  }

  // Initial run + re-run on hash changes (SPA navigations)
  runAutoSearch();
  window.addEventListener('hashchange', runAutoSearch);
})();
