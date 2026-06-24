import { useState, useRef, useEffect, useCallback } from 'react';
import { X, Wifi, WifiOff, Maximize2, Minimize2, ChevronUp, Square } from 'lucide-react';
import axios from 'axios';
import config from '../Config';

// Unified input dock — handles both 4-digit captcha and 6-digit OTP in the same spot.
// `mode` is 'captcha' | 'otp'.  The parent controls which is shown by polling /prompt.
// `captchaImage` is an optional base64 PNG of the captcha element (only for captcha mode).
function InputDock({ mode, jobId, captchaImage, onSubmitted }) {
  const len = mode === 'captcha' ? 4 : 6;
  const isCaptcha = mode === 'captcha';

  const [digits, setDigits] = useState(Array(len).fill(''));
  const [state, setState] = useState('idle'); // idle | submitting | ok | error
  const [errMsg, setErrMsg] = useState('');
  const inputRefs = useRef([]);

  // Reset boxes whenever the mode switches (captcha → otp)
  useEffect(() => {
    setDigits(Array(len).fill(''));
    setState('idle');
    setErrMsg('');
    setTimeout(() => inputRefs.current[0]?.focus(), 50);
  }, [mode, len]);

  const reset = useCallback(() => {
    setDigits(Array(len).fill(''));
    setState('idle');
    setErrMsg('');
    inputRefs.current[0]?.focus();
  }, [len]);

  const submit = useCallback(async (value) => {
    setState('submitting');
    try {
      const token = localStorage.getItem('token');
      const url = isCaptcha
        ? `${config.API_URL}/stream/${jobId}/captcha`
        : `${config.API_URL}/stream/${jobId}/otp`;
      const body = isCaptcha ? { captcha: value } : { otp: value };
      await axios.post(url, body, { headers: { Authorization: `Bearer ${token}` } });
      setState('ok');
      setTimeout(() => onSubmitted?.(), 800);
    } catch (err) {
      setErrMsg(err?.response?.data?.error || 'Submission failed');
      setState('error');
      setTimeout(reset, 2500);
    }
  }, [isCaptcha, jobId, onSubmitted, reset]);

  const handleChange = (idx, val) => {
    if (!/^\d?$/.test(val)) return;
    const next = [...digits];
    next[idx] = val;
    setDigits(next);
    if (val && idx < len - 1) inputRefs.current[idx + 1]?.focus();
    if (next.every(d => d !== '')) submit(next.join(''));
  };

  const handleKeyDown = (idx, e) => {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) inputRefs.current[idx - 1]?.focus();
    if (e.key === 'ArrowLeft' && idx > 0) inputRefs.current[idx - 1]?.focus();
    if (e.key === 'ArrowRight' && idx < len - 1) inputRefs.current[idx + 1]?.focus();
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, len);
    if (!pasted) return;
    const next = Array(len).fill('');
    [...pasted].forEach((ch, i) => { next[i] = ch; });
    setDigits(next);
    inputRefs.current[Math.min(pasted.length, len - 1)]?.focus();
    if (pasted.length === len) submit(pasted);
  };

  const statusText =
    state === 'ok'         ? (isCaptcha ? 'Captcha submitted ✓' : 'OTP sent ✓') :
    state === 'error'      ? errMsg :
    state === 'submitting' ? 'Submitting…' :
    isCaptcha              ? 'Type the 4-digit captcha shown on screen' :
                             'Enter the OTP sent to your phone';

  const statusColor =
    state === 'ok'    ? (isCaptcha ? 'text-amber-400'   : 'text-emerald-400') :
    state === 'error' ? 'text-red-400' :
    state === 'submitting' ? 'text-slate-400' :
                        'text-slate-400';

  return (
    <div
      className={`flex flex-col items-center gap-2 py-3 px-4 bg-slate-900 border-t transition-opacity duration-500 ${
        isCaptcha ? 'border-amber-700/40' : 'border-slate-800'
      }`}
      style={{ opacity: state === 'ok' ? 0 : 1 }}
    >
      {isCaptcha && (
        <span className="text-xs font-semibold uppercase tracking-widest text-amber-500">
          Captcha Required
        </span>
      )}
      {isCaptcha && captchaImage && (
        <img
          src={`data:image/png;base64,${captchaImage}`}
          alt="captcha"
          className="h-12 rounded border border-amber-700/50 bg-white px-2 py-1"
          style={{ imageRendering: 'crisp-edges' }}
        />
      )}
      <p className={`text-xs font-mono ${statusColor} transition-colors`}>{statusText}</p>
      <div className="flex items-center gap-2">
        {Array.from({ length: len }).map((_, i) => (
          <input
            key={`${mode}-${i}`}
            ref={el => { inputRefs.current[i] = el; }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digits[i]}
            disabled={state === 'submitting' || state === 'ok'}
            onChange={e => handleChange(i, e.target.value)}
            onKeyDown={e => handleKeyDown(i, e)}
            onPaste={handlePaste}
            className={`
              w-10 h-12 text-center text-lg font-mono font-bold rounded-lg border
              bg-slate-800 text-white outline-none transition-all duration-150
              disabled:opacity-40 disabled:cursor-not-allowed
              ${digits[i]
                ? (isCaptcha ? 'border-amber-500' : 'border-emerald-500')
                : 'border-slate-600'
              }
              ${isCaptcha
                ? 'caret-amber-400 focus:border-amber-400 focus:ring-1 focus:ring-amber-400/40'
                : 'caret-emerald-400 focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400/40'
              }
            `}
          />
        ))}
      </div>
    </div>
  );
}

function LoadingOverlay({ status }) {
  if (status === 'live') return null;

  const isError = status === 'error';

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-5 bg-slate-950/95 z-10">
      {isError ? (
        <>
          <WifiOff className="w-14 h-14 text-slate-600 opacity-60" />
          <div className="text-center">
            <p className="text-slate-400 text-sm font-medium">Stream unavailable</p>
            <p className="text-slate-600 text-xs mt-1">
              The scraping job may have ended or hasn't started yet.
            </p>
          </div>
        </>
      ) : (
        <>
          {/* Outer ring */}
          <div className="relative w-16 h-16">
            <div className="absolute inset-0 rounded-full border-2 border-slate-700" />
            <div className="absolute inset-0 rounded-full border-2 border-t-emerald-400 border-r-emerald-400/40 border-b-transparent border-l-transparent animate-spin" />
            <div className="absolute inset-2 rounded-full border border-t-emerald-500/50 border-r-transparent border-b-transparent border-l-transparent animate-spin" style={{ animationDuration: '1.5s', animationDirection: 'reverse' }} />
          </div>
          <div className="text-center">
            <p className="text-slate-300 text-sm font-medium">
              {status === 'waiting' ? 'Starting scraping job…' : 'Connecting to browser…'}
            </p>
            <p className="text-slate-600 text-xs mt-1">
              {status === 'waiting' ? 'Launching Playwright browser' : 'Waiting for first frame'}
            </p>
          </div>
          {/* Pulsing dots */}
          <div className="flex items-center gap-1.5">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"
                style={{ animationDelay: `${i * 200}ms` }}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function LiveScrapeFeed({ jobId, shortCode, isOpen, onClose, onStreamEnd, onKill }) {
  const [status, setStatus] = useState('waiting');
  const [minimized, setMinimized] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [killing, setKilling] = useState(false);
  // prompt: 'captcha' | 'otp' | null — driven by polling GET /stream/:id/prompt
  const [prompt, setPrompt] = useState(null);
  const [captchaImage, setCaptchaImage] = useState(null); // base64 PNG from backend
  // Hide the dock right after the user submits; re-show if the prompt changes again
  const [dockHidden, setDockHidden] = useState(false);
  const prevPromptRef = useRef(null);
  const imgRef = useRef(null);
  const containerRef = useRef(null);

  const streamUrl = jobId ? `${config.API_URL}/stream/${jobId}` : null;

  useEffect(() => {
    if (!isOpen) return;
    setStatus(jobId ? 'connecting' : 'waiting');
  }, [isOpen, jobId]);

  // Reset minimized state when re-opened
  useEffect(() => {
    if (isOpen) setMinimized(false);
  }, [isOpen]);

  // Reset input state when a new job starts
  useEffect(() => {
    setKilling(false);
    setPrompt(null);
    setCaptchaImage(null);
    setDockHidden(false);
    prevPromptRef.current = null;
  }, [jobId]);

  // Poll backend for which input the user should fill in right now
  useEffect(() => {
    if (!jobId || !isOpen) return;
    const poll = async () => {
      try {
        const token = localStorage.getItem('token');
        const { data } = await axios.get(`${config.API_URL}/stream/${jobId}/prompt`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const next = data.prompt ?? null;
        if (next !== prevPromptRef.current) {
          prevPromptRef.current = next;
          setPrompt(next);
          setCaptchaImage(data.captcha_b64 ?? null);
          if (next) setDockHidden(false); // a new prompt appeared — always show dock
        }
      } catch {
        // network hiccup — just skip this tick
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, [jobId, isOpen]);

  const handleLoad = () => setStatus('live');
  const handleError = () => {
    setStatus('error');
    onStreamEnd?.();
  };

  const handleKill = async () => {
    setKilling(true);
    await onKill?.();
  };

  const toggleFullscreen = () => {
    if (!fullscreen) {
      containerRef.current?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
    setFullscreen(f => !f);
  };

  if (!isOpen) return null;

  // ── Minimized: floating pill (stream stays connected in hidden <img>) ──────
  if (minimized) {
    return (
      <div className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 px-3.5 py-2.5 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl">
        <span className={`w-2 h-2 rounded-full shrink-0 ${
          status === 'live'    ? 'bg-green-400 animate-pulse' :
          status === 'error'   ? 'bg-amber-500' :
                                 'bg-slate-500 animate-pulse'
        }`} />
        <span className="text-slate-200 text-xs font-mono font-semibold">{shortCode}</span>
        <span className="text-slate-500 text-xs">
          {status === 'live' ? 'LIVE' : status === 'error' ? 'offline' : 'starting…'}
        </span>
        <button
          onClick={() => setMinimized(false)}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          title="Restore feed"
        >
          <ChevronUp className="w-3.5 h-3.5" />
        </button>
        {onKill && (
          <button
            onClick={handleKill}
            disabled={killing}
            className="p-1 rounded-lg text-red-400 hover:text-red-300 hover:bg-slate-700 transition-colors disabled:opacity-40"
            title="Stop scraper"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
          </button>
        )}
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-700 transition-colors"
          title="Close stream"
        >
          <X className="w-3.5 h-3.5" />
        </button>

        {/* Keep <img> mounted so the MJPEG connection stays alive */}
        {streamUrl && (
          <img
            ref={imgRef}
            src={streamUrl}
            alt=""
            className="hidden"
            onLoad={handleLoad}
            onError={handleError}
          />
        )}
      </div>
    );
  }

  // ── Full modal ───────────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
      <div
        ref={containerRef}
        className="relative bg-slate-950 rounded-2xl shadow-2xl overflow-hidden flex flex-col w-full max-w-5xl"
        style={{ maxHeight: '90vh' }}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  status === 'live'  ? 'bg-red-500 animate-pulse' :
                  status === 'error' ? 'bg-amber-500' :
                                       'bg-slate-500 animate-pulse'
                }`}
              />
              <span className="text-xs font-bold uppercase tracking-widest text-slate-300">
                {status === 'live'       ? 'Live'         :
                 status === 'error'      ? 'Offline'      :
                 status === 'waiting'    ? 'Starting…'    :
                                          'Connecting…'}
              </span>
            </span>

            <span className="text-slate-500 text-xs">|</span>

            <span className="text-slate-300 text-sm font-medium">
              Scraping <span className="text-emerald-400 font-mono">{shortCode}</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            {status === 'live'
              ? <Wifi className="w-4 h-4 text-emerald-400" />
              : <WifiOff className="w-4 h-4 text-slate-500" />
            }

            {/* Stop scraper */}
            {onKill && (
              <button
                onClick={handleKill}
                disabled={killing}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-red-400 border border-red-500/30 hover:bg-red-500/10 hover:border-red-500/60 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                title="Stop scraper"
              >
                <Square className="w-3 h-3 fill-current" />
                {killing ? 'Stopping…' : 'Stop'}
              </button>
            )}

            <button
              onClick={() => setMinimized(true)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
              title="Minimize"
            >
              <Minimize2 className="w-4 h-4" />
            </button>

            <button
              onClick={toggleFullscreen}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
              title="Toggle fullscreen"
            >
              <Maximize2 className="w-4 h-4" />
            </button>

            <button
              onClick={() => setMinimized(true)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
              title="Minimise to tray"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ── Video feed ── */}
        <div
          className="relative flex-1 bg-black flex items-center justify-center overflow-hidden"
          style={{ minHeight: 400 }}
        >
          {streamUrl && (
            <img
              ref={imgRef}
              src={streamUrl}
              alt="Live scrape feed"
              className={`max-w-full max-h-full object-contain transition-opacity duration-500 ${
                status === 'live' ? 'opacity-100' : 'opacity-0'
              }`}
              onLoad={handleLoad}
              onError={handleError}
            />
          )}

          <LoadingOverlay status={status} />
        </div>

        {/* ── Input dock (captcha or OTP, same spot) ── */}
        {jobId && prompt && !dockHidden && (
          <InputDock
            mode={prompt}
            jobId={jobId}
            captchaImage={captchaImage}
            onSubmitted={() => setDockHidden(true)}
          />
        )}

        {/* ── Footer ── */}
        <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-t border-slate-800 shrink-0">
          <span className="text-slate-600 text-xs font-mono">job: {jobId ?? '—'}</span>
          <span className="text-slate-600 text-xs">CDP Screencast · MJPEG</span>
        </div>
      </div>
    </div>
  );
}

export default LiveScrapeFeed;
