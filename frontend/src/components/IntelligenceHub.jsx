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
      const token = localStorage.getItem('access_token');
      const [resProfile, resInteg] = await Promise.all([
        fetch(`${API_URL}/api/hub/profile`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/hub/integrations`, { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      
      if (resProfile.ok) {
        const data = await resProfile.json();
        setProfile(data);
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
      const token = localStorage.getItem('access_token');
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
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
            🧠 Candidate Intelligence Hub
          </h2>
          <p className="text-slate-400 mt-1">
            Persistent AI Workspace & Career Vault
          </p>
        </div>
        <div className="flex space-x-2">
          <span className="bg-indigo-500/20 text-indigo-300 px-4 py-2 rounded-full text-sm font-mono border border-indigo-500/30 flex items-center">
            <Activity className="h-4 w-4 mr-2 text-indigo-400" />
            Health Score: {profile.career_health_score}/100
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-4 border-b border-slate-700/50 pb-2">
        <button 
          className={`px-4 py-2 rounded-t-lg transition-colors ${activeView === 'overview' ? 'bg-slate-800/80 text-white border-b-2 border-indigo-500' : 'text-slate-400 hover:text-white'}`}
          onClick={() => setActiveView('overview')}
        >
          Overview & Timeline
        </button>
        <button 
          className={`px-4 py-2 rounded-t-lg transition-colors ${activeView === 'vault' ? 'bg-slate-800/80 text-white border-b-2 border-cyan-500' : 'text-slate-400 hover:text-white'}`}
          onClick={() => setActiveView('vault')}
        >
          📂 Resume Vault
        </button>
        <button 
          className={`px-4 py-2 rounded-t-lg transition-colors ${activeView === 'interviews' ? 'bg-slate-800/80 text-white border-b-2 border-emerald-500' : 'text-slate-400 hover:text-white'}`}
          onClick={() => setActiveView('interviews')}
        >
          🎙️ Interview History
        </button>
        <button 
          className={`px-4 py-2 rounded-t-lg transition-colors ${activeView === 'integrations' ? 'bg-slate-800/80 text-white border-b-2 border-red-500' : 'text-slate-400 hover:text-white'}`}
          onClick={() => setActiveView('integrations')}
        >
          🔌 Integrations (MCP)
        </button>
      </div>

      {activeView === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-panel p-6 border-l-4 border-l-indigo-500">
            <h3 className="text-xl font-semibold mb-4 flex items-center text-white">
              <Database className="mr-2 h-5 w-5 text-indigo-400" />
              AI Memory & Weaknesses
            </h3>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm text-slate-400 uppercase tracking-wider mb-2">Identified Strengths</h4>
                <div className="flex flex-wrap gap-2">
                  {profile.ai_memory.strengths.length > 0 ? (
                    profile.ai_memory.strengths.map((s, i) => (
                      <span key={i} className="bg-emerald-500/20 text-emerald-300 px-3 py-1 rounded text-sm border border-emerald-500/30">{s}</span>
                    ))
                  ) : (
                    <span className="text-slate-500 italic">No data yet. Upload a resume.</span>
                  )}
                </div>
              </div>
              <div>
                <h4 className="text-sm text-slate-400 uppercase tracking-wider mb-2">Areas for Improvement</h4>
                <div className="flex flex-wrap gap-2">
                  {profile.ai_memory.weaknesses.length > 0 ? (
                    profile.ai_memory.weaknesses.map((w, i) => (
                      <span key={i} className="bg-red-500/20 text-red-300 px-3 py-1 rounded text-sm border border-red-500/30">{w}</span>
                    ))
                  ) : (
                    <span className="text-slate-500 italic">No data yet.</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="glass-panel p-6 border-l-4 border-l-cyan-500">
            <h3 className="text-xl font-semibold mb-4 flex items-center text-white">
              <TrendingUp className="mr-2 h-5 w-5 text-cyan-400" />
              Skill Genome Progression
            </h3>
            {Object.keys(profile.skill_genome).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(profile.skill_genome).map(([skill, weight], idx) => (
                  <div key={idx}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-300">{skill}</span>
                      <span className="text-cyan-400">{Math.round(weight * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-700/50 rounded-full h-2">
                      <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full" style={{ width: `${Math.min(100, weight * 100)}%` }}></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-32 text-slate-500">
                <Layers className="h-8 w-8 mb-2 opacity-50" />
                <p>Upload a resume to generate your Skill Genome</p>
              </div>
            )}
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
