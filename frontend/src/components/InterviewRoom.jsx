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

  // Extract last AI message for the massive prominent question display
  const lastAiMessage = [...messages].reverse().find(m => m.role === 'ai');
  const displayQuestion = lastAiMessage ? lastAiMessage.content : (isLoading ? "SYNTHESIZING NEXT INQUIRY..." : "INITIALIZING COGNITIVE ENGINE...");

  return (
    <div className="min-h-screen bg-[#080808] text-white p-4 md:p-6 lg:p-8 flex flex-col md:flex-row gap-8 relative overflow-hidden" style={{
      backgroundImage: 'radial-gradient(#e60012 1px, transparent 1px)',
      backgroundSize: '24px 24px'
    }}>
      <div className="absolute inset-0 bg-black/60 pointer-events-none"></div>

      {/* Left Panel: Proctoring & Context (50%) */}
      <div className="flex-1 flex flex-col gap-8 shrink-0 z-10 animate-[slashReveal_0.6s_ease-out_both]">
        
        {/* Camera Feed - P5 TV Screen Style */}
        <div className="bg-[#121212] border-4 border-white p-2 transform skew-x-[-2deg] shadow-[8px_8px_0px_#000] relative group flex-1 flex flex-col">
          <div className="flex-1 overflow-hidden border-2 border-black relative bg-black min-h-[300px]">
            <video 
              ref={videoRef} 
              autoPlay 
              muted 
              playsInline 
              className="w-full h-full object-cover transform scale-x-[-1] transition-transform duration-700 group-hover:scale-105"
            />
            
            {/* Top Overlay */}
            <div className="absolute top-0 inset-x-0 p-3 bg-gradient-to-b from-black/80 to-transparent flex justify-between items-start pointer-events-none">
              <div className="bg-[#e60012] text-white px-3 py-1 font-black text-xs uppercase border-2 border-black shadow-[2px_2px_0px_#000] transform skew-x-[-10deg] flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                LIVE FEED
              </div>
              <div className="text-xs font-black text-white/80 bg-black px-2 py-1 transform skew-x-[10deg] border border-white/20">
                ID: {sessionId?.substring(0,6) || "INIT"}
              </div>
            </div>
            
            {/* Proctoring Alerts Overlay */}
            {visionAlerts.length > 0 && (
              <div className="absolute inset-x-4 bottom-4">
                <div className="bg-[#fff200] border-4 border-black text-black p-3 font-black text-sm uppercase shadow-[4px_4px_0px_#e60012] transform skew-x-[-5deg] animate-pulse">
                  <div className="flex items-center gap-2 mb-1 text-[#e60012]">
                    <span className="w-3 h-3 bg-[#e60012] rounded-full"></span>
                    SECURITY ALERT
                  </div>
                  <div>{visionAlerts.join(" | ")}</div>
                </div>
              </div>
            )}

            {/* Vision Scanner Grid overlay */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:40px_40px]"></div>
          </div>
        </div>

        {/* Interview Meta dashboard - P5 Style */}
        <div className="bg-[#e60012] border-4 border-white p-6 transform skew-x-[2deg] shadow-[8px_8px_0px_#000] flex flex-row gap-6 items-center justify-between relative overflow-hidden shrink-0">
          <div className="absolute inset-0 opacity-20 pointer-events-none bg-[repeating-linear-gradient(-45deg,transparent,transparent_10px,#000_10px,#000_20px)]"></div>
          
          <div className="relative z-10 flex-1 flex gap-6 items-center">
            <h3 className="bg-black text-white inline-block px-4 py-2 font-black uppercase text-sm transform skew-x-[-10deg] border-2 border-white shadow-[4px_4px_0px_#000]">
              Telemetry
            </h3>
            
            <div className="flex-1 bg-white text-black border-4 border-black p-3 transform skew-x-[-2deg] shadow-[4px_4px_0px_rgba(0,0,0,0.5)]">
              <div className="text-xs font-black uppercase tracking-widest text-[#e60012] mb-1">Current Vector</div>
              <div className="font-bold text-md leading-tight uppercase truncate">
                {currentTopic || "Awaiting Node..."}
              </div>
            </div>
            
            <div className="flex-1 bg-black border-4 border-white p-3 transform skew-x-[2deg] shadow-[4px_4px_0px_rgba(0,0,0,0.5)]">
              <div className="flex justify-between items-end mb-1">
                <div className="text-[10px] font-black uppercase tracking-widest text-white">Cognitive Load</div>
                <div className="text-sm font-black text-[#fff200]">Lvl {difficulty}/10</div>
              </div>
              <div className="w-full bg-[#121212] border-2 border-[#fff200] h-3 p-0.5">
                <div 
                  className="h-full bg-[#fff200] transition-all duration-1000 ease-out" 
                  style={{ width: `${(difficulty / 10) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
          
          <button 
            onClick={handleEnd}
            className="px-6 py-4 bg-black text-white hover:bg-[#fff200] hover:text-black hover:border-black border-4 border-white transform skew-x-[-5deg] transition-all font-black text-sm uppercase shadow-[4px_4px_0px_rgba(0,0,0,0.5)] relative z-10 whitespace-nowrap"
          >
            Terminate
          </button>
        </div>
      </div>

      {/* Right Panel: Chat Interface - P5 Dialogue Box Style (50%) */}
      <div className="flex-1 bg-[#121212] border-4 border-white shadow-[12px_12px_0px_#000] flex flex-col z-10 transform skew-x-[-1deg] relative overflow-hidden animate-[slashReveal_0.8s_ease-out_both]">
        
        {/* Massive Current Question Display */}
        <div className="bg-[#e60012] border-b-4 border-black p-8 relative min-h-[35%] flex flex-col justify-center">
          <div className="absolute inset-0 opacity-10 pointer-events-none bg-[radial-gradient(#fff_2px,transparent_2px)] bg-[size:20px_20px]"></div>
          
          <div className="absolute top-4 left-4 bg-black text-white px-3 py-1 font-black text-xs uppercase border-2 border-white transform skew-x-[-10deg] shadow-[2px_2px_0px_#fff200]">
            CURRENT INQUIRY
          </div>

          <div className="relative z-10 mt-6">
            <h1 className="text-3xl md:text-4xl lg:text-5xl font-black text-white uppercase leading-tight" style={{ textShadow: '4px 4px 0px #000' }}>
              {displayQuestion}
            </h1>
            
            {isLoading && (
               <div className="mt-6 flex gap-2">
                 <div className="w-3 h-3 bg-[#fff200] border-2 border-black shadow-[2px_2px_0px_#000] transform skew-x-[-10deg] animate-pulse"></div>
                 <div className="w-3 h-3 bg-[#fff200] border-2 border-black shadow-[2px_2px_0px_#000] transform skew-x-[-10deg] animate-pulse" style={{ animationDelay: "0.2s" }}></div>
                 <div className="w-3 h-3 bg-[#fff200] border-2 border-black shadow-[2px_2px_0px_#000] transform skew-x-[-10deg] animate-pulse" style={{ animationDelay: "0.4s" }}></div>
               </div>
            )}
          </div>
        </div>

        {/* Small Scrollable Transcript Log */}
        <div className="flex-1 bg-white border-b-4 border-black overflow-y-auto p-4 flex flex-col gap-3 relative">
          <div className="absolute top-2 right-4 text-black opacity-30 font-black text-6xl italic transform skew-x-[-20deg] pointer-events-none">
            LOG
          </div>
          {messages.map((msg, idx) => (
            <div key={idx} className={`p-3 border-2 border-black ${msg.role === 'human' ? 'bg-black text-white ml-12' : 'bg-[#f0f0f0] text-black mr-12'} shadow-[2px_2px_0px_#000] transform ${msg.role === 'human' ? 'skew-x-[1deg]' : 'skew-x-[-1deg]'}`}>
              <div className="text-[10px] font-black uppercase text-[#e60012] mb-1">
                {msg.role === 'human' ? 'CANDIDATE' : 'AI SUPERVISOR'}
              </div>
              <div className="font-bold text-sm leading-snug">{msg.content}</div>
            </div>
          ))}
          {/* Scroll anchor */}
          <div style={{ float:"left", clear: "both" }}></div>
        </div>

        {/* Chat Input */}
        <form onSubmit={handleSendMessage} className="p-6 bg-black border-t-4 border-white">
          <div className="flex items-end gap-4">
            <div className="flex-1">
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
                className="w-full bg-white text-black border-4 border-black p-4 font-bold text-lg focus:outline-none focus:border-[#e60012] transition-colors disabled:opacity-50 resize-none min-h-[70px] max-h-[150px] shadow-[4px_4px_0px_rgba(255,255,255,0.2)] focus:shadow-[4px_4px_0px_#e60012] transform skew-x-[-1deg]"
              />
            </div>
            <button 
              type="submit"
              disabled={isComplete || isLoading || !inputMessage.trim()}
              className="h-[70px] px-8 bg-[#e60012] text-white hover:bg-[#fff200] hover:text-black disabled:bg-[#333] disabled:text-[#666] border-4 border-white font-black text-xl uppercase shadow-[6px_6px_0px_#000] transform skew-x-[-5deg] transition-all disabled:shadow-none shrink-0"
            >
              Submit
            </button>
          </div>
          <div className="mt-3 text-right">
             <span className="text-xs text-[#fff200] font-black tracking-widest uppercase bg-white/10 px-2 py-0.5 transform skew-x-[10deg] inline-block">PSI Cognitive Processing Engine v2.0</span>
          </div>
        </form>
      </div>
      
    </div>
  );
}
