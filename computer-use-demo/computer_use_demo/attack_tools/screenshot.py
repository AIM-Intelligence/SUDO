import os
import streamlit as st
from PIL import Image
from playwright.async_api import async_playwright

LOG_DIR = "/home/computeruse/computer_use_demo/log"

async def capture_screenshot(identifier):
    """http://localhost:6080/ 화면을 캡처하여 identifier.png로 저장"""
    screenshot_path = os.path.join(LOG_DIR + "/screenshot", f"{identifier}.png")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)  # ✅ 비동기 Await 사용
            page = await browser.new_page()
            await page.goto("http://127.0.0.1:6080/vnc.html?&resize=scale&autoconnect=1&view_only=1", wait_until="networkidle")  # ✅ 비동기 Await 사용 #&reconnect=1&reconnect_delay=2000
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()
            # ✅ 스크린샷을 크롭하기 위해 이미지 열기
            image = Image.open(screenshot_path)
            width, height = image.size  # 이미지 크기 가져오기

            # ✅ 자를 영역 설정 (좌측 158.5, 상단 0, 우측 width-158.5, 하단 height 유지)
            left = 158.5
            top = 0
            right = width - 158.5
            bottom = height

            cropped_image = image.crop((left, top, right, bottom))  # ✅ 이미지 크롭
            cropped_image.save(screenshot_path)  # ✅ 크롭된 이미지 저장

        st.success(f"📸 Screen Capture complete!: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        st.error(f"❌ Screen Capture failed: {e}")
