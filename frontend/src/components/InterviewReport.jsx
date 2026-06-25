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
    <div className="min-h-screen bg-[#080808] text-white p-4 md:p-12 overflow-y-auto relative" style={{
      backgroundImage: 'radial-gradient(#e60012 1px, transparent 1px)',
      backgroundSize: '24px 24px'
    }}>
      <div className="absolute inset-0 bg-black/50 pointer-events-none"></div>

      <div className="max-w-6xl mx-auto space-y-12 relative z-10 animate-[slashReveal_0.8s_ease-out_both]">
        
        {/* Header - Persona 5 Style */}
        <div className="bg-[#e60012] border-4 border-white p-8 shadow-[8px_8px_0px_#000] transform skew-x-[-2deg] rotate-[-1deg] relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="absolute top-0 left-0 right-0 h-1 bg-white/50 animate-[scanLine_3s_linear_infinite]"></div>
          <div>
            <div className="inline-block bg-black text-[#fff200] px-4 py-1 font-black uppercase tracking-widest text-sm mb-4 transform skew-x-[-10deg] border-2 border-white shadow-[4px_4px_0px_#000]">
              MISSION ACCOMPLISHED
            </div>
            <h1 className="text-5xl md:text-6xl font-black uppercase text-white drop-shadow-[4px_4px_0px_#000] tracking-tighter" style={{ fontFamily: 'Outfit, sans-serif', animation: 'glitchText 4s infinite' }}>
              Cognitive Audit
            </h1>
            <p className="text-white bg-black inline-block px-3 py-1 font-bold mt-2 transform skew-x-[-5deg]">
              FINAL SYNTHESIS LOG
            </p>
          </div>
          <button 
            onClick={onClose}
            className="px-8 py-4 bg-black text-white hover:bg-white hover:text-black border-4 border-white transform skew-x-[-5deg] transition-all font-black text-xl uppercase shadow-[6px_6px_0px_rgba(0,0,0,0.5)] hover:translate-y-[-4px] hover:shadow-[10px_10px_0px_#e60012]"
          >
            Return
          </button>
        </div>

        {/* Top Metrics - Jagged Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 bg-[#121212] border-4 border-white p-8 transform skew-x-[-3deg] shadow-[8px_8px_0px_#000] hover:-translate-y-2 hover:shadow-[12px_12px_0px_#e60012] transition-all relative overflow-hidden group">
            <h3 className="text-xl font-black text-[#e60012] uppercase tracking-[0.2em] mb-4 drop-shadow-[2px_2px_0px_#000]">Hiring Probability</h3>
            <div className="flex items-baseline gap-4 mb-6">
              <span className="text-8xl md:text-9xl font-black text-white drop-shadow-[6px_6px_0px_#e60012] group-hover:scale-110 transition-transform">
                {hiring_probability}%
              </span>
            </div>
            <div className="w-full bg-black h-6 border-4 border-white p-1">
              <div 
                className="h-full bg-[#fff200]" 
                style={{ width: `${hiring_probability}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-[#121212] border-4 border-white p-8 transform skew-x-[3deg] shadow-[8px_8px_0px_#000] hover:-translate-y-2 hover:shadow-[12px_12px_0px_#fff200] transition-all flex flex-col justify-center items-center text-center">
            <h3 className="text-xl font-black text-white bg-[#e60012] px-4 py-2 uppercase tracking-[0.1em] mb-6 transform skew-x-[-10deg]">Judge Verdict</h3>
            <div className={`text-4xl md:text-5xl font-black transform scale-125 ${
              recommendation?.includes("HIRE") ? 'text-[#fff200] drop-shadow-[4px_4px_0px_#e60012]' : 'text-white drop-shadow-[4px_4px_0px_#e60012]'
            }`}>
              {recommendation}
            </div>
          </div>
        </div>

        {/* Strengths / Weaknesses */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-[#1a1a1c] border-4 border-[#fff200] p-8 shadow-[8px_8px_0px_#000] transform skew-x-[2deg] hover:-translate-y-2 transition-all">
            <h3 className="text-[#fff200] font-black text-2xl uppercase mb-6 flex items-center gap-3 drop-shadow-[2px_2px_0px_#000]">
              <span className="text-4xl">✦</span> Core Strengths
            </h3>
            <ul className="space-y-4">
              {strengths?.map((s, i) => (
                <li key={i} className="text-white text-lg font-bold flex gap-4 items-start leading-tight bg-black p-4 border-l-4 border-[#fff200] transform skew-x-[-2deg]">
                  {s}
                </li>
              ))}
            </ul>
          </div>
          
          <div className="bg-[#1a1a1c] border-4 border-[#e60012] p-8 shadow-[8px_8px_0px_#000] transform skew-x-[-2deg] hover:-translate-y-2 transition-all">
            <h3 className="text-[#e60012] font-black text-2xl uppercase mb-6 flex items-center gap-3 drop-shadow-[2px_2px_0px_#000]">
              <span className="text-4xl">✕</span> Weaknesses
            </h3>
            <ul className="space-y-4">
              {weaknesses?.map((w, i) => (
                <li key={i} className="text-white text-lg font-bold flex gap-4 items-start leading-tight bg-black p-4 border-l-4 border-[#e60012] transform skew-x-[2deg]">
                  {w}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Committee Debate Log */}
        <div className="bg-[#121212] border-4 border-white p-8 md:p-12 shadow-[10px_10px_0px_#000] relative mt-12">
          <div className="absolute -top-6 left-8 bg-[#e60012] text-white border-4 border-white px-6 py-2 transform skew-x-[-10deg] font-black text-2xl uppercase shadow-[4px_4px_0px_#000]">
            Swarm Transcript
          </div>
          
          <div className="space-y-6 mt-8">
            {debate?.map((d, i) => (
              <div key={i} className="flex flex-col md:flex-row gap-4 items-start group">
                <div className="flex-shrink-0 bg-white text-black border-4 border-black px-4 py-3 transform skew-x-[-15deg] font-black text-lg uppercase shadow-[4px_4px_0px_#e60012] group-hover:bg-[#fff200] transition-colors w-48 text-center">
                  <span className="inline-block transform skew-x-[15deg]">{d.agent}</span>
                </div>
                <div className="flex-1 bg-black text-white border-2 border-white/20 p-5 font-bold text-lg transform skew-x-[-2deg] shadow-[4px_4px_0px_rgba(255,255,255,0.1)] group-hover:border-[#e60012] transition-colors relative">
                  <div className="absolute top-2 left-2 text-[#e60012] text-4xl opacity-50 font-serif">"</div>
                  <div className="relative z-10 pl-6">{d.opinion}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
