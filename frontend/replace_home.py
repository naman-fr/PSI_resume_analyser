
with open('src/App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "      {/* ── TAB CONTENT: ENTERPRISE PORTAL ────────────────────────── */}"
end_marker = "      {/* ── TAB CONTENT: ANALYZE RESUME ───────────────────────────── */}"

if start_marker in content and end_marker in content:
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    new_home = '''      {/* ── HEIST BRIEFING (PREMIUM 3D HOME) ────────────────────────── */}
      {activeTab === 'home' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', paddingBottom: '4rem' }}>
          
          <div style={{
            background: 'var(--p5-red)',
            color: 'var(--p5-white)',
            border: '4px solid var(--p5-white)',
            padding: '1.5rem',
            transform: 'skewX(-4deg) rotate(-1deg)',
            boxShadow: '12px 12px 0px #000',
            position: 'relative',
            animation: 'shakeEntry 0.6s var(--ease-p5)'
          }}>
            <h2 style={{ fontFamily: 'var(--font-title)', fontSize: '2.5rem', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
              Heist Briefing
            </h2>
            <p style={{ fontSize: '1rem', fontWeight: 800, opacity: 0.9 }}>
              Select your target operation below to infiltrate the candidate data.
            </p>
          </div>

          <div className="p5-heist-deck">
            
            {/* CALLING CARD 1 */}
            <div className="p5-heist-card" onClick={() => { setActiveTab('analyze'); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
              <div className="p5-heist-card-content">
                <span className="badge badge-purple" style={{ marginBottom: '1rem', display: 'inline-block' }}>OPERATION 01</span>
                <h3 style={{ fontSize: '2rem', fontFamily: 'var(--font-title)', fontWeight: 900, color: 'var(--p5-yellow)', textTransform: 'uppercase', lineHeight: 1.1, marginBottom: '0.5rem', textShadow: '3px 3px 0px #000' }}>
                  Analyze<br/>Resumes
                </h3>
                <p style={{ color: 'var(--p5-white)', fontWeight: 600, fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                  Execute a multi-agent Semantic & Lexical scan to expose hidden candidate alignments against our Target JD.
                </p>
                <div style={{ color: 'var(--p5-red)', fontWeight: 900, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  Launch Matcher <span style={{ transform: 'translateX(0)', transition: 'transform 0.3s ease' }}>→</span>
                </div>
              </div>
            </div>

            {/* CALLING CARD 2 */}
            <div className="p5-heist-card" onClick={() => { setActiveTab('improve'); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
              <div className="p5-heist-card-content">
                <span className="badge badge-blue" style={{ marginBottom: '1rem', display: 'inline-block' }}>OPERATION 02</span>
                <h3 style={{ fontSize: '2rem', fontFamily: 'var(--font-title)', fontWeight: 900, color: 'var(--p5-yellow)', textTransform: 'uppercase', lineHeight: 1.1, marginBottom: '0.5rem', textShadow: '3px 3px 0px #000' }}>
                  Improve<br/>Bullets
                </h3>
                <p style={{ color: 'var(--p5-white)', fontWeight: 600, fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                  Rewrite weak resume bullet points into ultra-optimized STAR-format statements to bypass recruiter defenses.
                </p>
                <div style={{ color: 'var(--p5-red)', fontWeight: 900, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  Optimize Stats <span style={{ transform: 'translateX(0)', transition: 'transform 0.3s ease' }}>→</span>
                </div>
              </div>
            </div>

            {/* CALLING CARD 3 */}
            <div className="p5-heist-card" onClick={() => { setActiveTab('jobs'); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
              <div className="p5-heist-card-content">
                <span className="badge badge-green" style={{ marginBottom: '1rem', display: 'inline-block' }}>OPERATION 03</span>
                <h3 style={{ fontSize: '2rem', fontFamily: 'var(--font-title)', fontWeight: 900, color: 'var(--p5-yellow)', textTransform: 'uppercase', lineHeight: 1.1, marginBottom: '0.5rem', textShadow: '3px 3px 0px #000' }}>
                  Swipe<br/>Deck
                </h3>
                <p style={{ color: 'var(--p5-white)', fontWeight: 600, fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                  A rapid-fire Tinder-style interface for live global job APIs. Swipe right to execute applications.
                </p>
                <div style={{ color: 'var(--p5-red)', fontWeight: 900, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  Find Targets <span style={{ transform: 'translateX(0)', transition: 'transform 0.3s ease' }}>→</span>
                </div>
              </div>
            </div>

          </div>

        </div>
      )}
\n'''
    new_content = content[:start_idx] + new_home + content[end_idx:]
    with open('src/App.jsx', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully replaced the Home tab content.")
else:
    print("Could not find markers. Start:", start_marker in content, "End:", end_marker in content)
