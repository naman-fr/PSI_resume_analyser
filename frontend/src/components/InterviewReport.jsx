import React from 'react';

export default function InterviewReport({ report, transcript, onClose }) {
  if (!report) return null;

  const {
    hiring_probability,
    recommendation,
    strengths,
    weaknesses,
    debate
  } = report;

  return (
    <div className="min-h-screen bg-[#050505] text-white p-4 md:p-12 overflow-y-auto" style={{
      backgroundImage: 'radial-gradient(circle at 50% 0%, rgba(30, 58, 138, 0.15) 0%, transparent 50%), radial-gradient(circle at 100% 100%, rgba(16, 185, 129, 0.1) 0%, transparent 50%)'
    }}>
      <div className="max-w-6xl mx-auto space-y-12 animate-in fade-in slide-in-from-bottom-8 duration-700">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-white/5 pb-8 gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-semibold tracking-widest uppercase text-blue-400">
                AI Agent Swarm Complete
              </span>
            </div>
            <h1 className="text-4xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400 tracking-tight">
              Cognitive Interview Audit
            </h1>
            <p className="text-gray-400 mt-2 text-lg">Final Hiring Committee Synthesis & Debate Log</p>
          </div>
          <button 
            onClick={onClose}
            className="px-8 py-3 bg-white/5 hover:bg-white/10 border border-white/10 backdrop-blur-md rounded-2xl transition-all font-medium flex items-center gap-2 hover:shadow-[0_0_20px_rgba(255,255,255,0.05)]"
          >
            <span>Exit to Dashboard</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>

        {/* Top Metrics Hero */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 p-8 md:p-10 rounded-[2rem] relative overflow-hidden group hover:border-blue-500/30 transition-colors">
            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/20 blur-[100px] rounded-full group-hover:bg-blue-500/30 transition-colors duration-700"></div>
            <h3 className="text-sm font-bold text-blue-400 uppercase tracking-[0.2em] mb-4">Final Hiring Probability</h3>
            <div className="flex items-baseline gap-4 mb-8">
              <span className="text-7xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white to-gray-500">
                {hiring_probability}%
              </span>
            </div>
            <div className="w-full bg-white/5 h-3 rounded-full overflow-hidden border border-white/5">
              <div 
                className="h-full bg-gradient-to-r from-blue-600 to-emerald-500 rounded-full shadow-[0_0_15px_rgba(59,130,246,0.5)] relative" 
                style={{ width: `${hiring_probability}%` }}
              >
                <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
              </div>
            </div>
          </div>

          <div className="bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 p-8 md:p-10 rounded-[2rem] relative overflow-hidden flex flex-col justify-center items-center text-center group hover:border-white/20 transition-colors">
            <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 blur-[80px] rounded-full ${
              recommendation?.includes("HIRE") ? 'bg-emerald-500/20' : 'bg-red-500/20'
            }`}></div>
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-[0.2em] mb-6 relative z-10">Committee Verdict</h3>
            <div className={`text-4xl md:text-5xl font-black relative z-10 ${
              recommendation?.includes("HIRE") ? 'text-emerald-400 drop-shadow-[0_0_15px_rgba(16,185,129,0.3)]' : 'text-red-400 drop-shadow-[0_0_15px_rgba(239,68,68,0.3)]'
            }`}>
              {recommendation}
            </div>
          </div>
        </div>

        {/* Strengths / Weaknesses */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gradient-to-br from-[#0a0a0a] to-[#051510] border border-emerald-500/20 p-8 rounded-[2rem] hover:border-emerald-500/40 transition-colors relative overflow-hidden">
             <div className="absolute top-0 right-0 p-8 opacity-10">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
             </div>
            <h3 className="text-emerald-400 font-bold mb-6 flex items-center gap-3 text-xl">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)]"></span>
              </div>
              Core Strengths
            </h3>
            <ul className="space-y-4">
              {strengths?.map((s, i) => (
                <li key={i} className="text-gray-300 text-base flex gap-4 items-start leading-relaxed">
                  <span className="text-emerald-500 mt-1">✦</span> {s}
                </li>
              ))}
            </ul>
          </div>
          
          <div className="bg-gradient-to-br from-[#0a0a0a] to-[#150505] border border-red-500/20 p-8 rounded-[2rem] hover:border-red-500/40 transition-colors relative overflow-hidden">
             <div className="absolute top-0 right-0 p-8 opacity-10">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
             </div>
            <h3 className="text-red-400 font-bold mb-6 flex items-center gap-3 text-xl">
              <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400 shadow-[0_0_10px_rgba(239,68,68,0.8)]"></span>
              </div>
              Identified Weaknesses
            </h3>
            <ul className="space-y-4">
              {weaknesses?.map((w, i) => (
                <li key={i} className="text-gray-300 text-base flex gap-4 items-start leading-relaxed">
                  <span className="text-red-500 mt-1">✕</span> {w}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Committee Debate Log */}
        <div className="bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 p-8 md:p-12 rounded-[2rem]">
          <div className="flex items-center gap-4 mb-10">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
            </div>
            <div>
              <h3 className="font-bold text-2xl tracking-tight">Agent Swarm Transcript</h3>
              <p className="text-gray-400 text-sm mt-1">Uncensored debate log from the LangGraph committee.</p>
            </div>
          </div>
          
          <div className="space-y-8 relative before:absolute before:inset-0 before:ml-6 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-white/10 before:to-transparent">
            {debate?.map((d, i) => (
              <div key={i} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                <div className="flex items-center justify-center w-12 h-12 rounded-full border-4 border-[#050505] bg-[#111] text-indigo-400 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 transition-transform duration-300 group-hover:scale-110 group-hover:bg-indigo-500/20 group-hover:border-indigo-500/50">
                  <span className="text-xs font-black">{d.agent.substring(0, 2).toUpperCase()}</span>
                </div>
                <div className="w-[calc(100%-4rem)] md:w-[calc(50%-3rem)] p-6 rounded-2xl bg-white/5 border border-white/10 shadow-[0_0_20px_rgba(0,0,0,0.2)] group-hover:bg-white/10 transition-colors">
                  <div className="font-bold text-indigo-300 mb-2">{d.agent}</div>
                  <div className="text-gray-300 leading-relaxed text-sm md:text-base">{d.opinion}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
