import os
import re
import requests
import json
import time
import random
from dotenv import load_dotenv
from tqdm import tqdm
from requests.adapters import HTTPAdapter, Retry

# Imgur API Client ID
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)
CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")

IMAGE_FOLDER = "./attack/screenshot"
JSON_OUTPUT = os.path.join(IMAGE_FOLDER, "img_urls.json")

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
    match = re.search(r'scenchg(\d+)\.png$', filename)
    return int(match.group(1)) if match else None

def upload_to_imgur(image_path):
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    with open(image_path, "rb") as image_file:
        response = requests.post("https://api.imgur.com/3/upload", headers=headers, files={"image": image_file})
    
    if response.status_code == 200:
        return response.json()["data"]["link"]
    else:
        print(f"Upload failed: {response.text}")
        return None

def process_and_upload_images():
    uploaded_images = [] 

    image_files = sorted([f for f in os.listdir(IMAGE_FOLDER) if f.startswith("scenchg") and f.endswith(".png")])

    numbered_files = {extract_number(f): f for f in image_files if extract_number(f) is not None}
    
    if len(numbered_files) != len(identifiers):
        print(f"[!] Number of image files({len(numbered_files)})does not match the number of identifiers ({len(identifiers)})!")
        return None

    for i in range(50): 
        if i not in numbered_files:
            print(f"[!] scenchg{i}.png file not found!")
            continue

        old_filename = numbered_files[i]
        old_path = os.path.join(IMAGE_FOLDER, old_filename)
        new_filename = f"{identifiers[i]}.png"
        new_path = os.path.join(IMAGE_FOLDER, new_filename)

        os.rename(old_path, new_path)
        print(f"[+] Renamed: {old_filename} → {new_filename}")

        imgur_url = upload_to_imgur(new_path)

        if imgur_url:
            uploaded_images.append({"identifier": identifiers[i], "url": imgur_url})
            print(f"Uploaded: {new_filename} → {imgur_url}")

    with open(JSON_OUTPUT, "w", encoding="utf-8") as json_file:
        json.dump(uploaded_images, json_file, indent=4, ensure_ascii=False)
    
    print(f"\n[+] JSON saved successfully: {JSON_OUTPUT}")
    return uploaded_images

img_urls = process_and_upload_images()

if img_urls:
    print("\n [+] All images uploaded successfully! JSON saved successfully.")
    for item in tqdm(img_urls):
        print(f"identifier: {item['identifier']}, url: {item['url']}")