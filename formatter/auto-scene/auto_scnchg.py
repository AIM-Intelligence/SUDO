import json
import os 

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def insert_scenechg_with_urls(scenechg_data, main_data):
    """
    inserts scanechg data (45) alternately with the existing JSON list (main_data)
    """
    modified_data = []
    index = 0

    for item in main_data:
        if index < len(scenechg_data):
            modified_data.append(scenechg_data[index])  #scenechg
            index += 1
        modified_data.append(item) 
    
    return modified_data

def gen_auto_attack(filename):
    scenechg_data = load_json("harmGUI_scnchg.json")
    attack_task = filename
    attack_w_scnchg = insert_scenechg_with_urls(scenechg_data, load_json(attack_task))
    output_file = os.path.splitext(attack_task)[0] + "_auto.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(attack_w_scnchg, f, indent=4, ensure_ascii=False)

    print(f"Save'{output_file}' completed.")


filename = "/home/jiankim/project/aim/AimAgent/data/before_auto_scnchg/gpt4.5_static.json"
gen_auto_attack(filename)
