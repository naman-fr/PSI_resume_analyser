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


def _list_sample_jds() -> Dict[str, str]:
    """Discover sample JD files under data/sample_jds/."""
    samples: Dict[str, str] = {}
    if SAMPLE_JD_DIR.is_dir():
        for f in sorted(SAMPLE_JD_DIR.glob("*.txt")):
            label = f.stem.replace("_", " ").title()
            samples[label] = f.read_text(encoding="utf-8")
    return samples


SAMPLE_JDS = _list_sample_jds()

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
) -> Tuple[str, str, str, str, str, str, str, str]:
    """
    Run the full resume analysis pipeline.

    Returns eight string outputs for the Gradio UI components:
      0 – overall_score_html
      1 – score_breakdown_html
      2 – skill_match_html
      3 – experience_html
      4 – education_html
      5 – strengths_html
      6 – gaps_html
      7 – status_message
    """
    # ── 1. Validate inputs ────────────────────────────────────────────────
    valid, err = validate_pdf(pdf_file)
    if not valid:
        return ("", "", "", "", "", "", "", f"⚠️ {err}")

    valid, err = validate_jd_text(jd_text)
    if not valid:
        return ("", "", "", "", "", "", "", f"⚠️ {err}")

    # ── 2. Extract text from PDF ──────────────────────────────────────────
    try:
        file_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        resume_text = extract_text_from_pdf(file_path)
    except Exception as exc:
        logger.exception("PDF extraction failed")
        return ("", "", "", "", "", "", "", f"⚠️ Failed to extract text from PDF: {exc}")

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
            "", "", "", "", "", "", "",
            "⚠️ Analysis engine not available. Please ensure agents/graph.py is implemented.",
        )
    except Exception as exc:
        logger.exception("Analysis pipeline failed")
        return ("", "", "", "", "", "", "", f"⚠️ Analysis failed: {exc}")

    # ── 4. Check for pipeline errors ──────────────────────────────────────
    if result.get("error"):
        return ("", "", "", "", "", "", "", f"⚠️ {result['error']}")

    # ── 5. Format results ─────────────────────────────────────────────────
    overall = result.get("overall_score", 0.0)
    keyword = result.get("keyword_score", 0.0)
    semantic = result.get("semantic_score", 0.0)
    experience_score = result.get("experience_score", 0.0)
    education_score = result.get("education_score", 0.0)

    skill_match: dict = result.get("skill_match", {})
    experience_match: dict = result.get("experience_match", {})
    education_match: dict = result.get("education_match", {})
    strengths: list = result.get("strengths", [])
    gaps: list = result.get("gaps", [])

    # Overall score display
    score_cls = _score_class(overall)
    overall_html = (
        f'<div class="score-display score-animate">'
        f'  <div class="score-number {score_cls}">{overall:.1f}</div>'
        f'  <div style="font-size:1.1rem;color:#94a3b8">/100</div>'
        f'  <div class="score-label">{_score_emoji(overall)} {_score_label(overall)}</div>'
        f"</div>"
    )

    # Score breakdown bars
    breakdown_html = (
        _format_score_bar("🎯 Keyword Match", keyword, "40%")
        + _format_score_bar("🧠 Semantic Similarity", semantic, "25%")
        + _format_score_bar("💼 Experience Relevance", experience_score, "25%")
        + _format_score_bar("🎓 Education Match", education_score, "10%")
    )

    # Skill match
    matched = skill_match.get("matched_skills", [])
    missing = skill_match.get("missing_skills", [])
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

    # Strengths & Gaps
    strengths_html = _format_list_items(strengths, "strength-item")
    gaps_html = _format_list_items(gaps, "gap-item")

    provider = result.get("provider_used", "unknown")
    status = f"✅ Analysis complete • Provider: {provider} • Score: {overall:.1f}/100"

    return (
        overall_html,
        breakdown_html,
        skill_html,
        experience_html,
        education_html,
        strengths_html,
        gaps_html,
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
                impact_badge = f' <span class="score-badge badge-yellow">{impact}</span>' if impact else ""
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
                kw_str = ", ".join(keywords) if keywords else ""
                bullet_parts.append(
                    f'<div class="improvement-item">'
                    f'  <p style="color:#94a3b8;font-size:0.82rem;margin-bottom:4px">Original:</p>'
                    f"  <p style=\"margin-bottom:8px\">{original}</p>"
                    f'  <p style="color:#34d399;font-size:0.82rem;margin-bottom:4px">✨ Optimized:</p>'
                    f"  <p><strong>{improved}</strong></p>"
                    + (f'  <p style="font-size:0.78rem;color:#fbbf24;margin-top:6px">Keywords added: {kw_str}</p>' if kw_str else "")
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

            overall = result.get("overall_score", 0.0)
            matched = result.get("skill_match", {}).get("matched_skills", [])
            top_skills = ", ".join(matched[:5]) if matched else "—"
            label = _score_label(overall)

            rows.append([
                file_name,
                f"{overall:.1f}",
                f"{_score_emoji(overall)} {label}",
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

                # Wire up events
                load_btn.click(
                    fn=load_sample_jd,
                    inputs=[sample_dropdown],
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

                batch_btn.click(
                    fn=batch_analyze,
                    inputs=[batch_files, batch_jd],
                    outputs=[batch_results, batch_status],
                )

            # ══════════════════════════════════════════════════════════════
            #  TAB 4 — About
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
