import { useState, useRef, useEffect } from 'react';
import { X, Wifi, WifiOff, Maximize2, Minimize2, ChevronUp } from 'lucide-react';
import config from '../Config';

function LiveScrapeFeed({ jobId, shortCode, isOpen, onClose, onStreamEnd }) {
  const [status, setStatus] = useState('waiting');
  const [minimized, setMinimized] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const imgRef = useRef(null);
  const containerRef = useRef(null);

  const streamUrl = jobId ? `${config.API_URL}/stream/${jobId}` : null;

  useEffect(() => {
    if (!isOpen) return;
    if (!jobId) {
      setStatus('waiting');
      return;
    }
    setStatus('connecting');
    const timer = setTimeout(() => setStatus(s => s === 'connecting' ? 'live' : s), 2000);
    return () => clearTimeout(timer);
  }, [isOpen, jobId]);

  // Reset minimized state when re-opened
  useEffect(() => {
    if (isOpen) setMinimized(false);
  }, [isOpen]);

  const handleLoad = () => setStatus('live');
  const handleError = () => {
    setStatus('error');
    onStreamEnd?.();
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
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
              title="Close"
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
              className={`max-w-full max-h-full object-contain transition-opacity duration-300 ${
                status === 'live' ? 'opacity-100' : 'opacity-0'
              }`}
              onLoad={handleLoad}
              onError={handleError}
            />
          )}

          {status === 'waiting' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="w-10 h-10 border-2 border-slate-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-400 text-sm">Starting scraping job…</p>
            </div>
          )}

          {status === 'connecting' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
              <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-400 text-sm">Waiting for browser stream…</p>
            </div>
          )}

          {status === 'error' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-500">
              <WifiOff className="w-14 h-14 opacity-40" />
              <p className="text-sm">Stream unavailable</p>
              <p className="text-xs text-slate-600">
                The scraping job may have ended or hasn't started yet.
              </p>
            </div>
          )}
        </div>

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
