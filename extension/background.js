// background.js — Service Worker
// Polls backend for pending verification jobs, orchestrates tab opening and result posting.
//
// Authentication: uses a static shared secret (EXTENSION_SECRET) set on the backend .env.
// Set the same value below — users just install the extension, no login needed.

const BACKEND_URL = 'https://kwamz-ai.org';   // ← change if self-hosting
const EXTENSION_SECRET = '9fff7a4c-b313-4f87-bddd-9310a666de87'; // ← must match server .env

let activeJob = null;
let kraTabId = null;
let dciTabId = null;
let kraResult = null;
let dciResult = null;
let kraStarted = false;  // guard: prevent re-init if KRA page reloads
let dciStarted = false;  // guard: prevent re-init if DCI page reloads

// ── Keep-alive via alarms ─────────────────────────────────────────────────────
// Chrome MV3 kills service workers after ~30s of inactivity.
// chrome.alarms wakes the worker every 25 seconds to keep polling alive.

chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 }); // every ~25 seconds

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'keepAlive') {
    pollForJob();
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const url = BACKEND_URL.replace(/\/$/, '') + path;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Extension-Secret': EXTENSION_SECRET,
      ...(options.headers || {})
    }
  });
  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.error || `HTTP ${res.status}`);
  }
  return json;
}

async function updateStatus(msg) {
  await chrome.storage.local.set({ lastStatus: msg, lastStatusTime: Date.now() });
  console.log('[Kwamz]', msg);
}

// ── Polling ───────────────────────────────────────────────────────────────────

async function pollForJob() {
  if (activeJob) return; // already handling a job

  try {
    const data = await apiFetch('/api/verification/pending');
    if (data.job) {
      activeJob = data.job;
      kraResult = null;
      dciResult = null;
      kraStarted = false;
      dciStarted = false;
      console.log('[Kwamz] Picked up job:', activeJob.job_id);
      await updateStatus(`Processing job ${activeJob.job_id}...`);
      await startKraVerification();
    }
  } catch (err) {
    console.warn('[Kwamz] Poll error:', err.message);
  }
}

// ── KRA Verification ──────────────────────────────────────────────────────────

async function startKraVerification() {
  await updateStatus('Opening KRA portal...');
  const tab = await chrome.tabs.create({
    url: 'https://itax.kra.go.ke/KRA-Portal/pinChecker.htm',
    active: false
  });
  kraTabId = tab.id;
}

// ── DCI Verification ──────────────────────────────────────────────────────────

async function startDciVerification() {
  await updateStatus('Opening DCI portal...');
  const tab = await chrome.tabs.create({
    url: 'https://dci.ecitizen.go.ke/verify',
    active: false
  });
  dciTabId = tab.id;
}

// ── Post Final Result ─────────────────────────────────────────────────────────

async function postFinalResult() {
  if (!activeJob) return;

  const kraOk = kraResult && kraResult.includes('Active');
  const dciOk = dciResult && dciResult.toUpperCase().includes('VALID');

  let status = 'completed';
  if (!kraOk && !dciOk) status = 'failed';

  try {
    await apiFetch(`/api/verification/result/${activeJob.job_id}`, {
      method: 'POST',
      body: JSON.stringify({
        kra_result: kraResult || 'Unknown',
        police_result: dciResult || 'Unknown',
        status
      })
    });
    await updateStatus(`Job ${activeJob.job_id} done — KRA: ${kraResult}, DCI: ${dciResult}`);
  } catch (err) {
    console.error('[Kwamz] Failed to post result:', err.message);
    await updateStatus(`Failed to post result: ${err.message}`);
  } finally {
    activeJob = null;
    kraTabId = null;
    dciTabId = null;
    kraStarted = false;
    dciStarted = false;
  }
}

function resetJob() {
  activeJob = null;
  kraTabId = null;
  dciTabId = null;
  kraStarted = false;
  dciStarted = false;
}

// ── Message Handling ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  handleMessage(msg, sender).then(sendResponse).catch((err) => {
    sendResponse({ error: err.message });
  });
  return true; // keep channel open for async response
});

async function handleMessage(msg, sender) {
  switch (msg.type) {

    case 'KRA_READY': {
      // Ignore if no active job, wrong tab, or KRA already started for this job
      if (!activeJob || sender.tab?.id !== kraTabId || kraStarted) {
        return { ignored: true };
      }
      kraStarted = true; // mark so any page reload doesn't re-trigger
      return { type: 'KRA_START', kraPin: activeJob.kra_pin };
    }

    case 'KRA_CAPTCHA': {
      if (!activeJob) return { error: 'No active job' };
      const data = await apiFetch('/api/verification/solve-captcha', {
        method: 'POST',
        body: JSON.stringify({ image: msg.imageBase64 })
      });
      return { type: 'CAPTCHA_ANSWER', answer: data.answer };
    }

    case 'KRA_DONE': {
      kraResult = msg.result;
      await updateStatus(`KRA done: ${kraResult}. Starting DCI...`);
      if (kraTabId) {
        try { await chrome.tabs.remove(kraTabId); } catch (_) {}
        kraTabId = null;
      }
      await startDciVerification();
      return { ok: true };
    }

    case 'DCI_READY': {
      // Ignore if no active job, wrong tab, or DCI already started for this job
      if (!activeJob || sender.tab?.id !== dciTabId || dciStarted) {
        return { ignored: true };
      }
      dciStarted = true;
      return {
        type: 'DCI_START',
        policeClearance: activeJob.police_clearance,
        idNumber: activeJob.id_number
      };
    }

    case 'DCI_DONE': {
      dciResult = msg.result;
      await updateStatus(`DCI done: ${dciResult}. Posting result...`);
      if (dciTabId) {
        try { await chrome.tabs.remove(dciTabId); } catch (_) {}
        dciTabId = null;
      }
      await postFinalResult();
      return { ok: true };
    }

    case 'STEP_ERROR': {
      const step = msg.step || 'unknown';
      await updateStatus(`Error in ${step}: ${msg.error}`);
      if (activeJob) {
        try {
          await apiFetch(`/api/verification/result/${activeJob.job_id}`, {
            method: 'POST',
            body: JSON.stringify({
              kra_result: kraResult || 'Error',
              police_result: dciResult || 'Error',
              status: 'failed'
            })
          });
        } catch (_) {}
        resetJob();
      }
      return { ok: true };
    }

    default:
      return { error: 'Unknown message type' };
  }
}

// ── Startup ───────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
  pollForJob();
});

chrome.runtime.onStartup.addListener(() => {
  pollForJob();
});

// Poll immediately when service worker wakes
pollForJob();
