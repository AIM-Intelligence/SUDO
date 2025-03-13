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
CALCULATE_SCORE_SCRIPT = "./eval/calculate_score.py"
DYNAMIC_ATTACK_SCRIPT = "./dynamic_attack/dynamic_attack.py"
AUTO_SCENECHG_SCRIPT = "./formatter/auto-scene/auto_scnchg.py"
CONVERT_FORMAT_SCRIPT = "./formatter/csv2json/convert_format.py"

# 공격 결과 로그 파일 & 이동 경로
# ATTACK_LOG = "./claude-cua/computer-use-demo/computer_use_demo/log:/home/computeruse/computer_use_demo/log/result.json"
# EVAL_LOG_FOLDER = "./eval/logs/"

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
    dest_path = os.path.join(dest_folder, os.path.basename(src))

    if os.path.exists(src):
        # 목적지에 파일이 이미 존재하면 삭제 후 이동
        if os.path.exists(dest_path):
            os.remove(dest_path)
            print(f"[!] 기존 파일을 삭제했습니다: {dest_path}")

        shutil.move(src, dest_folder)
        print(f"[+] {src} → {dest_folder} 이동 완료")
    else:
        print(f"[!] 파일을 찾지 못했습니다: {src}")

def run_attack_generation():
    """
    1) 공격 JSON 생성 (Scene Change Task 삽입 포함)
    """
    print("[+] 공격 JSON 생성 중...")
    subprocess.run(["python3", ATTACK_SCRIPT], check=True)

def run_formatter(generated_csv, column_name):
    """
    generated_csv: ./attack/result 내부에 존재.
    column_name: CSV → JSON 변환 시 사용하는 column 이름

    1) 생성된 CSV를 formatter로 이동
    2) JSON으로 변환 (파라미터로 컬럼명 전달)
    3) 자동화 가능한 JSON(_auto.json)으로 변환 (파라미터 전달)
    4) cua/.../data 경로로 이동
    """
    # 경로 설정
    formatter_csv_folder = "./formatter/csv2json/csv"
    formatter_json_folder = "./formatter/csv2json/json"
    before_auto_folder = "./formatter/auto-scene/before_auto_scnchg"
    after_auto_folder = "./formatter/auto-scene/after_auto_scnchg"
    data_folder = "./claude-cua/computer-use-demo/computer_use_demo/data/"
    
    print("[+] formatter 실행 중...")

    # 1. CSV 파일 이동
    move_file(generated_csv, formatter_csv_folder)

    base_name = os.path.splitext(os.path.basename(generated_csv))[0]

    # 2. CSV → JSON 변환 (명시적 파일명 및 컬럼 전달)
    subprocess.run([
        "python3", CONVERT_FORMAT_SCRIPT, base_name, column_name
    ], check=True)

    generated_json = os.path.join(formatter_json_folder, base_name + ".json")

    # 3. JSON 파일을 자동화 전 폴더로 이동
    move_file(generated_json, before_auto_folder)

    # 4. 자동화 가능한 JSON(_auto.json)으로 변환 (명시적 파일명 전달)
    subprocess.run([
        "python3", AUTO_SCENECHG_SCRIPT, base_name
    ], check=True)

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

def run_attack(generated_csv="./attack/result/result.csv", column_name="dynamic_response_round_1"):
    """
    (기존 Attack 단계처럼)
    1) 공격 JSON 생성
    2) 자동화
    3) Docker 실행
    """
    run_attack_generation()
    run_formatter(generated_csv, column_name)
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
    subprocess.run(["python3", CALCULATE_SCORE_SCRIPT], check=True)

def run_dynamic_attack():
    """
    평가 결과를 기반으로 동적 공격 생성 (dynamic_attack.py)
    """
    print("[+] Dynamic Attack 생성 중...")
    subprocess.run(["python3", DYNAMIC_ATTACK_SCRIPT], check=True)

def main():
    parser = argparse.ArgumentParser(description="Main Controller for Attack / Docker / Evaluation / Dynamic")
    # action="store_true" 추가적인 값을 받을 수 있는 파라미터,nargs와 함께 쓸 수 없음.
    parser.add_argument("--attack-gen", action="store_true", help="공격 JSON 생성만 수행")
    parser.add_argument("--formatter", nargs=2, metavar=("generated_csv", "column_name"), help="포맷터 실행")
    parser.add_argument("--docker-run", action="store_true", help="Docker 실행만 수행")
    parser.add_argument("--attack", nargs=2, metavar=("generated_csv", "column_name"), help="공격 생성 + 포매터 + Docker 실행")
    parser.add_argument("--evaluate", metavar="attack_log", help="평가 실행")
    parser.add_argument("--dynamic", action="store_true", help="Dynamic Attack 실행")
    parser.add_argument("--all", nargs=3, metavar=("generated_csv", "column_name", "attack_log"), help="전체 파이프라인 실행")

    args = parser.parse_args()
    
    if args.attack_gen:
        run_attack_generation()

    if args.formatter:
        run_formatter(args.formatter[0], args.formatter[1])

    if args.docker_run:
            run_docker_run()

    if args.attack:
        run_attack(args.formatter[0], args.formatter[1])

    if args.evaluate:
        run_evaluation(args.evaluate)

    if args.dynamic:
        run_dynamic_attack()

    if args.all:
        run_attack(args.formatter[0], args.formatter[1])
        run_evaluation(args.formatter[2])
        run_dynamic_attack()

if __name__ == "__main__":
    main()
