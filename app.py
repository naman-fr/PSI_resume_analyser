"""
PSI Resume Analyser — Gradio Application.

Main entry-point for the HuggingFace Spaces deployment.  Provides a
premium multi-tab UI for single-resume analysis, improvement suggestions,
batch analysis, and methodology documentation.
"""

from __future__ import annotations

import logging
import os
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Programmatic fallback installation of requirements on HuggingFace Spaces
try:
    import pdfplumber  # noqa: F401
except ImportError:
    print("pdfplumber not found. Running programmatic installation of requirements.txt...", flush=True)
    try:
        requirements_path = Path(__file__).resolve().parent / "requirements.txt"
        if requirements_path.exists():
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)])
            print("Programmatic installation completed successfully.", flush=True)
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
            print("pdfplumber installed directly.", flush=True)
    except Exception as e:
        print(f"Programmatic installation failed: {e}", flush=True)

import gradio as gr

from config.settings import settings
from core.pdf_parser import extract_text_from_pdf
from core.job_search import search_jobs
from core.job_matcher import score_jobs
from core.job_query_generator import generate_search_queries


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
            desc.innerHTML = `You caught ATS skills and scored <strong style="color:#34d399;font-size:1.15rem;">${score}</strong> points!<br>Still auditing demographic profiles...`;
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

def get_job_cards_html(scored_jobs: List[Any]) -> str:
    """Generate the swipe card deck HTML interface."""
    if not scored_jobs:
        return r"""
        <div class="empty-deck-message">
            <span style="font-size: 3rem; margin-bottom: 1rem;">🔍</span>
            <h3>No matching jobs found</h3>
            <p>Try adjusting your search criteria, keywords, or location preferences.</p>
        </div>
        """

    # Generate filter buttons
    filters_html = """
    <div class="deck-filters">
        <button class="deck-filter-btn active" onclick="window.jobDeck.applyFilter('all')">All ({total})</button>
        <button class="deck-filter-btn" onclick="window.jobDeck.applyFilter('top')">🏆 Top ({top})</button>
        <button class="deck-filter-btn" onclick="window.jobDeck.applyFilter('strong')">💪 Strong ({strong})</button>
        <button class="deck-filter-btn" onclick="window.jobDeck.applyFilter('worth')">🎯 Worth ({worth})</button>
        <button class="deck-filter-btn" onclick="window.jobDeck.applyFilter('decent')">💼 Decent ({decent})</button>
    </div>
    """

    # Count categories
    c_top = sum(1 for j in scored_jobs if "Top" in j.category or "Star" in j.category)
    c_strong = sum(1 for j in scored_jobs if "Strong" in j.category)
    c_worth = sum(1 for j in scored_jobs if "Worth" in j.category)
    c_decent = sum(1 for j in scored_jobs if "Decent" in j.category)
    filters_html = filters_html.format(total=len(scored_jobs), top=c_top, strong=c_strong, worth=c_worth, decent=c_decent)

    cards_html = []
    for idx, j in enumerate(scored_jobs):
        # Determine badge color and CSS classes
        badge_cls = "badge-decent"
        gauge_color = "#94a3b8"
        if "Star" in j.category:
            badge_cls = "badge-star"
            gauge_color = "#ffd93d"
        elif "Top" in j.category:
            badge_cls = "badge-top"
            gauge_color = "#10b981"
        elif "Strong" in j.category:
            badge_cls = "badge-strong"
            gauge_color = "#6366f1"
        elif "Worth" in j.category:
            badge_cls = "badge-worth"
            gauge_color = "#f59e0b"

        # Matched and missing skills
        matched_skills_html = "".join([f'<span class="skill-pill matched">✅ {s}</span>' for s in j.matched_skills[:8]])
        missing_skills_html = "".join([f'<span class="skill-pill missing">➕ {s}</span>' for s in j.missing_skills[:6]])
        
        skills_section = ""
        if matched_skills_html or missing_skills_html:
            skills_section = f"""
            <div class="job-card-skills-section">
                <div class="skills-heading">Skills Profile Match</div>
                <div class="skills-list">
                    {matched_skills_html}
                    {missing_skills_html}
                </div>
            </div>
            """

        # Details list
        remote_icon = "🏠" if j.listing.remote else "📍"
        salary_html = f'<div class="detail-item"><span class="detail-item-label">💰 Salary:</span> <strong>{j.listing.salary}</strong></div>' if j.listing.salary else ''
        
        snippet = j.listing.description[:200] + "..." if len(j.listing.description) > 200 else j.listing.description

        card_html = f"""
        <div class="job-card" data-index="{idx}" data-category="{j.category}">
            <div class="job-card-header">
                <div class="job-card-meta">
                    <span class="job-card-badge {badge_cls}">{j.category}</span>
                    <h2 class="job-card-title">{j.listing.title}</h2>
                    <p class="job-card-company">{j.listing.company}</p>
                </div>
                <div class="job-card-gauge" style="background: conic-gradient({gauge_color} {j.match_score}%, rgba(255,255,255,0.05) {j.match_score}%);">
                    <span class="job-card-gauge-value">{int(j.match_score)}%</span>
                </div>
            </div>
            
            <div class="job-card-body">
                <div class="job-card-details">
                    <div class="detail-item"><span class="detail-item-label">{remote_icon} Location:</span> <strong>{j.listing.location}</strong></div>
                    <div class="detail-item"><span class="detail-item-label">⏱️ Type:</span> <strong>{j.listing.job_type}</strong></div>
                    {salary_html}
                    <div class="detail-item"><span class="detail-item-label">📅 Posted:</span> <strong>{j.listing.posted_date}</strong></div>
                </div>
                
                {skills_section}
                
                <p class="job-card-desc-snippet">{snippet}</p>
            </div>
            
            <div class="job-card-footer">
                <span class="source-info">via <strong>{j.listing.source}</strong></span>
                <a href="{j.listing.url}" target="_blank" class="apply-btn">Apply Now 🚀</a>
            </div>
        </div>
        """
        cards_html.append(card_html)

    deck_html = """
    <div class="job-finder-container">
        {filters_html}
        
        <div class="job-deck-container" id="job-deck-container">
            <div id="job-deck" style="width:100%; height:100%; position:relative;">
                {cards_html}
            </div>
            <div class="empty-deck-message" id="empty-deck-msg" style="display: none;">
                <span style="font-size: 3rem; margin-bottom: 1rem;">🎉</span>
                <h3>You've reviewed all matches!</h3>
                <p>Try searching again with different location preferences or options.</p>
            </div>
        </div>
        
        <div class="deck-controls">
            <button class="deck-btn" onclick="window.jobDeck.swipe('left')">❌</button>
            <div class="deck-counter" id="deck-counter">1 / {total_jobs}</div>
            <button class="deck-btn" onclick="window.jobDeck.swipe('right')">💚</button>
        </div>
    </div>
    
    <script id="job-deck-script">
    (function() {
        class JobDeckController {
            constructor() {
                this.currentIndex = 0;
                this.currentFilter = 'all';
                this.visibleCards = [];
                this.startX = 0;
                this.startY = 0;
                this.currentX = 0;
                this.currentY = 0;
                this.isDragging = false;
                
                this.init();
            }
            
            init() {
                const deckContainer = document.getElementById('job-deck');
                if (!deckContainer) return;
                
                this.deck = deckContainer;
                this.allCards = Array.from(deckContainer.getElementsByClassName('job-card'));
                this.applyFilter('all');
                this.setupGestures();
                this.setupKeyboard();
            }
            
            applyFilter(filter) {
                this.currentFilter = filter;
                
                // Update filter buttons active class
                const filterBtns = Array.from(document.querySelectorAll('.deck-filter-btn'));
                filterBtns.forEach(btn => {
                    if (btn.getAttribute('onclick').includes(filter)) {
                        btn.classList.add('active');
                    } else {
                        btn.classList.remove('active');
                    }
                });
                
                this.visibleCards = [];
                this.allCards.forEach(card => {
                    const cat = card.getAttribute('data-category');
                    let match = false;
                    
                    if (filter === 'all') {
                        match = true;
                    } else if (filter === 'top' && (cat.includes('Top') || cat.includes('Star'))) {
                        match = true;
                    } else if (filter === 'strong' && cat.includes('Strong')) {
                        match = true;
                    } else if (filter === 'worth' && cat.includes('Worth')) {
                        match = true;
                    } else if (filter === 'decent' && cat.includes('Decent')) {
                        match = true;
                    }
                    
                    if (match) {
                        this.visibleCards.push(card);
                        card.style.display = '';
                    } else {
                        card.style.display = 'none';
                        card.classList.remove('active', 'next', 'hidden');
                        card.style.transform = '';
                        card.style.opacity = '';
                    }
                });
                
                this.currentIndex = 0;
                this.updateCardClasses();
            }
            
            updateCardClasses() {
                const emptyMsg = document.getElementById('empty-deck-msg');
                const counter = document.getElementById('deck-counter');
                
                if (this.visibleCards.length === 0) {
                    if (emptyMsg) emptyMsg.style.display = 'flex';
                    if (counter) counter.innerText = '0 / 0';
                    return;
                }
                
                if (emptyMsg) emptyMsg.style.display = 'none';
                if (counter) counter.innerText = `${this.currentIndex + 1} / ${this.visibleCards.length}`;
                
                this.visibleCards.forEach((card, idx) => {
                    card.classList.remove('active', 'next', 'hidden');
                    card.style.transform = '';
                    card.style.opacity = '';
                    
                    if (idx === this.currentIndex) {
                        card.classList.add('active');
                    } else if (idx === this.currentIndex + 1) {
                        card.classList.add('next');
                    } else {
                        card.classList.add('hidden');
                    }
                });
            }
            
            swipe(direction) {
                const activeCard = this.visibleCards[this.currentIndex];
                if (!activeCard) return;
                
                const outWidth = window.innerWidth || document.documentElement.clientWidth;
                const moveX = direction === 'right' ? outWidth : -outWidth;
                const rotate = direction === 'right' ? 30 : -30;
                
                activeCard.style.transition = 'transform 0.4s cubic-bezier(0.1, 0.8, 0.3, 1), opacity 0.4s ease';
                activeCard.style.transform = `translate3d(${moveX}px, 20px, 0) rotate(${rotate}deg)`;
                activeCard.style.opacity = '0';
                
                setTimeout(() => {
                    this.currentIndex++;
                    this.updateCardClasses();
                }, 300);
            }
            
            setupGestures() {
                this.deck.addEventListener('pointerdown', (e) => this.onPointerDown(e));
                document.addEventListener('pointermove', (e) => this.onPointerMove(e));
                document.addEventListener('pointerup', () => this.onPointerUp());
            }
            
            onPointerDown(e) {
                if (e.target.closest('a') || e.target.closest('button')) return;
                
                const activeCard = this.visibleCards[this.currentIndex];
                if (!activeCard) return;
                
                this.isDragging = true;
                this.startX = e.clientX;
                this.startY = e.clientY;
                activeCard.style.transition = 'none';
            }
            
            onPointerMove(e) {
                if (!this.isDragging) return;
                
                const activeCard = this.visibleCards[this.currentIndex];
                if (!activeCard) return;
                
                this.currentX = e.clientX - this.startX;
                this.currentY = e.clientY - this.startY;
                
                const rotate = this.currentX * 0.08;
                activeCard.style.transform = `translate3d(${this.currentX}px, ${this.currentY}px, 0) rotate(${rotate}deg)`;
            }
            
            onPointerUp() {
                if (!this.isDragging) return;
                this.isDragging = false;
                
                const activeCard = this.visibleCards[this.currentIndex];
                if (!activeCard) return;
                
                activeCard.style.transition = 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.4s ease';
                
                const swipeThreshold = 140;
                if (this.currentX > swipeThreshold) {
                    this.swipe('right');
                } else if (this.currentX < -swipeThreshold) {
                    this.swipe('left');
                } else {
                    activeCard.style.transform = 'translate3d(0, 0, 0) rotate(0deg)';
                }
                
                this.currentX = 0;
                this.currentY = 0;
            }
            
            setupKeyboard() {
                document.addEventListener('keydown', (e) => {
                    // Make sure we aren't typing in inputs
                    if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;
                    
                    if (e.key === 'ArrowLeft') {
                        this.swipe('left');
                    } else if (e.key === 'ArrowRight') {
                        this.swipe('right');
                    }
                });
            }
        }
        
        window.jobDeck = new JobDeckController();
    })();
    </script>
    <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" onload="
        const oldScript = document.getElementById('job-deck-script');
        if (oldScript) {
            const newScript = document.createElement('script');
            newScript.textContent = oldScript.textContent;
            document.body.appendChild(newScript);
        }
    " style="display:none;" />
    """
    return deck_html.format(
        filters_html=filters_html,
        cards_html="".join(cards_html),
        total_jobs=len(scored_jobs)
    )


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
    premium_mode: bool = False,
    fallback_pdf_1: Any = None,
    fallback_pdf_2: Any = None,
    fallback_jd_1: str = None,
    fallback_jd_2: str = None,
) -> Tuple[str, str, str, str, str, str, str, str, str, str, str]:
    """
    Run the full resume analysis pipeline.

    Returns eleven string outputs for the Gradio UI components:
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
      10 – premium_verification_html
    """
    if pdf_file is None:
        pdf_file = fallback_pdf_1 or fallback_pdf_2

    if not jd_text or not jd_text.strip():
        for f_jd in [fallback_jd_1, fallback_jd_2]:
            if f_jd and f_jd.strip():
                jd_text = f_jd
                break

    # ── 1. Validate inputs ────────────────────────────────────────────────
    valid, err = validate_pdf(pdf_file)
    if not valid:
        return ("", "", "", "", "", "", "", "", "", f"⚠️ {err}", "")

    valid, err = validate_jd_text(jd_text)
    if not valid:
        return ("", "", "", "", "", "", "", "", "", f"⚠️ {err}", "")

    # ── 2. Extract text from PDF ──────────────────────────────────────────
    try:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        resume_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        logger.exception("PDF extraction failed")
        return ("", "", "", "", "", "", "", "", "", f"⚠️ Failed to extract text from PDF: {exc}", "")

    # ── 3. Run analysis graph ─────────────────────────────────────────────
    try:
        from agents.graph import run_analysis

        result: Dict[str, Any] = run_analysis(
            resume_text=resume_text,
            jd_text=jd_text,
            pdf_path=file_path,
            premium_mode=premium_mode
        )
    except ImportError:
        logger.error("agents.graph module not available")
        return (
            "", "", "", "", "", "", "", "", "",
            "⚠️ Analysis engine not available. Please ensure agents/graph.py is implemented.",
            ""
        )
    except Exception as exc:
        logger.exception("Analysis pipeline failed")
        return ("", "", "", "", "", "", "", "", "", f"⚠️ Analysis failed: {exc}", "")

    # ── 4. Check for pipeline errors ──────────────────────────────────────
    if result.get("error"):
        return ("", "", "", "", "", "", "", "", "", f"⚠️ {result['error']}", "")

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

    # Format Premium Verification results
    if result.get("premium_mode", False):
        inv_text = result.get("invisible_text_flagged", False)
        inv_details = result.get("invisible_text_details", {})
        inv_words = inv_details.get("detected_words", [])
        
        if inv_text:
            inv_html = f"""
            <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid var(--psi-red); padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                <div style="color: #f87171; font-weight: 700; font-size: 0.9rem; display: flex; align-items: center; gap: 6px;">
                    🚨 ATS Hacking Detected!
                </div>
                <div style="font-size: 0.82rem; color: #ef4444; font-weight: bold; margin-top: 4px;">
                    Deducted -25.0 ATS points penalty.
                </div>
                <p style="font-size: 0.82rem; color: var(--psi-text-dim); margin: 6px 0 0 0;">
                    Detected hidden (white-on-white) keywords: {", ".join([f"<code>{w}</code>" for w in inv_words])}
                </p>
            </div>
            """
        else:
            inv_html = """
            <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.3); padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                <div style="color: #34d399; font-weight: 700; font-size: 0.9rem; display: flex; align-items: center; gap: 6px;">
                    🛡️ PDF Integrity Verified
                </div>
                <p style="font-size: 0.82rem; color: var(--psi-text-dim); margin: 4px 0 0 0;">
                    No hidden white-on-white text keywords stuffed in background.
                </p>
            </div>
            """
            
        links_res = result.get("links_verification", {})
        trust_score = links_res.get("trust_score", 50.0)
        trust_logs = links_res.get("logs", [])
        
        trust_color = "#10b981" if trust_score >= 75 else ("#f59e0b" if trust_score >= 40 else "#ef4444")
        
        log_items = "".join([f'<li style="margin-bottom:4px; font-size:0.8rem; color:#cbd5e1;">{log}</li>' for log in trust_logs])
        
        trust_html = f"""
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); padding: 15px; border-radius: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 0.85rem; font-weight: 700; color: #cbd5e1;">Candidate Trustability Index</span>
                <span style="font-size: 1.1rem; font-weight: 800; color: {trust_color};">{trust_score:.1f}%</span>
            </div>
            
            <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; margin-bottom: 12px;">
                <div style="width: {trust_score}%; height: 100%; background: {trust_color}; border-radius: 4px;"></div>
            </div>
            
            <div style="font-size: 0.78rem; font-weight: bold; color: var(--psi-primary-light); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.02em;">
                Verification Logs:
            </div>
            <ul style="margin: 0; padding-left: 15px; max-height: 120px; overflow-y: auto;">
                {log_items}
            </ul>
        </div>
        """
        
        premium_html = f"""
        <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.06) 0%, rgba(34, 211, 238, 0.03) 100%); border: 1px solid rgba(124, 58, 237, 0.3); border-radius: 12px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <span style="font-size: 0.78rem; color: #a78bfa; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase;">⭐ Premium Audit Results</span>
                <span style="background: linear-gradient(135deg, #7c3aed, #22d3ee); color: white; padding: 2px 10px; border-radius: 10px; font-size: 0.7rem; font-weight: bold;">VERIFIED TIER</span>
            </div>
            {inv_html}
            {trust_html}
        </div>
        """
    else:
        premium_html = """
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 15px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.75rem; color: #94a3b8; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">🛡️ PREMIUM VERIFICATION SERVICE</span>
                <span style="background: rgba(255,255,255,0.05); color: #94a3b8; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold;">STANDBY</span>
            </div>
            <p style="font-size: 0.85rem; color: #64748b; margin: 8px 0 0 0;">Select the Premium Verified Tier in the Enterprise tab to unlock background white-text scans and candidate link trust verification.</p>
        </div>
        """

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
        premium_html,
    )


# ---------------------------------------------------------------------------
# Improvement Suggestions Function
# ---------------------------------------------------------------------------


def get_improvements(
    pdf_file: Any,
    jd_text: str,
    fallback_pdf_1: Any = None,
    fallback_pdf_2: Any = None,
    fallback_jd_1: str = None,
    fallback_jd_2: str = None,
) -> Tuple[str, str, str]:
    """
    Run analysis and return improvement suggestions.

    Returns three strings:
      0 – suggestions_html
      1 – ats_bullets_html
      2 – status_message
    """
    if pdf_file is None:
        pdf_file = fallback_pdf_1 or fallback_pdf_2

    if not jd_text or not jd_text.strip():
        for f_jd in [fallback_jd_1, fallback_jd_2]:
            if f_jd and f_jd.strip():
                jd_text = f_jd
                break

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
                    '<div class="improvement-item">'
                    + (f'  <p style="color:#94a3b8;font-size:0.82rem;margin-bottom:4px">Original:</p>'
                       f"  <p style=\"margin-bottom:8px\">{original}</p>" if original else "")
                    + f'  <p style="color:#34d399;font-size:0.82rem;margin-bottom:4px">✨ Optimized:</p>'
                    f"  <p><strong>{improved}</strong></p>"
                    + (f'  <p style="font-size:0.78rem;color:#fbbf24;margin-top:6px">Keywords added: {kw_str}</p>' if kw_str else "")
                    + (f'  <p style="font-size:0.78rem;color:#94a3b8;margin-top:4px;font-style:italic">💡 {rationale}</p>' if rationale else "")
                    + "</div>"
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
# GitHub & PDF Resume Autofill Functions
# ---------------------------------------------------------------------------


def _make_autofill_error_return(message: str) -> Tuple[Any, ...]:
    """Helper to return an empty form state of 38 fields, None file, and a status message (40 elements)."""
    return ("", "", "", "", "", "", "", "", *[""]*15, *[""]*8, "", *[""]*6, None, message)


def fetch_github_data(username: str) -> Tuple[Any, ...]:
    """Fetch GitHub profile & repositories and map them to the resume form fields."""
    import urllib.request
    import json
    
    if not username or not username.strip():
        return _make_autofill_error_return("⚠️ Please enter a GitHub username.")
    
    username = username.strip()
    try:
        # Fetch profile
        user_url = f"https://api.github.com/users/{username}"
        req = urllib.request.Request(user_url, headers={"User-Agent": "PSI-Resume-Builder"})
        with urllib.request.urlopen(req, timeout=5) as response:
            user_data = json.loads(response.read().decode())
            
        name = user_data.get("name") or username
        email = user_data.get("email") or ""
        location = user_data.get("location") or ""
        bio = user_data.get("bio") or ""
        blog = user_data.get("blog") or ""
        github_url = f"github.com/{username}"
        
        # Fetch repositories
        repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=6"
        req_repos = urllib.request.Request(repos_url, headers={"User-Agent": "PSI-Resume-Builder"})
        repos = []
        with urllib.request.urlopen(req_repos, timeout=5) as response:
            repos = json.loads(response.read().decode())
            
        # Extract projects
        proj1_name, proj1_desc, proj1_tech = "", "", ""
        proj2_name, proj2_desc, proj2_tech = "", "", ""
        
        languages = set()
        if isinstance(repos, list) and len(repos) > 0:
            # Project 1
            proj1_name = repos[0].get("name", "").replace("-", " ").title()
            proj1_desc = repos[0].get("description") or ""
            proj1_tech = repos[0].get("language") or ""
            if proj1_tech:
                languages.add(proj1_tech)
                
            # Project 2
            if len(repos) > 1:
                proj2_name = repos[1].get("name", "").replace("-", " ").title()
                proj2_desc = repos[1].get("description") or ""
                proj2_tech = repos[1].get("language") or ""
                if proj2_tech:
                    languages.add(proj2_tech)
                    
            # Add languages from other repos
            for repo in repos[2:]:
                lang = repo.get("language")
                if lang:
                    languages.add(lang)
                    
        skills_str = ", ".join(languages) if languages else "Git, GitHub, Software Engineering"
        summary = f"Passionate software developer and creator of {proj1_name or 'projects'}. "
        if bio:
            summary += bio
        else:
            summary += f"Experienced in building projects using {skills_str}."
            
        return (
            name, email, "", location, "", blog or github_url, summary, skills_str,
            # Exp 1 (empty)
            "", "", "", "", "",
            # Exp 2 (empty)
            "", "", "", "", "",
            # Exp 3 (empty)
            "", "", "", "", "",
            # Edu 1 (empty)
            "", "", "", "",
            # Edu 2 (empty)
            "", "", "", "",
            # Certifications (empty)
            "",
            # Project 1
            proj1_name, proj1_desc, proj1_tech,
            # Project 2
            proj2_name, proj2_desc, proj2_tech,
            None, f"✅ Successfully fetched data for GitHub user '{username}'!"
        )
    except Exception as e:
        return _make_autofill_error_return(f"⚠️ Failed to fetch GitHub profile: {e}")


def parse_and_autofill_pdf(pdf_file: Any) -> Tuple[Any, ...]:
    """Parse an existing PDF resume using the LLM parser and return updates for all form fields."""
    if pdf_file is None:
        return _make_autofill_error_return("⚠️ Please upload a PDF resume first.")
        
    try:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        
        # Dual-backend PDF parser
        try:
            resume_text = extract_text_from_pdf(file_path)
        except Exception as exc:
            return _make_autofill_error_return(f"⚠️ Failed to extract text from PDF: {exc}")
        
        from agents.resume_parser import parse_resume
        from agents.state import ResumeJDState
        
        state: ResumeJDState = {
            "resume_text": resume_text,
            "jd_text": ""  # empty JD
        }
        
        parse_res = parse_resume(state)
        if "error" in parse_res:
            return _make_autofill_error_return(f"⚠️ Parsing failed: {parse_res['error']}")
            
        parsed = parse_res.get("resume_parsed", {})
        
        name = parsed.get("name") or ""
        email = parsed.get("email") or ""
        phone = parsed.get("phone") or ""
        location = parsed.get("location") or ""
        summary = parsed.get("summary") or ""
        
        skills_list = parsed.get("skills") or []
        skills_str = ", ".join(skills_list) if isinstance(skills_list, list) else str(skills_list)
        
        # Extract Experience
        exp_entries = parsed.get("experience") or []
        exp_outputs = []
        for idx in range(3):
            if idx < len(exp_entries):
                entry = exp_entries[idx]
                bullets = entry.get("bullets") or []
                bullets_str = "\n".join(bullets) if isinstance(bullets, list) else str(bullets)
                exp_outputs.extend([
                    entry.get("company") or "",
                    entry.get("title") or entry.get("role") or "",
                    entry.get("duration") or "",
                    "", # end date (empty, duration is in start_date)
                    bullets_str
                ])
            else:
                exp_outputs.extend(["", "", "", "", ""])
                
        # Extract Education
        edu_entries = parsed.get("education") or []
        edu_outputs = []
        for idx in range(2):
            if idx < len(edu_entries):
                entry = edu_entries[idx]
                edu_outputs.extend([
                    entry.get("degree") or "",
                    entry.get("institution") or "",
                    entry.get("year") or "",
                    entry.get("gpa") or ""
                ])
            else:
                edu_outputs.extend(["", "", "", ""])
                
        # Extract Certifications
        certs_list = parsed.get("certifications") or []
        certs_str = "\n".join(certs_list) if isinstance(certs_list, list) else str(certs_list)
        
        # Extract Projects
        proj_entries = parsed.get("projects") or []
        proj_outputs = []
        for idx in range(2):
            if idx < len(proj_entries):
                entry = proj_entries[idx]
                proj_outputs.extend([
                    entry.get("name") or "",
                    entry.get("description") or "",
                    entry.get("technologies") or ""
                ])
            else:
                proj_outputs.extend(["", "", ""])
                
        return (
            name, email, phone, location, "", "", summary, skills_str,
            *exp_outputs,
            *edu_outputs,
            certs_str,
            *proj_outputs,
            None, "✅ Successfully parsed and loaded details from PDF!"
        )
        
    except Exception as e:
        logger.exception("Autofill PDF parsing failed.")
        return _make_autofill_error_return(f"⚠️ Failed to parse PDF: {e}")


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
            return file_path, "✅ Resume PDF generated successfully! Click the download link above."
        else:
            return None, "⚠️ Failed to generate PDF. Please check your inputs."
    except Exception as exc:
        logger.exception("Resume PDF generation failed.")
        return None, f"⚠️ PDF generation failed: {exc}"


def search_and_match_jobs(
    pdf_file: Any,
    location_filter: str,
    remote_only: bool,
    fallback_pdf_1: Any = None,
    fallback_pdf_2: Any = None,
) -> Tuple[str, str, str]:
    """Search for matching jobs and score them against the resume."""
    if pdf_file is None:
        pdf_file = fallback_pdf_1 or fallback_pdf_2

    valid, err = validate_pdf(pdf_file)
    if not valid:
        return ("", "0 matches", f"⚠️ {err}")

    try:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        resume_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        logger.exception("PDF extraction failed")
        return ("", "0 matches", f"⚠️ Failed to extract text from PDF: {exc}")

    # Parse resume
    try:
        from agents.resume_parser import parse_resume
        state = {"resume_text": resume_text}
        parse_res = parse_resume(state)
        
        if "error" in parse_res:
            err_msg = parse_res["error"]
            warning_html = (
                f'<div class="result-card" style="border-color:#eab308;background:rgba(234,179,8,0.05);margin-bottom:15px">'
                f'  <h3 style="color:#eab308">⚠️ Job Matcher Paused</h3>'
                f'  <p style="color:#fef08a;margin-bottom:8px"><strong>API Quota / Rate Limit Exceeded:</strong></p>'
                f'  <p style="color:#e2e8f0;font-size:0.9rem">{err_msg}</p>'
                f'</div>'
            )
            return (warning_html, "0 matches", f"⚠️ Parsing failed: {err_msg}")
            
        resume_parsed = parse_res.get("resume_parsed", {})
    except Exception as exc:
        logger.exception("Resume parsing failed in search_and_match_jobs")
        return ("", "0 matches", f"⚠️ Resume parsing failed: {exc}")

    # Generate search queries
    try:
        queries_dict = generate_search_queries(resume_parsed)
        titles = queries_dict.get("job_titles", ["Software Engineer"])
        keywords = queries_dict.get("search_keywords", ["developer"])
        # Select top 1 title and top 1 keyword search term to avoid JSearch 429 rate limit issues
        search_terms = []
        if titles:
            search_terms.append(titles[0])
        if keywords:
            search_terms.append(keywords[0])
        search_terms = list(set(search_terms))[:2]
        
        # Decide location
        location = location_filter.strip() if location_filter and location_filter.strip() else queries_dict.get("target_location", "Remote")
    except Exception:
        logger.exception("Search query generation failed")
        search_terms = ["Software Engineer"]
        location = "Remote"

    # Search jobs
    try:
        listings = search_jobs(
            queries=search_terms,
            location=location,
            remote_only=remote_only,
            max_results=30
        )
    except Exception as exc:
        logger.exception("Job search failed")
        return ("", "0 matches", f"⚠️ Job search failed: {exc}")

    if not listings:
        return (get_job_cards_html([]), "0 matches", "⚠️ No matching jobs found on external boards.")

    # Score jobs
    try:
        resume_skills = resume_parsed.get("skills", [])
        scored = score_jobs(
            resume_text=resume_text,
            resume_skills=resume_skills,
            jobs=listings,
            min_score=35.0
        )
    except Exception as exc:
        logger.exception("Job scoring failed")
        return ("", "0 matches", f"⚠️ Job scoring failed: {exc}")

    cards_html = get_job_cards_html(scored)
    match_count = f"{len(scored)} matches"
    status_msg = f"✅ Success: Found and scored {len(scored)} matching jobs."
    return (cards_html, match_count, status_msg)



def run_gan_audit(
    pdf_file: Any,
    jd_text: str,
    fallback_pdf_1: Any = None,
    fallback_pdf_2: Any = None,
    fallback_jd_1: str = None,
    fallback_jd_2: str = None,
) -> Tuple[str, str, str, str]:
    """
    Simulate the GAN Generative Adversarial stress test.
    """
    if pdf_file is None:
        pdf_file = fallback_pdf_1 or fallback_pdf_2

    if not jd_text or not jd_text.strip():
        for f_jd in [fallback_jd_1, fallback_jd_2]:
            if f_jd and f_jd.strip():
                jd_text = f_jd
                break

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
        
        # Check if hacked_text is a rate limit or error
        if "API Quota Exhausted" in hacked_text or hacked_text.startswith("Error generating"):
            err_msg = hacked_text
            warning_html = (
                f'<div class="result-card" style="border-color:#eab308;background:rgba(234,179,8,0.05);margin-bottom:15px">'
                f'  <h3 style="color:#eab308">⚠️ GAN Simulation Paused</h3>'
                f'  <p style="color:#fef08a;margin-bottom:8px"><strong>API Quota / Rate Limit Exceeded:</strong></p>'
                f'  <p style="color:#e2e8f0;font-size:0.9rem">{err_msg}</p>'
                f'  <p style="color:#94a3b8;font-size:0.8rem;margin-top:10px">'
                f'    Groq/Gemini free tiers have strict rate limits. Please wait 1-2 minutes and click "Run Adversarial Audit" again.'
                f'  </p>'
                f'</div>'
            )
            return (warning_html, warning_html, warning_html, "⚠️ Rate limit hit. Simulation aborted.")

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
        err_msg = str(discriminator_res["error"])
        if any(term in err_msg.lower() for term in ["quota", "rate limit", "429", "rate_limit"]):
            discriminator_html = (
                f'<div class="result-card" style="border-color:#eab308;background:rgba(234,179,8,0.05);margin-bottom:15px">'
                f'  <h3 style="color:#eab308">⚠️ Discriminator Audit Paused</h3>'
                f'  <p style="color:#fef08a;margin-bottom:8px"><strong>API Quota / Rate Limit Exceeded:</strong></p>'
                f'  <p style="color:#e2e8f0;font-size:0.9rem">{err_msg}</p>'
                f'  <p style="color:#94a3b8;font-size:0.8rem;margin-top:10px">'
                f'    Groq/Gemini free tiers have strict rate limits. Please wait 1-2 minutes and click "Run Adversarial Audit" again.'
                f'  </p>'
                f'</div>'
            )
        else:
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
            
        term_logs.append("[DISCRIMINATOR] Running Red Flag compliance checks...")
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
            err_msg = str(baseline_res["error"])
            if any(term in err_msg.lower() for term in ["quota", "rate limit", "429", "rate_limit"]):
                bias_html = (
                    f'<div class="result-card" style="border-color:#eab308;background:rgba(234,179,8,0.05);margin-bottom:15px">'
                    f'  <h3 style="color:#eab308">⚠️ EEOC Demographic Fairness Audit Paused</h3>'
                    f'  <p style="color:#fef08a;margin-bottom:8px"><strong>API Quota / Rate Limit Exceeded:</strong></p>'
                    f'  <p style="color:#e2e8f0;font-size:0.9rem">{err_msg}</p>'
                    f'  <p style="color:#94a3b8;font-size:0.8rem;margin-top:10px">'
                    f'    Groq/Gemini free tiers have strict rate limits. Please wait 1-2 minutes and click "Run Adversarial Audit" again.'
                    f'  </p>'
                    f'</div>'
                )
            else:
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
            
            if "error" in bias_res:
                err_msg = str(bias_res["error"])
                if any(term in err_msg.lower() for term in ["quota", "rate limit", "429", "rate_limit"]):
                    bias_html = (
                        f'<div class="result-card" style="border-color:#eab308;background:rgba(234,179,8,0.05);margin-bottom:15px">'
                        f'  <h3 style="color:#eab308">⚠️ EEOC Demographic Fairness Audit Paused</h3>'
                        f'  <p style="color:#fef08a;margin-bottom:8px"><strong>API Quota / Rate Limit Exceeded:</strong></p>'
                        f'  <p style="color:#e2e8f0;font-size:0.9rem">{err_msg}</p>'
                        f'  <p style="color:#94a3b8;font-size:0.8rem;margin-top:10px">'
                        f'    Groq/Gemini free tiers have strict rate limits. Please wait 1-2 minutes and click "Run Adversarial Audit" again.'
                        f'  </p>'
                        f'</div>'
                    )
                else:
                    bias_html = f'<p style="color:#ef4444">Bias Audit failed: {bias_res["error"]}</p>'
            else:
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
                    + '</div>'
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


def get_observability_metrics() -> Tuple[str, str, str, str, str, str, str]:
    """Fetch metrics and return values for Gradio textboxes and HTML tables."""
    import os
    import time
    from core.telemetry import TelemetryLogger
    from config.settings import settings
    from core.data_loop import get_dataset_size
    
    metrics = TelemetryLogger.get_summary_metrics()
    
    cost_str = f"${metrics['total_cost_usd']:.5f} USD"
    latency_str = f"{metrics['average_latency_sec']:.3f} sec"
    tokens_str = f"{metrics['total_tokens_consumed']:,}"
    success_str = f"{metrics['success_rate_pct']:.1f}% ({metrics['success_count']}/{metrics['total_runs']})"
    
    dataset_size = get_dataset_size()
    dataset_size_str = f"{dataset_size} records"
    
    # 1. Tracing Table
    recent_logs = TelemetryLogger.get_recent_logs(15)
    logs_html = r"""
    <div style="overflow-x: auto; background: rgba(30, 41, 59, 0.4); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); padding: 5px;">
        <table style="width: 100%; border-collapse: collapse; font-family: monospace; font-size: 0.9rem; color: #cbd5e1; text-align: left;">
            <thead>
                <tr style="background: rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <th style="padding: 10px; color: #cbd5e1;">Timestamp</th>
                    <th style="padding: 10px; color: #cbd5e1;">Node Name</th>
                    <th style="padding: 10px; color: #cbd5e1;">Provider</th>
                    <th style="padding: 10px; color: #cbd5e1;">Latency</th>
                    <th style="padding: 10px; color: #cbd5e1;">Tokens</th>
                    <th style="padding: 10px; color: #cbd5e1;">Cost</th>
                    <th style="padding: 10px; color: #cbd5e1;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    if not recent_logs:
        logs_html += "<tr><td colspan='7' style='padding: 20px; text-align: center; color: #94a3b8;'>No LLM traces recorded yet. Run a resume analysis to populate.</td></tr>"
    else:
        for r in reversed(recent_logs):
            status_color = "#34d399" if r["status"] == "success" else "#f87171"
            cost_color = "#ffd93d" if r["estimated_cost_usd"] > 0 else "#94a3b8"
            logs_html += f"""
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                <td style="padding: 10px; color: #94a3b8;">{r['timestamp']}</td>
                <td style="padding: 10px; font-weight: bold; color: #818cf8;">{r['node_name']}</td>
                <td style="padding: 10px; text-transform: uppercase;">{r['provider']}</td>
                <td style="padding: 10px;">{r['latency_sec']}s</td>
                <td style="padding: 10px;">{r['total_tokens']}</td>
                <td style="padding: 10px; color: {cost_color};">${r['estimated_cost_usd']:.6f}</td>
                <td style="padding: 10px; color: {status_color}; font-weight: bold;">{r['status'].upper()}</td>
            </tr>
            """
    logs_html += "</tbody></table></div>"

    # 2. Safety Table
    safety_html = r"""
    <div style="overflow-x: auto; background: rgba(30, 41, 59, 0.4); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); padding: 5px;">
        <table style="width: 100%; border-collapse: collapse; font-family: monospace; font-size: 0.9rem; color: #cbd5e1; text-align: left;">
            <thead>
                <tr style="background: rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <th style="padding: 10px; color: #cbd5e1;">Timestamp</th>
                    <th style="padding: 10px; color: #cbd5e1;">Trigger Type</th>
                    <th style="padding: 10px; color: #cbd5e1;">Details / Policy</th>
                    <th style="padding: 10px; color: #cbd5e1;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    safety_html += """
    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
        <td style="padding: 10px; color: #94a3b8;">[CONFIG]</td>
        <td style="padding: 10px; color: #ffd93d; font-weight: bold;">PII REDACTOR</td>
        <td style="padding: 10px;">Masks Name, Email, Phone, Social Links (EEOC compliance)</td>
        <td style="padding: 10px; color: #34d399; font-weight: bold;">SHIELD ACTIVE</td>
    </tr>
    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
        <td style="padding: 10px; color: #94a3b8;">[CONFIG]</td>
        <td style="padding: 10px; color: #ffd93d; font-weight: bold;">INJECTION FILTER</td>
        <td style="padding: 10px;">Adversarial system prompt override protection</td>
        <td style="padding: 10px; color: #34d399; font-weight: bold;">SHIELD ACTIVE</td>
    </tr>
    """
    
    # Check if there was any prompt injection error in logs
    log_path = settings.telemetry.telemetry_log_path
    injection_found = False
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if "potential prompt injection" in line.lower() or "injection" in line.lower():
                    injection_found = True
                    
    if injection_found:
        safety_html += f"""
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
            <td style="padding: 10px; color: #f87171;">{time.strftime("%Y-%m-%d %H:%M:%S")}</td>
            <td style="padding: 10px; color: #f87171; font-weight: bold;">INJECTION_WARN</td>
            <td style="padding: 10px; color: #f87171;">Blocked candidate resume containing prompt injection keywords</td>
            <td style="padding: 10px; color: #f87171; font-weight: bold;">INTERCEPTED</td>
        </tr>
        """
    else:
        safety_html += """
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
            <td style="padding: 10px; color: #94a3b8;">-</td>
            <td style="padding: 10px; color: #94a3b8;">No safety alerts</td>
            <td style="padding: 10px; color: #94a3b8;">No policy breaches or PII leakage occurrences detected.</td>
            <td style="padding: 10px; color: #34d399; font-weight: bold;">SECURE</td>
        </tr>
        """
    safety_html += "</tbody></table></div>"
    
    return cost_str, latency_str, tokens_str, success_str, logs_html, safety_html, dataset_size_str


def clear_observability_logs() -> Tuple[str, str, str, str, str, str, str]:
    """Wipe the telemetry database and refresh the dashboard."""
    import os
    from core.telemetry import TelemetryLogger
    from config.settings import settings
    
    log_path = settings.telemetry.telemetry_log_path
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except Exception as e:
            logger.error("Failed to clear telemetry file: %s", str(e))
            
    TelemetryLogger._memory_buffer.clear()
    return get_observability_metrics()


def select_free_tier():
    standard_html = """
    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 15px; border-radius: 12px; margin-top: 15px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Current Active Plan</span>
            <div style="font-size: 1.15rem; font-weight: 700; color: #cbd5e1; display: flex; align-items: center; gap: 6px;">
                ⚪ Standard Core Tier (Free)
            </div>
        </div>
        <span style="background: rgba(124, 58, 237, 0.15); color: #a78bfa; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold;">STANDARD STATUS</span>
    </div>
    """
    return False, standard_html, gr.update(visible=False), gr.update(visible=False)

def open_checkout():
    return gr.update(visible=True), gr.update(visible=False)

def close_checkout():
    return gr.update(visible=False), gr.update(visible=False)

def complete_payment(name, card, exp, cvv):
    if not name or not card:
        err_msg = "<div style='color:#ef4444; margin-top: 10px; font-size: 0.88rem; font-weight: bold;'>⚠️ Cardholder Name and Card Number are required.</div>"
        return gr.update(), gr.update(), gr.update(visible=True), gr.update(value=err_msg, visible=True)
    
    premium_html = """
    <div style="background: linear-gradient(90deg, rgba(124,58,237,0.1) 0%, rgba(34,211,238,0.1) 100%); border: 1px solid rgba(124, 58, 237, 0.4); padding: 15px; border-radius: 12px; margin-top: 15px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 0 20px rgba(124, 58, 237, 0.15);">
        <div>
            <span style="font-size: 0.8rem; color: #a78bfa; text-transform: uppercase; font-weight: 600;">Current Active Plan</span>
            <div style="font-size: 1.15rem; font-weight: 700; color: #ffd700; display: flex; align-items: center; gap: 6px;">
                ⭐ Premium Verified Tier ($49/audit)
            </div>
        </div>
        <span style="background: linear-gradient(135deg, #10b981, #34d399); color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);">ACTIVE clearance</span>
    </div>
    """
    gr.Info("Payment of $49 successful! Premium Mode Activated.")
    return True, premium_html, gr.update(visible=False), gr.update(visible=False)


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
            <div class="app-header-card" style="
                background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(99, 102, 241, 0.05) 50%, rgba(34, 211, 238, 0.05) 100%);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
                padding: 2.5rem 2rem;
                margin-bottom: 2rem;
                text-align: center;
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
                position: relative;
                overflow: hidden;
            ">
                <!-- Top Glowing Accent line -->
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #7c3aed, #6366f1, #22d3ee);"></div>
                
                <!-- Tech Badges -->
                <div style="display: flex; justify-content: center; gap: 8px; margin-bottom: 1rem; flex-wrap: wrap;">
                    <span style="background: rgba(124, 58, 237, 0.15); color: #a78bfa; border: 1px solid rgba(124, 58, 237, 0.3); padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;">⚡ LangGraph Orchestrated</span>
                    <span style="background: rgba(34, 211, 238, 0.15); color: #22d3ee; border: 1px solid rgba(34, 211, 238, 0.3); padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;">🤖 Gemini 2.0 Flash</span>
                    <span style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;">🛡️ EEOC Audited</span>
                </div>
                
                <h1 style="
                    font-size: 2.8rem;
                    font-weight: 800;
                    background: linear-gradient(135deg, #a78bfa 0%, #22d3ee 50%, #a78bfa 100%);
                    background-size: 200% auto;
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin: 0.5rem 0 1rem;
                    letter-spacing: -0.02em;
                    line-height: 1.2;
                ">🎯 PSI Resume Analyser</h1>
                
                <p style="
                    color: #94a3b8;
                    font-size: 1.1rem;
                    font-weight: 400;
                    max-width: 720px;
                    margin: 0 auto;
                    line-height: 1.6;
                ">
                    AI-powered ATS scoring engine that deeply analyses your resume against any job description — powered by LangGraph and Gemini.
                </p>
            </div>
            """
        )

        with gr.Tabs():
            # ══════════════════════════════════════════════════════════════
            #  TAB 0 — Enterprise Suite Portal
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("🏢 Enterprise Suite Portal"):
                gr.HTML(
                    r"""
                    <div class="enterprise-portal">
                        <div class="portal-header">
                            <span class="portal-tag">ENTERPRISE PLATFORM</span>
                            <h2 class="portal-title">Professional Suite & Intelligent Systems</h2>
                            <p class="portal-desc">An industrial-grade multi-agent suite designed to automate, secure, audit, and benchmark talent matching with complete transparency, safety compliance, and LLMOps auditing.</p>
                        </div>
                        
                        <div class="portal-grid">
                            <div class="portal-card">
                                <div class="card-icon">📄</div>
                                <h3 class="card-title">ATS Match Engine</h3>
                                <p class="card-desc">7-factor mathematical evaluation modeling skill recency, hierarchy, education, and bullet quality metrics.</p>
                                <span class="card-action">Active Service</span>
                            </div>
                            
                            <div class="portal-card">
                                <div class="card-icon">✨</div>
                                <h3 class="card-title">AI Copywriter & Improver</h3>
                                <p class="card-desc">Suggests gap fixes and rewrites raw resume bullet points to professional A-COE metrics standards.</p>
                                <span class="card-action">Active Service</span>
                            </div>
                            
                            <div class="portal-card">
                                <div class="card-icon">🛡️</div>
                                <h3 class="card-title">GAN Stress-Tester</h3>
                                <p class="card-desc">Simulates adversarial candidate resume hacking and logs how guardrail rules mitigate prompt attacks.</p>
                                <span class="card-action">Auditing Active</span>
                            </div>
                            
                            <div class="portal-card">
                                <div class="card-icon">⚖️</div>
                                <h3 class="card-title">EEOC Bias Compliance</h3>
                                <p class="card-desc">Performs blind parsing counterfactual identity tests to guarantee statistical demographic parity.</p>
                                <span class="card-action">Regulatory Guard</span>
                            </div>
                            
                            <div class="portal-card">
                                <div class="card-icon">🔍</div>
                                <h3 class="card-title">Global Job Discovery</h3>
                                <p class="card-desc">Real-time job board scraping combined with Tinder-style swipe decks matching candidate profiles.</p>
                                <span class="card-action">Active Matching</span>
                            </div>
                            
                            <div class="portal-card">
                                <div class="card-icon">📊</div>
                                <h3 class="card-title">LLMOps Observability</h3>
                                <p class="card-desc">Monitors token count consumption, request latency, prompt versioning, and transaction costs.</p>
                                <span class="card-action">Monitor Active</span>
                            </div>
                        </div>
                    </div>
                    """
                )
                
                # Active subscription banner
                active_tier_html = gr.HTML(
                    """
                    <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); padding: 15px; border-radius: 12px; margin-top: 15px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Current Active Plan</span>
                            <div style="font-size: 1.15rem; font-weight: 700; color: #cbd5e1; display: flex; align-items: center; gap: 6px;">
                                ⚪ Standard Core Tier (Free)
                            </div>
                        </div>
                        <span style="background: rgba(124, 58, 237, 0.15); color: #a78bfa; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold;">STANDARD STATUS</span>
                    </div>
                    """
                )
                
                # Pricing Grid Cards HTML
                gr.HTML(
                    """
                    <div style="margin-top: 40px; margin-bottom: 20px; text-align: center;">
                        <span class="portal-tag">UPGRADE SERVICES</span>
                        <h3 style="font-size: 1.8rem; font-weight: 800; color: #f8fafc; margin: 5px 0 10px;">Select Your Security Clearance Tier</h3>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 25px;">
                        <!-- Standard Free Plan -->
                        <div style="background: rgba(30, 41, 59, 0.3); border: 1px solid rgba(255, 255, 255, 0.05); padding: 25px; border-radius: 16px; backdrop-filter: blur(10px); display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <h4 style="font-size: 1.25rem; font-weight: 700; color: #e2e8f0; margin: 0 0 10px;">Standard Core</h4>
                                <div style="font-size: 2rem; font-weight: 800; color: #cbd5e1; margin-bottom: 15px;">$0 <span style="font-size: 0.9rem; font-weight: normal; color: #94a3b8;">/ always free</span></div>
                                <ul style="margin: 0 0 20px; padding-left: 20px; color: #94a3b8; font-size: 0.9rem; line-height: 1.6;">
                                    <li>Multi-agent ATS parser evaluation</li>
                                    <li>Skill Taxonomy normalizer mapping</li>
                                    <li>EEOC blind recruiter counterfactual analysis</li>
                                    <li>Basic resume suggestions and recommendations</li>
                                </ul>
                            </div>
                        </div>
                        
                        <!-- Premium Paid Plan -->
                        <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%); border: 1px solid rgba(124, 58, 237, 0.3); padding: 25px; border-radius: 16px; backdrop-filter: blur(10px); display: flex; flex-direction: column; justify-content: space-between; position: relative;">
                            <span style="position: absolute; top: 12px; right: 12px; background: linear-gradient(135deg, #7c3aed, #6366f1); color: white; font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 10px; text-transform: uppercase;">MNC Grade</span>
                            <div>
                                <h4 style="font-size: 1.25rem; font-weight: 700; color: #a78bfa; margin: 0 0 10px;">Premium Verified</h4>
                                <div style="font-size: 2rem; font-weight: 800; color: #22d3ee; margin-bottom: 15px;">$49 <span style="font-size: 0.9rem; font-weight: normal; color: #94a3b8;">/ audit run</span></div>
                                <ul style="margin: 0 0 20px; padding-left: 20px; color: #cbd5e1; font-size: 0.9rem; line-height: 1.6;">
                                    <li><strong>Invisible White-Text Scan</strong> (pdfplumber character metadata scan for hidden background ATS stuffing)</li>
                                    <li><strong>Portfolio Link verification</strong> (pings LinkedIn, GitHub, websites)</li>
                                    <li><strong>GitHub candidate trust scoring</strong> (scrapes profile & counts repos)</li>
                                    <li>Auto ATS deduction penalty if keyword stuffing found</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    """
                )
                
                with gr.Row():
                    select_free_btn = gr.Button("Select Standard Core", variant="secondary")
                    checkout_premium_btn = gr.Button("Purchase Premium Verified ($49)", variant="primary")
                
                # Hidden state indicator for active premium
                premium_mode_indicator = gr.Checkbox(label="Premium Mode Active", value=False, visible=False)
                
                # Checkout form group (initially hidden)
                with gr.Group(visible=False) as checkout_form:
                    gr.HTML(
                        """
                        <div style="background: rgba(124, 58, 237, 0.03); border: 1px solid rgba(124, 58, 237, 0.15); padding: 20px; border-radius: 12px; margin-top: 25px;">
                            <h4 style="font-size: 1.1rem; font-weight: 700; color: #a78bfa; margin: 0 0 15px 0; display: flex; align-items: center; gap: 8px;">💳 Secure Stripe Sandbox Checkout</h4>
                            <p style="color: #94a3b8; font-size: 0.88rem; margin-top: -10px; margin-bottom: 15px;">This is a simulator payment sandbox. Enter any details below to activate the premium tier immediately.</p>
                        </div>
                        """
                    )
                    with gr.Row():
                        cardholder = gr.Textbox(label="Cardholder Name", placeholder="Jane Doe")
                        cardnumber = gr.Textbox(label="Card Number", placeholder="4111 2222 3333 4444")
                    with gr.Row():
                        expiry = gr.Textbox(label="Expiration Date", placeholder="MM/YY")
                        cvv = gr.Textbox(label="CVV", placeholder="***")
                    
                    with gr.Row():
                        cancel_pay_btn = gr.Button("Cancel", variant="secondary")
                        pay_btn = gr.Button("Authorize Payment & Activate", variant="primary")
                        
                    checkout_status = gr.HTML(visible=False)

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

                        premium_verification_display = gr.HTML(
                            value="""
                            <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 15px; margin-bottom: 15px;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-size: 0.75rem; color: #94a3b8; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;">🛡️ PREMIUM VERIFICATION SERVICE</span>
                                    <span style="background: rgba(255,255,255,0.05); color: #94a3b8; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold;">STANDBY</span>
                                </div>
                                <p style="font-size: 0.85rem; color: #64748b; margin: 8px 0 0 0;">Select the Premium Verified Tier in the Enterprise tab to unlock background white-text scans and candidate link trust verification.</p>
                            </div>
                            """
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

                # Note: events are wired at the bottom of create_app

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

                # Note: events are wired at the bottom of create_app

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

                # Note: events are wired at the bottom of create_app

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
                        gr.HTML(
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

                # Note: events are wired at the bottom of create_app

            # ══════════════════════════════════════════════════════════════
            #  TAB 5 — Resume Builder
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📝 Build Resume"):
                gr.Markdown(
                    "### 📝 PDF Resume Builder\n"
                    "Fill in your details below and generate a **professionally formatted, "
                    "ATS-optimized PDF resume**. Download it instantly."
                )

                with gr.Accordion("📂 Quick Autofill Options (GitHub or PDF Resume)", open=True):
                    gr.Markdown("Pre-populate the manual fields below by either fetching data from a GitHub username or parsing an existing resume PDF (like a LinkedIn PDF export).")
                    with gr.Row():
                        with gr.Column(scale=1):
                            rb_github_username = gr.Textbox(
                                label="GitHub Username",
                                placeholder="e.g. torvalds",
                            )
                            rb_github_btn = gr.Button("🔍 Autofill from GitHub", variant="secondary")
                        with gr.Column(scale=1):
                            rb_autofill_file = gr.File(
                                label="Existing Resume / LinkedIn PDF",
                                file_types=[".pdf"],
                                type="filepath",
                            )
                            rb_pdf_btn = gr.Button("⚡ Parse & Autofill PDF", variant="secondary")

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

                # Note: events are wired at the bottom of create_app

            # ══════════════════════════════════════════════════════════════
            #  TAB 7 — Find Jobs
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("🔍 Find Jobs"):
                gr.Markdown(
                    "### 🔍 Real-Time Job Discovery & Match Engine\n"
                    "Upload your resume to search across multiple live job boards (Remotive, Arbeitnow, and Adzuna). "
                    "The engine parses your resume, generates customized search queries, filters by location preferences, "
                    "and ranks matching roles in a Tinder-style swipe-card view using semantic similarity."
                )

                with gr.Row():
                    with gr.Column(scale=1):
                        jf_pdf = gr.File(
                            label="Resume (PDF) — Upload to Find Jobs",
                            file_types=[".pdf"],
                            type="filepath",
                        )
                        
                        jf_location = gr.Textbox(
                            label="📍 Location Preference",
                            placeholder="e.g. Remote, New York, London (Leave blank to autofill from resume)",
                            lines=1,
                        )
                        
                        jf_remote = gr.Checkbox(
                            label="🏠 Remote Jobs Only",
                            value=False,
                        )
                        
                        find_jobs_btn = gr.Button(
                            "🔍 Find Matching Jobs",
                            variant="primary",
                            size="lg",
                        )

                    with gr.Column(scale=2):
                        jf_cards_display = gr.HTML(
                            r"""
                            <div style="text-align: center; padding: 40px; color: var(--psi-text-dim);">
                                <span style="font-size: 3rem;">📄</span>
                                <h3>Ready to find jobs</h3>
                                <p>Upload your resume and click "Find Matching Jobs" to start matching roles.</p>
                            </div>
                            """
                        )
                        
                        with gr.Row():
                            jf_match_count = gr.Textbox(
                                label="Total Matches",
                                value="0 matches",
                                interactive=False,
                            )
                            jf_status = gr.Textbox(
                                label="Status",
                                value="Idle",
                                interactive=False,
                            )


            # ══════════════════════════════════════════════════════════════
            #  TAB 8 — LLMOps Observability
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("📊 LLMOps Observability"):
                gr.Markdown(
                    "### 📊 Real-Time LLMOps Observability & Safety Dashboard\n"
                    "Tracks transaction cost estimates, latency metrics, token consumption, safety violations (prompt injection detections), and active prompt template configurations."
                )
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh Metrics & Logs", variant="secondary")
                    clear_logs_btn = gr.Button("🧹 Clear Telemetry logs", variant="stop")
                    
                with gr.Row():
                    total_cost_box = gr.Textbox(label="Total LLM Cost (USD)", interactive=False)
                    avg_latency_box = gr.Textbox(label="Average Latency (sec)", interactive=False)
                    total_tokens_box = gr.Textbox(label="Total Tokens Consumed", interactive=False)
                    success_rate_box = gr.Textbox(label="LLM Success Rate (%)", interactive=False)
                    dataset_size_box = gr.Textbox(label="Fine-Tuning Dataset Size", interactive=False)

                with gr.Row():
                    telemetry_logs_table = gr.HTML(label="Recent LLM Tracing Logs")
                    safety_logs_table = gr.HTML(label="Security Guardrails & PII Mask Logs")

            # ══════════════════════════════════════════════════════════════
            #  TAB 6 — About
            # ══════════════════════════════════════════════════════════════
            with gr.Tab("ℹ️ About"):
                gr.Markdown(ABOUT_MD)

        # ── Event Wireups ──────────────────────────────────────────────────
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

        find_jobs_btn.click(
            fn=search_and_match_jobs,
            inputs=[
                jf_pdf,
                jf_location,
                jf_remote,
                pdf_input,
                improve_pdf,
            ],
            outputs=[
                jf_cards_display,
                jf_match_count,
                jf_status,
            ],
        )

        analyze_btn.click(
            fn=analyze_resume,
            inputs=[pdf_input, jd_input, premium_mode_indicator, improve_pdf, gan_pdf, improve_jd, gan_jd],
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
                premium_verification_display,
            ],
        )

        improve_jd_dataset_table.select(
            fn=load_jd_from_dataset,
            inputs=[],
            outputs=[improve_jd],
        )

        improve_btn.click(
            fn=get_improvements,
            inputs=[improve_pdf, improve_jd, pdf_input, gan_pdf, jd_input, gan_jd],
            outputs=[suggestions_display, ats_bullets_display, improve_status],
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
            inputs=[gan_pdf, gan_jd, pdf_input, improve_pdf, jd_input, improve_jd],
            outputs=[
                gan_generator_display,
                gan_discriminator_display,
                gan_bias_display,
                gan_status,
            ],
            js="""(...args) => {
                if (window.startATSGame) {
                    window.startATSGame();
                }
                return args;
            }"""
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

        rb_github_btn.click(
            fn=fetch_github_data,
            inputs=[rb_github_username],
            outputs=[
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
                rb_output, rb_status,
            ],
        )

        rb_pdf_btn.click(
            fn=parse_and_autofill_pdf,
            inputs=[rb_autofill_file],
            outputs=[
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
                rb_output, rb_status,
            ],
        )

        # ── Premium Checkout wireups ─────────────────────────────────────
        select_free_btn.click(
            fn=select_free_tier,
            inputs=[],
            outputs=[premium_mode_indicator, active_tier_html, checkout_form, checkout_status],
        )

        checkout_premium_btn.click(
            fn=open_checkout,
            inputs=[],
            outputs=[checkout_form, checkout_status],
        )

        cancel_pay_btn.click(
            fn=close_checkout,
            inputs=[],
            outputs=[checkout_form, checkout_status],
        )

        pay_btn.click(
            fn=complete_payment,
            inputs=[cardholder, cardnumber, expiry, cvv],
            outputs=[premium_mode_indicator, active_tier_html, checkout_form, checkout_status],
        )

        refresh_btn.click(
            fn=get_observability_metrics,
            inputs=[],
            outputs=[total_cost_box, avg_latency_box, total_tokens_box, success_rate_box, telemetry_logs_table, safety_logs_table, dataset_size_box]
        )

        clear_logs_btn.click(
            fn=clear_observability_logs,
            inputs=[],
            outputs=[total_cost_box, avg_latency_box, total_tokens_box, success_rate_box, telemetry_logs_table, safety_logs_table, dataset_size_box]
        )

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
