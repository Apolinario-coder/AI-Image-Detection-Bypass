import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def query_imagedetector(image_path, timeout_sec=40):
    resolved = str(Path(image_path).resolve())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        detect_json = None
        
        def on_response(response):
            nonlocal detect_json
            if '/api/detect' in response.url:
                try:
                    detect_json = response.json()
                except Exception:
                    pass

        page.on('response', on_response)
        page.goto('https://imagedetector.com/')
        page.locator('#file-upload').set_input_files(resolved)
        
        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            if detect_json is not None:
                break
            time.sleep(0.5)
            
        browser.close()
        return detect_json

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '2_deai.jpg'
    print(f"Testing {target} on ImageDetector...")
    res = query_imagedetector(target)
    if res:
        details = res.get('result_details', {})
        print("Result % AI:", res.get('result'))
        print("Final Result:", details.get('final_result'))
        print("Confidence:", details.get('confidence'))
        print("SynthID:", details.get('synthid'))
        print("ML Model:", details.get('ml_model'))
        print("Warnings:", details.get('warnings'))
    else:
        print("No response from ImageDetector.")
