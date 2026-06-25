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
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8 overflow-y-auto">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-center border-b border-white/10 pb-6">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
              Cognitive Interview Audit
            </h1>
            <p className="text-gray-400 mt-2">Final Hiring Committee Synthesis</p>
          </div>
          <button 
            onClick={onClose}
            className="px-6 py-2 bg-white/10 hover:bg-white/20 rounded-xl transition-colors font-medium"
          >
            Exit to Dashboard
          </button>
        </div>

        {/* Top Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-[#111] border border-white/10 p-6 rounded-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 blur-3xl rounded-full"></div>
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Hiring Probability</h3>
            <div className="flex items-baseline gap-2">
              <span className="text-5xl font-black text-blue-400">{hiring_probability}%</span>
            </div>
            <div className="w-full bg-black h-2 rounded-full mt-4">
              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${hiring_probability}%` }}></div>
            </div>
          </div>

          <div className="bg-[#111] border border-white/10 p-6 rounded-2xl relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-32 h-32 blur-3xl rounded-full ${
              recommendation.includes("HIRE") ? 'bg-emerald-500/10' : 'bg-red-500/10'
            }`}></div>
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">Judge Recommendation</h3>
            <div className="flex items-baseline gap-2">
              <span className={`text-4xl font-black ${
                recommendation.includes("HIRE") ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {recommendation}
              </span>
            </div>
          </div>
        </div>

        {/* Strengths / Weaknesses */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-[#111] border border-emerald-500/20 p-6 rounded-2xl">
            <h3 className="text-emerald-400 font-bold mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Core Strengths
            </h3>
            <ul className="space-y-3">
              {strengths?.map((s, i) => (
                <li key={i} className="text-gray-300 text-sm flex gap-3">
                  <span className="text-emerald-500">✓</span> {s}
                </li>
              ))}
            </ul>
          </div>
          
          <div className="bg-[#111] border border-red-500/20 p-6 rounded-2xl">
            <h3 className="text-red-400 font-bold mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500"></span> Identified Weaknesses
            </h3>
            <ul className="space-y-3">
              {weaknesses?.map((w, i) => (
                <li key={i} className="text-gray-300 text-sm flex gap-3">
                  <span className="text-red-500">✕</span> {w}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Committee Debate Log */}
        <div className="bg-[#111] border border-white/10 p-6 rounded-2xl">
          <h3 className="font-bold mb-6 text-xl">Hiring Committee Debate Transcript</h3>
          <div className="space-y-6">
            {debate?.map((d, i) => (
              <div key={i} className="border-l-2 border-white/10 pl-4 py-1">
                <div className="font-bold text-indigo-400 mb-1">{d.agent}</div>
                <div className="text-sm text-gray-300 leading-relaxed">{d.opinion}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
