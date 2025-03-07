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

# 공격 결과 로그 파일 & 이동 경로
ATTACK_LOG = "./attack/result.json"
EVAL_LOG_FOLDER = "./eval/logs/"

# ===== Docker 실행 명령어 =====
DOCKER_COMMAND = [
    "docker", "run",
    "-e", f"ANTHROPIC_API_KEY={ANTHROPIC_KEY}",
    "-v", f"{os.getcwd()}/computer-use-demo:/home/computeruse/computer_use_demo/",
    "-v", f"{os.getcwd()}/claude-cua/computer-use-demo/computer_use_demo/data:/home/computeruse/computer_use_demo/data",
    "-v", f"{os.getcwd()}/claude-cua/computer-use-demo/computer_use_demo/log:/home/computeruse/computer_use_demo/log",
    "-v", "$HOME/.anthropic:/home/computeruse/.anthropic",
    "-p", "5900:5900",
    "-p", "8501:8501",
    "-p", "6080:6080",
    "-p", "8080:8080",
    "-it", "sudo-cua:local"
]

def run_attack_generation():
    """
    1) 공격 JSON 생성 (Scene Change Task 삽입 포함)
    2) 생성된 JSON을 `computer-use-demo/computer_use_demo/data`로 이동
    """
    print("[+] 공격 JSON 생성 중...")
    subprocess.run(["python3", ATTACK_SCRIPT], check=True)

    # 생성된 공격 JSON 예: ./attack/generated_attack.json
    generated_json = "./attack/generated_attack.json"
    data_folder = "./computer-use-demo/computer_use_demo/data/"

    if os.path.exists(generated_json):
        shutil.move(generated_json, data_folder)
        print(f"[+] {generated_json} → {data_folder} 이동 완료")
    else:
        print("[!] 공격 JSON 파일을 찾지 못했습니다. 경로를 확인하세요.")

def run_docker_run():
    """
    claude-cua/computer-use-demo 폴더로 이동한 뒤, Docker 명령 실행
    """
    print("[+] Docker 실행 중...")

    # (1) cd claude-cua/computer-use-demo
    # (2) DOCKER_COMMAND 실행
    docker_cmd_str = "cd claude-cua/computer-use-demo && " + " ".join(DOCKER_COMMAND)

    # shell=True 로 서브셸에서 cd + docker를 순차 실행
    subprocess.run(docker_cmd_str, shell=True, check=True)

def run_attack():
    """
    (기존 Attack 단계처럼)
    1) 공격 JSON 생성
    2) Docker 실행
    """
    run_attack_generation()
    run_docker_run()

def run_evaluation():
    """
    1) attack/result.json → eval/logs 폴더로 이동
    2) 평가 스크립트 실행 (evaluation_json.py)
    """
    print("[+] 평가 시작...")

    if os.path.exists(ATTACK_LOG):
        shutil.move(ATTACK_LOG, EVAL_LOG_FOLDER)
        print(f"[+] {ATTACK_LOG} → {EVAL_LOG_FOLDER} 이동 완료")
    else:
        print("[!] 공격 결과 파일(result.json)을 찾지 못했습니다.")

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
