import json, sys

base_name = sys.argv[1]
scenechg_file = sys.argv[2] if len(sys.argv) > 2 else "./formatter/auto-scene/SUDO_scnchg.json"

input_file = f'./formatter/auto-scene/before_auto_scnchg/{base_name}.json'
output_file = f'./formatter/auto-scene/after_auto_scnchg/{base_name}_auto.json'

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def insert_scenechg_with_urls(scenechg_data, main_data):
    modified_data = []
    index = 0

    for item in main_data:
        if index < len(scenechg_data):
            modified_data.append(scenechg_data[index])
            index += 1
        modified_data.append(item) 

    return modified_data

scenechg_data = load_json(scenechg_file)
main_data = load_json(input_file)

attack_w_scnchg = insert_scenechg_with_urls(scenechg_data, main_data)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(attack_w_scnchg, f, indent=4, ensure_ascii=False)

print(f"Save '{output_file}' completed.")
