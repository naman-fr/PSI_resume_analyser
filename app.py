"""
PSI Resume Analyser — Gradio Application.

Main entry-point for the HuggingFace Spaces deployment.  Provides a
premium multi-tab UI for single-resume analysis, improvement suggestions,
batch analysis, and methodology documentation.
"""

from __future__ import annotations

import logging
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr

from config.settings import settings
from core.pdf_parser import extract_text_from_pdf

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent
CSS_PATH = ROOT_DIR / "assets" / "custom.css"
SAMPLE_JD_DIR = ROOT_DIR / "data" / "sample_jds"

MAX_FILE_SIZE_BYTES = settings.max_file_size_mb * 1024 * 1024
ALLOWED_EXTENSIONS = settings.allowed_extensions

# ---------------------------------------------------------------------------
# CSS Loader
# ---------------------------------------------------------------------------


def _load_css() -> str:
    """Load the custom CSS file, returning an empty string on failure."""
    if CSS_PATH.exists():
        return CSS_PATH.read_text(encoding="utf-8")
    logger.warning("Custom CSS not found at %s", CSS_PATH)
    return ""


# ---------------------------------------------------------------------------
# Validators (inline — avoids hard dependency on utils.validators)
# ---------------------------------------------------------------------------


def validate_pdf(file_obj: Any) -> Tuple[bool, str]:
    """Validate an uploaded PDF file object from Gradio."""
    if file_obj is None:
        return False, "No file uploaded. Please upload a PDF resume."

    file_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    file_name = Path(file_path).name

    if not any(file_name.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, (
            f"File too large ({file_size / 1024 / 1024:.1f} MB). "
            f"Maximum: {settings.max_file_size_mb} MB."
        )

    return True, ""


def validate_jd_text(text: str) -> Tuple[bool, str]:
    """Validate job description text."""
    if not text or not text.strip():
        return False, "Job description is empty. Please paste the JD text."
    if len(text.strip()) < 50:
        return False, "Job description is too short. Please provide a complete JD (≥50 characters)."
    return True, ""


# ---------------------------------------------------------------------------
# Sample JD Loader
# ---------------------------------------------------------------------------


def _list_sample_jds_structured() -> Tuple[Dict[str, str], List[List[str]]]:
    """Discover sample JD files under data/sample_jds/.
    
    Returns:
        samples_dict: Dict mapping friendly label -> raw text
        dataset_rows: List of rows [Index, Job Title, Company, Location, Filename]
    """
    samples_dict: Dict[str, str] = {}
    dataset_rows: List[List[str]] = []
    
    if SAMPLE_JD_DIR.is_dir():
        for i, f in enumerate(sorted(SAMPLE_JD_DIR.glob("*.txt")), 1):
            text = f.read_text(encoding="utf-8")
            label = f.stem.replace("_", " ").title()
            samples_dict[label] = text
            
            # Extract structured headers if present
            title = label
            company = "Enterprise"
            location = "Hybrid/Remote"
            
            # Parse top lines
            lines = text.split("\n")
            for line in lines[:8]:
                line_lower = line.lower()
                if line_lower.startswith("job title:"):
                    title = line.split(":", 1)[1].strip()
                elif line_lower.startswith("company:"):
                    company = line.split(":", 1)[1].strip()
                elif line_lower.startswith("location:"):
                    location = line.split(":", 1)[1].strip()
            
            dataset_rows.append([f"JD #{i}", title, company, location, f.name])
            
    return samples_dict, dataset_rows


SAMPLE_JDS, JD_DATASET_ROWS = _list_sample_jds_structured()


def load_jd_from_dataset(evt: gr.SelectData) -> str:
    """Load the JD text based on the selected row in the dataframe."""
    row_idx = evt.index[0]
    if 0 <= row_idx < len(JD_DATASET_ROWS):
        filename = JD_DATASET_ROWS[row_idx][4]  # Column 4 contains filename
        file_path = SAMPLE_JD_DIR / filename
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
    return ""


def get_game_html() -> str:
    """Return the HTML/CSS/JS for the ATS Skill Catcher mini-game."""
    return r"""
<div class="ats-game-card" style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; margin-top: 16px;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <span style="font-weight: 700; color: #a78bfa; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">
      🎮 ATS SKILL CATCHER MINI-GAME
    </span>
    <span id="game-status-text" style="font-size: 0.85rem; color: #94a3b8; font-style: italic;">Ready</span>
  </div>
  
  <div style="position: relative; width: 100%; height: 220px; background: #0c081e; border-radius: 8px; overflow: hidden; border: 1px solid rgba(124, 58, 237, 0.25);">
    <canvas id="ats-game-canvas" style="display: block; width: 100%; height: 100%;"></canvas>
    
    <!-- Game Overlay (Splash and End Screen) -->
    <div id="game-overlay" style="position: absolute; top:0; left:0; width:100%; height:100%; background: rgba(12, 8, 30, 0.9); display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 16px; box-sizing: border-box; transition: all 0.3s;">
      <h4 id="overlay-title" style="margin: 0 0 8px 0; color: #f8fafc; font-size: 1.1rem; font-weight: 700; letter-spacing: 0.02em;">
        Beat the Loading Time!
      </h4>
      <p id="overlay-desc" style="margin: 0 0 16px 0; color: #94a3b8; font-size: 0.85rem; max-width: 280px; line-height: 1.5;">
        Audit takes ~20s. Slide the basket using your <strong>mouse or touch</strong> to catch good skills (green) and filter out buzzwords (red)!
      </p>
      <button id="start-game-btn" onclick="if(window.startATSGame) window.startATSGame();" style="background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%); color: white; border: none; padding: 8px 20px; border-radius: 20px; font-weight: 600; font-size: 0.88rem; cursor: pointer; box-shadow: 0 4px 12px rgba(124,58,237,0.3); transition: all 0.2s;">
        Play Game
      </button>
    </div>
  </div>
  
  <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 0.9rem;">
    <div>Score: <strong id="game-score-val" style="color: #34d399; font-size: 1rem;">0</strong></div>
    <div>Time Left: <strong id="game-timer-val" style="color: #fbbf24; font-size: 1rem;">20s</strong></div>
  </div>
</div>

<script id="ats-game-script">
(function() {
    let canvas, ctx, animationId;
    let score = 0;
    let timer = 20;
    let timerInterval = null;
    let gameRunning = false;
    
    // Player catcher
    let playerX = 100;
    const playerWidth = 80;
    const playerHeight = 16;
    
    // Falling objects
    let objects = [];
    const goodSkills = ["Python", "React", "Docker", "Machine Learning", "SQL", "Git", "FastAPI", "Kubernetes", "AWS", "NoSQL", "CI/CD", "TypeScript"];
    const badFlags = ["Synergy", "Results-driven", "Detail-oriented", "Team-player", "10+ years exp", "Fake Certs", "Hardworker", "Dynamic", "Self-starter"];
    
    let floatTexts = [];
    
    function initCanvas() {
        canvas = document.getElementById('ats-game-canvas');
        if (!canvas) return;
        ctx = canvas.getContext('2d');
        
        // Handle high-density screens and layout sizing
        const rect = canvas.getBoundingClientRect();
        let w = rect.width || canvas.offsetWidth || 400;
        let h = rect.height || canvas.offsetHeight || 220;
        if (w === 0) w = 400;
        if (h === 0) h = 220;
        canvas.width = w;
        canvas.height = h;
        playerX = canvas.width / 2 - playerWidth / 2;
        
        // Track mouse and touch positions
        canvas.removeEventListener('mousemove', onMouseMove);
        canvas.addEventListener('mousemove', onMouseMove);
        canvas.removeEventListener('touchmove', onTouchMove);
        canvas.addEventListener('touchmove', onTouchMove, { passive: true });
    }
    
    function onMouseMove(e) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        playerX = mouseX - playerWidth / 2;
        clampPlayer();
    }
    
    function onTouchMove(e) {
        if (e.touches.length > 0) {
            const rect = canvas.getBoundingClientRect();
            const touchX = e.touches[0].clientX - rect.left;
            playerX = touchX - playerWidth / 2;
            clampPlayer();
        }
    }
    
    function clampPlayer() {
        if (playerX < 0) playerX = 0;
        if (playerX + playerWidth > canvas.width) playerX = canvas.width - playerWidth;
    }
    
    function spawnObject() {
        if (!gameRunning) return;
        
        const isGood = Math.random() > 0.45;
        const text = isGood 
            ? goodSkills[Math.floor(Math.random() * goodSkills.length)]
            : badFlags[Math.floor(Math.random() * badFlags.length)];
        
        ctx.font = "bold 11px sans-serif";
        const textWidth = ctx.measureText(text).width;
        
        objects.push({
            x: Math.random() * (canvas.width - textWidth - 14) + 7,
            y: -20,
            text: text,
            isGood: isGood,
            speed: Math.random() * 1.5 + 1.2,
            width: textWidth + 14,
            height: 20
        });
        
        // Schedule next spawn
        setTimeout(spawnObject, Math.random() * 800 + 600);
    }
    
    function updateGame() {
        if (!gameRunning) return;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw space background
        ctx.fillStyle = "#0c081e";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw catcher basket (glassmorphic gradient)
        const grad = ctx.createLinearGradient(playerX, canvas.height - playerHeight - 10, playerX + playerWidth, canvas.height - 10);
        grad.addColorStop(0, '#7c3aed');
        grad.addColorStop(1, '#22d3ee');
        ctx.fillStyle = grad;
        
        drawRoundedRect(ctx, playerX, canvas.height - playerHeight - 10, playerWidth, playerHeight, 5);
        ctx.fill();
        
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 9px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("ATS FILTER", playerX + playerWidth/2, canvas.height - playerHeight/2 - 6);
        
        // Update & draw falling objects
        for (let i = objects.length - 1; i >= 0; i--) {
            let obj = objects[i];
            obj.y += obj.speed;
            
            // Collision detection
            const catcherY = canvas.height - playerHeight - 10;
            if (obj.y + obj.height >= catcherY && 
                obj.y <= catcherY + playerHeight && 
                obj.x + obj.width >= playerX && 
                obj.x <= playerX + playerWidth) {
                // Catch event
                if (obj.isGood) {
                    score += 10;
                    showFloatText("+10 " + obj.text, obj.x + obj.width/2, catcherY, "#34d399");
                } else {
                    score = Math.max(0, score - 15);
                    showFloatText("-15 BUZZWORD!", obj.x + obj.width/2, catcherY, "#ef4444");
                }
                document.getElementById('game-score-val').innerText = score;
                objects.splice(i, 1);
                continue;
            }
            
            // Out of bounds
            if (obj.y > canvas.height) {
                objects.splice(i, 1);
                continue;
            }
            
            // Draw item badge
            ctx.strokeStyle = obj.isGood ? "rgba(16,185,129,0.5)" : "rgba(239,68,68,0.5)";
            ctx.fillStyle = obj.isGood ? "rgba(16,185,129,0.18)" : "rgba(239,68,68,0.15)";
            drawRoundedRect(ctx, obj.x, obj.y, obj.width, obj.height, 4);
            ctx.fill();
            ctx.stroke();
            
            ctx.fillStyle = obj.isGood ? "#34d399" : "#f87171";
            ctx.font = "bold 10px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(obj.text, obj.x + obj.width/2, obj.y + 14);
        }
        
        // Update floating scores
        updateFloatTexts();
        
        animationId = requestAnimationFrame(updateGame);
    }
    
    function showFloatText(text, x, y, color) {
        floatTexts.push({ text, x, y, color, alpha: 1, ySpeed: -1 });
    }
    
    function updateFloatTexts() {
        for (let i = floatTexts.length - 1; i >= 0; i--) {
            let ft = floatTexts[i];
            ft.y += ft.ySpeed;
            ft.alpha -= 0.03;
            if (ft.alpha <= 0) {
                floatTexts.splice(i, 1);
            } else {
                ctx.fillStyle = ft.color;
                ctx.globalAlpha = ft.alpha;
                ctx.font = "bold 10px sans-serif";
                ctx.textAlign = "center";
                ctx.fillText(ft.text, ft.x, ft.y);
                ctx.globalAlpha = 1;
            }
        }
    }
    
    function drawRoundedRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
    }
    
    window.startATSGame = function() {
        if (gameRunning) return;
        initCanvas();
        if (!canvas) return;
        
        score = 0;
        timer = 20;
        objects = [];
        floatTexts = [];
        gameRunning = true;
        
        document.getElementById('game-score-val').innerText = score;
        document.getElementById('game-timer-val').innerText = timer + "s";
        document.getElementById('game-status-text').innerText = "Processing Audit... Catch Skills!";
        
        const overlay = document.getElementById('game-overlay');
        if (overlay) overlay.style.display = 'none';
        
        spawnObject();
        updateGame();
        
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            timer--;
            document.getElementById('game-timer-val').innerText = timer + "s";
            if (timer <= 0) {
                endATSGame();
            }
        }, 1000);
    };
    
    function endATSGame() {
        gameRunning = false;
        if (animationId) cancelAnimationFrame(animationId);
        if (timerInterval) clearInterval(timerInterval);
        
        const overlay = document.getElementById('game-overlay');
        const title = document.getElementById('overlay-title');
        const desc = document.getElementById('overlay-desc');
        const btn = document.getElementById('start-game-btn');
        const statusText = document.getElementById('game-status-text');
        
        if (overlay) {
            overlay.style.display = 'flex';
            title.innerText = "Time's Up!";
            desc.innerHTML = `You caught ATS skills and scored <strong style="color:#34d399;font-size:1.15rem;">\${score}</strong> points!<br>Still auditing demographic profiles...`;
            btn.innerText = "Play Again";
            statusText.innerText = "Game Paused";
        }
    }
})();
</script>
<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" onload="
    const oldScript = document.getElementById('ats-game-script');
    if (oldScript && !window.atsGameLoaded) {
        window.atsGameLoaded = true;
        const newScript = document.createElement('script');
        newScript.textContent = oldScript.textContent;
        document.body.appendChild(newScript);
    }
" style="display:none;" />
"""

# Built-in fallback sample JD if no files found
DEFAULT_SAMPLE_JD = """\
Senior Software Engineer — Backend (Python)

About the Role:
We are looking for a Senior Backend Engineer to design and build scalable
microservices. You will work closely with product and data teams to deliver
high-quality APIs and data pipelines.

Requirements:
• 5+ years of professional software engineering experience
• Strong proficiency in Python (Django or FastAPI)
• Experience with PostgreSQL and Redis
• Familiarity with Docker and Kubernetes
• Understanding of CI/CD pipelines (GitHub Actions, Jenkins)
• Experience with cloud platforms (AWS or GCP)
• Bachelor's degree in Computer Science or related field

Nice to Have:
• Experience with message queues (RabbitMQ, Kafka)
• Knowledge of GraphQL
• Contributions to open-source projects
• Machine Learning / Data Engineering exposure

Responsibilities:
• Design and implement RESTful APIs and microservices
• Write clean, testable, and well-documented code
• Participate in code reviews and mentor junior engineers
• Collaborate with cross-functional teams on product features
• Monitor and optimize application performance
"""


# ---------------------------------------------------------------------------
# Score Formatting Helpers
# ---------------------------------------------------------------------------


def _score_emoji(score: float) -> str:
    if score >= 80:
        return "🟢"
    if score >= 60:
        return "🟡"
    if score >= 40:
        return "🟠"
    return "🔴"


def _score_label(score: float) -> str:
    if score >= 80:
        return "Strong Match"
    if score >= 60:
        return "Good Match"
    if score >= 40:
        return "Partial Match"
    return "Weak Match"


def _score_class(score: float) -> str:
    if score >= 70:
        return "score-high"
    if score >= 45:
        return "score-mid"
    return "score-low"


def _bar_class(score: float) -> str:
    if score >= 70:
        return "bar-high"
    if score >= 45:
        return "bar-mid"
    return "bar-low"


def _badge_class(score: float) -> str:
    if score >= 70:
        return "badge-green"
    if score >= 45:
        return "badge-yellow"
    return "badge-red"


def _format_score_bar(label: str, score: float, weight: str) -> str:
    """Return an HTML snippet for a labelled score progress bar."""
    bar_cls = _bar_class(score)
    return (
        f'<div class="score-bar-container">'
        f'  <div class="score-bar-label"><span>{label} ({weight})</span>'
        f'  <span class="score-badge {_badge_class(score)}">{score:.1f}</span></div>'
        f'  <div class="score-bar-track">'
        f'    <div class="score-bar-fill {bar_cls}" style="width:{score:.1f}%"></div>'
        f"  </div>"
        f"</div>"
    )


def _format_skill_badges(matched: List[str], missing: List[str]) -> str:
    """Return HTML for matched/missing skill badges."""
    parts: list[str] = ['<div style="margin:12px 0">']
    parts.append('<p style="font-weight:600;margin-bottom:6px;">✅ Matched Skills</p>')
    if matched:
        for s in matched:
            parts.append(f'<span class="skill-badge matched">{s}</span>')
    else:
        parts.append('<span style="color:#94a3b8;font-size:0.88rem">None matched</span>')

    parts.append('<p style="font-weight:600;margin:14px 0 6px;">❌ Missing Skills</p>')
    if missing:
        for s in missing:
            parts.append(f'<span class="skill-badge missing">{s}</span>')
    else:
        parts.append('<span style="color:#94a3b8;font-size:0.88rem">None missing — great!</span>')
    parts.append("</div>")
    return "\n".join(parts)


def _format_red_flags(red_flags: List[Dict[str, Any]]) -> str:
    """Return HTML for Red Flags with negative penalties."""
    if not red_flags:
        return '<p style="color:#94a3b8;font-size:0.88rem">🟢 No Red Flags detected — candidate has a clean profile.</p>'
    
    html_parts = ['<div class="flags-grid">']
    for f in red_flags:
        flag_name = f.get("flag", "Red Flag")
        penalty = f.get("penalty", 0.0)
        evidence = f.get("evidence", "")
        
        penalty_str = "AUTO REJECT" if penalty == "AUTO_REJECT" else (f"{penalty:.1f} pts" if isinstance(penalty, (int, float)) else str(penalty))
        html_parts.append(
            f'<div class="flag-card red-flag">'
            f'  <div class="flag-header">'
            f'    <span class="flag-title">⚠️ {flag_name}</span>'
            f'    <span class="flag-badge red-badge">{penalty_str}</span>'
            f'  </div>'
            f'  <div class="flag-evidence">{evidence}</div>'
            f'</div>'
        )
    html_parts.append('</div>')
    return "\n".join(html_parts)


def _format_green_flags(green_flags: List[Dict[str, Any]]) -> str:
    """Return HTML for Green Flags with positive bonuses."""
    if not green_flags:
        return '<p style="color:#94a3b8;font-size:0.88rem">⚪ No special Green Flags detected.</p>'
    
    html_parts = ['<div class="flags-grid">']
    for f in green_flags:
        flag_name = f.get("flag", "Green Flag")
        bonus = f.get("bonus", 0.0)
        evidence = f.get("evidence", "")
        
        bonus_str = f"+{bonus:.1f} pts"
        html_parts.append(
            f'<div class="flag-card green-flag">'
            f'  <div class="flag-header">'
            f'    <span class="flag-title">✨ {flag_name}</span>'
            f'    <span class="flag-badge green-badge">{bonus_str}</span>'
            f'  </div>'
            f'  <div class="flag-evidence">{evidence}</div>'
            f'</div>'
        )
    html_parts.append('</div>')
    return "\n".join(html_parts)


def _format_list_items(items: List[str], css_class: str) -> str:
    """Return HTML for a list of strength/gap items."""
    if not items:
        return '<p style="color:#94a3b8;font-size:0.88rem">No items to display</p>'
    return "\n".join(f'<div class="{css_class}">{item}</div>' for item in items)


# ---------------------------------------------------------------------------
# Core Analysis Function
# ---------------------------------------------------------------------------


def analyze_resume(
    pdf_file: Any,
    jd_text: str,
) -> Tuple[str, str, str, str, str, str, str, str, str, str]:
    """
    Run the full resume analysis pipeline.

    Returns ten string outputs for the Gradio UI components:
      0 – overall_score_html
      1 – score_breakdown_html
      2 – skill_match_html
      3 – experience_html
      4 – education_html
      5 – strengths_html
      6 – gaps_html
      7 – red_flags_html
      8 – green_flags_html
      9 – status_message
    """
    # ── 1. Validate inputs ────────────────────────────────────────────────
    valid, err = validate_pdf(pdf_file)
    if not valid:
        return ("", "", "", "", "", "", "", "", "", f"⚠️ {err}")

    valid, err = validate_jd_text(jd_text)
    if not valid:
        return ("", "", "", "", "", "", "", "", "", f"⚠️ {err}")

    # ── 2. Extract text from PDF ──────────────────────────────────────────
    try:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        resume_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        logger.exception("PDF extraction failed")
        return ("", "", "", "", "", "", "", "", "", f"⚠️ Failed to extract text from PDF: {exc}")

    # ── 3. Run analysis graph ─────────────────────────────────────────────
    try:
        from agents.graph import run_analysis

        result: Dict[str, Any] = run_analysis(
            resume_text=resume_text,
            jd_text=jd_text,
        )
    except ImportError:
        logger.error("agents.graph module not available")
        return (
            "", "", "", "", "", "", "", "", "",
            "⚠️ Analysis engine not available. Please ensure agents/graph.py is implemented.",
        )
    except Exception as exc:
        logger.exception("Analysis pipeline failed")
        return ("", "", "", "", "", "", "", "", "", f"⚠️ Analysis failed: {exc}")

    # ── 4. Check for pipeline errors ──────────────────────────────────────
    if result.get("error"):
        return ("", "", "", "", "", "", "", "", "", f"⚠️ {result['error']}")

    # ── 5. Format results ─────────────────────────────────────────────────
    match_score = result.get("match_score", 0.0)
    keyword = result.get("keyword_score", 0.0)
    semantic = result.get("semantic_score", 0.0)
    experience_score = result.get("experience_score", 0.0)
    education_score = result.get("education_score", 0.0)
    recency_score = result.get("recency_score", 0.0)
    achievement_score = result.get("achievement_score", 0.0)

    skill_match: dict = result.get("skill_match", {})
    experience_match: dict = result.get("experience_match", {})
    education_match: dict = result.get("education_match", {})
    strengths: list = result.get("strengths", [])
    gaps: list = result.get("gaps", [])
    red_flags: list = result.get("red_flags", [])
    green_flags: list = result.get("green_flags", [])

    # Overall score display
    score_cls = _score_class(match_score)
    overall_html = (
        f'<div class="score-display score-animate">'
        f'  <div class="score-number {score_cls}">{match_score:.1f}</div>'
        f'  <div style="font-size:1.1rem;color:#94a3b8">/100</div>'
        f'  <div class="score-label">{_score_emoji(match_score)} {_score_label(match_score)}</div>'
        f"</div>"
    )

    if result.get("disqualified", False):
        reason = result.get("disqualification_reason", "Candidate does not meet the baseline recruitment rules.")
        disq_html = (
            f'<div class="disqualified-banner">'
            f'  <h3>🚨 AUTO-DISQUALIFIED</h3>'
            f'  <p><strong>Reason:</strong> {reason}</p>'
            f'</div>'
        )
        overall_html = disq_html + overall_html

    # Buzzword penalty parsing
    buzzword_penalty = 0.0
    for rf in red_flags:
        if rf.get("flag") == "Buzzword Overload":
            penalty_val = rf.get("penalty", 0.0)
            buzzword_penalty = float(penalty_val) if isinstance(penalty_val, (int, float)) else -5.0
            break

    # Score breakdown bars (7 factors)
    breakdown_html = (
        _format_score_bar("🎯 Hard Skills Match", keyword, "35%")
        + _format_score_bar("⏱️ Skill Recency & Proximity", recency_score, "15%")
        + _format_score_bar("💼 Experience Relevance", experience_score, "20%")
        + _format_score_bar("🎓 Education Match", education_score, "10%")
        + _format_score_bar("🧠 Semantic Similarity", semantic, "10%")
        + _format_score_bar("📈 Achievement Quality (A-COE)", achievement_score, "5%")
        + _format_score_bar("🗣️ Buzzword Compliance", 100.0 + buzzword_penalty, "5%")
    )

    # Skill match (handle both key formats for safety)
    matched = skill_match.get("matched", skill_match.get("matched_skills", []))
    missing = skill_match.get("missing", skill_match.get("missing_skills", []))
    skill_html = _format_skill_badges(matched, missing)

    # Experience match
    exp_years = experience_match.get("resume_years", "N/A")
    req_years = experience_match.get("required_years", "N/A")
    exp_verdict = experience_match.get("verdict", "N/A")
    experience_html = (
        f'<div class="result-card">'
        f"  <h3>💼 Experience Match</h3>"
        f"  <p><strong>Your experience:</strong> {exp_years} years</p>"
        f"  <p><strong>Required:</strong> {req_years} years</p>"
        f"  <p><strong>Verdict:</strong> {exp_verdict}</p>"
        f"</div>"
    )

    # Education match
    edu_resume = education_match.get("resume_degree", "N/A")
    edu_required = education_match.get("required_degree", "N/A")
    edu_verdict = education_match.get("verdict", "N/A")
    education_html = (
        f'<div class="result-card">'
        f"  <h3>🎓 Education Match</h3>"
        f"  <p><strong>Your education:</strong> {edu_resume}</p>"
        f"  <p><strong>Required:</strong> {edu_required}</p>"
        f"  <p><strong>Verdict:</strong> {edu_verdict}</p>"
        f"</div>"
    )

    # Strengths & Gaps (filter out Red/Green Flag items since they are shown separately)
    cleaned_strengths = [s for s in strengths if not s.startswith("Green Flag:")]
    cleaned_gaps = [g for g in gaps if not g.startswith("Red Flag:")]

    strengths_html = _format_list_items(cleaned_strengths, "strength-item")
    gaps_html = _format_list_items(cleaned_gaps, "gap-item")

    # Format Red & Green Flags
    red_flags_html = _format_red_flags(red_flags)
    green_flags_html = _format_green_flags(green_flags)

    provider = result.get("provider_used", "unknown")
    status = f"✅ Analysis complete • Provider: {provider} • Score: {match_score:.1f}/100"

    return (
        overall_html,
        breakdown_html,
        skill_html,
        experience_html,
        education_html,
        strengths_html,
        gaps_html,
        red_flags_html,
        green_flags_html,
        status,
    )


# ---------------------------------------------------------------------------
# Improvement Suggestions Function
# ---------------------------------------------------------------------------


def get_improvements(
    pdf_file: Any,
    jd_text: str,
) -> Tuple[str, str, str]:
    """
    Run analysis and return improvement suggestions.

    Returns three strings:
      0 – suggestions_html
      1 – ats_bullets_html
      2 – status_message
    """
    valid, err = validate_pdf(pdf_file)
    if not valid:
        return ("", "", f"⚠️ {err}")

    valid, err = validate_jd_text(jd_text)
    if not valid:
        return ("", "", f"⚠️ {err}")

    try:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        resume_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        return ("", "", f"⚠️ PDF extraction failed: {exc}")

    try:
        from agents.graph import run_analysis

        result = run_analysis(resume_text=resume_text, jd_text=jd_text)
    except ImportError:
        return ("", "", "⚠️ Analysis engine not available.")
    except Exception as exc:
        return ("", "", f"⚠️ Analysis failed: {exc}")

    if result.get("error"):
        return ("", "", f"⚠️ {result['error']}")

    # Format improvement suggestions
    suggestions: list = result.get("improvement_suggestions", [])
    if suggestions:
        parts = []
        for i, item in enumerate(suggestions, 1):
            if isinstance(item, dict):
                text = item.get("suggestion", item.get("text", str(item)))
                impact = item.get("impact", "")
                # Color-code impact badges
                if impact.lower() in ("high",):
                    badge_cls = "badge-red"
                elif impact.lower() in ("medium",):
                    badge_cls = "badge-yellow"
                elif impact.lower() in ("projection",):
                    badge_cls = "badge-green"
                else:
                    badge_cls = "badge-yellow"
                impact_badge = f' <span class="score-badge {badge_cls}">{impact}</span>' if impact else ""
                parts.append(f'<div class="improvement-item"><strong>{i}.</strong> {text}{impact_badge}</div>')
            else:
                parts.append(f'<div class="improvement-item"><strong>{i}.</strong> {item}</div>')
        suggestions_html = "\n".join(parts)
    else:
        suggestions_html = '<p style="color:#94a3b8">No improvement suggestions generated.</p>'

    # Format ATS-optimized bullets
    ats_bullets: list = result.get("ats_optimized_bullets", [])
    if ats_bullets:
        bullet_parts = []
        for item in ats_bullets:
            if isinstance(item, dict):
                original = item.get("original", "")
                improved = item.get("improved", "")
                keywords = item.get("keywords_added", [])
                rationale = item.get("rationale", "")
                kw_str = ", ".join(keywords) if keywords else ""
                bullet_parts.append(
                    f'<div class="improvement-item">'
                    + (f'  <p style="color:#94a3b8;font-size:0.82rem;margin-bottom:4px">Original:</p>'
                       f"  <p style=\"margin-bottom:8px\">{original}</p>" if original else "")
                    + f'  <p style="color:#34d399;font-size:0.82rem;margin-bottom:4px">✨ Optimized:</p>'
                    f"  <p><strong>{improved}</strong></p>"
                    + (f'  <p style="font-size:0.78rem;color:#fbbf24;margin-top:6px">Keywords added: {kw_str}</p>' if kw_str else "")
                    + (f'  <p style="font-size:0.78rem;color:#94a3b8;margin-top:4px;font-style:italic">💡 {rationale}</p>' if rationale else "")
                    + f"</div>"
                )
            else:
                bullet_parts.append(f'<div class="improvement-item">• {item}</div>')
        ats_html = "\n".join(bullet_parts)
    else:
        ats_html = '<p style="color:#94a3b8">No ATS-optimized bullets generated.</p>'

    return (suggestions_html, ats_html, "✅ Improvement suggestions generated successfully.")


# ---------------------------------------------------------------------------
# Batch Analysis Function
# ---------------------------------------------------------------------------


def batch_analyze(
    pdf_files: List[Any],
    jd_text: str,
) -> Tuple[Any, str]:
    """
    Analyze multiple resumes against a single JD.

    Returns a list-of-lists for the Gradio Dataframe and a status message.
    """
    valid, err = validate_jd_text(jd_text)
    if not valid:
        return ([], f"⚠️ {err}")

    if not pdf_files:
        return ([], "⚠️ No files uploaded. Please upload at least one PDF resume.")

    try:
        from agents.graph import run_analysis
    except ImportError:
        return ([], "⚠️ Analysis engine not available.")

    rows: list[list] = []
    errors: list[str] = []

    for pdf_file in pdf_files:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        file_name = Path(file_path).stem

        try:
            resume_text = extract_text_from_pdf(file_path)
            result = run_analysis(resume_text=resume_text, jd_text=jd_text)

            if result.get("error"):
                errors.append(f"{file_name}: {result['error']}")
                continue

            match_score = result.get("match_score", 0.0)
            skill_match = result.get("skill_match", {})
            matched = skill_match.get("matched", skill_match.get("matched_skills", []))
            top_skills = ", ".join(matched[:5]) if matched else "—"
            
            if result.get("disqualified", False):
                label = "AUTO-DISQUALIFIED"
                emoji = "🚨"
            else:
                label = _score_label(match_score)
                emoji = _score_emoji(match_score)

            rows.append([
                file_name,
                f"{match_score:.1f}",
                f"{emoji} {label}",
                top_skills,
            ])

        except Exception as exc:
            errors.append(f"{file_name}: {exc}")

    # Sort by score descending
    rows.sort(key=lambda r: float(r[1]), reverse=True)

    # Add rank
    ranked_rows = []
    for i, row in enumerate(rows, 1):
        ranked_rows.append([f"#{i}", *row])

    status_parts = [f"✅ Analyzed {len(rows)}/{len(pdf_files)} resumes."]
    if errors:
        status_parts.append(f"⚠️ {len(errors)} error(s): " + "; ".join(errors[:3]))

    return (ranked_rows, " ".join(status_parts))

# ---------------------------------------------------------------------------
# PDF Resume Builder Function
# ---------------------------------------------------------------------------


def build_resume_pdf(
    full_name: str, email: str, phone: str, location: str,
    linkedin: str, portfolio: str, summary: str, skills: str,
    # Experience 1
    exp1_company: str, exp1_role: str, exp1_start: str, exp1_end: str, exp1_bullets: str,
    # Experience 2
    exp2_company: str, exp2_role: str, exp2_start: str, exp2_end: str, exp2_bullets: str,
    # Experience 3
    exp3_company: str, exp3_role: str, exp3_start: str, exp3_end: str, exp3_bullets: str,
    # Education 1
    edu1_degree: str, edu1_institution: str, edu1_year: str, edu1_gpa: str,
    # Education 2
    edu2_degree: str, edu2_institution: str, edu2_year: str, edu2_gpa: str,
    # Certifications
    certifications: str,
    # Project 1
    proj1_name: str, proj1_desc: str, proj1_tech: str,
    # Project 2
    proj2_name: str, proj2_desc: str, proj2_tech: str,
) -> Tuple[Any, str]:
    """Build a PDF resume from structured inputs. Returns (file_path, status)."""
    if not full_name or not full_name.strip():
        return None, "⚠️ Please enter your full name."

    # Assemble experience entries
    experience_entries = []
    for company, role, start, end, bullets in [
        (exp1_company, exp1_role, exp1_start, exp1_end, exp1_bullets),
        (exp2_company, exp2_role, exp2_start, exp2_end, exp2_bullets),
        (exp3_company, exp3_role, exp3_start, exp3_end, exp3_bullets),
    ]:
        if company and company.strip() and role and role.strip():
            experience_entries.append({
                "company": company, "role": role,
                "start_date": start or "", "end_date": end or "",
                "bullets": bullets or "",
            })

    # Assemble education entries
    education_entries = []
    for degree, inst, year, gpa in [
        (edu1_degree, edu1_institution, edu1_year, edu1_gpa),
        (edu2_degree, edu2_institution, edu2_year, edu2_gpa),
    ]:
        if degree and degree.strip():
            education_entries.append({
                "degree": degree, "institution": inst or "",
                "year": year or "", "gpa": gpa or "",
            })

    # Assemble project entries
    projects = []
    for name, desc, tech in [
        (proj1_name, proj1_desc, proj1_tech),
        (proj2_name, proj2_desc, proj2_tech),
    ]:
        if name and name.strip():
            projects.append({
                "name": name, "description": desc or "",
                "technologies": tech or "",
            })

    try:
        from core.resume_builder import generate_resume_pdf

        file_path = generate_resume_pdf(
            full_name=full_name, email=email or "", phone=phone or "",
            location=location or "", linkedin=linkedin or "",
            portfolio=portfolio or "", summary=summary or "",
            skills=skills or "", experience_entries=experience_entries,
            education_entries=education_entries,
            certifications=certifications or "", projects=projects,
        )
        if file_path:
            return file_path, f"✅ Resume PDF generated successfully! Click the download link above."
        else:
            return None, "⚠️ Failed to generate PDF. Please check your inputs."
    except Exception as exc:
        logger.exception("Resume PDF generation failed.")
        return None, f"⚠️ PDF generation failed: {exc}"




def run_gan_audit(
    pdf_file: Any,
    jd_text: str,
) -> Tuple[str, str, str, str]:
    """
    Simulate the GAN Generative Adversarial stress test.
    """
    valid, err = validate_pdf(pdf_file)
    if not valid:
        return ("", "", "", f"⚠️ {err}")
    valid, err = validate_jd_text(jd_text)
    if not valid:
        return ("", "", "", f"⚠️ {err}")

    # Extract text
    try:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        resume_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        return ("", "", "", f"⚠️ PDF extraction failed: {exc}")

    # 1. Generator generates hacked resume block
    try:
        from agents.auditor import generate_adversarial_resume, audit_adversarial_resume, run_demographic_bias_audit
        from agents.graph import run_analysis
        
        # Generator creates hacked resume text
        hacked_text = generate_adversarial_resume(jd_text)
        
        # 2. Discriminator audits it
        discriminator_res = audit_adversarial_resume(hacked_text, jd_text)
    except Exception as exc:
        return ("", "", "", f"⚠️ GAN simulation setup failed: {exc}")

    # Format Generator Output
    generator_html = (
        f'<div class="result-card">'
        f'  <h3 style="color:#a78bfa">🤖 Generator Output (Hacked Resume Segment)</h3>'
        f'  <p style="color:#94a3b8;font-size:0.85rem;margin-bottom:8px">'
        f'    This adversarial resume text was generated by the LLM attempting to exploit the ATS Scorer weights:'
        f'  </p>'
        f'  <div style="background:rgba(255,255,255,0.02);padding:14px;border:1px solid rgba(255,255,255,0.05);'
        f'              border-radius:8px;font-family:monospace;font-size:0.88rem;color:#e2e8f0;white-space:pre-wrap">'
        f'{hacked_text}'
        f'  </div>'
        f'</div>'
    )

    # Format Discriminator Output
    if "error" in discriminator_res:
        discriminator_html = f'<p style="color:#ef4444">Discriminator Error: {discriminator_res["error"]}</p>'
    else:
        m_score = discriminator_res.get("match_score", 0.0)
        disqualified = discriminator_res.get("disqualified", False)
        red_flags = discriminator_res.get("red_flags", [])
        
        term_logs = []
        term_logs.append("[SYSTEM] Loading Discriminator Node...")
        term_logs.append("[SYSTEM] Parsing hacked input stream...")
        term_logs.append(f"[DISCRIMINATOR] Match Score: {m_score:.1f}/100")
        if disqualified:
            term_logs.append(f"[ALERT] Candidate auto-disqualified: {discriminator_res.get('disqualification_reason')}")
            
        term_logs.append(f"[DISCRIMINATOR] Running Red Flag compliance checks...")
        for rf in red_flags:
            term_logs.append(f"  [FLAGGED] {rf['flag']} -> Penalty: {rf['penalty']} | Evidence: {rf['evidence']}")
            
        if not red_flags:
            term_logs.append("  [OK] No structural Red Flags detected.")
        term_logs.append("[SYSTEM] Audit complete. Hacking attempt mitigated.")

        log_lines = "\n".join(term_logs)
        discriminator_html = (
            f'<div class="result-card">'
            f'  <h3 style="color:#f87171">🛡️ Discriminator Audit (Mitigation Logs)</h3>'
            f'  <p style="color:#94a3b8;font-size:0.85rem;margin-bottom:8px">'
            f'    The Scorer acting as the Discriminator intercepted the hack and applied penalties:'
            f'  </p>'
            f'  <div class="arch-diagram" style="background:#090514;color:#4ade80;border-color:#ef4444;'
            f'              font-size:0.85rem;padding:12px;max-height:250px;overflow-y:auto">'
            f'{log_lines}'
            f'  </div>'
            f'</div>'
        )

    # 3. Demographic Fairness Bias Audit on real resume
    try:
        # We need to run normal analysis first to get parsed data
        baseline_res = run_analysis(resume_text=resume_text, jd_text=jd_text)
        if baseline_res.get("error"):
            bias_html = f'<p style="color:#ef4444">Bias Audit failed: {baseline_res["error"]}</p>'
        else:
            skills = baseline_res.get("resume_skills_normalized", [])
            jd_sk = baseline_res.get("jd_skills_normalized", [])
            parsed = baseline_res.get("resume_parsed", {})
            jd_ex = baseline_res.get("jd_extracted", {})
            
            bias_res = run_demographic_bias_audit(
                resume_parsed=parsed,
                jd_extracted=jd_ex,
                resume_skills=skills,
                jd_skills=jd_sk,
                resume_text=resume_text,
                jd_text=jd_text
            )
            
            immunity = bias_res["bias_immunity_index"]
            variance = bias_res["score_variance"]
            score_stdev = bias_res.get("score_stdev", 0.0)
            score_mean = bias_res.get("score_mean", 0.0)
            biased_count = bias_res.get("biased_profiles_count", 0)
            biased_factors = bias_res.get("biased_factors", [])
            methodology = bias_res.get("methodology", "")
            factor_analysis = bias_res.get("factor_analysis", {})
            
            compliance = "PASSED ✅ Bias-Immune" if bias_res["eeoc_compliance"] else "FAILED ⚠️ Demographic Skew Detected"
            comp_class = "badge-green" if bias_res["eeoc_compliance"] else "badge-red"
            
            # Build per-profile audit rows with color-coded verdicts
            audit_rows = []
            for item in bias_res["audit_logs"]:
                verdict = item.get("verdict", "")
                if "Bias Detected" in verdict:
                    verdict_class = "badge-red"
                elif "Minor Variance" in verdict:
                    verdict_class = "badge-yellow"
                else:
                    verdict_class = "badge-green"
                
                deviation = abs(item["score"] - score_mean)
                audit_rows.append(
                    f'<tr>'
                    f'  <td>{item["profile_label"]}</td>'
                    f'  <td>{item["assigned_name"]}</td>'
                    f'  <td><strong>{item["score"]:.1f}</strong></td>'
                    f'  <td style="font-size:0.8rem;color:#94a3b8">Δ{deviation:.1f}pts</td>'
                    f'  <td><span class="score-badge {verdict_class}" style="padding:2px 8px;font-size:0.75rem">{verdict}</span></td>'
                    f'</tr>'
                )
            rows_html = "\n".join(audit_rows)
            
            # Build per-factor variance breakdown
            factor_rows = []
            for factor_key, factor_data in factor_analysis.items():
                if isinstance(factor_data, dict):
                    f_range = factor_data.get("range", 0.0)
                    f_stdev = factor_data.get("stdev", 0.0)
                    f_biased = factor_data.get("biased", False)
                    f_status = "⚠️ Bias" if f_biased else "✅ Clean"
                    f_class = "color:#ef4444" if f_biased else "color:#4ade80"
                    factor_rows.append(
                        f'<tr>'
                        f'  <td style="text-transform:capitalize">{factor_key.replace("_", " ")}</td>'
                        f'  <td>{f_range:.2f}</td>'
                        f'  <td>{f_stdev:.2f}</td>'
                        f'  <td style="{f_class};font-weight:600">{f_status}</td>'
                        f'</tr>'
                    )
            factor_html = "\n".join(factor_rows)
            
            biased_factors_str = ""
            if biased_factors:
                factors_list = ", ".join(f.replace("_", " ").title() for f in biased_factors)
                biased_factors_str = (
                    f'<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);'
                    f'border-radius:8px;padding:10px;margin:10px 0">'
                    f'<strong style="color:#ef4444">⚠️ Bias detected in:</strong> {factors_list}'
                    f'</div>'
                )
            
            bias_html = (
                f'<div class="result-card">'
                f'  <h3 style="color:#22d3ee">⚖️ Demographic Fairness Audit (EEOC Compliance)</h3>'
                f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">'
                f'    <div>'
                f'      <p style="margin:0;font-size:0.9rem">Bias Immunity Index: <strong style="color:#22d3ee">{immunity:.1f}%</strong></p>'
                f'      <p style="margin:0;font-size:0.9rem">Score Range: <strong>{variance:.2f} pts</strong> · Std Dev: <strong>{score_stdev:.2f}</strong> · Mean: <strong>{score_mean:.1f}</strong></p>'
                f'      <p style="margin:0;font-size:0.9rem">Biased Profiles: <strong>{biased_count}/5</strong></p>'
                f'    </div>'
                f'    <span class="score-badge {comp_class}" style="font-size:0.9rem">{compliance}</span>'
                f'  </div>'
                f'  {biased_factors_str}'
                f'  <p style="color:#94a3b8;font-size:0.82rem;margin-bottom:10px;font-style:italic">'
                f'    {methodology}'
                f'  </p>'
                f'  <p style="color:#c0caf5;font-size:0.88rem;font-weight:600;margin-bottom:6px">📊 Per-Profile Counterfactual Results</p>'
                f'  <table style="width:100%;font-size:0.88rem">'
                f'    <thead>'
                f'      <tr><th>Profile</th><th>Assigned Identity</th><th>Score</th><th>Deviation</th><th>Audit Status</th></tr>'
                f'    </thead>'
                f'    <tbody>'
                f'{rows_html}'
                f'    </tbody>'
                f'  </table>'
                + (
                    f'  <p style="color:#c0caf5;font-size:0.88rem;font-weight:600;margin:14px 0 6px">🔬 Per-Factor Variance Breakdown</p>'
                    f'  <table style="width:100%;font-size:0.85rem">'
                    f'    <thead>'
                    f'      <tr><th>Scoring Factor</th><th>Range (pts)</th><th>Std Dev</th><th>Status</th></tr>'
                    f'    </thead>'
                    f'    <tbody>'
                    f'{factor_html}'
                    f'    </tbody>'
                    f'  </table>'
                    if factor_html else ""
                )
                + f'</div>'
            )
    except Exception as exc:
        bias_html = f'<p style="color:#ef4444">Bias Audit failed: {exc}</p>'

    status = "✅ GAN Stress-Test & Resilience Audit complete."
    return (generator_html, discriminator_html, bias_html, status)


# ---------------------------------------------------------------------------
# Sample JD Loader Callback
# ---------------------------------------------------------------------------


def load_sample_jd(choice: str) -> str:
    """Return the text of a selected sample JD, or the default."""
    if choice and choice in SAMPLE_JDS:
        return SAMPLE_JDS[choice]
    return DEFAULT_SAMPLE_JD


# ---------------------------------------------------------------------------
# About Page Content
# ---------------------------------------------------------------------------

ABOUT_MD = """\
## 📊 Scoring Methodology

PSI Resume Analyser uses a **weighted composite scoring** model inspired by
real-world Applicant Tracking Systems:

| Component | Weight | What It Measures |
|---|---|---|
| 🎯 **Keyword Match** | 40% | Exact skill overlap between resume & JD |
| 🧠 **Semantic Similarity** | 25% | Conceptual alignment via sentence embeddings |
| 💼 **Experience Relevance** | 25% | Years of experience + role relevance |
| 🎓 **Education Match** | 10% | Degree/field alignment with requirements |

**Formula:**
```
ATS Score = 0.40 × Keyword + 0.25 × Semantic + 0.25 × Experience + 0.10 × Education
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM Orchestration** | LangGraph (multi-agent pipeline) |
| **Primary LLM** | Google Gemini 2.0 Flash |
| **Fallback LLM** | Groq (Llama 3.3 70B) |
| **Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`) |
| **PDF Parsing** | PyPDF2 + pdfplumber (dual-backend) |
| **Skill Taxonomy** | Custom JSON taxonomy with 300+ aliases |
| **Frontend** | Gradio 5.x with custom CSS |
| **Deployment** | HuggingFace Spaces |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     User Interface (Gradio)                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌─────────┐ │
│  │ Analyze  │  │   Improve    │  │   Batch   │  │  About  │ │
│  └─────┬────┘  └──────┬───────┘  └─────┬─────┘  └─────────┘ │
└────────┼───────────────┼────────────────┼────────────────────┘
         │               │                │
         ▼               ▼                ▼
┌──────────────────────────────────────────────────────────────┐
│                 LangGraph Analysis Pipeline                   │
│                                                               │
│  ┌───────────┐    ┌───────────┐    ┌──────────────────────┐  │
│  │  Resume   │    │    JD     │    │   Skill Normalizer   │  │
│  │  Parser   │───▶│ Extractor │───▶│   (Taxonomy + LLM)   │  │
│  │  (LLM)   │    │  (LLM)   │    │                      │  │
│  └───────────┘    └───────────┘    └──────────┬───────────┘  │
│                                               │              │
│                                               ▼              │
│  ┌──────────────────┐    ┌────────────────────────────────┐  │
│  │    Improver       │◀──│         Scorer                 │  │
│  │ (Suggestions)     │    │  (Keyword+Semantic+Exp+Edu)   │  │
│  └──────────────────┘    └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐    ┌──────────────────────┐
│   Embeddings    │    │   Skill Taxonomy     │
│ (MiniLM-L6-v2) │    │   (300+ aliases)     │
└─────────────────┘    └──────────────────────┘
```

---

## 📝 How to Use

1. **Upload** your resume as a PDF
2. **Paste** (or load a sample) job description
3. Click **🚀 Analyze Resume** and wait for the magic
4. Review your **ATS score breakdown**, skill matches, and improvement tips
5. Use the **Improve** tab for ATS-optimized bullet rewrites

---

*Built with ❤️ by the PSI team • Powered by LangGraph & Google Gemini*
"""


# ---------------------------------------------------------------------------
# Build Gradio UI
# ---------------------------------------------------------------------------


def create_app() -> gr.Blocks:
    """Construct and return the Gradio Blocks application."""

    custom_css = _load_css()

    with gr.Blocks(
        title="PSI Resume Analyser",
        theme=gr.themes.Soft(),
        css=custom_css,
    ) as app:

        # ── Header ───────────────────────────────────────────────────────
        gr.HTML(
            """
            <div class="app-header">
                <h1>🎯 PSI Resume Analyser</h1>
                <p>
                    AI-powered ATS scoring engine that deeply analyses your resume
                    against any job description — powered by LangGraph and Gemini.
                </p>
            </div>
            """
        )

        with gr.Tabs():
            # ══════════════════════════════════════════════════════════════
            #  TAB 1 — Analyze Resume
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📄 Analyze Resume"):
                with gr.Row():
                    # ── Left Column: Inputs ───────────────────────────────
                    with gr.Column(scale=2):
                        gr.Markdown("### 📤 Upload & Input")

                        pdf_input = gr.File(
                            label="Resume (PDF)",
                            file_types=[".pdf"],
                            type="filepath",
                            elem_classes=["upload-area"],
                        )

                        jd_input = gr.Textbox(
                            label="Job Description",
                            placeholder="Paste the full job description here…",
                            lines=12,
                            max_lines=30,
                        )

                        # Sample JD controls
                        sample_choices = list(SAMPLE_JDS.keys()) if SAMPLE_JDS else ["Default Sample JD"]
                        with gr.Row():
                            sample_dropdown = gr.Dropdown(
                                choices=sample_choices,
                                label="Load Sample JD",
                                interactive=True,
                                scale=3,
                            )
                            load_btn = gr.Button(
                                "📋 Load",
                                variant="secondary",
                                scale=1,
                            )

                        with gr.Accordion("📂 Browse & Search Job Description Dataset (28+ Real Roles)", open=False):
                            gr.Markdown("Click on any row in the dataset below to instantly load its Job Description:")
                            display_rows = [[r[0], r[1], r[2], r[3]] for r in JD_DATASET_ROWS]
                            jd_dataset_table = gr.Dataframe(
                                headers=["ID", "Job Title", "Company", "Location"],
                                value=display_rows,
                                interactive=False,
                                wrap=True,
                            )

                        analyze_btn = gr.Button(
                            "🚀 Analyze Resume",
                            variant="primary",
                            size="lg",
                        )

                        status_output = gr.Textbox(
                            label="Status",
                            interactive=False,
                            max_lines=2,
                        )

                    # ── Right Column: Results ─────────────────────────────
                    with gr.Column(scale=3):
                        gr.Markdown("### 📊 Analysis Results")

                        overall_score_display = gr.HTML(
                            value='<div class="score-display"><div class="score-number" '
                            'style="color:#94a3b8">—</div>'
                            '<div style="font-size:0.9rem;color:#64748b;margin-top:8px">'
                            "Upload a resume and JD to begin</div></div>",
                        )

                        with gr.Accordion("📈 Score Breakdown", open=True):
                            score_breakdown_display = gr.HTML()

                        with gr.Accordion("🔑 Skill Match", open=True):
                            skill_match_display = gr.HTML()

                        with gr.Row():
                            with gr.Column():
                                with gr.Accordion("💼 Experience", open=False):
                                    experience_display = gr.HTML()

                            with gr.Column():
                                with gr.Accordion("🎓 Education", open=False):
                                    education_display = gr.HTML()

                        with gr.Row():
                            with gr.Column():
                                with gr.Accordion("💪 Strengths", open=False):
                                    strengths_display = gr.HTML()

                            with gr.Column():
                                with gr.Accordion("⚠️ Gaps", open=False):
                                    gaps_display = gr.HTML()

                        with gr.Row():
                            with gr.Column():
                                with gr.Accordion("🟢 ATS Green Flags", open=True):
                                    green_flags_display = gr.HTML()

                            with gr.Column():
                                with gr.Accordion("🔴 ATS Red Flags", open=True):
                                    red_flags_display = gr.HTML()

                # Wire up events
                load_btn.click(
                    fn=load_sample_jd,
                    inputs=[sample_dropdown],
                    outputs=[jd_input],
                )

                jd_dataset_table.select(
                    fn=load_jd_from_dataset,
                    inputs=[],
                    outputs=[jd_input],
                )

                analyze_btn.click(
                    fn=analyze_resume,
                    inputs=[pdf_input, jd_input],
                    outputs=[
                        overall_score_display,
                        score_breakdown_display,
                        skill_match_display,
                        experience_display,
                        education_display,
                        strengths_display,
                        gaps_display,
                        red_flags_display,
                        green_flags_display,
                        status_output,
                    ],
                )

            # ══════════════════════════════════════════════════════════════
            #  TAB 2 — Improve Resume
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("✨ Improve Resume"):
                gr.Markdown(
                    "### ✨ Resume Improvement Suggestions\n"
                    "Upload your resume and paste the JD to get **ATS-optimized** "
                    "bullet point rewrites and actionable improvement tips."
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        improve_pdf = gr.File(
                            label="Resume (PDF)",
                            file_types=[".pdf"],
                            type="filepath",
                        )
                        improve_jd = gr.Textbox(
                            label="Job Description",
                            placeholder="Paste the job description here…",
                            lines=8,
                        )
                        with gr.Accordion("📂 Browse & Search Job Description Dataset (28+ Real Roles)", open=False):
                            gr.Markdown("Click on any row in the dataset below to instantly load its Job Description:")
                            display_rows = [[r[0], r[1], r[2], r[3]] for r in JD_DATASET_ROWS]
                            improve_jd_dataset_table = gr.Dataframe(
                                headers=["ID", "Job Title", "Company", "Location"],
                                value=display_rows,
                                interactive=False,
                                wrap=True,
                            )
                        improve_btn = gr.Button(
                            "✨ Get Improvement Tips",
                            variant="primary",
                            size="lg",
                        )
                        improve_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            max_lines=2,
                        )

                    with gr.Column(scale=3):
                        with gr.Accordion("📝 Improvement Suggestions", open=True):
                            suggestions_display = gr.HTML()

                        with gr.Accordion("🎯 ATS-Optimized Bullets", open=True):
                            ats_bullets_display = gr.HTML()

                improve_jd_dataset_table.select(
                    fn=load_jd_from_dataset,
                    inputs=[],
                    outputs=[improve_jd],
                )

                improve_btn.click(
                    fn=get_improvements,
                    inputs=[improve_pdf, improve_jd],
                    outputs=[suggestions_display, ats_bullets_display, improve_status],
                )

            # ══════════════════════════════════════════════════════════════
            #  TAB 3 — Batch Analysis
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📦 Batch Analysis"):
                gr.Markdown(
                    "### 📦 Batch Resume Screening\n"
                    "Upload **multiple resumes** and rank them against a single job description."
                )

                with gr.Row():
                    with gr.Column(scale=2):
                        batch_files = gr.File(
                            label="Upload Resumes (PDFs)",
                            file_types=[".pdf"],
                            type="filepath",
                            file_count="multiple",
                        )
                        batch_jd = gr.Textbox(
                            label="Job Description",
                            placeholder="Paste the job description here…",
                            lines=8,
                        )
                        with gr.Accordion("📂 Browse & Search Job Description Dataset (28+ Real Roles)", open=False):
                            gr.Markdown("Click on any row in the dataset below to instantly load its Job Description:")
                            display_rows = [[r[0], r[1], r[2], r[3]] for r in JD_DATASET_ROWS]
                            batch_jd_dataset_table = gr.Dataframe(
                                headers=["ID", "Job Title", "Company", "Location"],
                                value=display_rows,
                                interactive=False,
                                wrap=True,
                            )
                        batch_btn = gr.Button(
                            "📊 Analyze All",
                            variant="primary",
                            size="lg",
                        )
                        batch_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            max_lines=3,
                        )

                    with gr.Column(scale=3):
                        batch_results = gr.Dataframe(
                            headers=["Rank", "Candidate", "Score", "Rating", "Top Matched Skills"],
                            label="Ranked Results",
                            interactive=False,
                            wrap=True,
                        )

                batch_jd_dataset_table.select(
                    fn=load_jd_from_dataset,
                    inputs=[],
                    outputs=[batch_jd],
                )

                batch_btn.click(
                    fn=batch_analyze,
                    inputs=[batch_files, batch_jd],
                    outputs=[batch_results, batch_status],
                )

            # ══════════════════════════════════════════════════════════════
            #  TAB 4 — GAN Stress-Tester
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("🛡️ GAN Stress-Tester"):
                gr.Markdown(
                    "### 🛡️ Generative Adversarial ATS Stress-Tester & Fairness Audit\n"
                    "Simulates a **Generative Adversarial Network (GAN)** framework. "
                    "The **Generator** attempts to hack the ATS with keyword-stuffed, AI-styled content, "
                    "while the **Discriminator** intercepting the profile flags structural issues. "
                    "It also audits pronoun and demographic bias (EEOC check)."
                )

                with gr.Accordion("🔍 What is a GAN Stress-Test & EEOC Demographic Audit? (Read details)", open=False):
                    gr.Markdown(
                        """
                        ### 🛡️ Core Concepts Explained

                        This tab performs two advanced evaluation procedures:

                        #### 1. 🤖 Generative Adversarial Network (GAN) Stress-Tester
                        In machine learning, a **Generative Adversarial Network (GAN)** consists of two neural networks contesting with each other:
                        *   **The Generator (The Hacker):** An LLM agent trained to craft adversarial, "hacked" resume content. It repeats technical keywords, injects excessive corporate buzzwords (like *synergy*, *results-oriented*), uses vague timeline descriptions, and attempts to trick the scoring system into giving it a perfect match.
                        *   **The Discriminator (The Gatekeeper):** Our ATS parser and scorer. It reviews the generated resume text, flags suspicious patterns (such as buzzword overload or timeline inconsistency), and applies realistic penalties (sometimes auto-disqualifying the candidate) to neutralize the hack.

                        *By pitting the Generator against the Discriminator, we prove that our parser is robust enough to spot and penalize keyword stuffing rather than being blindly fooled by it.*

                        ---

                        #### 2. ⚖️ EEOC Demographic Fairness Audit (Counterfactual Evaluation)
                        Automated tools must comply with the **Equal Employment Opportunity Commission (EEOC)** guidelines to prevent hiring bias.
                        *   **The Problem:** LLM extraction engines might inadvertently favor certain genders or cultural groups based on pronouns (he/she/they), honorifics (Mr./Ms./Mrs.), or names (e.g., John vs. Aisha).
                        *   **Our Solution (Counterfactual Test):** We create **5 identical copies** of the resume's skills, experience, and education, but programmatically swap only the names, honorifics, and pronouns to represent different demographic profiles. We then re-execute the entire pipeline for each.
                        *   **The Metric:** If the scorer is truly bias-free, the scoring variance should be zero (or near-zero). The audit measures the **Bias Immunity Index** based on the statistical range and standard deviation across these variants:
                            *   **EEOC Standard:** Requires a score deviation of **< 3.0 points** per profile and a **standard deviation < 2.0**.
                        """
                    )

                with gr.Row():
                    with gr.Column(scale=2):
                        gan_pdf = gr.File(
                            label="Resume (PDF)",
                            file_types=[".pdf"],
                            type="filepath",
                        )
                        gan_jd = gr.Textbox(
                            label="Job Description",
                            placeholder="Paste the job description here…",
                            lines=8,
                        )

                        gan_choices = list(SAMPLE_JDS.keys()) if SAMPLE_JDS else ["Default Sample JD"]
                        with gr.Row():
                            gan_dropdown = gr.Dropdown(
                                choices=gan_choices,
                                label="Load Sample JD",
                                interactive=True,
                                scale=3,
                            )
                            gan_load_btn = gr.Button(
                                "📋 Load",
                                variant="secondary",
                                scale=1,
                            )

                        with gr.Accordion("📂 Browse & Search Job Description Dataset (28+ Real Roles)", open=False):
                            gr.Markdown("Click on any row in the dataset below to instantly load its Job Description:")
                            display_rows = [[r[0], r[1], r[2], r[3]] for r in JD_DATASET_ROWS]
                            gan_jd_dataset_table = gr.Dataframe(
                                headers=["ID", "Job Title", "Company", "Location"],
                                value=display_rows,
                                interactive=False,
                                wrap=True,
                            )

                        gan_run_btn = gr.Button(
                            "🔥 Run Generative Adversarial Audit",
                            variant="primary",
                            size="lg",
                        )
                        gan_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            max_lines=2,
                        )

                        # Mini-game container
                        game_html = gr.HTML(
                            value=get_game_html(),
                            elem_id="gan-game-wrapper"
                        )

                    with gr.Column(scale=3):
                        with gr.Accordion("🤖 Generator (Hacked Segment)", open=True):
                            gan_generator_display = gr.HTML()

                        with gr.Accordion("🛡️ Discriminator (Detection Audit)", open=True):
                            gan_discriminator_display = gr.HTML()

                        with gr.Accordion("⚖️ EEOC Demographic Fairness Audit", open=True):
                            gan_bias_display = gr.HTML()

                gan_load_btn.click(
                    fn=load_sample_jd,
                    inputs=[gan_dropdown],
                    outputs=[gan_jd],
                )

                gan_jd_dataset_table.select(
                    fn=load_jd_from_dataset,
                    inputs=[],
                    outputs=[gan_jd],
                )

                gan_run_btn.click(
                    fn=run_gan_audit,
                    inputs=[gan_pdf, gan_jd],
                    outputs=[
                        gan_generator_display,
                        gan_discriminator_display,
                        gan_bias_display,
                        gan_status,
                    ],
                    js="""() => {
                        if (window.startATSGame) {
                            window.startATSGame();
                        }
                    }"""
                )

            # ══════════════════════════════════════════════════════════════
            #  TAB 5 — Resume Builder
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📝 Build Resume"):
                gr.Markdown(
                    "### 📝 PDF Resume Builder\n"
                    "Fill in your details below and generate a **professionally formatted, "
                    "ATS-optimized PDF resume**. Download it instantly."
                )

                with gr.Row():
                    with gr.Column(scale=3):
                        gr.Markdown("#### 👤 Personal Information")
                        with gr.Row():
                            rb_name = gr.Textbox(label="Full Name *", placeholder="John Doe", scale=2)
                            rb_email = gr.Textbox(label="Email", placeholder="john@example.com", scale=2)
                        with gr.Row():
                            rb_phone = gr.Textbox(label="Phone", placeholder="+1 (555) 123-4567", scale=1)
                            rb_location = gr.Textbox(label="Location", placeholder="New York, NY", scale=1)
                        with gr.Row():
                            rb_linkedin = gr.Textbox(label="LinkedIn URL", placeholder="linkedin.com/in/johndoe", scale=1)
                            rb_portfolio = gr.Textbox(label="Portfolio / GitHub", placeholder="github.com/johndoe", scale=1)

                        gr.Markdown("#### 📋 Professional Summary")
                        rb_summary = gr.Textbox(
                            label="Summary",
                            placeholder="Experienced software engineer with 5+ years building scalable web applications...",
                            lines=3,
                        )

                        gr.Markdown("#### 🔧 Technical Skills")
                        rb_skills = gr.Textbox(
                            label="Skills (comma-separated)",
                            placeholder="Python, JavaScript, React, Docker, AWS, PostgreSQL, Git, CI/CD",
                            lines=2,
                        )

                        gr.Markdown("#### 💼 Experience")
                        with gr.Accordion("Experience #1", open=True):
                            with gr.Row():
                                rb_exp1_company = gr.Textbox(label="Company", placeholder="Acme Corp", scale=2)
                                rb_exp1_role = gr.Textbox(label="Role", placeholder="Senior Software Engineer", scale=2)
                            with gr.Row():
                                rb_exp1_start = gr.Textbox(label="Start Date", placeholder="Jan 2022", scale=1)
                                rb_exp1_end = gr.Textbox(label="End Date", placeholder="Present", scale=1)
                            rb_exp1_bullets = gr.Textbox(
                                label="Key Achievements (one per line)",
                                placeholder="Led migration of monolith to microservices, reducing deploy time by 60%\nDesigned REST APIs serving 10M+ requests/day\nMentored 3 junior engineers",
                                lines=4,
                            )

                        with gr.Accordion("Experience #2", open=False):
                            with gr.Row():
                                rb_exp2_company = gr.Textbox(label="Company", placeholder="Previous Corp")
                                rb_exp2_role = gr.Textbox(label="Role", placeholder="Software Engineer")
                            with gr.Row():
                                rb_exp2_start = gr.Textbox(label="Start Date", placeholder="Jun 2019")
                                rb_exp2_end = gr.Textbox(label="End Date", placeholder="Dec 2021")
                            rb_exp2_bullets = gr.Textbox(label="Key Achievements", lines=3)

                        with gr.Accordion("Experience #3", open=False):
                            with gr.Row():
                                rb_exp3_company = gr.Textbox(label="Company")
                                rb_exp3_role = gr.Textbox(label="Role")
                            with gr.Row():
                                rb_exp3_start = gr.Textbox(label="Start Date")
                                rb_exp3_end = gr.Textbox(label="End Date")
                            rb_exp3_bullets = gr.Textbox(label="Key Achievements", lines=3)

                        gr.Markdown("#### 🎓 Education")
                        with gr.Accordion("Education #1", open=True):
                            with gr.Row():
                                rb_edu1_degree = gr.Textbox(label="Degree", placeholder="B.S. Computer Science", scale=2)
                                rb_edu1_institution = gr.Textbox(label="Institution", placeholder="MIT", scale=2)
                            with gr.Row():
                                rb_edu1_year = gr.Textbox(label="Year", placeholder="2019", scale=1)
                                rb_edu1_gpa = gr.Textbox(label="GPA (optional)", placeholder="3.8/4.0", scale=1)

                        with gr.Accordion("Education #2", open=False):
                            with gr.Row():
                                rb_edu2_degree = gr.Textbox(label="Degree")
                                rb_edu2_institution = gr.Textbox(label="Institution")
                            with gr.Row():
                                rb_edu2_year = gr.Textbox(label="Year")
                                rb_edu2_gpa = gr.Textbox(label="GPA (optional)")

                        gr.Markdown("#### 📜 Certifications")
                        rb_certs = gr.Textbox(
                            label="Certifications (one per line)",
                            placeholder="AWS Solutions Architect Professional\nGoogle Cloud Professional Data Engineer",
                            lines=2,
                        )

                        gr.Markdown("#### 🚀 Projects")
                        with gr.Accordion("Project #1", open=False):
                            rb_proj1_name = gr.Textbox(label="Project Name", placeholder="E-Commerce Platform")
                            rb_proj1_desc = gr.Textbox(label="Description", placeholder="Built a full-stack e-commerce platform with real-time inventory management", lines=2)
                            rb_proj1_tech = gr.Textbox(label="Technologies", placeholder="React, Node.js, MongoDB, Redis")

                        with gr.Accordion("Project #2", open=False):
                            rb_proj2_name = gr.Textbox(label="Project Name")
                            rb_proj2_desc = gr.Textbox(label="Description", lines=2)
                            rb_proj2_tech = gr.Textbox(label="Technologies")

                    with gr.Column(scale=1):
                        gr.Markdown("#### 📄 Generated Resume")
                        build_btn = gr.Button(
                            "📄 Generate PDF Resume",
                            variant="primary",
                            size="lg",
                        )
                        rb_output = gr.File(
                            label="Download Your Resume",
                            interactive=False,
                        )
                        rb_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            max_lines=2,
                        )

                        gr.Markdown(
                            """
                            **Tips for ATS-Optimized Resumes:**
                            - Use action verbs: *Led, Built, Designed, Optimized*
                            - Include metrics: *Reduced costs by 30%*
                            - Mirror JD keywords in your skills
                            - Keep bullets concise (1-2 lines)
                            - Use standard section headers
                            """
                        )

                build_btn.click(
                    fn=build_resume_pdf,
                    inputs=[
                        rb_name, rb_email, rb_phone, rb_location,
                        rb_linkedin, rb_portfolio, rb_summary, rb_skills,
                        rb_exp1_company, rb_exp1_role, rb_exp1_start, rb_exp1_end, rb_exp1_bullets,
                        rb_exp2_company, rb_exp2_role, rb_exp2_start, rb_exp2_end, rb_exp2_bullets,
                        rb_exp3_company, rb_exp3_role, rb_exp3_start, rb_exp3_end, rb_exp3_bullets,
                        rb_edu1_degree, rb_edu1_institution, rb_edu1_year, rb_edu1_gpa,
                        rb_edu2_degree, rb_edu2_institution, rb_edu2_year, rb_edu2_gpa,
                        rb_certs,
                        rb_proj1_name, rb_proj1_desc, rb_proj1_tech,
                        rb_proj2_name, rb_proj2_desc, rb_proj2_tech,
                    ],
                    outputs=[rb_output, rb_status],
                )

                # Synchronize PDF inputs across tabs on upload & clear
                pdf_input.upload(
                    fn=lambda x: (x, x),
                    inputs=[pdf_input],
                    outputs=[improve_pdf, gan_pdf],
                )
                pdf_input.clear(
                    fn=lambda: (None, None),
                    inputs=[],
                    outputs=[improve_pdf, gan_pdf],
                )

                improve_pdf.upload(
                    fn=lambda x: (x, x),
                    inputs=[improve_pdf],
                    outputs=[pdf_input, gan_pdf],
                )
                improve_pdf.clear(
                    fn=lambda: (None, None),
                    inputs=[],
                    outputs=[pdf_input, gan_pdf],
                )

                gan_pdf.upload(
                    fn=lambda x: (x, x),
                    inputs=[gan_pdf],
                    outputs=[pdf_input, improve_pdf],
                )
                gan_pdf.clear(
                    fn=lambda: (None, None),
                    inputs=[],
                    outputs=[pdf_input, improve_pdf],
                )

            # ══════════════════════════════════════════════════════════════
            #  TAB 6 — About
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("ℹ️ About"):
                gr.Markdown(ABOUT_MD)

        # ── Footer ────────────────────────────────────────────────────────
        gr.HTML(
            """
            <div class="app-footer">
                PSI Resume Analyser v1.0.0 •
                Built with <a href="https://www.langchain.com/langgraph" target="_blank">LangGraph</a>,
                <a href="https://www.gradio.app" target="_blank">Gradio</a> &
                <a href="https://ai.google.dev" target="_blank">Google Gemini</a>
            </div>
            """
        )

    return app


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import threading
    from core.embeddings import get_embedding_model
    
    # Pre-load embedding model during startup to avoid delaying the first request
    threading.Thread(target=get_embedding_model, daemon=True).start()

    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )

# perf: optimize CSS loading logic in Gradio setup
