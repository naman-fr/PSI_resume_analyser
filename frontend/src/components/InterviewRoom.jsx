import React, { useState, useEffect, useRef } from 'react';
import { useProctoring } from '../hooks/useProctoring';
import { useVisionStream } from '../hooks/useVisionStream';
import InterviewReport from './InterviewReport';
import MCQAssessment from './MCQAssessment';

const BASE_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com';
const CLEAN_BASE = BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
const API_URL = CLEAN_BASE + '/api';

import './InterviewRoom.css';

export default function InterviewRoom({ resumeText, jdText, onExit }) {
  const [hasConsent, setHasConsent] = useState(false);
  const [assessmentFormat, setAssessmentFormat] = useState(null); // 'mcq' or 'interview'
  const [focusSelected, setFocusSelected] = useState(false);
  const [interviewFocus, setInterviewFocus] = useState("balanced");
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
  const [localResumeText, setLocalResumeText] = useState(resumeText === "Resume Not Provided" ? "" : resumeText || "");
  
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const [isListening, setIsListening] = useState(false);
  
  const videoRef = useRef(null);
  const recognitionRef = useRef(null);
  
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = false; // Disable interim results to fix duplication bug
      
      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          setInputMessage((prev) => prev + (prev ? " " : "") + finalTranscript.trim());
        }
      };
      
      recognitionRef.current.onerror = (e) => {
        console.error("Speech Recognition Error", e);
        setIsListening(false);
      };
      
      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      setInputMessage(""); // Clear before speaking new sentence
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const speakText = (text) => {
    if (window.speechSynthesis) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Attach proctoring once consent is given and session starts
  const { localAlerts } = useProctoring(hasConsent ? sessionId : null);
  const { visionAlerts } = useVisionStream(sessionId, videoRef, hasConsent && !isComplete);

  const combinedAlerts = [...(visionAlerts || []), ...(localAlerts || [])];

  useEffect(() => {
    if (cameraStream && videoRef.current) {
      videoRef.current.srcObject = cameraStream;
    }
  }, [cameraStream, focusSelected]);

  const [isFullscreenError, setIsFullscreenError] = useState(false);

  useEffect(() => {
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement && hasConsent && !isComplete) {
        setIsFullscreenError(true);
      }
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, [hasConsent, isComplete]);

  const requestPermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setCameraStream(stream);
      
      try {
        if (document.documentElement.requestFullscreen) {
          await document.documentElement.requestFullscreen();
        }
      } catch (fsErr) {
        console.warn("Fullscreen request failed", fsErr);
      }
      
      setHasConsent(true);
      setIsFullscreenError(false);
    } catch (err) {
      alert("Camera and Microphone permissions are required to proceed with the cognitive interview.");
    }
  };

  const handleReturnToFullscreen = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
        setIsFullscreenError(false);
      }
    } catch (err) {
      console.warn("Could not return to fullscreen", err);
    }
  };

  const handleFocusSelect = (focus, overrideResume) => {
    setInterviewFocus(focus);
    setFocusSelected(true);
    initInterview(focus, overrideResume);
  };

  const initInterview = async (focusStr, overrideResume, overrideJd) => {
    setIsLoading(true);
    setSessionId(Math.random().toString(36).substring(7)); // Mock session ID
    try {
      const res = await fetch(`${API_URL}/interview/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          resume_text: overrideResume || resumeText || "Resume Not Provided", 
          jd_text: overrideJd || jdText || "Sample JD",
          focus: focusStr || "balanced"
        })
      });
      if (!res.ok) throw new Error("Server error " + res.status);
      const data = await res.json();
      if (data.success && data.messages && data.messages.length > 0) {
        setMessages(data.messages);
        setInterviewTree(data.interview_tree);
        setCurrentTopic(data.current_topic);
        setDifficulty(data.difficulty_level);
        
        // Auto-speak the first question
        const firstAiMessage = data.messages.find(m => m.role === 'ai');
        if (firstAiMessage) {
           speakText(firstAiMessage.content);
        }
      } else {
        throw new Error(data.error || "Failed to generate interview questions. The AI may be rate-limited.");
      }
    } catch (e) {
      console.error(e);
      setMessages([{ role: "ai", content: `System Error: ${e.message}. Please restart the session.` }]);
    }
    setIsLoading(false);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isComplete) return;
    
    if (isListening) {
      toggleListening(); // Stop mic when submitting
    }

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
      if (!res.ok) throw new Error("Server error " + res.status);
      const data = await res.json();
      if (data.success && data.messages && data.messages.length > 0) {
        setMessages(data.messages);
        setDifficulty(data.difficulty_level);
        setEvaluations(data.evaluations);
        setIsComplete(data.is_complete);
        
        // Auto-speak the response
        const lastAiMessage = [...data.messages].reverse().find(m => m.role === 'ai');
        if (lastAiMessage && !data.is_complete) {
          speakText(lastAiMessage.content);
        }
        
        if (data.final_report) {
          setFinalReport(data.final_report);
        }
      } else {
        throw new Error(data.error || "AI failed to respond. The API might be rate-limited.");
      }
    } catch (e) {
      console.error(e);
      setMessages([...newMessages, { role: "ai", content: `Connection error: ${e.message}. Please repeat.` }]);
    }
    setIsLoading(false);
  };

  const handleEnd = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    
    // Save to Candidate Intelligence Hub if logged in
    const token = localStorage.getItem('token');
    if (token && messages.length > 0) {
      fetch(`${API_URL}/api/hub/save_interview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          duration_seconds: 600, // mock duration
          transcript: messages,
          final_feedback: messages[messages.length - 1]?.content || "Session ended abruptly."
        })
      }).catch(err => console.error("Failed to save interview to hub", err));
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
  
  if (hasConsent && !assessmentFormat) {
    return (
      <div className="ir-overlay">
        <div className="ir-overlay-bg"></div>
        <div className="ir-gateway-box" style={{ maxWidth: '800px' }}>
          <h2 className="ir-gateway-title" style={{ fontSize: '2rem' }}>SELECT ASSESSMENT FORMAT</h2>
          <div className="ir-gateway-warning" style={{ textAlign: 'center' }}>
            <p style={{ marginBottom: '1.5rem', color: '#000' }}>Choose your evaluation methodology.</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1rem' }}>
              <button onClick={() => setAssessmentFormat('mcq')} className="ir-btn-primary" style={{ transform: 'skewX(0deg)', background: '#121212', border: '2px solid #fff200' }}>
                <div style={{ color: '#fff200', marginBottom: '0.5rem' }}>2-LEVEL MCQ ASSESSMENT</div>
                <div style={{ fontSize: '0.8rem', color: '#fff', textTransform: 'none', fontWeight: 'normal' }}>Progressive difficulty (Easy to Hard) technical screening.</div>
              </button>
              <button onClick={() => setAssessmentFormat('interview')} className="ir-btn-primary" style={{ transform: 'skewX(0deg)', background: '#e60012', border: '2px solid #fff' }}>
                <div style={{ color: '#fff', marginBottom: '0.5rem' }}>COGNITIVE INTERVIEW (VOICE ENABLED)</div>
                <div style={{ fontSize: '0.8rem', color: '#fff', textTransform: 'none', fontWeight: 'normal' }}>Real-time Socratic dialogue with the AI Supervisor.</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  if (assessmentFormat === 'mcq') {
    return <MCQAssessment resumeText={resumeText} jdText={jdText} onExit={handleEnd} combinedAlerts={combinedAlerts} sessionId={sessionId} />;
  }

  if (hasConsent && assessmentFormat === 'interview' && !focusSelected) {
    return (
      <div className="ir-overlay">
        <div className="ir-overlay-bg"></div>
        <div className="ir-gateway-box" style={{ maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
          <h2 className="ir-gateway-title" style={{ fontSize: '2rem' }}>Configure Cognitive Vector</h2>
          
          {/* Missing Resume Paste Box */}
          {(!resumeText || resumeText === "Resume Not Provided" || resumeText === "Sample Resume") && (
            <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
              <div style={{ color: '#e60012', fontWeight: 'bold', marginBottom: '0.5rem' }}>NO RESUME DETECTED</div>
              <p style={{ color: '#000', fontSize: '0.9rem', marginBottom: '0.5rem' }}>The AI Supervisor requires context to grill you properly. Please paste your Resume or LinkedIn text below:</p>
              <textarea 
                value={localResumeText}
                onChange={(e) => setLocalResumeText(e.target.value)}
                placeholder="Paste or share your resume as text here..."
                style={{ width: '100%', height: '100px', background: '#121212', color: '#fff', border: '1px solid #333', padding: '0.5rem', fontFamily: 'monospace' }}
              />
            </div>
          )}

          <div className="ir-gateway-warning" style={{ textAlign: 'center' }}>
            <p style={{ marginBottom: '1.5rem', color: '#000' }}>How would you like the AI Supervisor to conduct this interview?</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1rem' }}>
              <button onClick={() => handleFocusSelect('resume', localResumeText)} className="ir-btn-primary" style={{ transform: 'skewX(0deg)', background: '#121212', border: '2px solid #e60012' }}>
                <div style={{ color: '#e60012', marginBottom: '0.5rem' }}>RESUME FOCUSED</div>
                <div style={{ fontSize: '0.8rem', color: '#fff', textTransform: 'none', fontWeight: 'normal' }}>Drill deep into your past experience, projects, and architecture decisions.</div>
              </button>
              <button onClick={() => handleFocusSelect('jd', localResumeText)} className="ir-btn-primary" style={{ transform: 'skewX(0deg)', background: '#121212', border: '2px solid #fff200' }}>
                <div style={{ color: '#fff200', marginBottom: '0.5rem' }}>REQUIREMENTS FOCUSED</div>
                <div style={{ fontSize: '0.8rem', color: '#fff', textTransform: 'none', fontWeight: 'normal' }}>Strictly assess your fitness against the core requirements of the Job Description.</div>
              </button>
              <button onClick={() => handleFocusSelect('balanced', localResumeText)} className="ir-btn-primary" style={{ transform: 'skewX(0deg)', background: '#e60012', border: '2px solid #fff' }}>
                <div style={{ color: '#fff', marginBottom: '0.5rem' }}>BALANCED (RECOMMENDED)</div>
                <div style={{ fontSize: '0.8rem', color: '#fff', textTransform: 'none', fontWeight: 'normal' }}>Connect your past experiences to the specific needs of the new role.</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (finalReport) {
    return <InterviewReport report={finalReport} transcript={messages} onClose={onExit} />;
  }

  if (isFullscreenError) {
    return (
      <div className="ir-overlay">
        <div className="ir-overlay-bg"></div>
        <div className="ir-gateway-box" style={{ borderColor: '#e60012', boxShadow: '12px 12px 0px #fff' }}>
          <div className="ir-icon-box" style={{ background: '#fff', color: '#e60012', borderColor: '#e60012' }}>
            <i className="fas fa-exclamation-triangle"></i>
          </div>
          <h2 className="ir-gateway-title" style={{ color: '#e60012', textShadow: '2px 2px 0px #fff' }}>SECURITY VIOLATION</h2>
          <div className="ir-gateway-warning">
            <p>FULL SCREEN EXITED</p>
            <ul>
              <li><span></span> The interview MUST be conducted in full screen mode.</li>
              <li><span></span> Split-screening or window minimizing is strictly prohibited.</li>
              <li><span></span> Return to full screen immediately or your session will be terminated.</li>
            </ul>
          </div>
          <button onClick={handleReturnToFullscreen} className="ir-btn-primary">
            RETURN TO FULL SCREEN
          </button>
          <button onClick={handleEnd} className="ir-btn-abort" style={{ color: '#e60012', borderColor: '#e60012' }}>
            TERMINATE INTERVIEW
          </button>
        </div>
      </div>
    );
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
          <div className="ir-chat-form-row" style={{ display: 'flex', gap: '0.5rem' }}>
            <div className="ir-chat-input-wrapper" style={{ flexGrow: 1 }}>
              <textarea 
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
                placeholder={isComplete ? "SESSION TERMINATED." : "ENTER RESPONSE OR USE VOICE..."}
                disabled={isComplete || isLoading}
                rows={1}
                className="ir-chat-textarea"
              />
            </div>
            
            {/* Voice Mic Button */}
            {window.SpeechRecognition || window.webkitSpeechRecognition ? (
              <button 
                type="button"
                onClick={toggleListening}
                className="ir-btn-submit"
                style={{ background: isListening ? '#e60012' : '#333', borderColor: isListening ? '#fff' : '#555', color: '#fff', width: '60px', padding: '0' }}
                title="Toggle Voice Input"
              >
                <i className={`fas fa-microphone${isListening ? '' : '-slash'}`}></i>
              </button>
            ) : null}

            <button 
              type="submit"
              disabled={isComplete || isLoading || !inputMessage.trim()}
              className="ir-btn-submit"
            >
              Submit
            </button>
          </div>
          <div className="ir-chat-footer">
             <span>PSI Cognitive Processing Engine v2.0 | Voice Recognition Active</span>
          </div>
        </form>
      </div>
      
    </div>
  );
}
