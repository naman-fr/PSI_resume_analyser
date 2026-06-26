import React, { useState, useEffect } from 'react';
import { Layers, Database, Lock, TrendingUp, History, Star, Activity, AlertTriangle, Book, Download, ShieldCheck } from 'lucide-react';
import { useAuth } from '../AuthContext';

const API_URL = import.meta.env.VITE_API_URL || '';

export default function IntelligenceHub() {
  const { currentUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('overview');

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
    <div className="space-y-6 animate-fade-in pb-12">
      <div className="flex justify-between items-center bg-black p-4" style={{ transform: 'skewX(-5deg)', border: '4px solid var(--p5-red)', boxShadow: '8px 8px 0px var(--p5-red)' }}>
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

      {/* Tabs */}
      <div className="flex space-x-4 border-b-4 border-red-600 pb-0 pt-4">
        {[
          { id: 'overview', label: 'OVERVIEW & TIMELINE' },
          { id: 'vault', label: '📂 RESUME VAULT' },
          { id: 'interviews', label: '🎙️ INTERVIEWS' },
          { id: 'integrations', label: '🔌 INTEGRATIONS (MCP)' }
        ].map(tab => (
          <button 
            key={tab.id}
            className="px-6 py-3 font-black text-lg uppercase tracking-widest transition-all"
            style={{ 
              background: activeView === tab.id ? 'var(--p5-red)' : '#111', 
              color: activeView === tab.id ? '#fff' : '#666',
              border: '2px solid',
              borderColor: activeView === tab.id ? 'var(--p5-red)' : '#333',
              borderBottom: 'none',
              transform: 'skewX(-10deg)',
              transformOrigin: 'bottom'
            }}
            onClick={() => setActiveView(tab.id)}
          >
            <span style={{ display: 'inline-block', transform: 'skewX(10deg)' }}>{tab.label}</span>
          </button>
        ))}
      </div>

      {activeView === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <div className="p-6 bg-black text-white" style={{ border: '4px solid #fff', transform: 'skewX(-2deg)', boxShadow: '6px 6px 0px #333' }}>
            <div style={{ transform: 'skewX(2deg)' }}>
              <h3 className="text-2xl font-black mb-4 flex items-center text-white uppercase tracking-widest border-b-2 border-red-600 pb-2">
                <Database className="mr-3 h-6 w-6 text-red-500" />
                AI Memory Core
              </h3>
              <div className="space-y-6 mt-4">
                <div>
                  <h4 className="text-md font-bold text-red-500 uppercase tracking-widest mb-3 bg-white inline-block px-2 py-1 shadow-[2px_2px_0px_#f00]">
                    [ IDENTIFIED STRENGTHS ]
                  </h4>
                  <div className="flex flex-wrap gap-3">
                    {profile.ai_memory.strengths.length > 0 ? (
                      profile.ai_memory.strengths.map((s, i) => (
                        <span key={i} className="bg-red-600 text-white font-bold px-3 py-1 text-sm border-2 border-white shadow-[2px_2px_0px_#555] uppercase tracking-wider">{s}</span>
                      ))
                    ) : (
                      <span className="text-gray-500 italic font-mono font-bold">NO DATA. UPLOAD RESUME.</span>
                    )}
                  </div>
                </div>
                <div>
                  <h4 className="text-md font-bold text-black bg-white uppercase tracking-widest mb-3 inline-block px-2 py-1 shadow-[2px_2px_0px_#555]">
                    [ IMPROVEMENT TARGETS ]
                  </h4>
                  <div className="flex flex-wrap gap-3">
                    {profile.ai_memory.weaknesses.length > 0 ? (
                      profile.ai_memory.weaknesses.map((w, i) => (
                        <span key={i} className="bg-gray-800 text-gray-300 font-bold px-3 py-1 text-sm border-2 border-gray-600 uppercase tracking-wider">{w}</span>
                      ))
                    ) : (
                      <span className="text-gray-500 italic font-mono font-bold">NO DATA.</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 bg-red-600 text-white" style={{ border: '4px solid #000', transform: 'skewX(-2deg)', boxShadow: '6px 6px 0px #000' }}>
            <div style={{ transform: 'skewX(2deg)' }}>
              <h3 className="text-2xl font-black mb-4 flex items-center text-white uppercase tracking-widest border-b-2 border-black pb-2">
                <TrendingUp className="mr-3 h-6 w-6 text-black" />
                Skill Genome Matrix
              </h3>
              {Object.keys(profile.skill_genome).length > 0 ? (
                <div className="space-y-4 mt-4">
                  {Object.entries(profile.skill_genome).map(([skill, weight], idx) => (
                    <div key={idx} className="bg-black p-2 border-2 border-white">
                      <div className="flex justify-between text-md font-bold mb-1 uppercase tracking-widest">
                        <span className="text-white">{skill}</span>
                        <span className="text-red-500">{Math.round(weight * 100)}%</span>
                      </div>
                      <div className="w-full bg-gray-800 h-3 border border-gray-600">
                        <div className="bg-white h-full" style={{ width: `${Math.min(100, weight * 100)}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-32 text-black font-bold text-center">
                  <Layers className="h-10 w-10 mb-2 opacity-80" />
                  <p className="uppercase tracking-widest bg-black text-white px-2 py-1 mt-2">UPLOAD RESUME TO GENERATE</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeView === 'vault' && (
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
      )}

      {activeView === 'interviews' && (
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
      )}

      {activeView === 'integrations' && (
        <div className="space-y-6">
          <div className="p5-glitch-header" style={{ padding: '2rem', background: '#000', border: '4px solid #e60012', transform: 'skewX(-2deg)', boxShadow: '8px 8px 0px #e60012' }}>
            <h3 className="text-3xl font-black text-white uppercase tracking-widest" style={{ textShadow: '2px 2px 0px #e60012' }}>
              MCP / External Addons
            </h3>
            <p className="text-red-400 font-bold mt-2 font-mono">
              [ WARNING: LINKING EXTERNAL DATA SOURCES INCREASES INTELLIGENCE ]
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { id: 'google_drive', name: 'Google Drive', icon: '📁', desc: 'Resume & Certificate Vault Sync', color: '#34a853' },
              { id: 'google_calendar', name: 'Google Calendar', icon: '📅', desc: 'AI Interview Scheduler', color: '#4285f4' },
              { id: 'github', name: 'GitHub MCP', icon: '🐙', desc: 'Portfolio & Code Analysis', color: '#f0f6fc' },
              { id: 'notion', name: 'Notion MCP', icon: '📝', desc: 'Learning Roadmap Sync', color: '#fff' },
              { id: 'slack', name: 'Slack Addon', icon: '💬', desc: 'Recruiter Notifications', color: '#e01e5a' },
              { id: 'neo4j', name: 'Neo4j MCP', icon: '🗄️', desc: 'Graph Database Skill Genome', color: '#018bff' }
            ].map((app) => {
              const isConnected = integrations[app.id];
              return (
                <div key={app.id} className="relative overflow-hidden" style={{ background: '#111', border: `2px solid ${isConnected ? '#e60012' : '#333'}`, transform: 'skewX(-2deg)', transition: 'all 0.3s' }}>
                  <div className="p-6 flex flex-col h-full relative z-10">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center space-x-3">
                        <span className="text-4xl">{app.icon}</span>
                        <div>
                          <h4 className="text-xl font-bold text-white uppercase tracking-wider">{app.name}</h4>
                          <span className="text-xs font-mono font-bold px-2 py-1 bg-black text-white mt-1 inline-block" style={{ border: `1px solid ${app.color}` }}>
                            {app.desc}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="mt-auto pt-4 flex justify-end">
                      <button 
                        onClick={() => handleToggleIntegration(app.id, isConnected)}
                        className="font-bold uppercase tracking-widest px-6 py-2 transition-all"
                        style={{ 
                          background: isConnected ? '#e60012' : 'transparent', 
                          color: isConnected ? '#fff' : '#888',
                          border: `2px solid ${isConnected ? '#e60012' : '#555'}`,
                          transform: 'skewX(-5deg)',
                          boxShadow: isConnected ? '4px 4px 0px #000' : 'none'
                        }}
                      >
                        {isConnected ? 'LINKED' : 'CONNECT'}
                      </button>
                    </div>
                  </div>
                  
                  {isConnected && (
                    <div className="absolute top-0 right-0 p-2 opacity-10">
                      <Lock className="w-24 h-24 text-red-500" style={{ transform: 'rotate(15deg)' }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
