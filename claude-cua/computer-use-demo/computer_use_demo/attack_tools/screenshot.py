import os
import streamlit as st
from PIL import Image
from playwright.async_api import async_playwright

LOG_DIR = "/home/computeruse/computer_use_demo/log"

async def capture_screenshot(identifier):
    screenshot_path = os.path.join(LOG_DIR + "/screenshot", f"{identifier}.png")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) 
            page = await browser.new_page()
            await page.goto("http://127.0.0.1:6080/vnc.html?&resize=scale&autoconnect=1&view_only=1", wait_until="networkidle")  
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()
            image = Image.open(screenshot_path)
            width, height = image.size  

            left = 158.5
            top = 0
            right = width - 158.5
            bottom = height

            cropped_image = image.crop((left, top, right, bottom))  
            cropped_image.save(screenshot_path) 

        st.success(f"📸 Screen Capture complete!: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        st.error(f"❌ Screen Capture failed: {e}")
