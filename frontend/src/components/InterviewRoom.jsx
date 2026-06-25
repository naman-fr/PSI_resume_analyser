import React, { useState, useEffect, useRef } from 'react';
import { useProctoring } from '../hooks/useProctoring';
import { useVisionStream } from '../hooks/useVisionStream';
import InterviewReport from './InterviewReport';

const API_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com/api';

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
  useProctoring(hasConsent ? sessionId : null);
  const { visionAlerts } = useVisionStream(sessionId, videoRef, hasConsent && !isComplete);

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
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4">
        <div className="bg-[#111] p-8 rounded-2xl border border-white/10 max-w-xl text-center">
          <div className="w-16 h-16 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center mx-auto mb-6 text-2xl">
            <i className="fas fa-shield-alt"></i>
          </div>
          <h2 className="text-2xl font-bold text-white mb-4">Compliance & Proctoring Gateway</h2>
          <p className="text-gray-400 mb-6 text-left">
            You are about to enter the PSI Cognitive Interview Suite. To ensure a fair and secure environment:
            <ul className="list-disc ml-6 mt-4 space-y-2 text-sm text-gray-300">
              <li>We require access to your Camera and Microphone.</li>
              <li>Your identity and gaze will be verified continuously (Phase 2 Vision).</li>
              <li>Navigating away from this tab will trigger an automated proctoring alert.</li>
            </ul>
          </p>
          <button 
            onClick={requestPermissions}
            className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-medium transition-all"
          >
            I Consent - Enable Camera & Mic
          </button>
          <button onClick={onExit} className="mt-4 text-gray-500 hover:text-white transition-colors text-sm">
            Cancel and Return
          </button>
        </div>
      </div>
    );
  }

  if (finalReport) {
    return <InterviewReport report={finalReport} transcript={messages} onClose={onExit} />;
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white p-4 md:p-6 lg:p-8 flex flex-col md:flex-row gap-6 relative overflow-hidden" style={{
      backgroundImage: 'radial-gradient(circle at 100% 0%, rgba(59, 130, 246, 0.1) 0%, transparent 50%), radial-gradient(circle at 0% 100%, rgba(16, 185, 129, 0.05) 0%, transparent 50%)'
    }}>
      
      {/* Left Panel: Proctoring & Context */}
      <div className="w-full md:w-[380px] lg:w-[420px] flex flex-col gap-6 shrink-0 z-10">
        
        {/* Camera Feed */}
        <div className="bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 rounded-3xl overflow-hidden relative aspect-[4/3] shadow-[0_0_30px_rgba(0,0,0,0.5)] group">
          <video 
            ref={videoRef} 
            autoPlay 
            muted 
            playsInline 
            className="w-full h-full object-cover transform scale-x-[-1] transition-transform duration-700 group-hover:scale-105"
          />
          
          {/* Top Overlay */}
          <div className="absolute top-0 inset-x-0 p-4 bg-gradient-to-b from-black/80 to-transparent flex justify-between items-start pointer-events-none">
            <div className="bg-red-500/20 text-red-500 px-3 py-1.5 rounded-full text-[10px] font-mono border border-red-500/50 flex items-center gap-2 backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              LIVE FEED
            </div>
            <div className="text-[10px] font-mono text-white/50 tracking-widest uppercase">
              NODE_ID: {sessionId?.substring(0,6) || "INIT"}
            </div>
          </div>
          
          {/* Proctoring Alerts Overlay */}
          {visionAlerts.length > 0 && (
            <div className="absolute inset-x-4 bottom-4">
              <div className="bg-red-950/80 backdrop-blur-md border border-red-500 text-red-200 p-3 rounded-2xl text-xs font-bold shadow-[0_0_20px_rgba(239,68,68,0.3)] animate-in slide-in-from-bottom-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-ping"></span>
                  <span className="text-red-400">PROCTORING ALERT</span>
                </div>
                <div className="font-mono text-[10px] uppercase opacity-80">{visionAlerts.join(" | ")}</div>
              </div>
            </div>
          )}

          {/* Vision Scanner Grid overlay */}
          <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_50%_50%_at_50%_50%,black_40%,transparent_100%)]"></div>
        </div>

        {/* Interview Meta dashboard */}
        <div className="bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 rounded-3xl p-6 flex-1 flex flex-col justify-between relative overflow-hidden shadow-[0_0_30px_rgba(0,0,0,0.5)]">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-[80px] rounded-full"></div>
          
          <div>
            <h3 className="flex items-center gap-2 text-white/40 uppercase tracking-[0.2em] text-[10px] font-bold mb-6">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
              Session Telemetry
            </h3>
            
            <div className="space-y-6">
              <div className="group">
                <div className="text-[10px] text-white/40 uppercase tracking-wider mb-2 flex justify-between">
                  <span>Current Vector</span>
                  <span className="text-blue-400 font-mono">0x{Math.floor(Math.random()*1000).toString(16)}</span>
                </div>
                <div className="font-mono text-blue-400 bg-blue-500/5 border border-blue-500/20 px-4 py-3 rounded-xl truncate transition-colors group-hover:bg-blue-500/10">
                  {currentTopic || "Awaiting Node..."}
                </div>
              </div>
              
              <div>
                <div className="flex justify-between items-end mb-2">
                  <div className="text-[10px] text-white/40 uppercase tracking-wider">Cognitive Load</div>
                  <div className="text-xs font-mono font-bold text-white/80">Lvl {difficulty}/10</div>
                </div>
                <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden border border-white/5">
                  <div 
                    className="h-full rounded-full transition-all duration-1000 ease-out relative" 
                    style={{ 
                      width: `${(difficulty / 10) * 100}%`,
                      background: `linear-gradient(90deg, #3b82f6 ${100 - (difficulty*10)}%, #ef4444 100%)`,
                      boxShadow: '0 0 10px rgba(59,130,246,0.5)'
                    }}
                  >
                    <div className="absolute inset-0 bg-white/20 animate-[pulse_2s_ease-in-out_infinite]"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <button 
            onClick={handleEnd}
            className="w-full mt-8 py-4 bg-red-500/5 hover:bg-red-500/10 text-red-400 rounded-2xl border border-red-500/20 transition-all font-medium text-sm flex items-center justify-center gap-2 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect></svg>
            Terminate Session
          </button>
        </div>
      </div>

      {/* Right Panel: Chat Interface */}
      <div className="flex-1 bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 rounded-3xl flex flex-col overflow-hidden shadow-[0_0_30px_rgba(0,0,0,0.5)] z-10">
        
        {/* Chat Header */}
        <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02] relative overflow-hidden">
          <div className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-blue-500/50 to-transparent"></div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500 rounded-full blur animate-pulse opacity-50"></div>
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-600 to-blue-500 flex items-center justify-center text-xl shadow-lg relative border border-white/20">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M12 2a2 2 0 0 1 2 2c0 1.1-.9 2-2 2s-2-.9-2-2 1.1-2 2-2zM19 14v4h2v2H3v-2h2v-4a7 7 0 0 1 14 0zM12 22a2 2 0 0 1-2-2h4a2 2 0 0 1-2 2z"/></svg>
              </div>
              <div className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-[#111] rounded-full"></div>
            </div>
            <div>
              <h2 className="font-bold text-lg leading-tight tracking-tight">Socratic Supervisor</h2>
              <div className="text-[10px] text-emerald-400 font-mono tracking-widest uppercase">
                LangGraph Link Active
              </div>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 scroll-smooth relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-500/5 blur-[120px] rounded-full pointer-events-none"></div>
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'human' ? 'justify-end' : 'justify-start'} relative z-10 animate-in fade-in slide-in-from-bottom-4 duration-500`} style={{ animationDelay: `${idx * 0.1}s` }}>
              <div className={`max-w-[85%] md:max-w-[75%] p-5 rounded-3xl text-[15px] leading-relaxed shadow-lg ${
                msg.role === 'human' 
                  ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-br-sm shadow-blue-900/20' 
                  : 'bg-white/5 border border-white/10 text-gray-200 rounded-bl-sm backdrop-blur-md shadow-black/50'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start relative z-10 animate-in fade-in">
              <div className="bg-white/5 border border-white/10 text-gray-400 p-5 rounded-3xl rounded-bl-sm backdrop-blur-md shadow-lg flex items-center gap-3">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></span>
                  <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></span>
                  <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></span>
                </div>
                <span className="text-xs font-mono opacity-50 ml-2">Synthesizing...</span>
              </div>
            </div>
          )}
        </div>

        {/* Chat Input */}
        <form onSubmit={handleSendMessage} className="p-4 md:p-6 border-t border-white/5 bg-white/[0.02] relative z-10">
          <div className="relative group flex items-end gap-3">
            <div className="flex-1 relative">
               <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-2xl blur opacity-20 group-hover:opacity-40 transition-opacity pointer-events-none"></div>
              <textarea 
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
                placeholder={isComplete ? "Session Terminated." : "Formulate your response..."}
                disabled={isComplete || isLoading}
                rows={1}
                className="w-full bg-[#111]/80 backdrop-blur-xl border border-white/10 rounded-2xl px-5 py-4 text-white focus:outline-none focus:border-blue-500/50 transition-colors disabled:opacity-50 resize-none min-h-[56px] max-h-[150px] relative z-10"
              />
            </div>
            <button 
              type="submit"
              disabled={isComplete || isLoading || !inputMessage.trim()}
              className="h-[56px] px-6 bg-white text-black hover:bg-gray-200 disabled:bg-white/10 disabled:text-white/30 rounded-2xl font-bold transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_20px_rgba(255,255,255,0.3)] disabled:shadow-none flex items-center justify-center shrink-0"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </div>
          <div className="text-center mt-3">
             <span className="text-[10px] text-white/30 font-mono tracking-widest uppercase">PSI Cognitive Processing Engine v2.0</span>
          </div>
        </form>
      </div>
      
    </div>
  );
}
