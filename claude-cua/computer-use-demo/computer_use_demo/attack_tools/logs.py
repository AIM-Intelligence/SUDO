import io
import os
import json
import base64
import streamlit as st
from datetime import datetime
import streamlit.components.v1 as components

LOG_DIR = "/home/computeruse/computer_use_demo/log"

def download_chat_logs(selected_file):
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
    st.session_state.saved_file_content = io.BytesIO(json_bytes)
    st.session_state.saved_file_name = f"{selected_file}_{timestamp}_{last_identifier}.json"
    st.write("✅ Log saved completed:", st.session_state.saved_file_name)
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
            const b64Data = "{b64_data}";
            const byteCharacters = atob(b64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {{
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }}
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], {{ type: "application/json" }});

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

def save_log_to_dir(selected_file):
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
            #st.write(f"📄 File size: {os.stat(log_file_path).st_size} bytes")
        else:
            st.error("❌ Log file was created but is empty. Please check the writing process.")

    except Exception as e:
        st.error(f"❌ Log saving failed: {e}")
