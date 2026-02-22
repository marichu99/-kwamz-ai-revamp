// content-kra.js — Content script for https://itax.kra.go.ke/KRA-Portal/pinChecker.htm
// Fills the KRA PIN checker form, screenshots the CAPTCHA via Canvas API,
// sends it to the background for solving, fills the answer, submits, and reads result.

(function () {
  'use strict';

  let jobData = null;

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  // ── Canvas CAPTCHA capture ───────────────────────────────────────────────────

  async function captureImageAsBase64(imgElement) {
    return new Promise((resolve, reject) => {
      const canvas = document.createElement('canvas');
      canvas.width = imgElement.naturalWidth || imgElement.width;
      canvas.height = imgElement.naturalHeight || imgElement.height;
      const ctx = canvas.getContext('2d');
      try {
        ctx.drawImage(imgElement, 0, 0);
        const dataUrl = canvas.toDataURL('image/png');
        // Strip the data URL prefix to get raw base64
        resolve(dataUrl.replace(/^data:image\/png;base64,/, ''));
      } catch (err) {
        reject(new Error(`Canvas draw failed: ${err.message}`));
      }
    });
  }

  // ── Communication with background ────────────────────────────────────────────

  function sendMessage(msg) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(msg, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else {
          resolve(response);
        }
      });
    });
  }

  // ── Main verification flow ────────────────────────────────────────────────────

  async function run() {
    try {
      // Signal background we're ready and get job data
      const init = await sendMessage({ type: 'KRA_READY' });
      if (!init || init.ignored || init.error) {
        console.warn('[KRA] Not initialised by background:', init);
        return;
      }
      jobData = init;

      // Wait for PIN input to be available
      await waitForElement('#vo\\.pinNo', 10000);

      // Fill PIN
      const pinInput = document.querySelector('#vo\\.pinNo');
      pinInput.value = jobData.kraPin;
      pinInput.dispatchEvent(new Event('input', { bubbles: true }));
      pinInput.dispatchEvent(new Event('change', { bubbles: true }));

      // Wait for CAPTCHA image
      const captchaImg = await waitForElement('#captcha_img', 10000);

      // Give the image a moment to render fully
      await sleep(1000);

      // Capture CAPTCHA
      const imageBase64 = await captureImageAsBase64(captchaImg);

      // Ask background to solve
      const solved = await sendMessage({ type: 'KRA_CAPTCHA', imageBase64 });
      if (!solved || solved.error) {
        throw new Error(`CAPTCHA solve failed: ${solved?.error}`);
      }

      // Fill CAPTCHA answer
      const captchaInput = document.querySelector('#captcahText');
      captchaInput.value = solved.answer;
      captchaInput.dispatchEvent(new Event('input', { bubbles: true }));

      // Submit
      const submitBtn = document.querySelector('#consult');
      submitBtn.click();

      // Wait for results table
      await sleep(3000);
      const result = readKraResult();

      // Send result to background
      await sendMessage({ type: 'KRA_DONE', result });

    } catch (err) {
      console.error('[KRA] Error:', err.message);
      await sendMessage({ type: 'STEP_ERROR', step: 'KRA', error: err.message });
    }
  }

  // ── Result reader ─────────────────────────────────────────────────────────────

  function readKraResult() {
    try {
      const tables = document.querySelectorAll('table.tab3.whitepapartdBig');
      const targetTable = tables[1] || tables[0];
      if (!targetTable) return 'No result table found';

      const rows = targetTable.querySelectorAll('tr');
      for (const row of rows) {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 2 && cells[0].innerText.trim() === 'PIN Status') {
          return cells[1].innerText.trim();
        }
      }
      return 'PIN Status not found';
    } catch (err) {
      return `Error reading result: ${err.message}`;
    }
  }

  // ── Utility ───────────────────────────────────────────────────────────────────

  function waitForElement(selector, timeout = 10000) {
    return new Promise((resolve, reject) => {
      const el = document.querySelector(selector);
      if (el) return resolve(el);

      const observer = new MutationObserver(() => {
        const found = document.querySelector(selector);
        if (found) {
          observer.disconnect();
          resolve(found);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Timeout waiting for ${selector}`));
      }, timeout);
    });
  }

  // ── Entry point ───────────────────────────────────────────────────────────────
  // Guard against running twice on the same page (e.g. after form submission
  // triggers a partial reload or history navigation within the same tab).

  if (document.body.dataset.kwamzKraInit) return;
  document.body.dataset.kwamzKraInit = 'true';

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
