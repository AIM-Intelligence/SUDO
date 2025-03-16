import time
import base64
import tempfile
import openai
import ollama
from openai import OpenAI as LlamaOpenAI
import pandas as pd
import csv
import anthropic
from tqdm import tqdm
from dotenv import load_dotenv
import os
import sys
import google.generativeai as genai
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
    "claude-3-7-sonnet-20250219",
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

def load_image(image_path):
    """ 로컬 파일 경로에서 이미지를 로드 """
    if not os.path.exists(image_path):
        print(f"[X] 이미지 파일 없음: {image_path}")
        return None

    try: 
        return PIL.Image.open(image_path)
    except Exception as e:
        print(f"[!] 이미지 로딩 실패: {e}")
        return None

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

def instructions_claude(model_name, prompt_text: str, image_url: str) -> str:
    """
    claude haiku, sonnet (Anthropic) : 이미지+텍스트
    """
    message = client.messages.create(
        model=model_name,
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

def instructions_gpt(model_name, prompt_text: str, image_url: str) -> str:
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
        model= model_name,
        messages=messages,
    )
    return response.choices[0].message.content

def instructions_llama32_vision(prompt_text: str, image_path: str) -> str:
    """
    Llama3.2-Vision 모델을 사용하여 이미지 기반 응답을 생성
"""
    try:
        response = ollama.chat(
            model='llama3.2-vision',
            messages=[{
                'role': 'user',
                'content': prompt_text,
                'images': [image_path]  
            }],
            options={"temperature": 0.3, "top_p": 0.8}
        )
        return response.message.content
    except Exception as e:
        print(f"[!] Llama3.2-Vision 요청 실패: {e}")
        return "[X] 요청 실패"

def instructions_gemini_flash(prompt_text: str, image_path: str) -> str:
    """
    gemini-2.0-flash 에 이미지 + 텍스트를 함께 전달하는 함수.
    google-genai 사용.
    image_path_or_url 인자가 로컬 파일 경로 혹은 HTTP URL일 수 있음.
    """
    # 1) 이미지 로딩 로직
    image = load_image(image_path)

    # 2) Gemini Client 생성
    genai.configure(api_key=GEMINI_API_KEY)  # API 키 설정
    model = genai.GenerativeModel("gemini-2.0-flash")

    # 3) generate_content 호출
    response = model.generate_content([prompt_text, image])
    return response.text

def get_instructions(prompt_text: str, image_url: str, image_path: str,model_name: str) -> str:
    """
    instructions 멀티모달 분기
    """
    if model_name in ["claude-3-5-haiku-20241022","claude-3-7-sonnet-20250219"]:
        return instructions_claude(model_name, prompt_text, image_url)
    elif model_name in ["o1" , "gpt-4.5-preview"]:
        return instructions_gpt(model_name, prompt_text, image_url)
    elif model_name == "llama3.2-90b-vision":
        return instructions_llama32_vision(prompt_text, image_path)
    elif model_name == "gemini-2.0-flash":
        return instructions_gemini_flash(prompt_text, image_path)
    else:
        raise ValueError(f"지원하지 않는 instructions 모델: {model_name}")

###############################################################################
# main
###############################################################################

def main(attack_name, instructions_model):
    df = pd.read_csv(BENCHMARK_CSV_PATH)
    required_columns = {"task(fast)", "default_url", "topic", "elements", "img_url", "image_path"}
    if not required_columns.issubset(df.columns):
        raise ValueError("CSV에 필수 컬럼이 누락됨. (task(fast), default_url, topic, elements, img_url, image_path)")

    # 프롬프트 파일 로드
    deharm_prompt_text   = load_prompt(DEHARM_PROMPT_PATH)
    instruct_prompt_text = load_prompt(INSTRUCT_PROMPT_PATH)
    attacker_prompt_text = load_prompt(ATTACKER_PROMPT_PATH)

    for index, row in tqdm(df.iterrows(), total=len(df), unit="index", desc="Generating Attack Instruction"):        
        task_val   = row["task(fast)"]
        website    = row["default_url"]
        rubric     = row["topic"]
        elements   = row["elements"]
        img_url = row["img_url"]
        image_path = row["image_path"]

        # 1) deharm => gpt-4o (원본 코드 동일)
        clean_text = deharm(task_val, website, "", deharm_prompt_text)

        # 2) instructions => instructions_model
        instructions_prompt = instruct_prompt_text.format(clean=clean_text, website=website, elements=elements)
        instructions_result = get_instructions(instructions_prompt, img_url, image_path, instructions_model)

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