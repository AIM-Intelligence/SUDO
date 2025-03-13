import argparse
import subprocess
import shutil
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ===== 경로 설정 =====
ATTACK_SCRIPT = "./attack/attack_generation.py"
EVALUATION_SCRIPT = "./eval/evaluation_json.py"
DYNAMIC_ATTACK_SCRIPT = "./dynamic_attack/dynamic_attack.py"
AUTO_SCENECHG_SCRIPT = "./formatter/auto-scene/auto_scnchg.py"
CONVERT_FORMAT_SCRIPT = "./formatter/csv2json/convert_format.py"

# 공격 결과 로그 파일 & 이동 경로
ATTACK_LOG = "./claude-cua/computer-use-demo/computer_use_demo/log:/home/computeruse/computer_use_demo/log/result.json"
EVAL_LOG_FOLDER = "./eval/logs/"

# ===== Docker 실행 명령어 =====
DOCKER_COMMAND = [
    "docker", "run",
    "-e", f"ANTHROPIC_API_KEY={ANTHROPIC_KEY}",
    "-v", f"{os.getcwd()}/claude-cua/computer-use-demo/computer_use_demo:/home/computeruse/computer_use_demo/",
    "-v", f"{os.getcwd()}/claude-cua/computer-use-demo/computer_use_demo/data:/home/computeruse/computer_use_demo/data",
    "-v", f"{os.getcwd()}/claude-cua/computer-use-demo/computer_use_demo/log:/home/computeruse/computer_use_demo/log",
    "-v", "$HOME/.anthropic:/home/computeruse/.anthropic",
    "-p", "5900:5900",
    "-p", "8501:8501",
    "-p", "6080:6080",
    "-p", "8080:8080",
    "-it", "sudo-cua:local"
]

def move_file(src, dest_folder):
    """
    src 파일을 dest_folder로 이동하는 함수
    """
    if os.path.exists(src):
        shutil.move(src, dest_folder)
        print(f"[+] {src} → {dest_folder} 이동 완료")
        return True
    else:
        print(f"[!] 파일을 찾지 못했습니다: {src}")
        return False

def run_attack_generation():
    """
    1) 공격 JSON 생성 (Scene Change Task 삽입 포함)
    """
    print("[+] 공격 JSON 생성 중...")
    subprocess.run(["python3", ATTACK_SCRIPT], check=True)

def run_fommatter(generated_csv): #확장자로 공격이 생성된 column 이름 필요, 각 스크립트 원본 폴더 파라미터 빼기 필요.
    """
    generated_csv: ./attack/result 내부에 존재.
    1) 생성된 CSV를 formatter로 이동
    2) JSON으로 변환
    3) 자동화 가능한 JSON(_auto.json)으로 변환
    4) cua/.../data 경로로 이동
    """
    # 경로 설정
    formatter_csv_folder = "./formatter/csv2json/csv"
    before_auto_folder = "./formatter/auto-scene/before_auto_scnchg"
    after_auto_folder = "./formatter/auto-scene/after_auto_scnchg"
    data_folder = "./computer-use-demo/computer_use_demo/data/"
    print("[+] formatter 실행 중...")
     # 1. CSV 파일 이동
    move_file(generated_csv, formatter_csv_folder)

    # 2. CSV → JSON 변환
    subprocess.run(["python3", CONVERT_FORMAT_SCRIPT], check=True)

    # 변환된 json 파일명 얻기
    base_name = os.path.splitext(os.path.basename(generated_csv))[0]
    generated_json = os.path.join(formatter_csv_folder, base_name + ".json")

    # 3. JSON 파일을 자동화 전 폴더로 이동
    move_file(generated_json, before_auto_folder)

    # 4. 자동화 가능한 JSON(_auto.json)으로 변환
    subprocess.run(["python3", AUTO_SCENECHG_SCRIPT], check=True)

    # 자동화된 JSON 파일명
    automatic_json = os.path.join(after_auto_folder, base_name + "_auto.json")

    # 5. 최종 JSON을 data 폴더로 이동
    move_file(automatic_json, data_folder)

def run_docker_run():
    """
    claude-cua/computer-use-demo 폴더로 이동한 뒤, Docker 명령 실행
    """
    print("[+] Docker 실행 중...")
    docker_cmd_str = " ".join(DOCKER_COMMAND)
    # shell=True 로 서브셸에서 docker run ...을 실행
    subprocess.run(docker_cmd_str, shell=True, check=True)

def run_attack():
    """
    (기존 Attack 단계처럼)
    1) 공격 JSON 생성
    2) 자동화
    3) Docker 실행
    """
    run_attack_generation()
    run_fommatter()
    run_docker_run()

def run_evaluation(attack_log): #attack_log = "./claude-cua/computer-use-demo/computer_use_demo/log:/home/computeruse/computer_use_demo/log/result.json"
    """
    1) attack/result.json → eval/logs 폴더로 이동
    2) 평가 스크립트 실행 (evaluation_json.py)
    """
    print("[+] 평가 시작...")
    eval_log_folder = "./eval/logs/"
    move_file(attack_log, eval_log_folder)
    # 평가 스크립트 실행
    subprocess.run(["python3", EVALUATION_SCRIPT], check=True)

def run_dynamic_attack():
    """
    평가 결과를 기반으로 동적 공격 생성 (dynamic_attack.py)
    """
    print("[+] Dynamic Attack 생성 중...")
    subprocess.run(["python3", DYNAMIC_ATTACK_SCRIPT], check=True)

def main():
    parser = argparse.ArgumentParser(description="Main Controller for Attack / Docker / Evaluation / Dynamic")
    # 공격 관련
    parser.add_argument("--attack-gen", action="store_true", help="공격 JSON 생성만 수행")
    parser.add_argument("--docker-run", action="store_true", help="Docker 실행만 수행")
    parser.add_argument("--attack", action="store_true", help="공격 생성 + Docker 실행 (연속)")

    # 평가, Dynamic Attack
    parser.add_argument("--evaluate", action="store_true", help="평가 실행")
    parser.add_argument("--dynamic", action="store_true", help="Dynamic Attack 실행")

    # 전체 파이프라인
    parser.add_argument("--all", action="store_true", help="Attack (JSON+Docker) → Evaluate → Dynamic 순서 전체 실행")

    args = parser.parse_args()

    if args.all:
        run_attack()
        run_evaluation()
        run_dynamic_attack()
    else:
        if args.attack_gen:
            run_attack_generation()

        if args.docker_run:
            run_docker_run()

        if args.attack:
            run_attack()

        if args.evaluate:
            run_evaluation()

        if args.dynamic:
            run_dynamic_attack()

if __name__ == "__main__":
    main()
