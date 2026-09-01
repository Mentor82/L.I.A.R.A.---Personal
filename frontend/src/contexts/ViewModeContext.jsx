import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ViewModeContext = createContext(null);

export function ViewModeProvider({ children }) {
  // 'auto' | 'mobile' | 'desktop'
  const [viewMode, setViewModeState] = useState(() => {
    return localStorage.getItem('liara_view_mode') || 'auto';
  });

  const [windowWidth, setWindowWidth] = useState(() => (typeof window !== 'undefined' ? window.innerWidth : 1200));

  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const setViewMode = useCallback((mode) => {
    setViewModeState(mode);
    localStorage.setItem('liara_view_mode', mode);
  }, []);

  const toggleViewMode = useCallback(() => {
    setViewModeState((prev) => {
      const next = prev === 'desktop' ? 'mobile' : 'desktop';
      localStorage.setItem('liara_view_mode', next);
      return next;
    });
  }, []);

  // Determine actual effective mobile state
  const isMobile = viewMode === 'mobile' || (viewMode === 'auto' && windowWidth < 768);

  const value = {
    viewMode,
    isMobile,
    setViewMode,
    toggleViewMode,
  };

  return (
    <ViewModeContext.Provider value={value}>
      {children}
    </ViewModeContext.Provider>
  );
}

export function useViewMode() {
  const context = useContext(ViewModeContext);
  if (!context) {
    throw new Error('useViewMode must be used within a ViewModeProvider');
  }
  return context;
}
