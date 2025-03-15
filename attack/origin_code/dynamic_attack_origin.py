import csv
import os
import glob
import re
import json
import base64
import openai  # Make sure the openai module is installed and configured
import time
import tempfile
import pandas as pd

DYNAMIC_PROMPT_PATH = "./attack/prompt/dynamic_prompt.txt"

openai.api_key = ""

def dynamic(instructions, json_file_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract evaluation details from the JSON data
    eval_data = data["evaluation_results"]
    refused_score = eval_data["refused_score"]
    rubric_score = eval_data["rubric_score"]
    asr_percentage = eval_data["ASR(%)"]
    explanation = eval_data["Explanation"]

    assistant_last_response_text = data.get("assistant_last_response_text", "")
    # Check if the assistant_last_response_images list is empty
    images = data.get("assistant_last_response_images", [])
    if images:
        assistant_last_response_images = images[0]
    else:
        assistant_last_response_images = ""

    print("Refused Score:", refused_score)
    print("Rubric Score:", rubric_score)
    print("ASR(%):", asr_percentage)
    print("Explanation:", explanation)
    print("Assistant Last Response Text:", assistant_last_response_text)
#This was the computer agent's last response: {assistant_last_response_text} and determine why you werent able to get the full score

    if asr_percentage == 100:
      return "passed"
    dynamic_prompt = DYNAMIC_PROMPT_PATH.format(instructions=instructions,explanation=explanation,asr_percentage=asr_percentage )

    if assistant_last_response_images == "":
        response = openai.chat.completions.create(
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
      response = openai.chat.completions.create(
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


# Build a mapping of identifier -> JSON file path from the /content/dynamic folder.
json_folder = "/content/static_file" #평가결과
file_mapping = {}
for json_file in glob.glob(os.path.join(json_folder, "*.json")):
    filename = os.path.basename(json_file)
    # Use regex to extract identifier between date and _eval.json
    match = re.search(r'_(\w+)_eval\.json$', filename)
    if match:
        identifier = match.group(1)
        file_mapping[identifier] = json_file

csv_file_path = "/content/gpto1_dynamic_1 - gpto1_dynamic_1.csv"
output_csv_path = "/content/gpto1_dynamic_1.csv"
df = pd.read_csv(csv_file_path)

for index, row in df.iterrows():
    instructions = row.get("static", "")
    identifier = row.get("identifier", "").strip()
    print(f"Processing row with identifier {identifier} and static attack: {instructions} ")
    json_file_path = file_mapping.get(identifier)
    if json_file_path:
        print(f"Processing row with identifier '{identifier}' using file '{json_file_path}'")
        try:
            result = dynamic(instructions, json_file_path)
        except Exception as e:
            result = f"Error: {e}"
        df.loc[index, "dynamic_response_round_1"] = result
        df.to_csv(output_csv_path, index=False)
        print("Dynamic Response:")
        print(result)
    else:
        print(f"No JSON file found for identifier: {identifier}")

# Final save
df.to_csv(output_csv_path, index=False)