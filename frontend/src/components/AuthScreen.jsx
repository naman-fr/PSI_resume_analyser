import React, { useState } from 'react';
import ThreeGem from './ThreeGem';
import GlitchText from './GlitchText';
import P5Button from './P5Button';
import { useAuth } from '../AuthContext';

import backgroundLogin from './Scenes/background_login.gif';
import loadingGif from './Scenes/loading_gif.gif';

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
      {/* Massive Immersive Background Scene */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, width: '100%', height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        background: '#000'
      }}>
        <img 
          src={backgroundLogin} 
          alt="Persona 5 Background"
          style={{ 
            pointerEvents: 'none', 
            objectFit: 'cover', 
            width: '100vw', 
            height: '100vh',
            opacity: 0.35,
            mixBlendMode: 'screen',
            transform: 'scale(1.05)'
          }}
        />
      </div>

      {/* Left side: 3D showcase */}
      <div className="auth-left" style={{ position: 'relative', overflow: 'hidden', zIndex: 1, background: 'transparent' }}>
        {/* Removed the random floating GIFs */}
        
        <div style={{ width: '100%', maxWidth: '350px', height: '350px', position: 'absolute', top: '15%', zIndex: 5, left: '50%', transform: 'translateX(-50%)' }}>
            <ThreeGem />
        </div>
        <div style={{ position: 'relative', zIndex: 10, marginTop: '280px', textAlign: 'center', background: 'rgba(8,8,8,0.7)', padding: '2rem', backdropFilter: 'blur(10px)', borderTop: '4px solid var(--p5-red)', borderBottom: '4px solid var(--p5-red)', width: '80%' }}>
            <div style={{ position: 'absolute', top: '-12px', left: '10px', background: 'var(--p5-yellow)', color: '#000', padding: '2px 10px', fontFamily: 'var(--ff-mono)', fontSize: '0.7rem', fontWeight: 'bold' }}>SYSTEM ACTIVE</div>
            <GlitchText text="PHANTOM CV" />
            <h3 style={{ fontFamily: 'var(--ff-display)', color: 'var(--p5-white)', fontSize: '1.2rem', letterSpacing: '0.2em', margin: '0.5rem 0', textTransform: 'uppercase' }}>Cognitive ATS Pipeline</h3>
            <p style={{ fontFamily: 'var(--ff-mono)', color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '400px', margin: '0 auto', lineHeight: '1.4' }}>
              Infiltrate black-box ATS algorithms. Upload your candidate data to reveal alignment scores and hidden potential.
            </p>
        </div>
      </div>
      
      {/* Right side: Auth Form */}
      <div className="auth-right">
        <div style={{ width: '100%', maxWidth: '420px', background: 'rgba(26,26,26,0.65)', backdropFilter: 'blur(10px)', padding: '3.5rem', borderTop: '4px solid var(--red)', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}>
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
                      <img src={loadingGif} alt="loading" style={{ height: '30px', filter: 'brightness(0) invert(1)' }} />
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
