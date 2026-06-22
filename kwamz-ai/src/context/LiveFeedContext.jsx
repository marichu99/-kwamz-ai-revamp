import { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';
import config from '../Config';

const STORAGE_KEY = 'kwamz_live_feed';
const LiveFeedContext = createContext(null);

function readStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function LiveFeedProvider({ children }) {
  const saved = readStorage();
  const [jobId, setJobId] = useState(saved?.jobId ?? null);
  const [shortCode, setShortCode] = useState(saved?.shortCode ?? null);
  const [isOpen, setIsOpen] = useState(saved != null);
  // Map<shortCode, jobId> — shared so any component can read live status.
  // Seeded from localStorage so the "Live" badge survives refresh/re-login.
  const [activeStreams, setActiveStreams] = useState(() => {
    const m = new Map();
    if (saved?.shortCode) m.set(saved.shortCode, saved.jobId ?? null);
    return m;
  });

  const startFeed = useCallback((newJobId, newShortCode) => {
    setJobId(newJobId);
    setShortCode(newShortCode);
    setIsOpen(true);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ jobId: newJobId, shortCode: newShortCode }));
    if (newShortCode) {
      setActiveStreams(prev => new Map(prev).set(newShortCode, newJobId));
    }
  }, []);

  const closeFeed = useCallback((targetShortCode) => {
    // targetShortCode lets callers remove a specific entry; falls back to current
    const sc = targetShortCode ?? shortCode;
    setIsOpen(false);
    setJobId(null);
    setShortCode(null);
    localStorage.removeItem(STORAGE_KEY);
    if (sc) {
      setActiveStreams(prev => {
        const m = new Map(prev);
        m.delete(sc);
        return m;
      });
    }
  }, [shortCode]);

  const killFeed = useCallback(async () => {
    if (jobId) {
      try {
        const token = localStorage.getItem('token');
        await axios.delete(`${config.API_URL}/stream/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // best-effort — clean up frontend regardless
      }
    }
    closeFeed();
  }, [jobId, closeFeed]);

  return (
    <LiveFeedContext.Provider value={{ jobId, shortCode, isOpen, activeStreams, startFeed, closeFeed, killFeed }}>
      {children}
    </LiveFeedContext.Provider>
  );
}

export function useLiveFeed() {
  return useContext(LiveFeedContext);
}
