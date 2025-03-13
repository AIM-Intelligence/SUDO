import io
import os
import json
import base64
import streamlit as st
from datetime import datetime
    # Streamlit components.html 로 삽입이 필요.
    # 원본 코드에서 import streamlit.components.v1 as components 를 주석했었음.
    # 여기서 임시로:
import streamlit.components.v1 as components

LOG_DIR = "/home/computeruse/computer_use_demo/log"

def download_chat_logs(selected_file):
    """로그 저장 시 파일명 변경 (chat_log → JSON 파일명)"""
    if not st.session_state.messages:
        st.write("⚠️ No messages to save")
        return None

    if st.session_state.log_saved:
        st.write("⚠️ Log has already been saved")
        return None
    
    st.session_state.log_saved = True
     # 가장 최근 identifier 가져오기 (없으면 "unknown")
    last_identifier = st.session_state.get("current_identifier", "unknown")

    # 날짜만 포함된 timestamp 생성
    timestamp = datetime.now().strftime("%Y-%m-%d")

    processed_messages = []

    for msg in st.session_state.messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # user 역할이지만 tool_result 타입을 포함한 경우 role을 assistant로 변경
        if role == "user" and isinstance(content, list):
            for item in content:
                if item.get("type") == "tool_result":
                    role = "assistant"
                    break  # 한 개만 있어도 변경하므로 빠르게 종료

        processed_messages.append({"role": role, "content": content})

    log_data = {
        "timestamp": timestamp,
        "identifier": last_identifier,  # identifier 추가
        "messages": processed_messages,
    }
    json_bytes = json.dumps(log_data, indent=4, ensure_ascii=False).encode("utf-8")
    st.session_state.saved_file_content = io.BytesIO(json_bytes)
    st.session_state.saved_file_name = f"{selected_file}_{timestamp}_{last_identifier}.json"
    st.write("✅ Log saved completed:", st.session_state.saved_file_name)
    st.write("📄 Stored data length:", len(json_bytes))
    return True

def trigger_auto_download():
    """automatic download trigger"""
    if not st.session_state.saved_file_content:
        st.write("⚠️ No messages to save")
        return
    
    st.session_state.saved_file_content.seek(0)
    file_data = st.session_state.saved_file_content.read()
    b64_data = base64.b64encode(file_data).decode()
    file_name = st.session_state.saved_file_name

    # JavaScript HTML 생성
    # (원본 코드 주석/문자열 모두 그대로 유지)
    components_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Auto Download</title>
    </head>
    <body>
        <script>
            // Base64 데이터를 Blob으로 변환
            const b64Data = "{b64_data}";
            const byteCharacters = atob(b64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {{
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }}
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], {{ type: "application/json" }});

            // Blob URL 생성 및 다운로드
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = "{file_name}";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            console.log("✅ Log saved completed");
        </script>
    </body>
    </html>
    """

    components.html(components_code, height=0)
    st.write("🚀 Automatic download trigger execution complete!")

def save_log_to_dir(selected_file):
    """로그를 log 디렉토리에 저장하는 함수"""
    st.write("⚠️ save_log_to_dir")
    if not st.session_state.messages:
        st.write("⚠️ No messages to save")
        return None

    if st.session_state.log_saved:
        st.write("⚠️ Log has already been saved")
        return None

    st.session_state.log_saved = True

    last_identifier = st.session_state.get("current_identifier", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d")

    processed_messages = []
    for msg in st.session_state.messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user" and isinstance(content, list):
            for item in content:
                if item.get("type") == "tool_result":
                    role = "assistant"
                    break

        processed_messages.append({"role": role, "content": content})

    log_data = {
        "timestamp": timestamp,
        "identifier": last_identifier,
        "messages": processed_messages,
    }

    json_bytes = json.dumps(log_data, indent=4, ensure_ascii=False).encode("utf-8")

    filename_without_ext = os.path.splitext(selected_file)[0].removesuffix('_auto')

    selected_log_dir = os.path.join(LOG_DIR, filename_without_ext)
    if not os.path.exists(selected_log_dir):
        os.makedirs(selected_log_dir, exist_ok=True)

    log_file_path = os.path.join(selected_log_dir, f"{filename_without_ext}_{timestamp}_{last_identifier}.json")

    try:
        with open(log_file_path, "wb") as log_file:
            log_file.write(json_bytes)

        if os.path.exists(log_file_path) and os.stat(log_file_path).st_size > 0:
            st.session_state.saved_file_name = log_file_path
            st.session_state.saved_file_content = io.BytesIO(json_bytes)
            st.write(f"✅ Log successfully saved: {log_file_path}")
            st.write(f"📄 File size: {os.stat(log_file_path).st_size} bytes")
        else:
            st.error("❌ Log file was created but is empty. Please check the writing process.")

    except Exception as e:
        st.error(f"❌ Log saving failed: {e}")
