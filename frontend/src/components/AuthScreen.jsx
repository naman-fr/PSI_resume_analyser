import React, { useState } from 'react';
import ThreeGem from './ThreeGem';
import GlitchText from './GlitchText';
import P5Button from './P5Button';
import { useAuth } from '../AuthContext';

export default function AuthScreen() {
  const { login } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
    const payload = isRegister ? { email, password, username } : { email, password };
    
    try {
      const res = await fetch((import.meta.env.VITE_API_URL || '') + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }
      
      login(data.access_token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      {/* Left side: 3D showcase */}
      <div className="auth-left" style={{ position: 'relative', overflow: 'hidden' }}>
        {/* Persona 5 All-Out Attack looping background (IFrame Fix) */}
        <div style={{
          position: 'absolute',
          top: '-10%', left: '-10%', width: '120%', height: '120%',
          opacity: 0.15,
          zIndex: 0,
          pointerEvents: 'none',
          mixBlendMode: 'luminosity'
        }}>
          <iframe src="https://giphy.com/embed/3o7bukaBzZhgCMB3u8" width="100%" height="100%" frameBorder="0" className="giphy-embed" allowFullScreen style={{ pointerEvents: 'none' }}></iframe>
        </div>
        
        {/* Joker background element */}
        <div style={{ position: 'absolute', bottom: '-50px', left: '-50px', width: '400px', height: '400px', zIndex: 0, opacity: 0.4, pointerEvents: 'none', mixBlendMode: 'lighten' }}>
          <iframe src="https://giphy.com/embed/LwsA3k0EweuDS" width="100%" height="100%" frameBorder="0" className="giphy-embed" allowFullScreen style={{ pointerEvents: 'none' }}></iframe>
        </div>
        
        {/* Floating Hologram Data */}
        <div style={{ position: 'absolute', top: '15%', left: '10%', zIndex: 1, animation: 'floatBob 4s infinite', opacity: 0.8 }}>
          <div style={{ borderLeft: '4px solid var(--red)', paddingLeft: '10px', fontFamily: 'var(--ff-mono)', color: 'var(--red)', fontSize: '0.85rem' }}>
            [ SYS.SCAN: active ]<br/>
            &gt; resume_db_04.pdf<br/>
            &gt; EXTRACTING NODES...
          </div>
        </div>

        <div style={{ position: 'absolute', bottom: '25%', right: '10%', zIndex: 1, animation: 'floatBob 3.5s infinite reverse', opacity: 0.8 }}>
          <div style={{ borderRight: '4px solid var(--p5-yellow)', paddingRight: '10px', textAlign: 'right', fontFamily: 'var(--ff-mono)', color: 'var(--p5-yellow)', fontSize: '0.85rem' }}>
            [ MATCH RATE ]<br/>
            &gt; 98.4% ALIGNMENT<br/>
            &gt; STATUS: CLEAR
          </div>
        </div>

        <div style={{ position: 'absolute', top: '45%', right: '5%', zIndex: 1, opacity: 0.4, transform: 'rotate(90deg)', transformOrigin: 'right center' }}>
          <div style={{ fontFamily: 'var(--ff-display)', fontSize: '4rem', color: 'var(--panel-2)', letterSpacing: '0.2em' }}>
            COGNITIVE // ATS
          </div>
        </div>

        <div style={{ width: '100%', maxWidth: '600px', height: '600px', position: 'absolute', top: '10%', zIndex: 5 }}>
            <ThreeGem />
        </div>
        <div style={{ position: 'relative', zIndex: 10, marginTop: '400px', textAlign: 'center' }}>
            <GlitchText text="PHANTOM CV" />
            <p style={{ fontFamily: 'var(--ff-mono)', color: 'var(--gray)', letterSpacing: '0.3em', textAlign: 'center', marginTop: '5px', textShadow: '2px 2px 0px #000' }}>COGNITIVE ATS PIPELINE</p>
        </div>
      </div>
      
      {/* Right side: Auth Form */}
      <div className="auth-right">
        <div style={{ width: '100%', maxWidth: '420px', background: 'var(--panel)', padding: '3.5rem', borderTop: '4px solid var(--red)', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}>
            <h2 style={{ fontFamily: 'var(--ff-display)', fontSize: '2.5rem', marginBottom: '2rem', color: 'var(--white)', letterSpacing: '0.02em' }}>
              {isRegister ? 'JOIN THE PHANTOMS' : 'ACCESS TERMINAL'}
            </h2>
            
            {error && (
              <div style={{ background: 'rgba(255,10,44,0.1)', borderLeft: '3px solid var(--red)', padding: '1rem', color: 'var(--red)', marginBottom: '1.5rem', fontFamily: 'var(--ff-mono)', fontSize: '0.85rem' }}>
                &gt; ERROR: {error}
              </div>
            )}
            
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {isRegister && (
                <div>
                  <label style={{ display: 'block', fontFamily: 'var(--ff-mono)', fontSize: '0.8rem', color: 'var(--gray)', marginBottom: '0.5rem', letterSpacing: '0.1em' }}>USERNAME</label>
                  <input type="text" value={username} onChange={e => setUsername(e.target.value)} required style={{ width: '100%', background: 'var(--ink)', border: '1px solid var(--panel-2)', color: 'var(--white)', padding: '1rem', fontFamily: 'var(--ff-body)', fontSize: '1rem' }} />
                </div>
              )}
              <div>
                <label style={{ display: 'block', fontFamily: 'var(--ff-mono)', fontSize: '0.8rem', color: 'var(--gray)', marginBottom: '0.5rem', letterSpacing: '0.1em' }}>EMAIL PROTOCOL</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} required style={{ width: '100%', background: 'var(--ink)', border: '1px solid var(--panel-2)', color: 'var(--white)', padding: '1rem', fontFamily: 'var(--ff-body)', fontSize: '1rem' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontFamily: 'var(--ff-mono)', fontSize: '0.8rem', color: 'var(--gray)', marginBottom: '0.5rem', letterSpacing: '0.1em' }}>PASSPHRASE</label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} required style={{ width: '100%', background: 'var(--ink)', border: '1px solid var(--panel-2)', color: 'var(--white)', padding: '1rem', fontFamily: 'var(--ff-body)', fontSize: '1rem' }} />
              </div>
              
              <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center' }}>
                <P5Button type="submit" disabled={loading} style={{ width: '100%' }}>
                  {loading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                      <img src="https://media.tenor.com/FwB8a_7D9hQAAAAi/persona-5-take-your-time.gif" alt="loading" style={{ height: '30px', filter: 'brightness(0) invert(1)' }} />
                      AUTHENTICATING...
                    </div>
                  ) : (isRegister ? 'INITIALIZE CONNECTION' : 'INFILTRATE')}
                </P5Button>
              </div>
            </form>
            
            <div style={{ marginTop: '2.5rem', textAlign: 'center' }}>
              <button onClick={() => setIsRegister(!isRegister)} style={{ background: 'none', border: 'none', color: 'var(--gray)', fontFamily: 'var(--ff-mono)', fontSize: '0.8rem', cursor: 'pointer', textDecoration: 'underline', letterSpacing: '0.05em' }}>
                {isRegister ? 'Already have access? Login here.' : 'Request new clearance? Register here.'}
              </button>
            </div>
        </div>
      </div>
    </div>
  );
}
