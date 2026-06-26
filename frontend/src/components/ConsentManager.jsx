import React, { useState, useEffect } from 'react';
import { ShieldAlert, CheckCircle2, X } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com';
const CLEAN_BASE = API_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
const ENDPOINT = `${CLEAN_BASE}/api/identity/consent`;

export default function ConsentManager({ userId = "anonymous", onClose }) {
    const [preferences, setPreferences] = useState({
        analytics: true,
        performance: true,
        marketing: false,
        ai_personalization: true,
        interview_memory: true,
        voice_storage: false
    });
    
    const [saved, setSaved] = useState(false);
    
    useEffect(() => {
        // Fetch existing consent
        fetch(`${ENDPOINT}/${userId}`)
            .then(r => r.json())
            .then(data => {
                if (data.success && data.consent) {
                    setPreferences(data.consent);
                }
            })
            .catch(e => console.error("Failed to load consent", e));
    }, [userId]);
    
    const toggle = (key) => {
        setPreferences(prev => ({ ...prev, [key]: !prev[key] }));
        setSaved(false);
    };
    
    const handleSave = async () => {
        try {
            const res = await fetch(ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, ...preferences })
            });
            if (res.ok) setSaved(true);
        } catch (e) {
            console.error("Failed to save consent", e);
        }
    };

    return (
        <div style={{
            background: '#121212',
            border: '2px solid var(--p5-yellow)',
            padding: '2rem',
            width: '100%',
            maxWidth: '600px',
            color: '#fff',
            fontFamily: 'var(--ff-body)',
            position: 'relative'
        }}>
            {onClose && (
                <button 
                  onClick={onClose}
                  style={{ position: 'absolute', top: 10, right: 10, background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}
                >
                    <X size={24} />
                </button>
            )}
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #333', paddingBottom: '1rem' }}>
                <ShieldAlert size={32} color="var(--p5-yellow)" />
                <h2 style={{ margin: 0, fontFamily: 'var(--ff-display)', color: 'var(--p5-yellow)' }}>AI Data Governance Center</h2>
            </div>
            
            <p style={{ fontSize: '0.9rem', color: '#aaa', marginBottom: '2rem' }}>
                Configure your AI Privacy Profile. We use advanced behavioral embeddings to personalize your experience, rather than traditional invasive cookies.
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {Object.entries(preferences).map(([key, val]) => (
                    <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#1a1a1a', padding: '1rem', borderLeft: `4px solid ${val ? 'var(--p5-red)' : '#333'}` }}>
                        <div>
                            <strong style={{ textTransform: 'capitalize', color: val ? '#fff' : '#888' }}>
                                {key.replace('_', ' ')}
                            </strong>
                        </div>
                        <button 
                            onClick={() => toggle(key)}
                            style={{
                                background: val ? 'var(--p5-red)' : '#333',
                                border: 'none',
                                color: '#fff',
                                padding: '0.5rem 1rem',
                                cursor: 'pointer',
                                fontWeight: 'bold'
                            }}
                        >
                            {val ? 'ENABLED' : 'DISABLED'}
                        </button>
                    </div>
                ))}
            </div>
            
            <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {saved ? (
                    <span style={{ color: '#4caf50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <CheckCircle2 size={18} /> Preferences Saved to Vector Profile
                    </span>
                ) : (
                    <span style={{ color: '#aaa', fontSize: '0.8rem' }}>Unsaved changes...</span>
                )}
                
                <button 
                    onClick={handleSave}
                    style={{
                        background: 'var(--p5-yellow)',
                        color: '#000',
                        border: 'none',
                        padding: '0.75rem 2rem',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        fontFamily: 'var(--ff-display)'
                    }}
                >
                    UPDATE IDENTITY VECTOR
                </button>
            </div>
        </div>
    );
}
