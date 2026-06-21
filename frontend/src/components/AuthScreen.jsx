import React, { useState } from 'react';
import ThreeGem from './ThreeGem';
import GlitchText from './GlitchText';
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
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--black, #0a0a0c)', color: 'var(--white, #fafaf6)', overflow: 'hidden' }}>
      {/* Left side: 3D showcase */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', borderRight: '1px solid var(--panel-2, #222226)', position: 'relative' }}>
        <div style={{ width: '100%', maxWidth: '600px', height: '600px', position: 'absolute', top: '10%' }}>
            <ThreeGem />
        </div>
        <div style={{ position: 'relative', zIndex: 10, marginTop: '400px', textAlign: 'center' }}>
            <GlitchText text="PHANTOM CV" />
            <p style={{ fontFamily: 'var(--ff-mono)', color: 'var(--gray)', letterSpacing: '0.3em', textAlign: 'center', marginTop: '5px' }}>COGNITIVE ATS PIPELINE</p>
        </div>
      </div>
      
      {/* Right side: Auth Form */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', background: 'radial-gradient(circle at center, #141417 0%, #0a0a0c 100%)' }}>
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
              
              <button type="submit" disabled={loading} style={{ background: 'var(--red)', color: 'var(--black)', border: 'none', padding: '1.2rem', fontFamily: 'var(--ff-display)', fontSize: '1.3rem', cursor: 'pointer', letterSpacing: '0.05em', marginTop: '1rem', transition: 'background 0.2s', boxShadow: '5px 5px 0px #7a0014' }}>
                {loading ? 'AUTHENTICATING...' : (isRegister ? 'INITIALIZE CONNECTION' : 'INFILTRATE')}
              </button>
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
