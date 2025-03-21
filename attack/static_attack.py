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

model_list = [
    "claude-3-5-haiku-20241022",
    "claude-3-7-sonnet-20250219",
    "o1",
    "gpt-4.5-preview",
    "llama3.2-90b-vision",
    "gemini-2.0-flash",
]


def load_prompt(prompt_path):
    with open(prompt_path, "r", encoding="utf-8") as file:
        content = file.read()
    return content

def load_image(image_path):
    if not os.path.exists(image_path):
        print(f"[X] No image file: {image_path}")
        return None

    try: 
        return PIL.Image.open(image_path)
    except Exception as e:
        print(f"[!] Failed to load image: {e}")
        return None

def generate_prompts_4o(prompt, system=""):

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content

def generate_prompts_4o_may(prompt, system=""):
    response = openai.ChatCompletion.create(
        model="gpt-4o-2024-05-13",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content


def deharm(task, website, rubric, deharm_prompt_text):
    prompt = deharm_prompt_text.format(task=task, website=website, rubric=rubric)
    return generate_prompts_4o(prompt, system="")

def attacker_prompt_generate(prompt):
    return generate_prompts_4o_may(prompt, system="")

def instructions_claude(model_name, prompt_text: str, image_url: str) -> str:
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
    response = openai.ChatCompletion.create(
        model= model_name,
        messages=messages,
    )
    return response.choices[0].message.content

def instructions_llama32_vision(prompt_text: str, image_path: str) -> str:
    try:
        response = ollama.chat(
            model='llama3.2-vision',
            messages=[{
                'role': 'user',
                'content': prompt_text,
                'images': [image_path]  
            }],
            options={"temperature": 0.3, "top_p": 0.8, "reset": True}
        )
        return response.message.content
    except Exception as e:
        print(f"[!] Llama3.2-Vision request failed: {e}")
def instructions_gemini_flash(prompt_text: str, image_path: str) -> str:
    image = load_image(image_path)
    genai.configure(api_key=GEMINI_API_KEY)  

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content([prompt_text, image])
    return response.text

def get_instructions(prompt_text: str, image_url: str, image_path: str,model_name: str) -> str:
    if model_name in ["claude-3-5-haiku-20241022","claude-3-7-sonnet-20250219"]:
        return instructions_claude(model_name, prompt_text, image_url)
    elif model_name in ["o1" , "gpt-4.5-preview"]:
        return instructions_gpt(model_name, prompt_text, image_url)
    elif model_name == "llama3.2-90b-vision":
        return instructions_llama32_vision(prompt_text, image_path)
    elif model_name == "gemini-2.0-flash":
        return instructions_gemini_flash(prompt_text, image_path)
    else:
        raise ValueError(f"Unsupported instructions model: {model_name}")

def main(attack_name, instructions_model):
    df = pd.read_csv(BENCHMARK_CSV_PATH)
    required_columns = {"task(fast)", "default_url", "topic", "elements", "img_url", "image_path"}
    if not required_columns.issubset(df.columns):
        raise ValueError("Required columns missing in CSV (task(fast), default_url, topic, elements, img_url, image_path)")

    deharm_prompt_text   = load_prompt(DEHARM_PROMPT_PATH)
    instruct_prompt_text = load_prompt(INSTRUCT_PROMPT_PATH)
    attacker_prompt_text = load_prompt(ATTACKER_PROMPT_PATH)

    for index, row in tqdm(df.iterrows(), total=len(df), unit="index", desc="Generating Attack Instruction"):        
        task_val   = row["task(fast)"]
        website    = row["default_url"]
        rubric     = row["topic"]
        img_url = row["img_url"]
        image_path = row["image_path"]

        clean_text = deharm(task_val, website, "", deharm_prompt_text)

        instructions_prompt = instruct_prompt_text.format(clean=clean_text, website=website)
        instructions_result = get_instructions(instructions_prompt, img_url, image_path, instructions_model)

        attacker_final = attacker_prompt_text.format(task_val=task_val, instructions=instructions_result)
        attack_result  = attacker_prompt_generate(attacker_final)

        df.at[index, "deharm"]        = clean_text
        df.at[index, "instructions"]  = instructions_result
        df.at[index, "static_response"] = attack_result

        df.to_csv(f"./attack/result/{attack_name}.csv", index=False)

    print(f"CSV file saved to ./attack/result/{attack_name}.csv")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python ./attack/static_attack.py <attack_name> <model_name>")
        sys.exit(1)

    attack_name      = sys.argv[1]
    instructions_model = sys.argv[2]

    if instructions_model not in model_list:
        print(f"Available models list: {model_list}")
        sys.exit(1)

    main(attack_name, instructions_model)