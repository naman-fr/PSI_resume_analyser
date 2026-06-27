import React, { useState, useEffect, useCallback } from 'react';
import { Layers, Database, Lock, TrendingUp, History, Star, Activity, AlertTriangle, Book, Download, ShieldCheck, HardDrive, Calendar, Github, MessageSquare } from 'lucide-react';
import { useAuth } from '../AuthContext';
import ThreeGem from './ThreeGem';
import useEmblaCarousel from 'embla-carousel-react';

const API_URL = import.meta.env.VITE_API_URL || '';

export default function IntelligenceHub() {
  const { currentUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true, skipSnaps: false });

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setSelectedIndex(emblaApi.selectedScrollSnap());
  }, [emblaApi, setSelectedIndex]);

  useEffect(() => {
    if (!emblaApi) return;
    onSelect();
    emblaApi.on('select', onSelect);
    emblaApi.on('reInit', onSelect);
  }, [emblaApi, onSelect]);

  const scrollTo = useCallback((index) => {
    if (emblaApi) emblaApi.scrollTo(index);
  }, [emblaApi]);


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
      <div className="hub-centered-loader">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="hub-glass-panel" style={{ textAlign: 'center', color: 'var(--p5-red)' }}>
        <ShieldCheck className="mx-auto h-12 w-12 mb-4" />
        <h2>Authentication Error</h2>
        <p>You must be logged in to access the Candidate Intelligence Hub.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', overflow: 'hidden', paddingBottom: '3rem' }}>
      {/* Diegetic Background Halftone Texture */}
      <div className="fixed top-0 left-0 w-screen h-screen -z-10 opacity-10 pointer-events-none" style={{ background: 'radial-gradient(var(--p5-red) 15%, transparent 16%), radial-gradient(var(--p5-red) 15%, transparent 16%)', backgroundSize: '20px 20px', backgroundPosition: '0 0, 10px 10px', animation: 'bgStripeScroll 20s linear infinite' }}></div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--p5-black)', padding: '1rem', width: '100%', maxWidth: '1200px', marginBottom: '2rem', transform: 'skewX(-5deg)', border: '4px solid var(--p5-red)', boxShadow: '8px 8px 0px var(--p5-red)' }}>
        <div style={{ transform: 'skewX(5deg)' }}>
          <h2 className="text-4xl font-black text-white uppercase tracking-widest" style={{ textShadow: '2px 2px 0px var(--p5-red)', fontFamily: 'var(--ff-display)' }}>
            🧠 Candidate Intelligence Hub
          </h2>
          <p className="text-red-400 mt-1 font-bold tracking-widest uppercase text-sm">
            [ PERSISTENT AI WORKSPACE & CAREER VAULT ]
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', transform: 'skewX(5deg)' }}>
          <span style={{ background: 'var(--p5-white)', color: 'var(--p5-black)', padding: '0.5rem 1rem', fontSize: '1.25rem', fontWeight: 900, fontFamily: 'monospace', border: '2px solid var(--p5-black)', display: 'flex', alignItems: 'center', boxShadow: '4px 4px 0px var(--p5-red)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <Activity className="h-6 w-6 mr-2 text-red-600" />
            Health: {profile.career_health_score}/100
          </span>
        </div>
      </div>

      {/* Static Navigation Triggers */}
      <div className="hub-nav">
        {[
          { id: 'overview', label: '01 PROFILE', index: 0 },
          { id: 'vault', label: '02 STATS', index: 1 },
          { id: 'interviews', label: '03 ARCHIVE', index: 2 },
          { id: 'integrations', label: '04 CONTACT', index: 3 }
        ].map(tab => (
          <button 
            key={tab.id}
            onClick={() => scrollTo(tab.index)}
            className="hub-nav-btn"
            style={{ 
              background: selectedIndex === tab.index ? 'var(--p5-red)' : '#fff', 
              color: selectedIndex === tab.index ? '#fff' : '#000',
              clipPath: selectedIndex === tab.index ? 'polygon(0 0, 100% 0, 100% 100%, 10% 100%)' : 'polygon(10% 0, 100% 0, 90% 100%, 0 100%)',
              border: 'none',
              transform: selectedIndex === tab.index ? 'scale(1.05) translateX(10px)' : 'none'
            }}
          >
            <span className="block transform" style={{ transform: 'skewX(-10deg)' }}>
              {tab.label}
            </span>
          </button>
        ))}
      </div>

      {/* Premium Carousel Viewport */}
      <div className="embla" ref={emblaRef}>
          <div className="embla__container">
              
              {/* SLIDE 1: ABOUT */}
              <div className="embla__slide">
                <div className="hub-slide">

        <div style={{ position: 'relative', marginTop: '3rem', marginBottom: '2rem' }}>
          {/* 3D Background Element */}
          <div style={{ position: 'absolute', inset: 0, zIndex: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.7, pointerEvents: 'none', transform: 'scale(1.5)' }}>
            <div style={{ width: '100%', height: '600px', pointerEvents: 'auto' }}>
              <ThreeGem />
            </div>
          </div>

          <div className="hub-grid">
            <div className="hub-card" style={{ transform: 'skewX(-3deg)' }}>
              <div style={{ transform: 'skewX(3deg)' }}>
                <h3 className="hub-title-sm" style={{ borderColor: 'var(--p5-red)' }}>
                  <Database className="mr-4 h-8 w-8 text-red-500 animate-pulse" />
                  AI Memory Core
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginTop: '1.5rem' }}>
                  <div>
                    <h4 className="hub-tag">
                      [ IDENTIFIED STRENGTHS ]
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '0.5rem' }}>
                      {profile.ai_memory.strengths.length > 0 ? (
                        profile.ai_memory.strengths.map((s, i) => (
                          <span key={i} className="hub-badge">{s}</span>
                        ))
                      ) : (
                        <span className="text-gray-400 italic font-mono font-bold">NO DATA. UPLOAD RESUME.</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <h4 className="hub-tag inverted">
                      [ IMPROVEMENT TARGETS ]
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '0.5rem' }}>
                      {profile.ai_memory.weaknesses.length > 0 ? (
                        profile.ai_memory.weaknesses.map((w, i) => (
                          <span key={i} className="hub-badge inverted">{w}</span>
                        ))
                      ) : (
                        <span className="text-gray-400 italic font-mono font-bold">NO DATA.</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="hub-card inverted" style={{ transform: 'skewX(-3deg)' }}>
              <div style={{ transform: 'skewX(3deg)' }}>
                <h3 className="hub-title-sm" style={{ borderColor: 'var(--p5-black)' }}>
                  <TrendingUp className="mr-4 h-8 w-8 text-white" />
                  Skill Genome Matrix
                </h3>
                {Object.keys(profile.skill_genome).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1.5rem' }}>
                    {Object.entries(profile.skill_genome).map(([skill, weight], idx) => (
                      <div key={idx} style={{ background: 'var(--p5-black)', padding: '0.75rem', border: '4px solid var(--p5-white)', transition: 'border-color 0.2s' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.125rem', fontWeight: 900, marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                          <span style={{ color: '#F5F5DC', transition: 'color 0.2s' }}>{skill}</span>
                          <span style={{ color: '#4ADE80' }}>{Math.round(weight * 100)}%</span>
                        </div>
                        <div className="hub-progress-bar">
                          <div className="hub-progress-fill" style={{ width: `${Math.min(100, weight * 100)}%` }}>
                            {/* Animated scanline effect for progress bar */}
                            <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to bottom, transparent, rgba(255,255,255,0.5), transparent)', width: '100%', animation: 'scanLine 2s linear infinite', animation: 'scanLine 2s linear infinite' }}></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '12rem', color: 'var(--p5-black)', fontWeight: 900, textAlign: 'center', border: '4px dashed var(--p5-black)', marginTop: '1rem' }}>
                    <Layers className="h-16 w-16 mb-4 opacity-80" />
                    <p style={{ textTransform: 'uppercase', letterSpacing: '0.2em', background: 'var(--p5-black)', color: 'var(--p5-white)', padding: '0.5rem 1rem', marginTop: '0.5rem', fontSize: '1.25rem', boxShadow: '4px 4px 0px var(--p5-white)' }}>UPLOAD RESUME TO GENERATE</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
                </div>
              </div>
              
              {/* SLIDE 2: VAULT */}
              <div className="embla__slide">
                <div className="hub-slide inverted">
        <div className="hub-glass-panel">
          <h3 className="hub-title-sm" style={{ color: 'var(--p5-white)', borderColor: 'var(--p5-white)', fontSize: '1.25rem' }}>
            <History className="mr-2 h-5 w-5 text-indigo-400" />
            Resume Version History
          </h3>
          {profile.resume_vault.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: '#888' }}>
              <Book className="mx-auto h-12 w-12 mb-4 opacity-30" />
              <p>Your vault is empty. Analyze a resume to automatically save it here.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {profile.resume_vault.map((item, idx) => (
                <div key={idx} style={{ background: 'rgba(0,0,0,0.5)', padding: '1rem', border: '2px solid #444', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h4 style={{ fontSize: '1.125rem', color: 'var(--p5-white)', fontWeight: 'bold' }}>Resume v{profile.resume_vault.length - idx}</h4>
                    <p style={{ fontSize: '0.875rem', color: '#888' }}>{new Date(item.timestamp).toLocaleString()}</p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ background: '#303f9f', color: '#fff', padding: '0.25rem 0.75rem', borderRadius: '999px', fontSize: '0.875rem', fontFamily: 'monospace' }}>
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
              </div>

              {/* SLIDE 3: INTERVIEWS */}
              <div className="embla__slide">
                <div className="hub-slide">
        <div className="hub-glass-panel">
          <h3 className="hub-title-sm" style={{ color: 'var(--p5-white)', borderColor: 'var(--p5-white)', fontSize: '1.25rem' }}>
            <Star className="mr-2 h-5 w-5 text-emerald-400" />
            Interview Transcripts
          </h3>
          {profile.interview_vault.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 0', color: '#888' }}>
              <AlertTriangle className="mx-auto h-12 w-12 mb-4 opacity-30" />
              <p>You haven't completed any Socratic interviews yet.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {profile.interview_vault.map((session, idx) => (
                <div key={idx} style={{ background: 'rgba(0,0,0,0.5)', padding: '1rem', border: '2px solid #444' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <div>
                      <h4 style={{ fontSize: '1.125rem', color: 'var(--p5-white)', fontWeight: 'bold' }}>Session {new Date(session.timestamp).toLocaleDateString()}</h4>
                      <p style={{ fontSize: '0.875rem', color: '#888' }}>Duration: {Math.round(session.duration / 60)} minutes</p>
                    </div>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.8)', padding: '0.75rem', fontSize: '0.875rem', color: '#ccc', fontStyle: 'italic', borderLeft: '2px solid #4caf50' }}>
                    "{session.feedback.substring(0, 150)}..."
                  </div>
                </div>
              )).reverse()}
            </div>
          )}
        </div>
                </div>
              </div>

              {/* SLIDE 4: INTEGRATIONS */}
              <div className="embla__slide">
                <div className="hub-slide inverted">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="p5-glitch-header" style={{ padding: '2rem', background: '#000', border: '4px solid #e60012', transform: 'skewX(-2deg)', boxShadow: '8px 8px 0px #e60012' }}>
            <h3 className="text-3xl font-black text-white uppercase tracking-widest" style={{ textShadow: '2px 2px 0px #e60012' }}>
              MCP / External Addons
            </h3>
            <p className="text-red-400 font-bold mt-2 font-mono">
              [ WARNING: LINKING EXTERNAL DATA SOURCES INCREASES INTELLIGENCE ]
            </p>
          </div>

          <div className="hub-integration-grid">
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
                <div key={app.id} style={{ position: 'relative', overflow: 'hidden', cursor: 'pointer', background: '#0a0a0a', transition: 'all 0.2s ease-in-out', background: '#0a0a0a', border: `3px solid ${isConnected ? '#e60012' : '#333'}`, transform: 'skewX(-2deg)', boxShadow: isConnected ? '8px 8px 0px #e60012' : '6px 6px 0px #111', transition: 'all 0.2s ease-in-out' }}>
                  <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', height: '100%', position: 'relative', zIndex: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ padding: '0.75rem', background: 'var(--p5-black)', border: '2px solid', borderColor: app.color, transform: 'skewX(2deg)' }}>
                          <div style={{ transform: 'skewX(-2deg)' }}>{app.icon}</div>
                        </div>
                        <div style={{ transform: 'skewX(2deg)' }}>
                          <h4 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--p5-white)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{app.name}</h4>
                          <span style={{ fontSize: '0.875rem', fontWeight: 'bold', padding: '0.25rem 0.5rem', background: 'var(--p5-black)', color: 'var(--p5-white)', marginTop: '0.5rem', display: 'inline-block', boxShadow: '2px 2px 0px #555', border: `1px solid ${app.color}` }}>
                            {app.desc}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', transform: 'skewX(2deg)', transform: 'skewX(2deg)' }}>
                      <button 
                        onClick={() => handleToggleIntegration(app.id, isConnected)}
                        style={{ fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.1em', padding: '0.75rem 2rem', transition: 'all 0.2s', cursor: 'pointer', 
background: isConnected ? '#e60012' : '#222', 
                          color: isConnected ? '#fff' : '#aaa',
                          border: `2px solid ${isConnected ? '#e60012' : '#555'}`,
                          transform: 'skewX(-8deg)',
                          boxShadow: isConnected ? '4px 4px 0px #000' : '4px 4px 0px #000' }}
                      >
                        <span style={{ display: 'inline-block', transform: 'skewX(8deg)' }}>
                          {isConnected ? 'LINKED / ACTIVE' : 'CONNECT API'}
                        </span>
                      </button>
                    </div>
                  </div>
                  
                  {isConnected && (
                    <div style={{ position: 'absolute', top: 0, right: 0, padding: '1rem', opacity: 0.1, pointerEvents: 'none' }}>
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
          
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '2rem', paddingBottom: '1rem' }}>
            {[0, 1, 2, 3].map((index) => (
              <div 
                key={index} 
                onClick={() => scrollTo(index)}
                className={`embla-dot ${index === selectedIndex ? 'is-active' : ''}`} 
              />
            ))}
          </div>
      </div>
    </div>
  );
}
