import time
import base64
import tempfile
import openai
from openai import OpenAI as LlamaOpenAI
import pandas as pd
import csv
import anthropic
from tqdm import tqdm
from dotenv import load_dotenv
import os
import sys
from google import genai
from google.genai import types
import PIL.Image
import requests
from io import BytesIO

"""
Static - Detox2tox
1) deharm -> GPT-4o
2) instructions -> model_list
3) attacker -> GPT-4o-2024-05-13
4) CSV 저장
"""


dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ATTACKER_PROMPT_PATH= "./attack/prompt/attacker_prompt.txt"
DEHARM_PROMPT_PATH = "./attack/prompt/deharm.txt"
INSTRUCT_PROMPT_PATH = "./attack/prompt/instructions_prompt.txt"
BENCHMARK_CSV_PATH = "./Benchmark/Web Agent Scenarios - Final_bench.csv"

openai.api_key = OPENAI_API_KEY
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

###############################################################################
# model_list : instructions 용 멀티모달 모델
# gpt-4o는 제외 (원본 코드에서는 instructions 용도로 안 씀)
# gpt-4.5-preview는 vision input이 가능하다고 가정
###############################################################################
model_list = [
    "claude-3-5-haiku-20241022",
    "o1",
    "gpt-4.5-preview",
    "llama3.2-90b-vision",
    "gemini-2.0-flash",
]

###############################################################################
# 공통 유틸
###############################################################################

def load_prompt(prompt_path):
    """
    주어진 경로의 텍스트 파일 내용을 문자열로 반환
    """
    with open(prompt_path, "r", encoding="utf-8") as file:
        content = file.read()
    return content

###############################################################################
# 1) 원본 코드에서 deharm + attacker 로직 (GPT-4o 고정, GPT-4o-2024-05-13)
###############################################################################

def generate_prompts_4o(prompt, system=""):
    """
    원본 코드: generate_prompts_4o => gpt-4o
    """
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content

def generate_prompts_4o_may(prompt, system=""):
    """
    원본 코드: generate_prompts => gpt-4o-2024-05-13
    """
    response = openai.chat.completions.create(
        model="gpt-4o-2024-05-13",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content


def deharm(task, website, rubric, deharm_prompt_text):
    """
    deharm : gpt-4o로 고정
    """
    prompt = deharm_prompt_text.format(task=task, website=website, rubric=rubric)
    return generate_prompts_4o(prompt, system="")

def attacker_prompt_generate(prompt):
    """
    attacker : gpt-4o-2024-05-13로 고정
    """
    return generate_prompts_4o_may(prompt, system="")

###############################################################################
# 2) instructions : 이미지 입력 멀티모달
###############################################################################

def instructions_claude(prompt_text: str, image_url: str) -> str:
    """
    claude-3-5-haiku-20241022 (Anthropic) : 이미지+텍스트
    """
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt_text,
                    }
                ],
            }
        ]
    )
    return message.content[0].text

def instructions_o1(prompt_text: str, image_url: str) -> str:
    """
    OpenAI o1 모델 : 이미지 + 텍스트
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ],
        }
    ]
    response = openai.chat.completions.create(
        model="o1",
        messages=messages,
    )
    return response.choices[0].message.content

def instructions_gpt45_preview(prompt_text: str, image_url: str) -> str:
    """
    gpt-4.5-preview : vision input 가능하다고 가정
    이미지+텍스트
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ],
        }
    ]
    response = openai.chat.completions.create(
        model="gpt-4.5-preview",
        messages=messages,
    )
    return response.choices[0].message.content

def instructions_llama32_vision(prompt_text: str, image_url: str) -> str:
    """
    llama3.2-90b-vision: 
    제공해주신 예시를 바탕으로, base_url='https://api.llama-api.com'을 쓴다고 가정
    여기서는 동일한 OpenAI 호환 인터페이스를 흉내내 보겠습니다.
    실제로는 'from openai import OpenAI(base_url=...)'식으로 다른 client 쓸 수도 있음
    """
    # 아래처럼 openai.ChatCompletion이 아닌, 
    # "llamaapi" 나 "OpenAI(base_url=...)"를 사용해야 할 수도 있음
    # 예시로만 작성:

    llama_client = LlamaOpenAI(
        api_key=LLAMA_API_KEY,  # 실제론 llama-api.com 전용 token
        base_url="https://api.llama-api.com/"
    )

    # 대화 메시지를 "image_url" 부분과 함께 어떻게 전달하는지
    # 공식 docs가 없으므로, o1과 유사한 형식으로 가정
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ],
        }
    ]

    chat_completion = llama_client.chat.completions.create(
        model="llama3.2-90b-vision",
        messages=messages,
        stream=False
    )
    return chat_completion["choices"][0]["message"]["content"]

def instructions_gemini_flash(prompt_text: str, image_path_or_url: str, gemini_api_key: str) -> str:
    """
    gemini-2.0-flash 에 이미지 + 텍스트를 함께 전달하는 함수.
    google-genai 사용.
    image_path_or_url 인자가 로컬 파일 경로 혹은 HTTP URL일 수 있음.
    """

    # 1) 이미지 로딩 로직
    # 만약 'http://' 또는 'https://' 로 시작하면 URL로 판단, requests로 다운로드
    if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
        response = requests.get(image_path_or_url)
        response.raise_for_status()  # 다운로드 실패 시 예외
        image_data = BytesIO(response.content)
        image = PIL.Image.open(image_data)
    else:
        # 그렇지 않으면 로컬 경로로 판단
        image = PIL.Image.open(image_path_or_url)

    # 2) Gemini Client 생성
    client = genai.Client(api_key=gemini_api_key)

    # 3) generate_content 호출
    # contents 배열에 [prompt_text, PIL.Image] 순서로 전달
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt_text, image]
    )

    return response.text


def get_instructions(prompt_text: str, image_url: str, model_name: str) -> str:
    """
    instructions 멀티모달 분기
    """
    if model_name == "claude-3-5-haiku-20241022":
        return instructions_claude(prompt_text, image_url)
    elif model_name == "o1":
        return instructions_o1(prompt_text, image_url)
    elif model_name == "gpt-4.5-preview":
        return instructions_gpt45_preview(prompt_text, image_url)
    elif model_name == "llama3.2-90b-vision":
        return instructions_llama32_vision(prompt_text, image_url)
    elif model_name == "gemini-2.0-flash":
        return instructions_gemini_flash(prompt_text, image_url)
    else:
        raise ValueError(f"지원하지 않는 instructions 모델: {model_name}")

###############################################################################
# main
###############################################################################

def main(attack_name, instructions_model):
    df = pd.read_csv(BENCHMARK_CSV_PATH)
    required_columns = {"task(fast)", "default_url", "topic", "elements", "img_url"}
    if not required_columns.issubset(df.columns):
        raise ValueError("CSV에 필수 컬럼이 누락됨. (task(fast), default_url, topic, elements, img_url)")

    # 프롬프트 파일 로드
    deharm_prompt_text   = load_prompt(DEHARM_PROMPT_PATH)
    instruct_prompt_text = load_prompt(INSTRUCT_PROMPT_PATH)
    attacker_prompt_text = load_prompt(ATTACKER_PROMPT_PATH)

    for index, row in tqdm(df.iterrows(), total=len(df), unit="index", desc="Generating Attack Instruction"):        
        task_val   = row["task(fast)"]
        website    = row["default_url"]
        rubric     = row["topic"]
        elements   = row["elements"]
        screenshot = row["img_url"]

        # 1) deharm => gpt-4o (원본 코드 동일)
        clean_text = deharm(task_val, website, rubric, deharm_prompt_text)

        # 2) instructions => instructions_model
        instructions_prompt = instruct_prompt_text.format(clean=clean_text, website=website, elements=elements)
        instructions_result = get_instructions(instructions_prompt, screenshot, instructions_model)

        # 3) attacker => gpt-4o-2024-05-13 (원본 코드 동일)
        attacker_final = attacker_prompt_text.format(task_val=task_val, instructions=instructions_result)
        attack_result  = attacker_prompt_generate(attacker_final)

        # CSV 결과 저장
        df.at[index, "deharm_new"]        = clean_text
        df.at[index, "instructions_new"]  = instructions_result
        df.at[index, "attack_result_new"] = attack_result

        df.to_csv(f"./attack/result/{attack_name}.csv", index=False)

    print(f"CSV file saved to ./attack/result/{attack_name}.csv")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python ./attack/static_attack.py <attack_name> <model_name>")
        sys.exit(1)

    attack_name      = sys.argv[1]
    instructions_model = sys.argv[2]

    if instructions_model not in model_list:
        print(f"사용가능한 모델 list: {model_list}")
        sys.exit(1)

    main(attack_name, instructions_model)