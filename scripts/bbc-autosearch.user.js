// ==UserScript==
// @name         BBC Lightning Leads — Auto-Search from URL hash
// @namespace    https://github.com/timfarr-ai/rt-companion
// @version      1.3
// @description  Auto-fills the BBC Lightning Leads search box when URL contains "#auto:<City, State>[|street:Street]" — sets max page size, sorts by DOM desc, runs search, then paginates up to 5 pages looking for the specific street. Highlights and scrolls to the match.
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
  const PAGE_SIZE = '20';            // BBC max
  const SORT_LABEL = '📅 Days on Market (High → Low)';
  const SEARCH_RENDER_WAIT_MS = 1800;
  const PAGE_RENDER_WAIT_MS = 1200;
  const MAX_PAGES_TO_SCAN = 5;
  const POLL_INTERVAL_MS = 200;
  const POLL_TIMEOUT_MS = 10000;

  function getAutoQuery() {
    const h = location.hash || '';
    if (!h.startsWith(HASH_PREFIX)) return null;
    try { return decodeURIComponent(h.slice(HASH_PREFIX.length)); }
    catch (e) { return h.slice(HASH_PREFIX.length); }
  }

  function findSearchInput() {
    return document.querySelector(
      'input[placeholder*="City" i], input[placeholder*="address" i]'
    );
  }

  function findSearchButton() {
    return Array.from(document.querySelectorAll('button')).find(
      b => b.innerText && b.innerText.trim().toLowerCase() === 'search'
    );
  }

  function setReactInputValue(input, value) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function setReactSelectValue(sel, value) {
    if (!sel) return;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
    setter.call(sel, value);
    sel.dispatchEvent(new Event('input', { bubbles: true }));
    sel.dispatchEvent(new Event('change', { bubbles: true }));
  }

  // Set page size dropdown to PAGE_SIZE (20). BBC has a "Show:" combobox near pagination.
  function setPageSize() {
    const selects = document.querySelectorAll('select');
    for (const s of selects) {
      const opts = Array.from(s.options || []).map(o => o.value);
      if (opts.includes('10') && opts.includes('15') && opts.includes('20')) {
        setReactSelectValue(s, PAGE_SIZE);
        return true;
      }
    }
    return false;
  }

  // Set sort dropdown to DOM desc (high to low). BBC's Sort combobox has the label
  // "📅 Days on Market (High → Low)".
  function setSortDomDesc() {
    const selects = document.querySelectorAll('select');
    for (const s of selects) {
      const opt = Array.from(s.options || []).find(o => o.value === SORT_LABEL || (o.textContent || '').trim() === SORT_LABEL);
      if (opt) {
        setReactSelectValue(s, opt.value);
        return true;
      }
    }
    return false;
  }

  function showBanner(msg, color) {
    const existing = document.getElementById('rt-autosearch-banner');
    if (existing) existing.remove();
    const div = document.createElement('div');
    div.id = 'rt-autosearch-banner';
    div.style.cssText =
      'position:fixed;top:12px;right:12px;z-index:99999;padding:8px 14px;' +
      'background:' + (color || '#1e2c44') + ';color:#fff;border-radius:8px;' +
      'font:13px -apple-system,BlinkMacSystemFont,sans-serif;box-shadow:0 4px 12px rgba(0,0,0,0.4);max-width:340px;';
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => { if (div.parentElement) div.remove(); }, 5000);
  }

  // Find the property card whose H3 contains the street name (case-insensitive).
  function findCardByStreet(street) {
    if (!street) return null;
    const needle = street.toLowerCase().trim();
    const headings = document.querySelectorAll('h3');
    for (const h of headings) {
      if (h.textContent && h.textContent.toLowerCase().includes(needle)) {
        // Walk up to a parent containing a "Create Offer" button — that's the card.
        let card = h;
        while (card && card.parentElement) {
          card = card.parentElement;
          const buttons = card.querySelectorAll('button');
          if (buttons.length > 0 &&
              Array.from(buttons).some(b => /create offer/i.test(b.textContent))) {
            return card;
          }
        }
        return h.closest('article, section, div');
      }
    }
    return null;
  }

  function highlightAndScroll(card, street) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const oldOutline = card.style.outline;
    const oldShadow = card.style.boxShadow;
    card.style.outline = '3px solid #56d364';
    card.style.boxShadow = '0 0 24px rgba(86, 211, 100, 0.7)';
    card.style.transition = 'all 0.3s ease';
    setTimeout(() => { card.style.outline = oldOutline; card.style.boxShadow = oldShadow; }, 6000);
    showBanner('🎯 Found: ' + street, '#1a4d2e');
  }

  // Find the pagination "Next" button (typically labelled "Next" or has an arrow).
  function findNextPageButton() {
    return Array.from(document.querySelectorAll('button')).find(b => {
      const t = (b.innerText || '').trim().toLowerCase();
      return t === 'next' && !b.disabled;
    });
  }

  async function paginateAndFind(street) {
    for (let page = 1; page <= MAX_PAGES_TO_SCAN; page++) {
      // Wait for results to render
      await new Promise(r => setTimeout(r, page === 1 ? SEARCH_RENDER_WAIT_MS : PAGE_RENDER_WAIT_MS));
      const card = findCardByStreet(street);
      if (card) {
        highlightAndScroll(card, street);
        return true;
      }
      // Not on this page — try next page if available
      const nextBtn = findNextPageButton();
      if (!nextBtn) {
        showBanner('⚠️ ' + street + ' not found in any of ' + page + ' page(s) of results. Try sorting differently or scroll BBC manually.', '#7d4d1a');
        return false;
      }
      showBanner('🔄 Page ' + page + ' — not found, paginating…', '#1e2c44');
      nextBtn.click();
    }
    showBanner('⚠️ ' + street + ' not found after ' + MAX_PAGES_TO_SCAN + ' pages. Property may be in a different BBC search slice.', '#7d4d1a');
    return false;
  }

  async function runAutoSearch() {
    const raw = getAutoQuery();
    if (!raw) return;

    // Hash format: "City, State" OR "City, State|street:51557 Forster Ln"
    let q = raw, street = '';
    const pipeIdx = raw.indexOf('|street:');
    if (pipeIdx > -1) {
      q = raw.slice(0, pipeIdx);
      street = raw.slice(pipeIdx + '|street:'.length);
    }

    // Poll until search input + button exist
    const start = Date.now();
    while (Date.now() - start < POLL_TIMEOUT_MS) {
      const input = findSearchInput();
      const btn = findSearchButton();
      if (input && btn) {
        setReactInputValue(input, q);
        await new Promise(r => setTimeout(r, 200));
        // Set sort + page size BEFORE clicking search so results come back maxed + DOM-desc
        setSortDomDesc();
        setPageSize();
        await new Promise(r => setTimeout(r, 150));
        btn.click();
        showBanner('🔍 Auto-searched: ' + q + (street ? ' · seeking ' + street : ''), '#1a4d2e');
        history.replaceState(null, '', location.pathname + location.search);
        if (street) {
          // Sort + page-size dropdowns may need a second nudge after BBC re-renders
          setTimeout(() => { setSortDomDesc(); setPageSize(); }, 800);
          paginateAndFind(street);
        }
        return;
      }
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    }
    showBanner('⚠️ Auto-search: search box not found. Paste manually: ' + q, '#7d4d1a');
  }

  runAutoSearch();
  window.addEventListener('hashchange', runAutoSearch);
})();
