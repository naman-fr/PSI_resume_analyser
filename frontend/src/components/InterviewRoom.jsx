import React, { useState, useEffect, useRef } from 'react';
import { useProctoring } from '../hooks/useProctoring';

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
  
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const videoRef = useRef(null);
  
  // Attach proctoring once consent is given and session starts
  useProctoring(hasConsent ? sessionId : null);

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

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white flex flex-col md:flex-row p-4 gap-4">
      
      {/* Left Panel: Proctoring & Context */}
      <div className="w-full md:w-1/3 flex flex-col gap-4">
        {/* Camera Feed */}
        <div className="bg-[#111] border border-white/10 rounded-2xl overflow-hidden relative aspect-video">
          <video 
            ref={videoRef} 
            autoPlay 
            muted 
            playsInline 
            className="w-full h-full object-cover transform scale-x-[-1]"
          />
          <div className="absolute top-2 left-2 bg-red-500/20 text-red-500 px-2 py-1 rounded text-xs font-mono border border-red-500/50 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            REC
          </div>
        </div>

        {/* Interview Meta */}
        <div className="bg-[#111] border border-white/10 rounded-2xl p-6 flex-1">
          <h3 className="text-gray-400 uppercase tracking-wider text-xs font-bold mb-4">Live Analysis</h3>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-gray-500 mb-1">Current Topic</div>
              <div className="font-mono text-blue-400">{currentTopic || "Initializing..."}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">Adaptive Difficulty (1-10)</div>
              <div className="w-full bg-black rounded-full h-2 mt-2">
                <div 
                  className="bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 h-2 rounded-full transition-all duration-500" 
                  style={{ width: `${(difficulty / 10) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
          
          <button 
            onClick={handleEnd}
            className="w-full mt-8 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl border border-red-500/30 transition-all font-medium"
          >
            End Interview
          </button>
        </div>
      </div>

      {/* Right Panel: Chat Interface */}
      <div className="w-full md:w-2/3 bg-[#111] border border-white/10 rounded-2xl flex flex-col">
        <div className="p-6 border-b border-white/10 flex justify-between items-center bg-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-xl shadow-[0_0_15px_rgba(168,85,247,0.4)]">
              🤖
            </div>
            <div>
              <h2 className="font-semibold text-lg leading-tight">PSI Socratic Agent</h2>
              <div className="text-xs text-emerald-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Online
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'human' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] p-4 rounded-2xl ${msg.role === 'human' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-white/5 border border-white/10 text-gray-200 rounded-bl-none'}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/5 border border-white/10 text-gray-400 p-4 rounded-2xl rounded-bl-none flex items-center gap-2">
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></span>
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></span>
              </div>
            </div>
          )}
        </div>

        <form onSubmit={handleSendMessage} className="p-4 border-t border-white/10 bg-black/20">
          <div className="flex gap-2">
            <input 
              type="text" 
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={isComplete ? "Interview Complete" : "Type your answer..."}
              disabled={isComplete || isLoading}
              className="flex-1 bg-[#222] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50"
            />
            <button 
              type="submit"
              disabled={isComplete || isLoading || !inputMessage.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-6 py-3 rounded-xl font-medium transition-colors"
            >
              Send
            </button>
          </div>
        </form>
      </div>
      
    </div>
  );
}
