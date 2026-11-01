"""Capture screenshots of the Streamlit interface for the thesis (run with a separate playwright venv)."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8502'
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else 'reports/thesis/ui')
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 6000}, device_scale_factor=1.5, color_scheme='light')
    page.goto(URL)
    page.wait_for_selector('text=Երթևեկության հոսքի վերլուծություն', timeout=60000)
    time.sleep(5)
    page.screenshot(path=str(OUT / 'full-settings.png'))
    button = page.get_by_role('button', name='Ցույց տալ պահպանված օրինակը')
    if button.count():
        button.first.click()
        page.wait_for_selector('text=Արդյունքներ', timeout=60000)
        time.sleep(8)
        page.set_viewport_size({'width': 1400, 'height': 9000}); time.sleep(4)
        page.screenshot(path=str(OUT / 'full-results.png'))
    else:
        print('saved-example button not found')
    browser.close()
print('done')
