import React, { useState, useEffect, useRef } from 'react';
import { useProctoring } from '../hooks/useProctoring';
import { useVisionStream } from '../hooks/useVisionStream';
import InterviewReport from './InterviewReport';

const API_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com/api';

import './InterviewRoom.css';

export default function InterviewRoom({ resumeText, jdText, onExit }) {
  const [hasConsent, setHasConsent] = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  
  // Interview State
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [interviewTree, setInterviewTree] = useState([]);
  const [currentTopic, setCurrentTopic] = useState("");
  const [difficulty, setDifficulty] = useState(5);
  const [evaluations, setEvaluations] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [finalReport, setFinalReport] = useState(null);
  
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const videoRef = useRef(null);
  
  // Attach proctoring once consent is given and session starts
  const { localAlerts } = useProctoring(hasConsent ? sessionId : null);
  const { visionAlerts } = useVisionStream(sessionId, videoRef, hasConsent && !isComplete);

  const combinedAlerts = [...(visionAlerts || []), ...(localAlerts || [])];

  useEffect(() => {
    if (cameraStream && videoRef.current) {
      videoRef.current.srcObject = cameraStream;
    }
  }, [cameraStream]);

  const requestPermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setCameraStream(stream);
      setHasConsent(true);
      initInterview();
    } catch (err) {
      alert("Camera and Microphone permissions are required to proceed with the cognitive interview.");
    }
  };

  const initInterview = async () => {
    setIsLoading(true);
    setSessionId(Math.random().toString(36).substring(7)); // Mock session ID
    try {
      const res = await fetch(`${API_URL}/interview/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resumeText || "Sample Resume", jd_text: jdText || "Sample JD" })
      });
      const data = await res.json();
      if (data.success) {
        setMessages(data.messages);
        setInterviewTree(data.interview_tree);
        setCurrentTopic(data.current_topic);
        setDifficulty(data.difficulty_level);
      }
    } catch (e) {
      console.error(e);
      setMessages([{ role: "ai", content: "System error initializing interview. Please try again later." }]);
    }
    setIsLoading(false);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isComplete) return;

    const newMessages = [...messages, { role: "human", content: inputMessage }];
    setMessages(newMessages);
    setInputMessage("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API_URL}/interview/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages,
          interview_tree: interviewTree,
          current_topic: currentTopic,
          difficulty_level: difficulty,
          evaluations: evaluations
        })
      });
      const data = await res.json();
      if (data.success) {
        setMessages(data.messages);
        setDifficulty(data.difficulty_level);
        setEvaluations(data.evaluations);
        setIsComplete(data.is_complete);
        if (data.final_report) {
          setFinalReport(data.final_report);
        }
      }
    } catch (e) {
      console.error(e);
      setMessages([...newMessages, { role: "ai", content: "Connection error. Please repeat." }]);
    }
    setIsLoading(false);
  };

  const handleEnd = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
    }
    onExit();
  };

  if (!hasConsent) {
    return (
      <div className="ir-overlay">
        <div className="ir-overlay-bg"></div>
        <div className="ir-gateway-box">
          <div className="ir-icon-box">
            <i className="fas fa-shield-alt"></i>
          </div>
          <h2 className="ir-gateway-title">Security Clearance Gateway</h2>
          <div className="ir-gateway-warning">
            <p>WARNING: Cognitive Proctoring Initiated</p>
            <ul>
              <li><span></span> Camera & Microphone access is mandatory.</li>
              <li><span></span> Advanced WebRTC Vision verifies identity and gaze tracking.</li>
              <li><span></span> Multiple Person detection is STRICTLY ENFORCED.</li>
              <li><span></span> Tab switching and focus loss will log immediate infractions.</li>
            </ul>
          </div>
          <button 
            onClick={requestPermissions}
            className="ir-btn-primary"
          >
            I CONSENT - INITIALIZE PROCTORING
          </button>
          <button onClick={onExit} className="ir-btn-abort">
            ABORT MISSION
          </button>
        </div>
      </div>
    );
  }

  if (finalReport) {
    return <InterviewReport report={finalReport} transcript={messages} onClose={onExit} />;
  }

  // Extract last AI message for the massive prominent question display
  const lastAiMessage = [...messages].reverse().find(m => m.role === 'ai');
  const displayQuestion = lastAiMessage ? lastAiMessage.content : (isLoading ? "SYNTHESIZING NEXT INQUIRY..." : "INITIALIZING COGNITIVE ENGINE...");

  return (
    <div className="ir-container">
      <div className="ir-overlay-bg"></div>

      {/* Left Panel: Proctoring & Context (50%) */}
      <div className="ir-left-panel">
        
        {/* Camera Feed - P5 TV Screen Style */}
        <div className="ir-video-wrapper">
          <div className="ir-video-inner">
            <video 
              ref={videoRef} 
              autoPlay 
              muted 
              playsInline 
              className="ir-video-element"
            />
            
            {/* Top Overlay */}
            <div className="ir-video-overlay-top">
              <div className="ir-live-badge">
                <span className="ir-live-badge-dot"></span>
                LIVE FEED
              </div>
              <div className="ir-id-badge">
                ID: {sessionId?.substring(0,6) || "INIT"}
              </div>
            </div>
            
            {/* Proctoring Alerts Overlay */}
            {combinedAlerts.length > 0 && (
              <div className="ir-alert-box">
                <div className="ir-alert-title">
                  <span className="ir-alert-dot"></span>
                  SECURITY ALERT
                </div>
                <div>{combinedAlerts.join(" | ")}</div>
              </div>
            )}
          </div>
        </div>

        {/* Interview Meta dashboard - P5 Style */}
        <div className="ir-telemetry">
          <div className="ir-telemetry-bg"></div>
          
          <div className="ir-telemetry-content">
            <h3 className="ir-telemetry-title">
              Telemetry
            </h3>
            
            <div className="ir-vector-box">
              <div className="ir-vector-label">Current Vector</div>
              <div className="ir-vector-value">
                {currentTopic || "Awaiting Node..."}
              </div>
            </div>
            
            <div className="ir-load-box">
              <div className="ir-load-header">
                <div className="ir-load-label">Cognitive Load</div>
                <div className="ir-load-val">Lvl {difficulty}/10</div>
              </div>
              <div className="ir-load-bar-bg">
                <div 
                  className="ir-load-bar-fill" 
                  style={{ width: `${(difficulty / 10) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
          
          <button 
            onClick={handleEnd}
            className="ir-btn-term"
          >
            Terminate
          </button>
        </div>
      </div>

      {/* Right Panel: Chat Interface - P5 Dialogue Box Style (50%) */}
      <div className="ir-right-panel">
        
        {/* Massive Current Question Display */}
        <div className="ir-chat-header">
          <div className="ir-chat-header-bg"></div>
          
          <div className="ir-chat-header-label">
            CURRENT INQUIRY
          </div>

          <div className="ir-chat-question">
            <h1>{displayQuestion}</h1>
            
            {isLoading && (
               <div className="ir-loading-dots">
                 <div className="ir-dot"></div>
                 <div className="ir-dot" style={{ animationDelay: "0.2s" }}></div>
                 <div className="ir-dot" style={{ animationDelay: "0.4s" }}></div>
               </div>
            )}
          </div>
        </div>

        {/* Small Scrollable Transcript Log */}
        <div className="ir-log-container">
          <div className="ir-log-watermark">LOG</div>
          {messages.map((msg, idx) => (
            <div key={idx} className={`ir-msg ${msg.role === 'human' ? 'ir-msg-human' : 'ir-msg-ai'}`}>
              <div className="ir-msg-label">
                {msg.role === 'human' ? 'CANDIDATE' : 'AI SUPERVISOR'}
              </div>
              <div className="ir-msg-content">{msg.content}</div>
            </div>
          ))}
          <div style={{ float:"left", clear: "both" }}></div>
        </div>

        {/* Chat Input */}
        <form onSubmit={handleSendMessage} className="ir-chat-form">
          <div className="ir-chat-form-row">
            <div className="ir-chat-input-wrapper">
              <textarea 
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
                placeholder={isComplete ? "SESSION TERMINATED." : "ENTER RESPONSE..."}
                disabled={isComplete || isLoading}
                rows={1}
                className="ir-chat-textarea"
              />
            </div>
            <button 
              type="submit"
              disabled={isComplete || isLoading || !inputMessage.trim()}
              className="ir-btn-submit"
            >
              Submit
            </button>
          </div>
          <div className="ir-chat-footer">
             <span>PSI Cognitive Processing Engine v2.0</span>
          </div>
        </form>
      </div>
      
    </div>
  );
}
