"""
Happy Path Screenshot Automation for VaaniSetu Prototype.

Uses Playwright to:
1. Open the deployed CloudFront prototype
2. Walk through the entire happy path (language select → scheme match → form fill → submit)
3. Take a screenshot at every significant step
4. Save all screenshots to screenshots/ folder

Why Playwright?
  - It drives a real Chromium browser, so the screenshots look exactly like
    what a real user would see (CSS, fonts, animations and all).

Updated: 2026-03-08 — deterministic form filling (no Bedrock calls during
form steps), so wait times are short (3-4s per field).
"""

import asyncio
import os
import time
from playwright.async_api import async_playwright

PROTOTYPE_URL = "https://d1mjmr4q1kedn7.cloudfront.net"
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")

# Happy path conversation messages — 12 steps
# Fields pre-populated from profile: state (Bihar), landSize (2)
# So form order: name → fatherName → aadhaar → phone → district → village → bankAccount → ifsc
CONVERSATION_STEPS = [
    {
        "message": "I am a farmer from Bihar with 2 acres of land. My annual income is 1 lakh rupees.",
        "wait_seconds": 12,
        "screenshot": "03_scheme_recommendations",
        "description": "AI recommends eligible schemes based on user profile",
    },
    {
        "message": "I want to apply for PM Kisan",
        "wait_seconds": 5,
        "screenshot": "04_form_start",
        "description": "PM-KISAN selected — form filling begins, asks for name",
    },
    {
        "message": "Rajesh Kumar",
        "wait_seconds": 4,
        "screenshot": "05_form_name",
        "description": "Name accepted — asks for father's name",
    },
    {
        "message": "Suresh Kumar",
        "wait_seconds": 4,
        "screenshot": "06_form_father",
        "description": "Father name accepted — asks for Aadhaar",
    },
    {
        "message": "234567890123",
        "wait_seconds": 4,
        "screenshot": "07_form_aadhaar",
        "description": "Aadhaar validated — asks for mobile number",
    },
    {
        "message": "9876543210",
        "wait_seconds": 4,
        "screenshot": "08_form_phone",
        "description": "Phone validated — asks for district",
    },
    {
        "message": "Patna",
        "wait_seconds": 4,
        "screenshot": "09_form_district",
        "description": "District accepted — asks for village",
    },
    {
        "message": "Danapur",
        "wait_seconds": 4,
        "screenshot": "10_form_village",
        "description": "Village accepted — asks for bank account",
    },
    {
        "message": "12345678901234",
        "wait_seconds": 4,
        "screenshot": "11_form_bank",
        "description": "Bank account validated — asks for IFSC",
    },
    {
        "message": "SBIN0001234",
        "wait_seconds": 5,
        "screenshot": "12_form_review",
        "description": "All fields complete — review summary shown",
    },
    {
        "message": "Yes, everything is correct",
        "wait_seconds": 5,
        "screenshot": "13_application_submitted",
        "description": "Application submitted with confirmation ID",
    },
]


async def take_screenshot(page, name: str, description: str) -> str:
    """Take a viewport screenshot and save it."""
    filepath = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    await page.screenshot(path=filepath, full_page=False)
    print(f"  📸 {name}.png — {description}")
    return filepath


async def send_message_and_wait(page, message: str, wait_seconds: int):
    """Type a message in the chat input and click send, then wait for AI response."""
    input_el = page.locator('input[type="text"]')
    await input_el.fill(message)
    await asyncio.sleep(0.3)
    send_btn = page.locator('form button[type="submit"]')
    await send_btn.click()
    print(f"  Waiting {wait_seconds}s for response...")
    await asyncio.sleep(wait_seconds)


async def scroll_to_bottom(page):
    """Scroll the chat container to the bottom so latest messages are visible."""
    await page.evaluate("""
        () => {
            // Try multiple possible scroll containers
            const containers = document.querySelectorAll('[class*="overflow-y"]');
            containers.forEach(c => { c.scrollTop = c.scrollHeight; });
            const main = document.querySelector('main');
            if (main) main.scrollTop = main.scrollHeight;
            // Also try the flex-1 container
            const flex = document.querySelector('.flex-1.overflow-y-auto');
            if (flex) flex.scrollTop = flex.scrollHeight;
        }
    """)
    await asyncio.sleep(0.5)


async def main():
    # Clean old screenshots
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    for f in os.listdir(SCREENSHOT_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(SCREENSHOT_DIR, f))
    print(f"Screenshots will be saved to: {os.path.abspath(SCREENSHOT_DIR)}")
    print(f"Prototype URL: {PROTOTYPE_URL}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=2,  # Retina-quality
        )
        page = await context.new_page()

        # ── Step 1: Load the prototype ──
        print("Step 1: Loading prototype...")
        await page.goto(PROTOTYPE_URL, wait_until="networkidle")
        await asyncio.sleep(6)  # Wait for session + greeting
        await take_screenshot(page, "01_landing_hindi", "Landing page — Hindi greeting")

        # ── Step 2: Switch to English ──
        print("\nStep 2: Switching to English...")
        english_btn = page.locator("button", has_text="English")
        await english_btn.click()
        await asyncio.sleep(8)  # Wait for English greeting from API
        await scroll_to_bottom(page)
        await take_screenshot(page, "02_english_greeting", "English greeting after language switch")

        # ── Steps 3–13: Walk through the conversation ──
        for i, step in enumerate(CONVERSATION_STEPS):
            step_num = i + 3
            msg_preview = step["message"][:50]
            print(f"\nStep {step_num}: \"{msg_preview}\"")

            await send_message_and_wait(page, step["message"], step["wait_seconds"])
            await scroll_to_bottom(page)
            await take_screenshot(page, step["screenshot"], step["description"])

        # ── Final: Full-page overview ──
        print("\nTaking final full-page screenshot...")
        await page.screenshot(
            path=os.path.join(SCREENSHOT_DIR, "14_full_conversation.png"),
            full_page=True,
        )
        print("  📸 14_full_conversation.png — Full conversation scroll capture")

        await browser.close()

    # Print summary
    screenshots = sorted(f for f in os.listdir(SCREENSHOT_DIR) if f.endswith(".png"))
    print(f"\n{'='*60}")
    print(f"DONE! {len(screenshots)} screenshots saved:")
    print(f"  {os.path.abspath(SCREENSHOT_DIR)}")
    print(f"{'='*60}")
    for s in screenshots:
        print(f"  - {s}")


if __name__ == "__main__":
    asyncio.run(main())
