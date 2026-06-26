import React, { useState, useEffect } from 'react';

const BASE_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com';
const CLEAN_BASE = BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
const API_URL = CLEAN_BASE + '/api';

export default function MCQAssessment({ resumeText, jdText, onExit, combinedAlerts, sessionId }) {
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isFinished, setIsFinished] = useState(false);
  const [score, setScore] = useState(0);

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const res = await fetch(`${API_URL}/interview/mcq_generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ resume_text: resumeText || "N/A", jd_text: jdText || "N/A" })
        });
        const data = await res.json();
        if (data.success && data.questions) {
          setQuestions(data.questions);
        } else {
          alert("Failed to generate MCQ questions.");
          onExit();
        }
      } catch (e) {
        console.error(e);
        alert("Error connecting to server.");
        onExit();
      }
      setIsLoading(false);
    };
    fetchQuestions();
  }, [resumeText, jdText, onExit]);

  const handleSelect = (idx) => {
    setAnswers({ ...answers, [currentIndex]: idx });
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      // Calculate score
      let s = 0;
      questions.forEach((q, i) => {
        if (answers[i] === q.correct_index) s++;
      });
      setScore(s);
      setIsFinished(true);
    }
  };

  if (isLoading) {
    return (
      <div className="ir-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="ir-overlay-bg"></div>
        <h2 style={{ color: '#fff', zIndex: 10 }}>SYNTHESIZING PROGRESSIVE MCQ ASSESSMENT...</h2>
      </div>
    );
  }

  if (isFinished) {
    return (
      <div className="ir-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', overflowY: 'auto', padding: '2rem' }}>
        <div className="ir-overlay-bg"></div>
        <div className="ir-gateway-box" style={{ zIndex: 10, maxWidth: '800px', width: '100%' }}>
          <h2 className="ir-gateway-title">ASSESSMENT COMPLETE</h2>
          <h1 style={{ color: score === questions.length ? '#10b981' : '#e60012', fontSize: '4rem', margin: '1rem 0' }}>
            {score} / {questions.length}
          </h1>
          <div style={{ color: '#fff', marginBottom: '2rem' }}>
            {questions.map((q, i) => (
              <div key={i} style={{ marginBottom: '1rem', textAlign: 'left', background: '#1a1a1a', padding: '1rem', borderLeft: answers[i] === q.correct_index ? '4px solid #10b981' : '4px solid #e60012' }}>
                <strong>Q: {q.question}</strong><br/>
                <span style={{ color: '#aaa', fontSize: '0.8rem' }}>Level: {q.level}</span><br/>
                <div style={{ marginTop: '0.5rem' }}>
                  {answers[i] === q.correct_index ? "✅ Correct" : "❌ Incorrect"} - {q.explanation}
                </div>
              </div>
            ))}
          </div>
          <button onClick={onExit} className="ir-btn-primary">RETURN TO HUB</button>
        </div>
      </div>
    );
  }

  const q = questions[currentIndex];

  return (
    <div className="ir-container">
      <div className="ir-overlay-bg"></div>
      
      {/* Top Bar for alerts */}
      {combinedAlerts && combinedAlerts.length > 0 && (
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, background: '#e60012', color: '#fff', padding: '0.5rem', textAlign: 'center', zIndex: 100, fontWeight: 'bold' }}>
          SECURITY ALERT: {combinedAlerts.join(" | ")}
        </div>
      )}

      <div style={{ zIndex: 10, width: '100%', maxWidth: '800px', margin: '4rem auto', padding: '2rem', background: '#000', border: '1px solid #333' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem', color: '#e60012', fontWeight: 'bold' }}>
          <span>QUESTION {currentIndex + 1} OF {questions.length}</span>
          <span>LEVEL: {q.level.toUpperCase()}</span>
        </div>

        <h2 style={{ color: '#fff', fontSize: '1.5rem', marginBottom: '2rem', lineHeight: '1.4' }}>
          {q.question}
        </h2>

        <div style={{ display: 'grid', gap: '1rem' }}>
          {q.options.map((opt, i) => (
            <button 
              key={i}
              onClick={() => handleSelect(i)}
              style={{
                padding: '1rem',
                background: answers[currentIndex] === i ? '#e60012' : '#1a1a1a',
                color: '#fff',
                border: '1px solid #333',
                textAlign: 'left',
                fontSize: '1.1rem',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {String.fromCharCode(65 + i)}. {opt}
            </button>
          ))}
        </div>

        <div style={{ marginTop: '3rem', textAlign: 'right' }}>
          <button 
            onClick={handleNext}
            disabled={answers[currentIndex] === undefined}
            className="ir-btn-primary"
            style={{ opacity: answers[currentIndex] === undefined ? 0.5 : 1 }}
          >
            {currentIndex === questions.length - 1 ? "SUBMIT ASSESSMENT" : "NEXT QUESTION"}
          </button>
        </div>
      </div>
    </div>
  );
}
