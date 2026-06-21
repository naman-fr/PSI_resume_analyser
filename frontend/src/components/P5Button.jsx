import React from 'react';
import './P5Button.css';

export default function P5Button({ children, onClick, type = 'button', className = '', style = {}, disabled = false }) {
  return (
    <button 
      type={type} 
      onClick={onClick} 
      className={`p5-menu-container ${className}`} 
      style={{ border: 'none', background: 'transparent', padding: 0, ...style }}
      disabled={disabled}
    >
      <div className="p5-menu-text">{children}</div>
      <div className="p5-menu-inner"></div>
      <div className="p5-menu-outer"></div>
    </button>
  );
}
