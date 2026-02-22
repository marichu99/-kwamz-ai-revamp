// content-dci.js — Content script for https://dci.ecitizen.go.ke/verify
// Fills the police clearance verification form and reads the result.

(function () {
  'use strict';

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

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

  function readDciResult() {
    try {
      // Look for the result heading inside the result table
      const heading = document.querySelector('table h1');
      if (heading) return heading.innerText.trim();

      // Fallback: look for any visible success/failure text
      const alert = document.querySelector('.alert');
      if (alert) return alert.innerText.trim();

      return 'Result not found';
    } catch (err) {
      return `Error reading result: ${err.message}`;
    }
  }

  async function run() {
    try {
      // Signal background we're ready and get job data
      const init = await sendMessage({ type: 'DCI_READY' });
      if (!init || init.ignored || init.error) {
        console.warn('[DCI] Not initialised by background:', init);
        return;
      }

      // Wait for the service dropdown
      await waitForElement('#q_service_id', 10000);

      // Select "Police Clearance" (option value 1)
      const dropdown = document.querySelector('#q_service_id');
      dropdown.value = '1';
      dropdown.dispatchEvent(new Event('change', { bubbles: true }));

      await sleep(500);

      // Fill reference number (police clearance number)
      const refInput = await waitForElement('#q_ref_number', 5000);
      refInput.value = init.policeClearance;
      refInput.dispatchEvent(new Event('input', { bubbles: true }));

      // Fill security question (ID number)
      const secInput = await waitForElement('#q_security_question', 5000);
      secInput.value = init.idNumber;
      secInput.dispatchEvent(new Event('input', { bubbles: true }));

      // Submit
      const submitBtn = document.querySelector('.btn.btn-primary.btn-sm');
      if (!submitBtn) throw new Error('Submit button not found');
      submitBtn.click();

      // Scroll down a bit so the result is in view (mirrors original Playwright script)
      window.scrollBy(0, 300);

      // Wait for result to appear
      await sleep(5000);

      const result = readDciResult();
      await sendMessage({ type: 'DCI_DONE', result });

    } catch (err) {
      console.error('[DCI] Error:', err.message);
      await sendMessage({ type: 'STEP_ERROR', step: 'DCI', error: err.message });
    }
  }

  if (document.body.dataset.kwamzDciInit) return;
  document.body.dataset.kwamzDciInit = 'true';

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
