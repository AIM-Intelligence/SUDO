import csv
import os
import glob
import re
import json
import base64
import openai 
import time
import tempfile
import pandas as pd
from dotenv import load_dotenv
import sys
import re
from tqdm import tqdm

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
DYNAMIC_PROMPT_PATH = "./attack/prompt/dynamic_prompt.txt"
openai.api_key = OPENAI_API_KEY

def dynamic(instructions, json_file_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    eval_data = data["evaluation_results"]
    refused_score = eval_data["refused_score"]
    rubric_score = eval_data["rubric_score"]
    asr_percentage = eval_data["ASR(%)"]
    explanation = eval_data["Explanation"]

    assistant_last_response_text = data.get("assistant_last_response_text", "")
    images = data.get("assistant_last_response_images", [])
    if images:
        assistant_last_response_images = images[0] 
    else:
        assistant_last_response_images = ""

    if asr_percentage == 100:
        return "passed"

    with open(DYNAMIC_PROMPT_PATH, "r", encoding="utf-8") as dp:
        dynamic_prompt_template = dp.read()

    dynamic_prompt = dynamic_prompt_template.format(
        instructions=instructions,
        explanation=explanation,
        asr_percentage=asr_percentage
    )

    if assistant_last_response_images == "":
        response = openai.ChatCompletion.create(
            model="gpt-4o-2024-05-13",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": dynamic_prompt,
                        },
                    ],
                }
            ],
        )
    else:
        response = openai.ChatCompletion.create(
            model="gpt-4o-2024-05-13",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": dynamic_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{assistant_last_response_images}"},
                        },
                    ],
                }
            ],
        )

    return response.choices[0].message.content

def build_file_mapping(json_folder):
    file_mapping = {}
    for json_file in glob.glob(os.path.join(json_folder, "*.json")):
        filename = os.path.basename(json_file)
        match = re.search(r'_(\w+)_eval\.json$', filename)
        if match:
            identifier = match.group(1)
            file_mapping[identifier] = json_file
    return file_mapping

def main(csv_file_path, output_csv_path, json_folder, based_dynamic_num):
    based_tactic = "static_response"
    if based_dynamic_num > 0:
        based_tactic = f"dynamic_response_round_{based_dynamic_num}"
    current_tactic = f"dynamic_response_round_{based_dynamic_num+1}"
    file_mapping = build_file_mapping(json_folder) 

    df = pd.read_csv(csv_file_path)
    if current_tactic not in df.columns:
            df[current_tactic] = ""  
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Generating Dynamic Attack", unit="index"):
        instructions = row.get(based_tactic, "")
        identifier = row.get("identifier", "").strip()

        json_file_path = file_mapping.get(identifier)
        if json_file_path:
            try:
                result = dynamic(instructions, json_file_path)  
            except Exception as e:
                result = f"Error: {e}"

            df.loc[index, current_tactic] = result
            df.to_csv(output_csv_path, index=False)

        else:
            print(f"No JSON file found for identifier: {identifier}")

    df.to_csv(output_csv_path, index=False)
    print(f"\nAll done. Final CSV saved to {output_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(f"Usage: python {sys.argv[0]} <csv_file_path> <output_csv_path> <eval result> <based dynamic num>")
        sys.exit(1)

    csv_file_path     = sys.argv[1]
    output_csv_path   = sys.argv[2]
    json_folder       = sys.argv[3]
    based_dynamic_num = int(sys.argv[4])

    main(csv_file_path, output_csv_path, json_folder, based_dynamic_num)
