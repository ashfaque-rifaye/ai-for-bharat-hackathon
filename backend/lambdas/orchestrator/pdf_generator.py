"""PDF Generator — Generates professional PDF reports for VaaniSetu.

Two report types:
  1. **Benefit Summary Report**: Eligible schemes, total benefit, synergies.
     Looks like a personalized government benefits report card.
  2. **Application Confirmation**: Application ID, submitted details, scheme info.
     Looks like a receipt/acknowledgment.

Uses fpdf2 (pure Python, no external C deps) with a bundled Noto Sans
Devanagari font so Hindi / Devanagari text renders correctly.  For languages
that the font doesn't cover, we fall back to the Latin subset.

Why fpdf2?
  - Zero native dependencies → runs in AWS Lambda without layers
  - TTF font support → can embed Devanagari glyphs
  - ~500 KB installed size → fits comfortably in 50 MB Lambda limit
"""

import io
import logging
import os
from datetime import datetime

from fpdf import FPDF

logger = logging.getLogger(__name__)

# ── Font Paths ───────────────────────────────────────────────────────
# In Lambda, the handler file lives at /var/task/handler.py so __file__
# resolves there.  The fonts/ directory is at /var/task/fonts/.
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_DEVANAGARI_TTF = os.path.join(_FONT_DIR, "NotoSansDevanagari.ttf")

# ── Language metadata ────────────────────────────────────────────────
LANG_LABELS = {
    "hi": {
        "title_benefit": "लाभ सारांश रिपोर्ट",
        "title_app": "आवेदन पुष्टि",
        "generated": "जनरेट किया गया",
        "total_benefit": "कुल वार्षिक लाभ",
        "eligible_schemes": "पात्र योजनाएं",
        "scheme": "योजना",
        "category": "श्रेणी",
        "annual_benefit": "वार्षिक लाभ",
        "synergies": "योजना तालमेल",
        "user_profile": "आपकी जानकारी",
        "app_id": "आवेदन संख्या",
        "status": "स्थिति",
        "submitted_at": "जमा करने की तिथि",
        "scheme_name": "योजना का नाम",
        "details": "विवरण",
        "footer": "वाणी सेतु — AI सरकारी योजना सहायक",
        "no_synergies": "कोई योजना तालमेल नहीं मिला",
        "confidence": "विश्वसनीयता",
    },
    "en": {
        "title_benefit": "Benefit Summary Report",
        "title_app": "Application Confirmation",
        "generated": "Generated on",
        "total_benefit": "Total Annual Benefit",
        "eligible_schemes": "Eligible Schemes",
        "scheme": "Scheme",
        "category": "Category",
        "annual_benefit": "Annual Benefit",
        "synergies": "Scheme Synergies",
        "user_profile": "Your Profile",
        "app_id": "Application ID",
        "status": "Status",
        "submitted_at": "Submitted On",
        "scheme_name": "Scheme Name",
        "details": "Details",
        "footer": "VaaniSetu — AI Government Scheme Assistant",
        "no_synergies": "No synergies detected",
        "confidence": "Confidence",
    },
}

# Colors
PRIMARY = (25, 72, 127)        # Deep govt-blue
ACCENT = (255, 153, 0)         # Saffron orange
WHITE = (255, 255, 255)
LIGHT_GRAY = (240, 240, 240)
DARK_TEXT = (33, 33, 33)
GREEN = (39, 174, 96)
HEADER_BG = (25, 72, 127)


class _VaaniPDF(FPDF):
    """Branded FPDF subclass with header/footer and Devanagari font."""

    def __init__(self, lang: str = "en") -> None:
        super().__init__()
        self.lang = lang
        self._labels = LANG_LABELS.get(lang, LANG_LABELS["en"])
        self._has_devanagari = False

        # Register Devanagari font (covers Latin + Devanagari glyphs)
        if os.path.exists(_DEVANAGARI_TTF):
            try:
                self.add_font("Noto", "", _DEVANAGARI_TTF)
                self.add_font("Noto", "B", _DEVANAGARI_TTF)
                self.add_font("Noto", "I", _DEVANAGARI_TTF)
                self._has_devanagari = True
            except Exception as exc:
                logger.warning(f"Could not load Devanagari font: {exc}")

    # ── helpers ──────────────────────────────────────────────────────

    def use_font(self, size: int = 10, bold: bool = False, italic: bool = False) -> None:
        """Pick the best font: Noto (universal) or fallback to Helvetica."""
        style = ""
        if bold:
            style += "B"
        if italic:
            style += "I"
        if self._has_devanagari:
            self.set_font("Noto", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def safe_text(self, text: str) -> str:
        """Replace chars unsupported by Helvetica (only needed when Noto is unavailable)."""
        if self._has_devanagari:
            return text
        # Replace em-dash, en-dash, special quotes with ASCII equivalents
        replacements = {
            "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
            "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u20b9": "Rs ",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    # ── branded header / footer ──────────────────────────────────────

    def header(self) -> None:
        # Saffron top bar
        self.set_fill_color(*ACCENT)
        self.rect(0, 0, 210, 4, "F")

        # Logo area
        self.set_fill_color(*HEADER_BG)
        self.rect(0, 4, 210, 18, "F")

        self.set_text_color(*WHITE)
        self.use_font(14, bold=True)
        self.set_y(7)
        self.cell(0, 10, text="VaaniSetu", align="L")

        # Tagline
        self.use_font(8)
        self.set_x(40)
        self.cell(0, 10, text=self.safe_text("AI Government Scheme Assistant"), align="L")

        # Indian flag colors stripe
        self.set_fill_color(255, 153, 51)   # saffron
        self.rect(0, 22, 210, 1.5, "F")
        self.set_fill_color(255, 255, 255)  # white
        self.rect(0, 23.5, 210, 1.5, "F")
        self.set_fill_color(19, 136, 8)     # green
        self.rect(0, 25, 210, 1.5, "F")

        self.set_y(30)
        self.set_text_color(*DARK_TEXT)

    def footer(self) -> None:
        self.set_y(-15)
        self.use_font(7, italic=True)
        self.set_text_color(128, 128, 128)
        footer = self.safe_text(f"{self._labels['footer']}  |  Page {self.page_no()}")
        self.cell(0, 10, text=footer, align="C")


def _format_inr(amount: int) -> str:
    """Indian comma grouping: 1,23,456."""
    s = str(amount)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    groups: list[str] = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(groups) + "," + last3


# =====================================================================
#  PUBLIC API
# =====================================================================

def generate_benefit_summary_pdf(
    benefit_data: dict,
    user_profile: dict,
    language: str = "hi",
) -> bytes:
    """Generate a Benefit Summary Report PDF.

    Args:
        benefit_data: Output of benefit_stacker.compute_benefit_stack().
        user_profile: The user's profile dict.
        language:     2-letter lang code ("hi", "en", …).

    Returns:
        Raw PDF bytes (ready to upload to S3).
    """
    lang = language[:2] if language else "en"
    labels = LANG_LABELS.get(lang, LANG_LABELS["en"])

    pdf = _VaaniPDF(lang)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Title ────────────────────────────────────────────────────────
    pdf.use_font(18, bold=True)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 12, text=pdf.safe_text(labels["title_benefit"]), ln=True, align="C")

    # Date
    pdf.use_font(9)
    pdf.set_text_color(100, 100, 100)
    now = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    pdf.cell(0, 6, text=f"{labels['generated']}: {now}", ln=True, align="C")
    pdf.ln(6)

    # ── Total Benefit Banner ─────────────────────────────────────────
    total = benefit_data.get("totalAnnualBenefit", 0)
    count = benefit_data.get("eligibleCount", 0)

    pdf.set_fill_color(*GREEN)
    pdf.set_text_color(*WHITE)
    pdf.use_font(22, bold=True)
    pdf.cell(0, 16, text=pdf.safe_text(f"  {labels['total_benefit']}:  Rs {_format_inr(total)}"), ln=True, fill=True)

    pdf.set_fill_color(*PRIMARY)
    pdf.use_font(12, bold=True)
    pdf.cell(0, 10, text=pdf.safe_text(f"  {labels['eligible_schemes']}: {count}"), ln=True, fill=True)
    pdf.set_text_color(*DARK_TEXT)
    pdf.ln(6)

    # ── User Profile Section ─────────────────────────────────────────
    if user_profile:
        pdf.use_font(12, bold=True)
        pdf.set_text_color(*PRIMARY)
        pdf.cell(0, 8, text=pdf.safe_text(labels["user_profile"]), ln=True)
        pdf.set_draw_color(*ACCENT)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.use_font(10)
        pdf.set_text_color(*DARK_TEXT)
        profile_keys = {
            "occupation": "Occupation",
            "income": "Annual Income",
            "state": "State",
            "landSize": "Land Size (acres)",
            "age": "Age",
            "gender": "Gender",
            "familySize": "Family Size",
            "caste": "Caste Category",
            "hasDaughters": "Has Daughters",
        }
        for key, label in profile_keys.items():
            val = user_profile.get(key)
            if val is not None:
                pdf.use_font(9, bold=True)
                pdf.cell(55, 6, text=f"  {label}:", ln=False)
                pdf.use_font(9)
                pdf.cell(0, 6, text=pdf.safe_text(str(val)), ln=True)
        pdf.ln(4)

    # ── Eligible Schemes Table ───────────────────────────────────────
    schemes = benefit_data.get("eligibleSchemes", [])
    if schemes:
        pdf.use_font(12, bold=True)
        pdf.set_text_color(*PRIMARY)
        pdf.cell(0, 8, text=pdf.safe_text(labels["eligible_schemes"]), ln=True)
        pdf.set_draw_color(*ACCENT)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

        # Table header
        pdf.set_fill_color(*HEADER_BG)
        pdf.set_text_color(*WHITE)
        pdf.use_font(9, bold=True)
        col_w = [10, 50, 35, 35, 30, 30]
        headers = ["#", labels["scheme"], labels["category"],
                    labels["annual_benefit"], labels["confidence"], "ID"]
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 8, text=pdf.safe_text(h), border=1, fill=True, align="C")
        pdf.ln()

        # Table rows
        pdf.set_text_color(*DARK_TEXT)
        for idx, scheme in enumerate(schemes, 1):
            bg = LIGHT_GRAY if idx % 2 == 0 else WHITE
            pdf.set_fill_color(*bg)
            pdf.use_font(8)

            row = [
                str(idx),
                scheme.get("name", "")[:28],
                scheme.get("category", ""),
                f"Rs {_format_inr(scheme.get('benefitAmount', 0))}",
                f"{int(scheme.get('confidence', 0) * 100)}%",
                scheme.get("schemeId", ""),
            ]
            for i, val in enumerate(row):
                align = "R" if i == 3 else "C" if i in (0, 4) else "L"
                pdf.cell(col_w[i], 7, text=pdf.safe_text(val), border=1, fill=True, align=align)
            pdf.ln()
        pdf.ln(4)

    # ── Synergies Section ────────────────────────────────────────────
    synergies = benefit_data.get("synergies", [])
    pdf.use_font(12, bold=True)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 8, text=pdf.safe_text(labels["synergies"]), ln=True)
    pdf.set_draw_color(*ACCENT)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    if synergies:
        for syn in synergies:
            pdf.set_fill_color(255, 248, 230)
            pdf.use_font(10, bold=True)
            pdf.set_text_color(*ACCENT)

            label = syn.get("label", "")
            full_match = syn.get("allMatched", False)
            badge = " [FULL MATCH]" if full_match else " [PARTIAL]"
            pdf.cell(0, 8, text=pdf.safe_text(f"  {label}{badge}"), ln=True, fill=True)

            pdf.use_font(9)
            pdf.set_text_color(*DARK_TEXT)
            desc = syn.get("description", "")
            pdf.multi_cell(0, 5, text=pdf.safe_text(f"    {desc}"))

            scheme_ids = ", ".join(syn.get("schemes", []))
            pdf.use_font(8, italic=True)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, text=pdf.safe_text(f"    Schemes: {scheme_ids}"), ln=True)
            pdf.ln(2)
    else:
        pdf.use_font(10)
        pdf.cell(0, 8, text=pdf.safe_text(f"  {labels['no_synergies']}"), ln=True)

    # ── Summary Text ─────────────────────────────────────────────────
    summary = benefit_data.get("summaryText", "")
    if summary:
        pdf.ln(4)
        pdf.set_fill_color(240, 248, 255)
        pdf.set_text_color(*DARK_TEXT)
        pdf.use_font(10)
        pdf.multi_cell(0, 6, text=pdf.safe_text(summary), fill=True)

    # ── Return bytes ─────────────────────────────────────────────────
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def generate_application_pdf(
    application_data: dict,
    scheme_data: dict,
    language: str = "hi",
) -> bytes:
    """Generate an Application Confirmation PDF.

    Args:
        application_data: Dict with applicationId, status, submittedAt, fields, etc.
        scheme_data:      The scheme details dict.
        language:         2-letter lang code.

    Returns:
        Raw PDF bytes.
    """
    lang = language[:2] if language else "en"
    labels = LANG_LABELS.get(lang, LANG_LABELS["en"])

    pdf = _VaaniPDF(lang)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Title ────────────────────────────────────────────────────────
    pdf.use_font(18, bold=True)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 12, text=pdf.safe_text(labels["title_app"]), ln=True, align="C")

    pdf.use_font(9)
    pdf.set_text_color(100, 100, 100)
    now = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    pdf.cell(0, 6, text=pdf.safe_text(f"{labels['generated']}: {now}"), ln=True, align="C")
    pdf.ln(6)

    # ── Application ID Banner ────────────────────────────────────────
    app_id = application_data.get("applicationId", "N/A")
    status = application_data.get("status", "SUBMITTED")

    pdf.set_fill_color(*PRIMARY)
    pdf.set_text_color(*WHITE)
    pdf.use_font(14, bold=True)
    pdf.cell(0, 12, text=pdf.safe_text(f"  {labels['app_id']}: {app_id}"), ln=True, fill=True)

    status_color = GREEN if status in ("SUBMITTED", "APPROVED") else ACCENT
    pdf.set_fill_color(*status_color)
    pdf.use_font(11, bold=True)
    pdf.cell(0, 9, text=pdf.safe_text(f"  {labels['status']}: {status}"), ln=True, fill=True)
    pdf.set_text_color(*DARK_TEXT)
    pdf.ln(6)

    # ── Scheme Details ───────────────────────────────────────────────
    scheme_name = scheme_data.get("name", {}).get(lang, scheme_data.get("name", {}).get("en", ""))
    scheme_id = scheme_data.get("schemeId", "")
    category = scheme_data.get("category", "")

    pdf.use_font(12, bold=True)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 8, text=pdf.safe_text(labels["scheme_name"]), ln=True)
    pdf.set_draw_color(*ACCENT)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.use_font(10)
    pdf.set_text_color(*DARK_TEXT)
    pdf.cell(40, 7, text="  Name:", ln=False)
    pdf.use_font(10, bold=True)
    pdf.cell(0, 7, text=pdf.safe_text(scheme_name or scheme_id), ln=True)

    pdf.use_font(10)
    pdf.cell(40, 7, text="  Scheme ID:", ln=False)
    pdf.cell(0, 7, text=pdf.safe_text(scheme_id), ln=True)

    pdf.cell(40, 7, text="  Category:", ln=False)
    pdf.cell(0, 7, text=pdf.safe_text(category), ln=True)
    pdf.ln(4)

    # ── Submitted Details ────────────────────────────────────────────
    fields = application_data.get("fields", {})
    if fields:
        pdf.use_font(12, bold=True)
        pdf.set_text_color(*PRIMARY)
        pdf.cell(0, 8, text=pdf.safe_text(labels["details"]), ln=True)
        pdf.set_draw_color(*ACCENT)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.set_text_color(*DARK_TEXT)
        for key, val in fields.items():
            bg = LIGHT_GRAY
            pdf.set_fill_color(*bg)
            pdf.use_font(9, bold=True)
            pdf.cell(55, 7, text=pdf.safe_text(f"  {key}:"), border=0, fill=True)
            pdf.use_font(9)
            pdf.cell(0, 7, text=pdf.safe_text(str(val)), border=0, fill=True, ln=True)
        pdf.ln(4)

    # ── Timestamp ────────────────────────────────────────────────────
    submitted_at = application_data.get("submittedAt", now)
    pdf.use_font(9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, text=pdf.safe_text(f"{labels['submitted_at']}: {submitted_at}"), ln=True)

    # ── Important Notice ─────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_fill_color(255, 243, 224)
    pdf.set_text_color(*DARK_TEXT)
    pdf.use_font(9, bold=True)
    notice_en = (
        "IMPORTANT: This is a digitally generated acknowledgment from VaaniSetu. "
        "Please keep this document for your records. Your application will be "
        "reviewed by the concerned department. You can track your status using "
        "the Application ID above."
    )
    notice_hi = (
        "महत्वपूर्ण: यह वाणी सेतु द्वारा डिजिटल रूप से जनित पावती है। "
        "कृपया इस दस्तावेज़ को अपने रिकॉर्ड के लिए रखें। आपके आवेदन की "
        "समीक्षा संबंधित विभाग द्वारा की जाएगी। आप ऊपर दिए गए आवेदन संख्या "
        "से अपनी स्थिति ट्रैक कर सकते हैं।"
    )
    notice = notice_hi if lang == "hi" else notice_en
    pdf.use_font(9)
    pdf.multi_cell(0, 5, text=pdf.safe_text(notice), fill=True)

    # ── Return bytes ─────────────────────────────────────────────────
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
