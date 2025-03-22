import os
import json
import streamlit as st
from datetime import datetime

DATA_DIR = "/home/computeruse/computer_use_demo/data"

def get_json_files():
    if not os.path.exists(DATA_DIR):
        st.error(f"[!] There is no data folder: {DATA_DIR}")
        return []
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]

def load_last_task(selected_file):
    last_task_path = os.path.join(DATA_DIR, f"{selected_file}_last_task.json")
    
    if os.path.exists(last_task_path):
        try:
            with open(last_task_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                last_identifier = data.get("last_identifier")

                if last_identifier:
                    return last_identifier
                else:
                    st.warning(f"[!] No Identifier. Start at first point")
                    return None
        except json.JSONDecodeError:
            st.warning(f"[!] Identifier get lost.: {last_task_path}.  Start at first point.")
            return None
    return None

def save_last_task(selected_file, identifier):
    last_task_path = os.path.join(DATA_DIR, f"{selected_file}_last_task.json")

    try:
        next_task_index = st.session_state.get("task_index", 0)

        if next_task_index < len(st.session_state.tasks) - 1:
            next_identifier = st.session_state.tasks[next_task_index + 1]["identifier"]
        else:
            next_identifier = "complete" 

        with open(last_task_path, "w", encoding="utf-8") as file:
            json.dump({"last_identifier": next_identifier}, file, indent=4, ensure_ascii=False)

    except Exception as e:
        st.error(f"[1] Fail to save last execution log: {e}")

def load_tasks_from_json(file_path):
    if not os.path.exists(file_path):
        st.error(f"[!] There is no json file: {file_path}")
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        
        if not isinstance(data, list):
            st.error("[!] json file format must be json.")
            return []

        formatted_data = []
        for item in data:
            if isinstance(item, dict) and "identifier" in item and "task" in item:
                formatted_data.append({"identifier": item["identifier"], "task": item["task"]})
            else:
                st.warning(f"[!] Wrong json file format: {item}")

        return formatted_data

    except json.JSONDecodeError as e:
        st.error(f"[!] json file loading error(wrong format): {e}")
        return []
    except Exception as e:
        st.error(f"[!] json file loading error: {e}")
        return []

def get_next_task(selected_file):
    file_path = os.path.join(DATA_DIR, selected_file)
    
    if "tasks" not in st.session_state or st.session_state.selected_file != selected_file:
        st.session_state.tasks = load_tasks_from_json(file_path)
        st.session_state.selected_file = selected_file
        
        if "task_index" not in st.session_state:
            st.session_state.task_index = 0  
    last_identifier = load_last_task(selected_file)    
    
    if last_identifier:
        if last_identifier == "complete":
            return None, None 
        else:
            found = False
            for idx, task in enumerate(st.session_state.tasks):
                if task["identifier"] == last_identifier:
                    st.session_state.task_index = idx # 1
                    found = True
                    break
            if not found:
                st.session_state.task_index = 0  
                
    if st.session_state.task_index < len(st.session_state.tasks):
        next_task_data = st.session_state.tasks[st.session_state.task_index]

        if isinstance(next_task_data, dict) and "identifier" in next_task_data and "task" in next_task_data:
            return next_task_data["identifier"], next_task_data["task"]
        else:
            return None, None
    else:
        return None, None
