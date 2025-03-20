import os
import json
import streamlit as st
from datetime import datetime

DATA_DIR = "/home/computeruse/computer_use_demo/data"

def get_json_files():
    """data/ 폴더 내 JSON 파일 리스트 반환"""
    if not os.path.exists(DATA_DIR):
        st.error(f"⚠️ 데이터 폴더가 존재하지 않습니다: {DATA_DIR}")
        return []
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]

def load_last_task(selected_file):
    """마지막 실행한 identifier를 불러오는 함수 (파일별 저장)"""
    last_task_path = os.path.join(DATA_DIR, f"{selected_file}_last_task.json")
    
    if os.path.exists(last_task_path):
        try:
            with open(last_task_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                last_identifier = data.get("last_identifier")

                if last_identifier:
                    return last_identifier
                else:
                    st.warning(f"⚠️ 저장된 identifier가 없습니다. 처음부터 실행합니다.")
                    return None
        except json.JSONDecodeError:
            st.warning(f"⚠️ 마지막 실행 기록이 손상됨: {last_task_path}. 처음부터 실행합니다.")
            return None
    return None

def save_last_task(selected_file, identifier):
    """현재 실행 중인 identifier를 저장하는 함수 (파일별 저장)"""
    last_task_path = os.path.join(DATA_DIR, f"{selected_file}_last_task.json")

    try:
        # ✅ task_index가 증가한 상태에서 저장해야 함.
        next_task_index = st.session_state.get("task_index", 0)

        if next_task_index < len(st.session_state.tasks) - 1:
            next_identifier = st.session_state.tasks[next_task_index + 1]["identifier"]
        else:
            next_identifier = "complete"  # ✅ 마지막 identifier 종료시 complete

        with open(last_task_path, "w", encoding="utf-8") as file:
            json.dump({"last_identifier": next_identifier}, file, indent=4, ensure_ascii=False)

        #st.write(f"✅ 실행된 identifier 저장 완료: {next_identifier}")

    except Exception as e:
        st.error(f"❌ 마지막 실행 기록 저장 실패: {e}")

def load_tasks_from_json(file_path):
    """JSON 파일에서 identifier와 task를 함께 로드"""
    if not os.path.exists(file_path):
        st.error(f"⚠️ JSON 파일이 존재하지 않습니다: {file_path}")
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        
        # 데이터 형식 검사 및 변환
        if not isinstance(data, list):  # JSON 파일이 리스트 형태가 아닌 경우
            st.error("❌ JSON 파일의 형식이 잘못되었습니다. 리스트여야 합니다.")
            return []

        formatted_data = []
        for item in data:
            if isinstance(item, dict) and "identifier" in item and "task" in item:
                formatted_data.append({"identifier": item["identifier"], "task": item["task"]})
            else:
                st.warning(f"⚠️ JSON 항목이 올바른 형식이 아닙니다: {item}")

        return formatted_data

    except json.JSONDecodeError as e:
        st.error(f"❌ JSON 파일 로드 중 오류 발생 (잘못된 형식): {e}")
        return []
    except Exception as e:
        st.error(f"❌ JSON 파일 로드 중 예기치 않은 오류 발생: {e}")
        return []

def get_next_task(selected_file):
    """선택된 JSON 파일에서 중지된 시점의 task를 identifier와 함께 가져오는 함수"""
    file_path = os.path.join(DATA_DIR, selected_file)
    
    if "tasks" not in st.session_state or st.session_state.selected_file != selected_file:
        st.session_state.tasks = load_tasks_from_json(file_path)
        st.session_state.selected_file = selected_file
        
        if "task_index" not in st.session_state:
            st.session_state.task_index = 0  # ✅ 새로운 파일을 선택하면 인덱스 초기화 안 함
    
    last_identifier = load_last_task(selected_file)    # ✅ 마지막 실행된 identifier 이후의 task부터 실행
    
    if last_identifier:
        if last_identifier == "complete":
            return None, None # 모든 task 완료됨
        else:
            found = False
            for idx, task in enumerate(st.session_state.tasks):
                if task["identifier"] == last_identifier:
                    st.session_state.task_index = idx # 1
                    #st.success(f"🔄 이전 실행된 task({last_identifier})를 확인했습니다. 이어서 실행합니다.")
                    found = True
                    break
            if not found:
                #st.warning(f"⚠️ 저장된 identifier({last_identifier})가 목록에 없습니다. 처음부터 실행합니다.")
                st.session_state.task_index = 0  # identifier가 목록에 없으면 처음부터 실행
                
    if st.session_state.task_index < len(st.session_state.tasks):
        next_task_data = st.session_state.tasks[st.session_state.task_index]

        if isinstance(next_task_data, dict) and "identifier" in next_task_data and "task" in next_task_data:
            #st.write(f"🔼 task_index 증가됨: {st.session_state.task_index}")
            return next_task_data["identifier"], next_task_data["task"]
        else:
            #st.error(f"❌ 잘못된 Task 데이터: {next_task_data}")
            return None, None
    else:
        return None, None
