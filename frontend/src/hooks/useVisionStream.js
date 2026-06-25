import { useEffect, useRef, useState } from 'react';

const BASE_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com';
const CLEAN_BASE = BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
const WS_URL = CLEAN_BASE.replace(/^http/, 'ws') + '/api/ws/interview/stream';

export function useVisionStream(sessionId, videoRef, isActive) {
  const [visionAlerts, setVisionAlerts] = useState([]);
  const ws = useRef(null);
  const canvasRef = useRef(document.createElement('canvas'));

  useEffect(() => {
    if (!isActive || !sessionId || !videoRef.current) return;

    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      console.log('Vision stream connected');
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'proctor_alert') {
          setVisionAlerts(data.alerts);
        } else if (data.type === 'proctor_status' && data.status === 'clear') {
          setVisionAlerts([]);
        }
      } catch (e) {
        console.error('Vision WebSocket parsing error:', e);
      }
    };

    const captureAndSendFrame = () => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
      if (videoRef.current.readyState !== videoRef.current.HAVE_ENOUGH_DATA) return;

      const canvas = canvasRef.current;
      const video = videoRef.current;
      
      // Scale down to reduce bandwidth (e.g., 320x240)
      canvas.width = 320;
      canvas.height = 240;
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Convert to base64 jpeg
      const frameBase64 = canvas.toDataURL('image/jpeg', 0.5);
      
      ws.current.send(JSON.stringify({
        session_id: sessionId,
        frame: frameBase64
      }));
    };

    // Send a frame every 500ms (2 FPS)
    const intervalId = setInterval(captureAndSendFrame, 500);

    return () => {
      clearInterval(intervalId);
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [sessionId, videoRef, isActive]);

  return { visionAlerts };
}
