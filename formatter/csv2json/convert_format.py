import csv
import json

def csv_to_json(csv_file, json_file, column1, column2):
    data = []
    
    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # 첫 번째 행을 헤더로 인식
        for row in reader:
            data.append({"identifier": row[column1], "task": row[column2]})

    with open(json_file, mode='w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)  # JSON 저장


file_name = "gpt4.5_static"

csv_to_json(f'./csv/{file_name}.csv', f'./json/{file_name}.json', 'identifier', 'attack_result_new')
