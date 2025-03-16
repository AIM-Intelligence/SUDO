import asyncio
import streamlit as st
from functools import partial
from contextlib import contextmanager
from datetime import datetime, timedelta
import httpx
import traceback

from anthropic import RateLimitError

# BetaContentBlockParam, BetaTextBlockParam, BetaToolResultBlockParam
# 등도 그대로 import
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
)
from streamlit.delta_generator import DeltaGenerator

from computer_use_demo.tools import ToolResult
from typing import cast

# 필요한 상수들
INTERRUPT_TEXT = "(user stopped or interrupted and wrote the following)"
INTERRUPT_TOOL_ERROR = "human stopped or interrupted tool execution"

# -- 아래는 Provider/Model import (원본에서 가져옴) --
from computer_use_demo.loop import (
    PROVIDER_TO_DEFAULT_MODEL_NAME,
    APIProvider,
    sampling_loop,  # 이건 원 코드에서 이미 정의
)

# -- run_task_loop 내부에서 get_next_task, maybe_add_interruption_blocks 등 참조 --
from .tasks import get_next_task
from .tasks import save_last_task

from .logs import save_log_to_dir
from .screenshot import capture_screenshot

################################################################################
# 그대로 옮긴 함수들 (validate_auth, maybe_add_interruption_blocks 등)
################################################################################

def validate_auth(provider: APIProvider, api_key: str | None):
    if provider == APIProvider.ANTHROPIC:
        if not api_key:
            return "Enter your Anthropic API key in the sidebar to continue."
    if provider == APIProvider.BEDROCK:
        import boto3
        if not boto3.Session().get_credentials():
            return "You must have AWS credentials set up to use the Bedrock API."
    if provider == APIProvider.VERTEX:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError
        if not os.environ.get("CLOUD_ML_REGION"):
            return "Set the CLOUD_ML_REGION environment variable to use the Vertex API."
        try:
            google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        except DefaultCredentialsError:
            return "Your google cloud credentials are not set up correctly."

def maybe_add_interruption_blocks():
    if not st.session_state.in_sampling_loop:
        return []
    result = []
    last_message = st.session_state.messages[-1]
    previous_tool_use_ids = [
        block["id"] for block in last_message["content"] if block["type"] == "tool_use"
    ]
    for tool_use_id in previous_tool_use_ids:
        st.session_state.tools[tool_use_id] = ToolResult(error=INTERRUPT_TOOL_ERROR)
        result.append(
            BetaToolResultBlockParam(
                tool_use_id=tool_use_id,
                type="tool_result",
                content=INTERRUPT_TOOL_ERROR,
                is_error=True,
            )
        )
    result.append(BetaTextBlockParam(type="text", text=INTERRUPT_TEXT))
    return result

def _api_response_callback(
    request: httpx.Request,
    response: httpx.Response | object | None,
    error: Exception | None,
    tab: DeltaGenerator,
    response_state: dict[str, tuple[httpx.Request, httpx.Response | object | None]],
):
    response_id = datetime.now().isoformat()
    response_state[response_id] = (request, response)
    if error:
        _render_error(error)
    _render_api_response(request, response, response_id, tab)

def _tool_output_callback(
    tool_output: ToolResult, tool_id: str, tool_state: dict[str, ToolResult]
):
    tool_state[tool_id] = tool_output
    _render_message("tool", tool_output)

def _render_api_response(
    request: httpx.Request,
    response: httpx.Response | object | None,
    response_id: str,
    tab: DeltaGenerator,
):
    if isinstance(tab, DeltaGenerator):
        with tab:
            with st.expander(f"Request/Response ({response_id})"):
                newline = "\n\n"
                st.markdown(
                    f"`{request.method} {request.url}`"
                    f"{newline}"
                    f"{newline.join(f'`{k}: {v}`' for k, v in request.headers.items())}"
                )
                st.json(request.read().decode())
                st.markdown("---")
                if isinstance(response, httpx.Response):
                    st.markdown(
                        f"`{response.status_code}`{newline}"
                        f"{newline.join(f'`{k}: {v}`' for k, v in response.headers.items())}"
                    )
                    st.json(response.text)
                else:
                    st.write(response)
    else:
        st.error("⚠️ Invalid tab object detected!")

def _render_error(error: Exception):
    if isinstance(error, RateLimitError):
        body = "You have been rate limited."
        if retry_after := error.response.headers.get("retry-after"):
            body += f" **Retry after {str(timedelta(seconds=int(retry_after)))} (HH:MM:SS).** See our API [documentation](https://docs.anthropic.com/en/api/rate-limits) for more details."
        body += f"\n\n{error.message}"
    else:
        body = str(error)
        body += "\n\n**Traceback:**"
        lines = "\n".join(traceback.format_exception(error))
        body += f"\n\n```{lines}```"
    # 원본 코드에서 save_to_storage(f"error_{datetime.now().timestamp()}.md", body), etc.
    # import 필요
    from .state import save_to_storage
    save_to_storage(f"error_{datetime.now().timestamp()}.md", body)
    st.error(f"**{error.__class__.__name__}**\n\n{body}", icon=":material/error:")

def _render_message(sender: str, message: str | BetaContentBlockParam | ToolResult):
    is_tool_result = not isinstance(message, str | dict)
    if not message or (
        is_tool_result
        and st.session_state.hide_images
        and not hasattr(message, "error")
        and not hasattr(message, "output")
    ):
        return
    with st.chat_message(sender):
        if is_tool_result:
            message = cast(ToolResult, message)
            if message.output:
                if message.__class__.__name__ == "CLIResult":
                    st.code(message.output)
                else:
                    st.markdown(message.output)
            if message.error:
                st.error(message.error)
            if message.base64_image and not st.session_state.hide_images:
                import base64
                st.image(base64.b64decode(message.base64_image))
        elif isinstance(message, dict):
            if message["type"] == "text":
                st.write(message["text"])
            elif message["type"] == "tool_use":
                st.code(f'Tool Use: {message["name"]}\nInput: {message["input"]}')
            else:
                raise Exception(f'Unexpected response type {message["type"]}')
        else:
            st.markdown(message)

################################################################################
# run_task_loop + track_sampling_loop
################################################################################

@contextmanager
def track_sampling_loop():
    """State management during sampling loop progress"""
    st.session_state.in_sampling_loop = True
    st.write("🔄 Start sampling loop")
    yield
    st.session_state.in_sampling_loop = False
    st.write("✅ End sampling loop")
    
    last_identifier = st.session_state.get("current_identifier", "unknown")
    save_last_task(st.session_state.selected_file, last_identifier)

    # 대화 로그 저장 way1 (바탕화면 저장)
    """
    success = download_chat_logs(st.session_state.selected_file)
    if success and not last_identifier.startswith("scenchg"):
        st.session_state.download_ready = True
        st.write("📂 Conversation auto-save completed!")
        trigger_auto_download()
    """
    # way2: 마운트 된 폴더에 저장
    if not last_identifier.startswith("scenchg"):
        st.session_state.download_ready = True
        save_log_to_dir(st.session_state.selected_file)
        st.write("📂 Conversation auto-save completed!")

    # Reset message after saving log (start new conversation)
    if st.session_state.messages:
        st.session_state.messages = []
    st.session_state.log_saved = False

    # harmGUI_scnchg.json 체크
    if st.session_state.selected_file == "harmGUI_scnchg.json":
        current_identifier = st.session_state.get("current_identifier", "unknown")

        async def run_capture():
            await capture_screenshot(current_identifier)

        asyncio.create_task(run_capture())

async def run_task_loop(http_logs, selected_file):
    """Task를 반복해서 실행하는 루프 (중단된 위치부터 재시작)"""
    while True:
        if st.session_state.messages:
            st.session_state.messages = []
            
        result = get_next_task(selected_file)
        if result is None or result == (None, None):
            st.warning("All tasks are exhausted. End.")
            return

        new_identifier, new_task = result
        st.session_state.current_identifier = new_identifier

        st.session_state.messages.append(
            {
                "role": "user",
                "content": [
                    *maybe_add_interruption_blocks(),
                    BetaTextBlockParam(type="text", text=new_task),
                ],
            }
        )
        _render_message("user", new_task)
        st.success(f"New Task assigned: [{new_identifier}] {new_task}")

        suffix = st.session_state.custom_system_prompt

        with track_sampling_loop():
            # 아래 sampling_loop는 computer_use_demo.loop 의 (동일 이름) 함수
            # 여기서는 그대로 import해 사용
            st.session_state.messages = await sampling_loop(
                system_prompt_suffix=suffix,
                model=st.session_state.model,
                provider=st.session_state.provider,
                messages=st.session_state.messages,
                output_callback=lambda msg: _render_message("assistant", msg),
                tool_output_callback=lambda out, tid: _tool_output_callback(out, tid, st.session_state.tools),
                api_response_callback=lambda req, resp, err: _api_response_callback(
                    req, resp, err, http_logs, st.session_state.responses
                ),
                api_key=st.session_state.api_key,
                only_n_most_recent_images=st.session_state.only_n_most_recent_images,
            )

        await asyncio.sleep(7)  # 4초 대기 (너무 빠른 반복 방지)
