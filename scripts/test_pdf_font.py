"""Test fpdf2 with Devanagari font."""
import os
import sys

try:
    from fpdf import FPDF
    print("fpdf2 imported OK")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

FONT_PATH = "backend/lambdas/orchestrator/fonts/NotoSansDevanagari.ttf"

if not os.path.exists(FONT_PATH):
    print(f"Font not found: {FONT_PATH}")
    sys.exit(1)

print(f"Font size: {os.path.getsize(FONT_PATH)} bytes")

try:
    pdf = FPDF()
    pdf.add_font("NotoDevanagari", "", FONT_PATH)
    pdf.add_page()
    pdf.set_font("NotoDevanagari", "", 14)
    pdf.cell(0, 10, txt="Hello World - नमस्ते दुनिया")
    pdf.output("test_hindi.pdf")
    print(f"PDF generated: {os.path.getsize('test_hindi.pdf')} bytes")
    os.remove("test_hindi.pdf")
    print("SUCCESS")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
