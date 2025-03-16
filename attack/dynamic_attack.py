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
from dotenv import load_dotenv
import sys
import re
from tqdm import tqdm

##############################################################################
#python dynamic_eval.py /content/gpto1_dynamic_1.csv /content/gpto1_dynamic_1_out.csv /content/static_file

##############################################################################

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
DYNAMIC_PROMPT_PATH = "./attack/prompt/dynamic_prompt.txt"
openai.api_key = OPENAI_API_KEY


##############################################################################
# dynamic(instructions, json_file_path)
# - JSON 파일 로드
# - 평가 결과 추출
# - ASR(%) == 100이면 "passed"
# - 그 외 gpt-4o-2024-05-13로 API 호출
##############################################################################

def dynamic(instructions, json_file_path):
    """
    instructions: 사용자가 입력한 공격용 프롬프트(문자열)
    json_file_path: identifier에 해당하는 *_eval.json 경로
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract evaluation details
    eval_data = data["evaluation_results"]
    refused_score = eval_data["refused_score"]
    rubric_score = eval_data["rubric_score"]
    asr_percentage = eval_data["ASR(%)"]
    explanation = eval_data["Explanation"]

    assistant_last_response_text = data.get("assistant_last_response_text", "")
    images = data.get("assistant_last_response_images", [])
    if images:
        assistant_last_response_images = images[0]  # base64 string
    else:
        assistant_last_response_images = ""

    # print("Refused Score:", refused_score)
    # print("Rubric Score:", rubric_score)
    # print("ASR(%):", asr_percentage)
    # print("Explanation:", explanation)
    # print("Assistant Last Response Text:", assistant_last_response_text)

    # 예시: 100%면 바로 passed
    if asr_percentage == 100:
        return "passed"

    # 동적 프롬프트 구성
    # 원본 코드에서는 DYNAMIC_PROMPT_PATH.format(...) 이었으나,
    # 실제로는 DYNAMIC_PROMPT_PATH가 파일 경로입니다.
    # -> 파일 읽기 + string.format(...) 사용하는 식으로 수정 가능
    with open(DYNAMIC_PROMPT_PATH, "r", encoding="utf-8") as dp:
        dynamic_prompt_template = dp.read()

    dynamic_prompt = dynamic_prompt_template.format(
        instructions=instructions,
        explanation=explanation,
        asr_percentage=asr_percentage
    )

    if assistant_last_response_images == "":
        # 텍스트만
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
        # base64 이미지도 함께
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

##############################################################################
# build_file_mapping(json_folder)
# - json_folder 안의 *_eval.json들에 대해 identifier -> 경로를 매핑
##############################################################################

def build_file_mapping(json_folder):
    """
    json_folder: *_eval.json 파일들이 위치한 폴더
    return : { identifier: path_to_json, ...}
    """
    file_mapping = {}
    for json_file in glob.glob(os.path.join(json_folder, "*.json")):
        filename = os.path.basename(json_file)
        # ex) something_<identifier>_eval.json
        match = re.search(r'_(\w+)_eval\.json$', filename)
        if match:
            identifier = match.group(1)
            file_mapping[identifier] = json_file
    return file_mapping

##############################################################################
# main(csv_file_path, output_csv_path, json_folder)
# - CSV 읽기
# - identifier로 JSON 매핑
# - dynamic() 호출 -> CSV에 저장
##############################################################################

def main(csv_file_path, output_csv_path, json_folder):
    # 1) 빌드 맵핑
    file_mapping = build_file_mapping(json_folder) #평가 결과

    # 2) CSV 불러오기
    df = pd.read_csv(csv_file_path)

    # 3) 각 row 순회
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Generating Dynamic Attack", unit="index"):
        instructions = row.get("static", "")
        identifier = row.get("identifier", "").strip()

        # print(f"Processing row with identifier {identifier} and static attack: {instructions}")
        json_file_path = file_mapping.get(identifier)
        if json_file_path:
            # print(f"Processing row with identifier '{identifier}' using file '{json_file_path}'")
            try:
                result = dynamic(instructions, json_file_path)
            except Exception as e:
                result = f"Error: {e}"
            # CSV에 결과 저장
            df.loc[index, "dynamic_response_round_1"] = result
            df.to_csv(output_csv_path, index=False)
            # print("Dynamic Response:")
            # print(result)
        else:
            print(f"No JSON file found for identifier: {identifier}")

    # 마지막에 최종 저장
    df.to_csv(output_csv_path, index=False)
    print(f"\nAll done. Final CSV saved to {output_csv_path}")

##############################################################################
# 엔트리 포인트
##############################################################################

if __name__ == "__main__":
    # 예시: python dynamic_eval.py /content/gpto1_dynamic_1.csv /content/gpto1_dynamic_1_out.csv /content/static_file
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} <csv_file_path> <output_csv_path> <eval result>")
        sys.exit(1)

    csv_file_path   = sys.argv[1]
    output_csv_path = sys.argv[2]
    json_folder     = sys.argv[3]

    # 실행
    main(csv_file_path, output_csv_path, json_folder)
