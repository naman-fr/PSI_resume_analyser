import { useEffect, useRef, useState } from 'react';

// Central API URL
const API_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com/api';

export function useProctoring(sessionId) {
  const warningsCount = useRef(0);
  const [localAlerts, setLocalAlerts] = useState([]);

  const addAlert = (alertMsg) => {
    setLocalAlerts(prev => {
      if (!prev.includes(alertMsg)) return [...prev, alertMsg];
      return prev;
    });
    // Remove alert after 5 seconds
    setTimeout(() => {
      setLocalAlerts(prev => prev.filter(a => a !== alertMsg));
    }, 5000);
  };

  useEffect(() => {
    if (!sessionId) return;

    const logEvent = async (eventType, details = {}) => {
      try {
        await fetch(`${API_URL}/interview/proctor`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            event_type: eventType,
            timestamp: new Date().toISOString(),
            details: details
          })
        });
      } catch (e) {
        console.error("Failed to log proctor event", e);
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        warningsCount.current += 1;
        addAlert("TAB SWITCHED / BACKGROUND DETECTED");
        logEvent('tab_switched', { warning_count: warningsCount.current });
      }
    };

    const handleBlur = () => {
      warningsCount.current += 1;
      addAlert("FOCUS LOST");
      logEvent('window_focus_lost', { warning_count: warningsCount.current });
    };

    const handlePaste = (e) => {
      const pastedText = (e.clipboardData || window.clipboardData).getData('text');
      addAlert("CLIPBOARD PASTE DETECTED");
      logEvent('clipboard_paste', { length: pastedText.length });
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleBlur);
    document.addEventListener("paste", handlePaste);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleBlur);
      document.removeEventListener("paste", handlePaste);
    };
  }, [sessionId]);

  return { warningsCount: warningsCount.current, localAlerts };
}
