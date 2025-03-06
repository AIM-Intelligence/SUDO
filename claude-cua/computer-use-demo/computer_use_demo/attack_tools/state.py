import os
import streamlit as st
from typing import cast

from computer_use_demo.loop import (
    PROVIDER_TO_DEFAULT_MODEL_NAME,
    APIProvider,
)

# CONFIG_DIR는 기존 코드에선 PosixPath("~/.anthropic"), 여기서 그대로 써도 됨
from pathlib import PosixPath
CONFIG_DIR = PosixPath("~/.anthropic").expanduser()
API_KEY_FILE = CONFIG_DIR / "api_key"

def setup_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_key" not in st.session_state:
        # Try to load API key from file first, then environment
        st.session_state.api_key = load_from_storage("api_key") or os.getenv(
            "ANTHROPIC_API_KEY", ""
        )
    if "provider" not in st.session_state:
        st.session_state.provider = (
            os.getenv("API_PROVIDER", "anthropic") or APIProvider.ANTHROPIC
        )
    if "provider_radio" not in st.session_state:
        st.session_state.provider_radio = st.session_state.provider
    if "model" not in st.session_state:
        _reset_model()
    if "auth_validated" not in st.session_state:
        st.session_state.auth_validated = False
    if "responses" not in st.session_state:
        st.session_state.responses = {}
    if "tools" not in st.session_state:
        st.session_state.tools = {}
    if "only_n_most_recent_images" not in st.session_state:
        st.session_state.only_n_most_recent_images = 3
    if "custom_system_prompt" not in st.session_state:
        st.session_state.custom_system_prompt = load_from_storage("system_prompt") or ""
    if "hide_images" not in st.session_state:
        st.session_state.hide_images = False
    if "in_sampling_loop" not in st.session_state:
        st.session_state.in_sampling_loop = False
    if "log_saved" not in st.session_state:
        st.session_state.log_saved = False
    if "download_ready" not in st.session_state:
        st.session_state.download_ready = False
    if "saved_file_name" not in st.session_state:
        st.session_state.saved_file_name = ""
    if "saved_file_content" not in st.session_state:
        st.session_state.saved_file_content = None  # 메모리 저장 방식으로 변경
    if "last_message_count" not in st.session_state:
        st.session_state.last_message_count = 0

    # JSON 파일 로드시 tasks와 task_index 설정 (main에서 이미 처리하면 여기선 생략 가능)
    if "selected_file" in st.session_state:
        from .tasks import load_tasks_from_json
        file_path = os.path.join("/home/computeruse/computer_use_demo/data", st.session_state.selected_file)

        if "tasks" not in st.session_state or st.session_state.get("tasks_file") != st.session_state.selected_file:
            st.session_state.tasks = load_tasks_from_json(file_path)
            st.session_state.task_index = 0
            st.session_state.tasks_file = st.session_state.selected_file

    if "task_index" not in st.session_state:
        st.session_state.task_index = 0

def _reset_model():
    st.session_state.model = PROVIDER_TO_DEFAULT_MODEL_NAME[
        cast(APIProvider, st.session_state.provider)
    ]

def load_from_storage(filename: str) -> str | None:
    """Load data from a file in the storage directory."""
    try:
        file_path = CONFIG_DIR / filename
        if file_path.exists():
            data = file_path.read_text().strip()
            if data:
                return data
    except Exception as e:
        st.write(f"Debug: Error loading {filename}: {e}")
    return None

def save_to_storage(filename: str, data: str) -> None:
    """Save data to a file in the storage directory."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        file_path = CONFIG_DIR / filename
        file_path.write_text(data)
        file_path.chmod(0o600)
    except Exception as e:
        st.write(f"Debug: Error saving {filename}: {e}")
