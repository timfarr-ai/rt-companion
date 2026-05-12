// ==UserScript==
// @name         HMHW Offer Oven — Prefill from briefing
// @namespace    https://github.com/timfarr-ai/rt-companion
// @version      1.0
// @description  Auto-fills the HMHW Offer Oven calculator with deal data passed via #prefill={json} hash. Used by the rt-companion briefing to one-tap verify deal numbers.
// @author       Tim Farr
// @match        https://www.hmhw.group/tools/offer-oven*
// @match        https://hmhw.group/tools/offer-oven*
// @grant        none
// @run-at       document-idle
// @updateURL    https://raw.githubusercontent.com/timfarr-ai/rt-companion/main/scripts/offer-oven-prefill.user.js
// @downloadURL  https://raw.githubusercontent.com/timfarr-ai/rt-companion/main/scripts/offer-oven-prefill.user.js
// ==/UserScript==

(function () {
  'use strict';

  const HASH_PREFIX = '#prefill=';
  const POLL_INTERVAL_MS = 250;
  const POLL_TIMEOUT_MS = 12000;

  // Map briefing field names → label patterns the userscript will match against
  // (case-insensitive, substring-of input's nearby label text or placeholder)
  const FIELD_MAP = {
    price:      ['Purchase Price', 'purchase price'],
    down:       ['Down Payment', 'down payment'],
    rate:       ['Interest Rate', 'interest rate'],   // Carryback rate (first match)
    term:       ['Term (Years)', 'amortization', 'Term'],
    balloon:    ['Balloon', 'balloon scenarios', 'balloon years'],
    rent:       ['Rental Revenue', 'annual rent', 'rent (annual)'],
    tax:        ['Property Tax', 'property tax (annual)', 'taxes'],
    insurance:  ['Insurance', 'insurance (annual)'],
    hoa:        ['HOA', 'hoa (annual)'],
    other:      ['Other (Annual)', 'other expense'],
    assignment: ['Assignment Fee', 'assignment fees'],
    closing:    ['Closing Cost', 'closing costs'],
  };

  function getPrefillData() {
    const h = location.hash || '';
    if (!h.startsWith(HASH_PREFIX)) return null;
    try {
      const raw = decodeURIComponent(h.slice(HASH_PREFIX.length));
      return JSON.parse(raw);
    } catch (e) {
      console.warn('[Offer Oven Prefill] Invalid JSON in hash:', e);
      return null;
    }
  }

  function setReactValue(input, value) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, String(value));
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function getNearbyLabel(input) {
    // Try: associated <label for=...>, parent .label, previous sibling, ancestor with text
    if (input.id) {
      const lbl = document.querySelector(`label[for="${input.id}"]`);
      if (lbl) return lbl.innerText.trim();
    }
    // Walk up to 5 ancestors looking for any short text node before this input
    let el = input;
    for (let i = 0; i < 5 && el; i++) {
      const parent = el.parentElement;
      if (!parent) break;
      // Look for previous sibling text/label
      let prev = el.previousElementSibling;
      while (prev) {
        const t = (prev.innerText || '').trim();
        if (t && t.length < 80) return t;
        prev = prev.previousElementSibling;
      }
      el = parent;
    }
    return '';
  }

  function findFieldForKey(key, allInputs) {
    const patterns = FIELD_MAP[key] || [];
    for (const pat of patterns) {
      const patLow = pat.toLowerCase();
      for (const input of allInputs) {
        const placeholder = (input.placeholder || '').toLowerCase();
        const label = (getNearbyLabel(input) || '').toLowerCase();
        if (placeholder.includes(patLow) || label.includes(patLow)) {
          return input;
        }
      }
    }
    return null;
  }

  function showBanner(msg, color) {
    const existing = document.getElementById('rt-prefill-banner');
    if (existing) existing.remove();
    const div = document.createElement('div');
    div.id = 'rt-prefill-banner';
    div.style.cssText =
      'position:fixed;top:12px;right:12px;z-index:99999;padding:8px 14px;' +
      'background:' + (color || '#1e2c44') + ';color:#fff;border-radius:8px;' +
      'font:13px -apple-system,BlinkMacSystemFont,sans-serif;box-shadow:0 4px 12px rgba(0,0,0,0.4);max-width:340px;';
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 5000);
  }

  function runPrefill() {
    const data = getPrefillData();
    if (!data) return;
    const startTime = Date.now();

    const tryFill = () => {
      // Look for the first "Purchase Price" input as a readiness signal
      const allInputs = Array.from(document.querySelectorAll('input[type="text"],input[type="number"],input:not([type])'));
      if (allInputs.length === 0) return false;

      // Need at least Purchase Price field present
      const priceInput = findFieldForKey('price', allInputs);
      if (!priceInput) return false;

      // Fill each known field
      const filled = [];
      const missed = [];
      Object.keys(FIELD_MAP).forEach(key => {
        if (data[key] === undefined || data[key] === null) return;
        const input = findFieldForKey(key, allInputs);
        if (input) {
          setReactValue(input, data[key]);
          filled.push(key);
        } else {
          missed.push(key);
        }
      });

      if (filled.length === 0) return false;
      const msg = `✓ Offer Oven prefilled: ${filled.join(', ')}` + (missed.length ? `  (could not match: ${missed.join(', ')})` : '');
      showBanner(msg, '#1a4d2e');
      // Clear hash so refresh doesn't re-trigger
      history.replaceState(null, '', location.pathname + location.search);
      return true;
    };

    if (tryFill()) return;
    const poll = setInterval(() => {
      if (tryFill() || Date.now() - startTime > POLL_TIMEOUT_MS) {
        clearInterval(poll);
        if (Date.now() - startTime > POLL_TIMEOUT_MS) {
          showBanner('⚠️ Offer Oven prefill: form not found. Open "Take the Wheel Mode" first.', '#7d4d1a');
        }
      }
    }, POLL_INTERVAL_MS);
  }

  runPrefill();
  window.addEventListener('hashchange', runPrefill);
})();
