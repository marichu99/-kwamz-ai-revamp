import { createContext, useContext, useState } from 'react';

const LiveFeedContext = createContext(null);

export function LiveFeedProvider({ children }) {
  const [jobId, setJobId] = useState(null);
  const [shortCode, setShortCode] = useState(null);
  const [isOpen, setIsOpen] = useState(false);

  const startFeed = (newJobId, newShortCode) => {
    setJobId(newJobId);
    setShortCode(newShortCode);
    setIsOpen(true);
  };

  const closeFeed = () => {
    setIsOpen(false);
    setJobId(null);
    setShortCode(null);
  };

  return (
    <LiveFeedContext.Provider value={{ jobId, shortCode, isOpen, startFeed, closeFeed }}>
      {children}
    </LiveFeedContext.Provider>
  );
}

export function useLiveFeed() {
  return useContext(LiveFeedContext);
}
