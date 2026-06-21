import React from 'react';
import './GlitchText.css';

export default function GlitchText({ text, className = '' }) {
  return (
    <div className={`glitch-wrapper ${className}`}>
      <h3 className="glitch" data-text={text}>{text}</h3>
    </div>
  );
}
