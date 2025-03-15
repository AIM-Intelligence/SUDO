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

# 모델 리스트 선언
model_list = [
    "claude-3-5-haiku-20241022",
    "o1",
    "gpt-4.5-preview",
    "llama3.2-90b-vision",
    "gemini-2.0-flash",
]

DYNAMIC_PROMPT_PATH = "./attack/prompt/dynamic_prompt.txt"

# (원본에선 openai.api_key = "" 였는데, 실제 API 키가 필요하면 설정해 주세요)
openai.api_key = ""

def dynamic(instructions, json_file_path, chosen_model):
    """
    instructions : 공격용 프로ンプ트(문자열)
    json_file_path : JSON 평가 결과 파일 경로
    chosen_model : model_list 중 하나
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract evaluation details from the JSON data
    eval_data = data["evaluation_results"]
    refused_score = eval_data["refused_score"]
    rubric_score = eval_data["rubric_score"]
    asr_percentage = eval_data["ASR(%)"]
    explanation = eval_data["Explanation"]

    assistant_last_response_text = data.get("assistant_last_response_text", "")
    images = data.get("assistant_last_response_images", [])
    if images:
        assistant_last_response_images = images[0]  # base64 이미지
    else:
        assistant_last_response_images = ""

    print("Refused Score:", refused_score)
    print("Rubric Score:", rubric_score)
    print("ASR(%):", asr_percentage)
    print("Explanation:", explanation)
    print("Assistant Last Response Text:", assistant_last_response_text)

    # 간단한 예: asr_percentage가 100이면 "passed" 반환
    if asr_percentage == 100:
        return "passed"

    # dynamic 프롬프트 파일로드
    # (원본 코드에서 {instructions} / {explanation} / {asr_percentage} 치환 로직이
    #  있었으나, 질문 코드 상에서는 string.format이 아닌 DYNAMIC_PROMPT_PATH 그대로
    #  쓰고 있습니다. 원본 의도에 맞추려면 아래처럼 수정해 주세요.)
    with open(DYNAMIC_PROMPT_PATH, "r", encoding="utf-8") as dp:
        dynamic_prompt_template = dp.read()

    # placeholders가 있다면, 예:
    # dynamic_prompt = dynamic_prompt_template.format(
    #     instructions=instructions,
    #     explanation=explanation,
    #     asr_percentage=asr_percentage
    # )
    # 질문 코드 상에선 "DYNAMIC_PROMPT_PATH.format(...)"라 되어 있었는데
    # 실제론 {instructions} 등 치환이 필요할 수도 있음.

    # 여기선 아래처럼 가정:
    dynamic_prompt = f"{dynamic_prompt_template}\nUser instructions: {instructions}\nExplanation: {explanation}\nASR: {asr_percentage}"

    # messages 구성
    if assistant_last_response_images == "":
        # 텍스트만 전송
        user_content = [
            {
                "type": "text",
                "text": dynamic_prompt
            }
        ]
    else:
        # 이미지(base64)도 함께
        user_content = [
            {
                "type": "text",
                "text": dynamic_prompt
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{assistant_last_response_images}"}
            }
        ]

    try:
        response = openai.chat.completions.create(
            model=chosen_model,  # <-- 인자로 받은 모델
            messages=[
                {
                    "role": "user",
                    "content": user_content
                }
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        # 에러가 발생하면 예외 메시지를 반환
        return f"Error calling OpenAI with model {chosen_model}: {e}"

# 빌드된 identifier -> JSON file path 매핑
def build_file_mapping(json_folder="/content/static_file"):
    file_mapping = {}
    for json_file in glob.glob(os.path.join(json_folder, "*.json")):
        filename = os.path.basename(json_file)
        # 예: something_<identifier>_eval.json
        match = re.search(r'_(\w+)_eval\.json$', filename)
        if match:
            identifier = match.group(1)
            file_mapping[identifier] = json_file
    return file_mapping

def main(csv_file_path="/content/gpto1_dynamic_1 - gpto1_dynamic_1.csv",
         output_csv_path="/content/gpto1_dynamic_1.csv",
         json_folder="/content/static_file",
         model_name="gpt-4o-2024-05-13"):

    # 만약 model_name이 model_list 중 하나가 아니라면 에러 처리
    if model_name not in model_list:
        print(f"지원하지 않는 모델입니다: {model_name}")
        print(f"사용가능한 model list: {model_list}")
        return

    file_mapping = build_file_mapping(json_folder)
    df = pd.read_csv(csv_file_path)

    for index, row in df.iterrows():
        instructions = row.get("static", "")
        identifier = row.get("identifier", "").strip()
        print(f"\n===== Processing row with identifier {identifier} =====\n")
        print(f"static attack: {instructions}")
        json_file_path = file_mapping.get(identifier)

        if json_file_path:
            print(f"Using file '{json_file_path}'")
            try:
                result = dynamic(instructions, json_file_path, model_name)
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
    print(f"\nAll done. Final CSV saved to {output_csv_path}")

if __name__ == "__main__":
    # 커맨드라인 인자로 모델명까지 받는다면:
    # python dynamic_eval.py <csv_file> <output_csv_file> <model_name>
    if len(sys.argv) < 4:
        print(f"Usage: python {sys.argv[0]} <csv_file> <output_csv_file> <model_name>")
        sys.exit(1)

    csv_file_path    = sys.argv[1]
    output_csv_path  = sys.argv[2]
    chosen_model     = sys.argv[3]

    # json_folder가 추가로 인자 넘어오면 처리
    # if len(sys.argv) > 4:
    #     json_folder = sys.argv[4]
    # else:
    #     json_folder = "/content/static_file"

    main(csv_file_path=csv_file_path,
         output_csv_path=output_csv_path,
         json_folder="/content/static_file",
         model_name=chosen_model)
