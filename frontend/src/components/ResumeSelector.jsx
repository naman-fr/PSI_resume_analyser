import React, { useState, useEffect } from 'react';
import { FileText, UploadCloud, CheckCircle } from 'lucide-react';
import { API_URL } from '../config';

const ResumeSelector = ({ onSelect, label = "Select Resume" }) => {
  const [vaultResumes, setVaultResumes] = useState([]);
  const [selectedId, setSelectedId] = useState('new');
  const [newFile, setNewFile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_URL}/api/hub/profile`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setVaultResumes(data.resume_vault || []);
        }
      } catch (err) {
        console.error("Failed to fetch profile vault:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleSelectExisting = (resume) => {
    setSelectedId(resume.id);
    setNewFile(null);
    onSelect(resume.id, resume.resume_text);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedId('new');
      setNewFile(file);
      onSelect(file, null);
    }
  };

  if (loading) {
    return <div style={{ color: 'var(--text-dim)', padding: '1rem', fontStyle: 'italic' }}>Loading vault...</div>;
  }

  return (
    <div className="input-group" style={{ background: '#0a0a0a', padding: '1rem', borderRadius: '4px', border: '1px solid #333' }}>
      <span className="input-label" style={{ display: 'block', marginBottom: '1rem', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {vaultResumes.map(resume => (
          <div 
            key={resume.id}
            onClick={() => handleSelectExisting(resume)}
            style={{
              padding: '0.75rem 1rem',
              background: selectedId === resume.id ? 'var(--p5-red)' : '#1a1a1a',
              color: selectedId === resume.id ? '#fff' : 'var(--text-dim)',
              border: `2px solid ${selectedId === resume.id ? 'var(--p5-red)' : '#333'}`,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              transform: selectedId === resume.id ? 'skewX(-2deg)' : 'none',
              transition: 'all 0.2s ease-in-out',
              boxShadow: selectedId === resume.id ? '4px 4px 0px #000' : 'none'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', transform: selectedId === resume.id ? 'skewX(2deg)' : 'none' }}>
              <FileText size={20} />
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 'bold' }}>{resume.filename || `Vault Resume (${new Date(resume.timestamp).toLocaleDateString()})`}</span>
                <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>Match Potential: {resume.overall_score || '--'}/100</span>
              </div>
            </div>
            {selectedId === resume.id && <CheckCircle size={20} />}
          </div>
        ))}
        
        {/* Upload New Option */}
        <div 
          onClick={() => document.getElementById(`resumeFileId_${label.replace(/\s/g, '')}`).click()}
          style={{
            padding: '1rem',
            background: selectedId === 'new' ? '#2a0a0a' : '#111',
            border: `2px dashed ${selectedId === 'new' ? 'var(--p5-red)' : '#444'}`,
            color: selectedId === 'new' ? 'var(--p5-white)' : 'var(--text-dim)',
            cursor: 'pointer',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.5rem',
            marginTop: '0.5rem',
            transition: 'all 0.2s ease-in-out'
          }}
        >
          <UploadCloud size={24} color={selectedId === 'new' ? 'var(--p5-red)' : '#666'} />
          <span style={{ fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px' }}>
            {newFile ? `SELECTED: ${newFile.name}` : 'Upload New Resume (PDF)'}
          </span>
          <span style={{ fontSize: '0.75rem' }}>Will automatically sync to your Intelligence Hub Vault</span>
        </div>
        <input 
          type="file" 
          id={`resumeFileId_${label.replace(/\s/g, '')}`} 
          accept=".pdf" 
          style={{ display: 'none' }} 
          onChange={handleFileChange}
        />
      </div>
    </div>
  );
};

export default ResumeSelector;
