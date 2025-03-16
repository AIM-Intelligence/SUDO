import ollama
import os

# ✅ 이미지 경로 설정
image_path = "/home/jiankim/project/aim/agentic_security/sudo/sudo_figure.png"

# ✅ 이미지 파일 확인
if not os.path.exists(image_path):
    raise FileNotFoundError(f"[X] 이미지 파일이 존재하지 않습니다: {image_path}")

# ✅ Ollama 모델 실행
response = ollama.chat(
    model='llama3.2-vision',
    messages=[{
        'role': 'user',
        'content': 'What is in this image?',
        'images': [image_path]  # ✅ 절대 경로 사용
    }]
)

# ✅ 결과 출력
print(response)
