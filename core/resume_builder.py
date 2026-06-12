"""
PDF Resume Builder Module.

Generates a professionally formatted PDF resume from user-provided structured
data. Uses fpdf2 for PDF generation with a clean, modern ATS-friendly layout.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)


class ResumePDF(FPDF):
    """Custom FPDF class for generating ATS-optimized resumes."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

        # Color palette (dark professional theme on white)
        self.PRIMARY = (33, 37, 41)       # Dark charcoal
        self.SECONDARY = (73, 80, 87)     # Medium gray
        self.ACCENT = (0, 102, 204)       # Professional blue
        self.LIGHT_GRAY = (200, 200, 200)
        self.TEXT = (51, 51, 51)

    def _draw_section_line(self):
        """Draw a thin accent-colored line under section headers."""
        self.set_draw_color(*self.ACCENT)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def _section_header(self, title: str):
        """Render a section header with underline."""
        self.ln(4)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.ACCENT)
        self.cell(0, 7, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self._draw_section_line()
        self.set_text_color(*self.TEXT)

    def _bullet_point(self, text: str, indent: float = 15):
        """Render a bullet point with proper indentation."""
        self.set_font("Helvetica", "", 10)
        self.set_x(indent)
        # Bullet character
        bullet = chr(8226)
        self.cell(5, 5, bullet)
        self.set_x(indent + 6)
        # Calculate available width
        avail_width = 200 - indent - 6
        self.multi_cell(avail_width, 5, text)
        self.ln(1)


def generate_resume_pdf(
    full_name: str,
    email: str,
    phone: str,
    location: str,
    linkedin: str,
    portfolio: str,
    summary: str,
    skills: str,
    experience_entries: List[Dict[str, str]],
    education_entries: List[Dict[str, str]],
    certifications: str,
    projects: List[Dict[str, str]],
) -> Optional[str]:
    """Generate a professional PDF resume and return the file path.

    Parameters
    ----------
    full_name : str
        Candidate's full name.
    email, phone, location : str
        Contact details.
    linkedin, portfolio : str
        LinkedIn URL and portfolio/GitHub URL.
    summary : str
        Professional summary paragraph.
    skills : str
        Comma-separated skills string.
    experience_entries : list of dict
        Each dict: {company, role, start_date, end_date, bullets}
        where bullets is a newline-separated string.
    education_entries : list of dict
        Each dict: {degree, institution, year, gpa}
    certifications : str
        Newline-separated certifications.
    projects : list of dict
        Each dict: {name, description, technologies}

    Returns
    -------
    str or None
        Absolute path to the generated PDF, or None on failure.
    """
    try:
        pdf = ResumePDF()
        pdf.add_page()

        # ── Header: Name ──────────────────────────────────────────────────
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*pdf.PRIMARY)
        pdf.cell(0, 12, full_name.strip() or "Your Name", align="C",
                 new_x="LMARGIN", new_y="NEXT")

        # ── Contact Info Line ─────────────────────────────────────────────
        contact_parts = []
        if email and email.strip():
            contact_parts.append(email.strip())
        if phone and phone.strip():
            contact_parts.append(phone.strip())
        if location and location.strip():
            contact_parts.append(location.strip())

        if contact_parts:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*pdf.SECONDARY)
            pdf.cell(0, 6, "  |  ".join(contact_parts), align="C",
                     new_x="LMARGIN", new_y="NEXT")

        # Links line
        link_parts = []
        if linkedin and linkedin.strip():
            link_parts.append(f"LinkedIn: {linkedin.strip()}")
        if portfolio and portfolio.strip():
            link_parts.append(f"Portfolio: {portfolio.strip()}")
        if link_parts:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*pdf.ACCENT)
            pdf.cell(0, 6, "  |  ".join(link_parts), align="C",
                     new_x="LMARGIN", new_y="NEXT")

        pdf.ln(2)
        # Divider
        pdf.set_draw_color(*pdf.LIGHT_GRAY)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

        # ── Professional Summary ──────────────────────────────────────────
        if summary and summary.strip():
            pdf._section_header("Professional Summary")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*pdf.TEXT)
            pdf.multi_cell(0, 5, summary.strip())
            pdf.ln(2)

        # ── Skills ────────────────────────────────────────────────────────
        if skills and skills.strip():
            pdf._section_header("Technical Skills")
            skill_list = [s.strip() for s in skills.split(",") if s.strip()]

            # Group skills into rows of 4-5 for a clean layout
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*pdf.TEXT)

            row_items = []
            for skill in skill_list:
                row_items.append(skill)
                if len(row_items) >= 5:
                    pdf.cell(0, 5, "  •  ".join(row_items),
                             new_x="LMARGIN", new_y="NEXT")
                    row_items = []
            if row_items:
                pdf.cell(0, 5, "  •  ".join(row_items),
                         new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        # ── Experience ────────────────────────────────────────────────────
        if experience_entries:
            pdf._section_header("Professional Experience")

            for entry in experience_entries:
                if not isinstance(entry, dict):
                    continue
                company = entry.get("company", "").strip()
                role = entry.get("role", "").strip()
                start = entry.get("start_date", "").strip()
                end = entry.get("end_date", "").strip()
                bullets_text = entry.get("bullets", "").strip()

                if not company and not role:
                    continue

                # Role title (bold)
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*pdf.PRIMARY)
                pdf.cell(0, 6, role, new_x="LMARGIN", new_y="NEXT")

                # Company and dates
                date_str = f"{start} - {end}" if start or end else ""
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(*pdf.SECONDARY)
                line = company
                if date_str:
                    line += f"  |  {date_str}"
                pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)

                # Bullet points
                pdf.set_text_color(*pdf.TEXT)
                if bullets_text:
                    for bullet in bullets_text.split("\n"):
                        bullet = bullet.strip()
                        if bullet and bullet not in ("-", "•", "*"):
                            # Remove leading bullet characters
                            bullet = bullet.lstrip("-•* ")
                            if bullet:
                                pdf._bullet_point(bullet)
                pdf.ln(2)

        # ── Education ─────────────────────────────────────────────────────
        if education_entries:
            pdf._section_header("Education")

            for entry in education_entries:
                if not isinstance(entry, dict):
                    continue
                degree = entry.get("degree", "").strip()
                institution = entry.get("institution", "").strip()
                year = entry.get("year", "").strip()
                gpa = entry.get("gpa", "").strip()

                if not degree and not institution:
                    continue

                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*pdf.PRIMARY)
                pdf.cell(0, 6, degree, new_x="LMARGIN", new_y="NEXT")

                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(*pdf.SECONDARY)
                line = institution
                if year:
                    line += f"  |  {year}"
                if gpa:
                    line += f"  |  GPA: {gpa}"
                pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(3)

        # ── Projects ──────────────────────────────────────────────────────
        if projects:
            pdf._section_header("Projects")

            for proj in projects:
                if not isinstance(proj, dict):
                    continue
                name = proj.get("name", "").strip()
                desc = proj.get("description", "").strip()
                tech = proj.get("technologies", "").strip()

                if not name:
                    continue

                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*pdf.PRIMARY)
                pdf.cell(0, 6, name, new_x="LMARGIN", new_y="NEXT")

                if tech:
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(*pdf.ACCENT)
                    pdf.cell(0, 5, f"Technologies: {tech}",
                             new_x="LMARGIN", new_y="NEXT")

                if desc:
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(*pdf.TEXT)
                    pdf.multi_cell(0, 5, desc)

                pdf.ln(3)

        # ── Certifications ────────────────────────────────────────────────
        if certifications and certifications.strip():
            pdf._section_header("Certifications")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*pdf.TEXT)
            for cert in certifications.strip().split("\n"):
                cert = cert.strip().lstrip("-•* ")
                if cert:
                    pdf._bullet_point(cert)

        # ── Save PDF ──────────────────────────────────────────────────────
        output_dir = tempfile.mkdtemp(prefix="resume_builder_")
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_"
                           for c in full_name.strip()) or "Resume"
        output_path = os.path.join(output_dir, f"{safe_name}_Resume.pdf")
        pdf.output(output_path)

        logger.info("Resume PDF generated: %s", output_path)
        return output_path

    except Exception as exc:
        logger.exception("Failed to generate resume PDF.")
        return None
