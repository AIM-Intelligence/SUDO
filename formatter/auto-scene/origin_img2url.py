import os
import re
import requests
import json
import time
import random
from dotenv import load_dotenv
from tqdm import tqdm
from requests.adapters import HTTPAdapter, Retry

# ✅ 환경 변수 로드 (Imgur API Client ID)
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)
CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")

# 이미지가 저장된 폴더 & JSON 저장 경로
IMAGE_FOLDER = "./attack/screenshot"
JSON_OUTPUT = os.path.join(IMAGE_FOLDER, "img_urls.json")

# identifier 리스트 (각 이미지의 새로운 파일명으로 사용)
identifiers = [
    "z3p6b8y", "d9x7m2q", "p9jtrm4", "8gbkcmj", "09lonmf",
    "b2cglv8", "tgvhsri", "fz2dx3g", "udag2zc", "p7sior5",
    "y4falrq", "blpov9z", "jh9i136", "h388rm6", "bq0xmxf",
    "33bnt7q", "ozt593d", "056ad8t", "cnt42cf", "1c7hepz",
    "vhlzxu4", "z4f7ksb", "qufkmn8", "meoqls1", "m2gvzar",
    "rlc4h30", "y9jf33o", "wmg7zve", "jnfxtx9", "1t8f65e",
    "2hncsoy", "5ownv1w", "vgiw7wd", "1vz6t8j", "fr8wpnt",
    "r5141dx", "fw5ztfn", "cfqfgwh", "345ag7a", "tnfk952",
    "aqxy8nu", "3pjc1lm", "f1v9y82", "trg5i2o", "759r9kp",
    "6gt8o9w", "gmapwxa", "14zf8li", "e0mgyib", "tb4ihem"
]



def extract_number(filename):
    """파일명에서 숫자(0~49)를 추출"""
    match = re.search(r'scenchg(\d+)\.png$', filename)
    return int(match.group(1)) if match else None

def upload_to_imgur(image_path):
    """이미지를 Imgur에 업로드하고 URL 반환"""
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    with open(image_path, "rb") as image_file:
        response = requests.post("https://api.imgur.com/3/upload", headers=headers, files={"image": image_file})
    
    if response.status_code == 200:
        return response.json()["data"]["link"]
    else:
        print(f"Upload failed: {response.text}")
        return None

def process_and_upload_images():
    """파일 번호를 기준으로 identifier와 매칭 후 Imgur 업로드 + JSON 저장"""
    uploaded_images = [] 

    image_files = sorted([f for f in os.listdir(IMAGE_FOLDER) if f.startswith("scenchg") and f.endswith(".png")])

    numbered_files = {extract_number(f): f for f in image_files if extract_number(f) is not None}
    
    if len(numbered_files) != len(identifiers):
        print(f"⚠️ 이미지 파일 개수({len(numbered_files)})와 identifier 개수({len(identifiers)})가 일치하지 않습니다!")
        return None

    for i in range(50):  # 0~49에 해당하는 파일만 처리
        if i not in numbered_files:
            print(f"⚠️ scenchg{i}.png 파일이 없습니다!")
            continue

        old_filename = numbered_files[i]
        old_path = os.path.join(IMAGE_FOLDER, old_filename)
        new_filename = f"{identifiers[i]}.png"
        new_path = os.path.join(IMAGE_FOLDER, new_filename)

        os.rename(old_path, new_path)
        print(f"✅ Renamed: {old_filename} → {new_filename}")

        imgur_url = upload_to_imgur(new_path)

        if imgur_url:
            uploaded_images.append({"identifier": identifiers[i], "url": imgur_url})
            print(f"Uploaded: {new_filename} → {imgur_url}")

    with open(JSON_OUTPUT, "w", encoding="utf-8") as json_file:
        json.dump(uploaded_images, json_file, indent=4, ensure_ascii=False)
    
    print(f"\nJSON 저장 완료: {JSON_OUTPUT}")
    return uploaded_images

img_urls = process_and_upload_images()

if img_urls:
    print("\n All Images Uploaded Successfully! JSON 저장 완료 ")
    for item in tqdm(img_urls):
        print(f"identifier: {item['identifier']}, url: {item['url']}")