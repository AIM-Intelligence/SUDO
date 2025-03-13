import csv, json, sys

"""
사용예시: python csv_to_json.py gpt4.5_dynamic_1 dynamic_response_round_1
"""

base_name = sys.argv[1]
column2 = sys.argv[2]  # task로 사용할 컬럼

csv_file = f'./formatter/csv2json/csv/{base_name}.csv'
json_file = f'./formatter/csv2json/json/{base_name}.json'

data = []

with open(csv_file, mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        data.append({
            "identifier": row["identifier"], 
            "task": row[column2]
        })

with open(json_file, mode='w', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=4)
