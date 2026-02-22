// popup.js — Shows current job status from storage (set by background.js)

const statusText = document.getElementById('statusText');
const dot = document.getElementById('dot');

function refresh(data) {
  const msg = data.lastStatus || 'Idle — waiting for verification jobs.';
  const age = data.lastStatusTime ? Date.now() - data.lastStatusTime : Infinity;
  const isRecent = age < 30000;

  statusText.textContent = msg;

  if (!isRecent || msg.startsWith('Idle')) {
    dot.className = 'dot';
  } else if (msg.startsWith('Job') && msg.includes('done')) {
    dot.className = 'dot done';
  } else {
    dot.className = 'dot active';
  }
}

// Load immediately
chrome.storage.local.get(['lastStatus', 'lastStatusTime'], refresh);

// Keep polling while popup is open
setInterval(() => {
  chrome.storage.local.get(['lastStatus', 'lastStatusTime'], refresh);
}, 1500);
