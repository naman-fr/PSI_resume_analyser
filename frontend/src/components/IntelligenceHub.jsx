import React, { useState, useEffect } from 'react';
import { Layers, Database, Lock, TrendingUp, History, Star, Activity, AlertTriangle, Book, Download, ShieldCheck, HardDrive, Calendar, Github, MessageSquare } from 'lucide-react';
import { useAuth } from '../AuthContext';
import ThreeGem from './ThreeGem';

const API_URL = import.meta.env.VITE_API_URL || '';

export default function IntelligenceHub() {
  const { currentUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('overview');
  const [currentRotation, setCurrentRotation] = useState(0);
  const sceneRef = React.useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!sceneRef.current) return;
      const xAxisDelta = (window.innerWidth / 2 - e.pageX); 
      const yAxisDelta = (window.innerHeight / 2 - e.pageY);
      const rotateY = xAxisDelta / 35;
      const rotateX = yAxisDelta / 35;
      sceneRef.current.style.transform = `rotateY(${rotateY}deg) rotateX(${rotateX}deg)`;
    };
    
    const handleMouseLeave = () => {
      if (!sceneRef.current) return;
      sceneRef.current.style.transition = 'transform 0.6s ease-out';
      sceneRef.current.style.transform = `rotateY(0deg) rotateX(0deg)`;
      setTimeout(() => {
        if(sceneRef.current) sceneRef.current.style.transition = 'transform 0.1s ease-out';
      }, 600);
    };

    window.addEventListener('mousemove', handleMouseMove);
    document.body.addEventListener('mouseleave', handleMouseLeave);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.body.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  const handleNavClick = (targetAngle, id) => {
    setActiveView(id);
    let diff = targetAngle - (currentRotation % 360);
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    setCurrentRotation(prev => prev + diff);
  };

  useEffect(() => {
    fetchProfile();
  }, []);

    const [integrations, setIntegrations] = useState({});

  const fetchProfile = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }
      
      const [resProfile, resInteg] = await Promise.all([
        fetch(`${API_URL}/api/hub/profile`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/hub/integrations`, { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      
      if (resProfile.ok) {
        const data = await resProfile.json();
        setProfile(data);
      } else if (resProfile.status === 401) {
        localStorage.removeItem('token');
        setLoading(false);
        return;
      }
      if (resInteg.ok) {
        const integData = await resInteg.json();
        setIntegrations(integData);
      }
    } catch (err) {
      console.error("Failed to fetch intelligence profile", err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleIntegration = async (id, currentStatus) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/api/hub/integrations/toggle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ integration_id: id, is_connected: !currentStatus })
      });
      if (res.ok) {
        setIntegrations(prev => ({ ...prev, [id]: !currentStatus }));
      }
    } catch (err) {
      console.error("Failed to toggle integration", err);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="glass-panel p-8 text-center text-red-400">
        <ShieldCheck className="mx-auto h-12 w-12 mb-4" />
        <h2>Authentication Error</h2>
        <p>You must be logged in to access the Candidate Intelligence Hub.</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in pb-12 w-full flex flex-col items-center overflow-hidden">
      {/* Diegetic Background Halftone Texture */}
      <div className="fixed top-0 left-0 w-screen h-screen -z-10 opacity-10 pointer-events-none" style={{ background: 'radial-gradient(var(--p5-red) 15%, transparent 16%), radial-gradient(var(--p5-red) 15%, transparent 16%)', backgroundSize: '20px 20px', backgroundPosition: '0 0, 10px 10px', animation: 'bgStripeScroll 20s linear infinite' }}></div>

      <div className="flex justify-between items-center bg-black p-4 w-full max-w-[1200px] mb-8" style={{ transform: 'skewX(-5deg)', border: '4px solid var(--p5-red)', boxShadow: '8px 8px 0px var(--p5-red)' }}>
        <div style={{ transform: 'skewX(5deg)' }}>
          <h2 className="text-4xl font-black text-white uppercase tracking-widest" style={{ textShadow: '2px 2px 0px var(--p5-red)', fontFamily: 'var(--ff-display)' }}>
            🧠 Candidate Intelligence Hub
          </h2>
          <p className="text-red-400 mt-1 font-bold tracking-widest uppercase text-sm">
            [ PERSISTENT AI WORKSPACE & CAREER VAULT ]
          </p>
        </div>
        <div className="flex space-x-2" style={{ transform: 'skewX(5deg)' }}>
          <span className="bg-white text-black px-4 py-2 text-xl font-black font-mono border-2 border-black flex items-center shadow-[4px_4px_0px_var(--p5-red)] uppercase tracking-wider">
            <Activity className="h-6 w-6 mr-2 text-red-600" />
            Health: {profile.career_health_score}/100
          </span>
        </div>
      </div>

      {/* Static Navigation Triggers */}
      <div className="w-full max-w-[1200px] flex justify-center space-x-6 mb-16 relative z-50 mt-6">
        {[
          { id: 'overview', label: '01 PROFILE', angle: 0 },
          { id: 'vault', label: '02 STATS', angle: -90 },
          { id: 'interviews', label: '03 ARCHIVE', angle: -180 },
          { id: 'integrations', label: '04 CONTACT', angle: -270 }
        ].map(tab => (
          <button 
            key={tab.id}
            onClick={() => handleNavClick(tab.angle, tab.id)}
            className="px-8 py-3 font-black text-xl uppercase tracking-widest transition-all duration-200 relative"
            style={{ 
              background: activeView === tab.id ? 'var(--p5-red)' : '#fff', 
              color: activeView === tab.id ? '#fff' : '#000',
              clipPath: activeView === tab.id ? 'polygon(0 0, 100% 0, 100% 100%, 10% 100%)' : 'polygon(10% 0, 100% 0, 90% 100%, 0 100%)',
              border: 'none',
              transform: activeView === tab.id ? 'scale(1.05) translateX(10px)' : 'none'
            }}
          >
            <span className="block transform" style={{ transform: 'skewX(-10deg)' }}>
              {tab.label}
            </span>
          </button>
        ))}
      </div>

      {/* 3D Spatial Perspective Wrapper */}
      <div className="hub-scene" ref={sceneRef}>
          {/* The Volumetric Rotating Prism */}
          <div className="hub-prism" style={{ transform: `rotateY(${currentRotation}deg)` }}>
              
              {/* FACE 1: ABOUT (FRONT) - 0deg */}
              <div className="hub-face hub-face-front">

        <div className="relative mt-12 mb-8">
          {/* 3D Background Element */}
          <div className="absolute inset-0 z-0 flex items-center justify-center opacity-70 pointer-events-none" style={{ transform: 'scale(1.5)' }}>
            <div className="w-full h-[600px] pointer-events-auto">
              <ThreeGem />
            </div>
          </div>

          <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-12 mt-6">
            <div className="p-8 bg-black/90 backdrop-blur-md text-white border-[6px] border-white shadow-[12px_12px_0px_#f00] hover:shadow-[16px_16px_0px_#f00] transition-all duration-300" style={{ transform: 'skewX(-3deg)' }}>
              <div style={{ transform: 'skewX(3deg)' }}>
                <h3 className="text-3xl font-black mb-6 flex items-center text-white uppercase tracking-[0.2em] border-b-4 border-red-600 pb-4">
                  <Database className="mr-4 h-8 w-8 text-red-500 animate-pulse" />
                  AI Memory Core
                </h3>
                <div className="space-y-8 mt-6">
                  <div>
                    <h4 className="text-lg font-black text-white uppercase tracking-widest mb-4 bg-red-600 inline-block px-4 py-2 shadow-[4px_4px_0px_#fff]">
                      [ IDENTIFIED STRENGTHS ]
                    </h4>
                    <div className="flex flex-wrap gap-4 mt-2">
                      {profile.ai_memory.strengths.length > 0 ? (
                        profile.ai_memory.strengths.map((s, i) => (
                          <span key={i} className="bg-white text-black font-black px-4 py-2 text-md border-2 border-black shadow-[3px_3px_0px_#f00] uppercase tracking-wider hover:translate-y-[-2px] transition-transform">{s}</span>
                        ))
                      ) : (
                        <span className="text-gray-400 italic font-mono font-bold">NO DATA. UPLOAD RESUME.</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <h4 className="text-lg font-black text-black bg-white uppercase tracking-widest mb-4 inline-block px-4 py-2 shadow-[4px_4px_0px_#333]">
                      [ IMPROVEMENT TARGETS ]
                    </h4>
                    <div className="flex flex-wrap gap-4 mt-2">
                      {profile.ai_memory.weaknesses.length > 0 ? (
                        profile.ai_memory.weaknesses.map((w, i) => (
                          <span key={i} className="bg-gray-800 text-gray-200 font-bold px-4 py-2 text-md border-2 border-gray-600 uppercase tracking-wider shadow-[3px_3px_0px_#000]">{w}</span>
                        ))
                      ) : (
                        <span className="text-gray-400 italic font-mono font-bold">NO DATA.</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-8 bg-red-600/95 backdrop-blur-md text-white border-[6px] border-black shadow-[12px_12px_0px_#000] hover:shadow-[16px_16px_0px_#000] transition-all duration-300" style={{ transform: 'skewX(-3deg)' }}>
              <div style={{ transform: 'skewX(3deg)' }}>
                <h3 className="text-3xl font-black mb-6 flex items-center text-black uppercase tracking-[0.2em] border-b-4 border-black pb-4">
                  <TrendingUp className="mr-4 h-8 w-8 text-white" />
                  Skill Genome Matrix
                </h3>
                {Object.keys(profile.skill_genome).length > 0 ? (
                  <div className="space-y-6 mt-6">
                    {Object.entries(profile.skill_genome).map(([skill, weight], idx) => (
                      <div key={idx} className="bg-black p-3 border-4 border-white group hover:border-red-400 transition-colors">
                        <div className="flex justify-between text-lg font-black mb-2 uppercase tracking-widest">
                          <span className="text-white group-hover:text-red-400 transition-colors">{skill}</span>
                          <span className="text-red-500">{Math.round(weight * 100)}%</span>
                        </div>
                        <div className="w-full bg-gray-900 h-4 border-2 border-gray-700 overflow-hidden relative">
                          <div className="bg-white h-full relative" style={{ width: `${Math.min(100, weight * 100)}%` }}>
                            {/* Animated scanline effect for progress bar */}
                            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white to-transparent w-full" style={{ animation: 'scanLine 2s linear infinite' }}></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-48 text-black font-black text-center border-4 border-dashed border-black mt-4">
                    <Layers className="h-16 w-16 mb-4 opacity-80" />
                    <p className="uppercase tracking-[0.2em] bg-black text-white px-4 py-2 mt-2 text-xl shadow-[4px_4px_0px_#fff]">UPLOAD RESUME TO GENERATE</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
              </div>
              
              {/* FACE 2: VAULT (RIGHT) - -90deg */}
              <div className="hub-face hub-face-right inverted">
        <div className="glass-panel p-6">
          <h3 className="text-xl font-semibold mb-6 flex items-center text-white">
            <History className="mr-2 h-5 w-5 text-indigo-400" />
            Resume Version History
          </h3>
          {profile.resume_vault.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Book className="mx-auto h-12 w-12 mb-4 opacity-30" />
              <p>Your vault is empty. Analyze a resume to automatically save it here.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {profile.resume_vault.map((item, idx) => (
                <div key={idx} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50 flex justify-between items-center hover:border-indigo-500/50 transition-colors">
                  <div>
                    <h4 className="text-lg text-white font-medium">Resume v{profile.resume_vault.length - idx}</h4>
                    <p className="text-sm text-slate-400">{new Date(item.timestamp).toLocaleString()}</p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className="bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full text-sm font-mono border border-indigo-500/30">
                      Score: {item.overall_score}/100
                    </span>
                    <button className="text-slate-400 hover:text-cyan-400 transition-colors" title="Download Archive">
                      <Download className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              )).reverse()}
            </div>
          )}
        </div>
              </div>

              {/* FACE 3: INTERVIEWS (BACK) - -180deg */}
              <div className="hub-face hub-face-back">
        <div className="glass-panel p-6">
          <h3 className="text-xl font-semibold mb-6 flex items-center text-white">
            <Star className="mr-2 h-5 w-5 text-emerald-400" />
            Interview Transcripts
          </h3>
          {profile.interview_vault.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <AlertTriangle className="mx-auto h-12 w-12 mb-4 opacity-30" />
              <p>You haven't completed any Socratic interviews yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {profile.interview_vault.map((session, idx) => (
                <div key={idx} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50 hover:border-emerald-500/50 transition-colors">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-lg text-white font-medium">Session {new Date(session.timestamp).toLocaleDateString()}</h4>
                      <p className="text-sm text-slate-400">Duration: {Math.round(session.duration / 60)} minutes</p>
                    </div>
                  </div>
                  <div className="bg-slate-900/50 p-3 rounded text-sm text-slate-300 italic border-l-2 border-emerald-500">
                    "{session.feedback.substring(0, 150)}..."
                  </div>
                </div>
              )).reverse()}
            </div>
          )}
        </div>
              </div>

              {/* FACE 4: INTEGRATIONS (LEFT) - -270deg */}
              <div className="hub-face hub-face-left inverted">
        <div className="space-y-6">
          <div className="p5-glitch-header" style={{ padding: '2rem', background: '#000', border: '4px solid #e60012', transform: 'skewX(-2deg)', boxShadow: '8px 8px 0px #e60012' }}>
            <h3 className="text-3xl font-black text-white uppercase tracking-widest" style={{ textShadow: '2px 2px 0px #e60012' }}>
              MCP / External Addons
            </h3>
            <p className="text-red-400 font-bold mt-2 font-mono">
              [ WARNING: LINKING EXTERNAL DATA SOURCES INCREASES INTELLIGENCE ]
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4">
            {[
              { id: 'google_drive', name: 'Google Drive', icon: <HardDrive size={32} color="#34a853" />, desc: 'Resume & Certificate Vault Sync', color: '#34a853' },
              { id: 'google_calendar', name: 'Google Calendar', icon: <Calendar size={32} color="#4285f4" />, desc: 'AI Interview Scheduler', color: '#4285f4' },
              { id: 'github', name: 'GitHub MCP', icon: <Github size={32} color="#f0f6fc" />, desc: 'Portfolio & Code Analysis', color: '#f0f6fc' },
              { id: 'notion', name: 'Notion MCP', icon: <Book size={32} color="#fff" />, desc: 'Learning Roadmap Sync', color: '#fff' },
              { id: 'slack', name: 'Slack Addon', icon: <MessageSquare size={32} color="#e01e5a" />, desc: 'Recruiter Notifications', color: '#e01e5a' },
              { id: 'neo4j', name: 'Neo4j MCP', icon: <Database size={32} color="#018bff" />, desc: 'Graph Database Skill Genome', color: '#018bff' }
            ].map((app) => {
              const isConnected = integrations[app.id];
              return (
                <div key={app.id} className="relative overflow-hidden group cursor-pointer" style={{ background: '#0a0a0a', border: `3px solid ${isConnected ? '#e60012' : '#333'}`, transform: 'skewX(-2deg)', boxShadow: isConnected ? '8px 8px 0px #e60012' : '6px 6px 0px #111', transition: 'all 0.2s ease-in-out' }}>
                  <div className="p-6 flex flex-col h-full relative z-10">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center space-x-4">
                        <div className="p-3 bg-black border-2" style={{ borderColor: app.color, transform: 'skewX(2deg)' }}>
                          <div style={{ transform: 'skewX(-2deg)' }}>{app.icon}</div>
                        </div>
                        <div style={{ transform: 'skewX(2deg)' }}>
                          <h4 className="text-2xl font-black text-white uppercase tracking-wider">{app.name}</h4>
                          <span className="text-sm font-bold px-2 py-1 bg-black text-white mt-2 inline-block shadow-[2px_2px_0px_#555]" style={{ border: `1px solid ${app.color}` }}>
                            {app.desc}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="mt-6 flex justify-end" style={{ transform: 'skewX(2deg)' }}>
                      <button 
                        onClick={() => handleToggleIntegration(app.id, isConnected)}
                        className="font-black uppercase tracking-widest px-8 py-3 transition-all hover:brightness-125"
                        style={{ 
                          background: isConnected ? '#e60012' : '#222', 
                          color: isConnected ? '#fff' : '#aaa',
                          border: `2px solid ${isConnected ? '#e60012' : '#555'}`,
                          transform: 'skewX(-8deg)',
                          boxShadow: isConnected ? '4px 4px 0px #000' : '4px 4px 0px #000'
                        }}
                      >
                        <span style={{ display: 'inline-block', transform: 'skewX(8deg)' }}>
                          {isConnected ? 'LINKED / ACTIVE' : 'CONNECT API'}
                        </span>
                      </button>
                    </div>
                  </div>
                  
                  {isConnected && (
                    <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                      <Lock className="w-32 h-32 text-red-500" style={{ transform: 'rotate(15deg)' }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
              </div>
          </div>
      </div>
    </div>
  );
}
