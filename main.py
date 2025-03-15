import argparse
import subprocess
import shutil
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ===== 경로 설정 =====
ATTACK_SCRIPT = "./attack/static_attack.py"
EVALUATION_SCRIPT = "./eval/evaluation_json.py"
CALCULATE_SCORE_SCRIPT = "./eval/calculate_score.py"
DYNAMIC_ATTACK_SCRIPT = "./dynamic_attack/dynamic_attack.py"
AUTO_SCENECHG_SCRIPT = "./formatter/auto-scene/auto_scnchg.py"
CONVERT_FORMAT_SCRIPT = "./formatter/csv2json/convert_format.py"

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

def move_all_files(src_folder, dest_folder, extension=".json"):
    """
    src 폴더 내 모든 특정 확장자 파일을 dest_folder의 동일한 폴더명으로 이동
    """
    if not os.path.exists(src_folder):
        print(f"[!] 원본 폴더를 찾지 못했습니다: {src_folder}")
        return

    # 원본 폴더의 폴더명 추출
    subfolder_name = os.path.basename(src_folder.rstrip('/'))
    final_dest_folder = os.path.join(dest_folder, subfolder_name)

    os.makedirs(final_dest_folder, exist_ok=True)

    moved = False
    for file in os.listdir(src_folder):
        if file.endswith(extension):
            src_file = os.path.join(src_folder, file)
            dest_file = os.path.join(final_dest_folder, file)

            if os.path.exists(dest_file):
                os.remove(dest_file)
                print(f"[!] 기존 파일 삭제: {dest_file}")

            shutil.move(src_file, final_dest_folder)
            print(f"[+] {src_file} → {final_dest_folder} 이동 완료")
            moved = True
    
    if not moved:
        print(f"[!] {src_folder}에 이동할 {extension} 파일이 없습니다.")



def run_attack_generation(attack_name, model_name):
    """
    1) 공격 JSON 생성 (Scene Change Task 삽입 포함)
    """
    print("[+] 공격 JSON 생성 중...")
    subprocess.run(["python3", ATTACK_SCRIPT,attack_name, model_name], check=True)

def run_formatter(attack_name, column_name):
    """
    generated_csv: ./attack/result 내부에 존재.
    column_name: CSV → JSON 변환 시 사용하는 column 이름

    1) 생성된 CSV를 formatter로 이동
    2) JSON으로 변환 (파라미터로 컬럼명 전달)
    3) 자동화 가능한 JSON(_auto.json)으로 변환 (파라미터 전달)
    4) cua/.../data 경로로 이동
    """
    # 경로 설정
    attack_result_folder = "./attack/result"
    formatter_csv_folder = "./formatter/csv2json/csv"
    formatter_json_folder = "./formatter/csv2json/json"
    before_auto_folder = "./formatter/auto-scene/before_auto_scnchg"
    after_auto_folder = "./formatter/auto-scene/after_auto_scnchg"
    data_folder = "./claude-cua/computer-use-demo/computer_use_demo/data/"
    
    print("[+] formatter 실행 중...")

    # 1. CSV 파일 이동
    move_file(f"{attack_result_folder}/{attack_name}.csv", formatter_csv_folder)

    #base_name = os.path.splitext(os.path.basename(generated_csv))[0]

    # 2. CSV → JSON 변환 (명시적 파일명 및 컬럼 전달)
    subprocess.run([
        "python3", CONVERT_FORMAT_SCRIPT, attack_name, column_name
    ], check=True)

    generated_json = os.path.join(formatter_json_folder, attack_name + ".json")

    # 3. JSON 파일을 자동화 전 폴더로 이동
    move_file(generated_json, before_auto_folder)

    # 4. 자동화 가능한 JSON(_auto.json)으로 변환 (명시적 파일명 전달)
    subprocess.run([
        "python3", AUTO_SCENECHG_SCRIPT, attack_name
    ], check=True)

    automatic_json = os.path.join(after_auto_folder, attack_name + "_auto.json")

    # 5. 최종 JSON을 claude-cua data 폴더로 이동
    move_file(automatic_json, data_folder)


def run_docker_run():
    """
    claude-cua/computer-use-demo 폴더로 이동한 뒤, Docker 명령 실행
    """
    print("[+] Docker 실행 중...")
    docker_cmd_str = " ".join(DOCKER_COMMAND)
    # shell=True 로 서브셸에서 docker run ...을 실행
    subprocess.run(docker_cmd_str, shell=True, check=True)

def run_attack(attack_name, column_name="dynamic_response_round_1"):
    """
    (기존 Attack 단계처럼)
    1) 공격 JSON 생성
    2) 자동화
    3) Docker 실행
    """
    run_attack_generation()
    run_formatter(attack_name, column_name)
    run_docker_run()

def run_evaluation(log_folder):
    """
    Input: attack_log_folder - 
    평가 시작:
    1) attack_log_folder 내 JSON 결과 로그 파일들을 eval/logs/[폴더명]으로 이동
    2) 평가 및 점수 계산 스크립트 실행
    """
    print("[+] 평가 시작...")
    attack_log_folder = f"./claude-cua/computer-use-demo/computer_use_demo/log/{log_folder}"
    eval_log_folder = "./eval/logs/"

    move_all_files(attack_log_folder, eval_log_folder, extension=".json")

    subprocess.run(["python3", EVALUATION_SCRIPT, log_folder], check=True)
    subprocess.run(["python3", CALCULATE_SCORE_SCRIPT, log_folder], check=True)

def run_dynamic_attack():
    """
    평가 결과를 기반으로 동적 공격 생성 (dynamic_attack.py)
    """
    print("[+] Dynamic Attack 생성 중...")
    subprocess.run(["python3", DYNAMIC_ATTACK_SCRIPT], check=True)

def main():
    parser = argparse.ArgumentParser(description="Main Controller for Attack / Docker / Evaluation / Dynamic")
    # action="store_true" 추가적인 값을 받을 수 있는 파라미터,nargs와 함께 쓸 수 없음.
    parser.add_argument("--attack-gen", nargs=2, metavar=("attack_name", "model_name"), help="공격 JSON 생성만 수행")
    parser.add_argument("--formatter", nargs=2, metavar=("attack_name", "column_name"), help="포맷터 실행")
    parser.add_argument("--docker-run", action="store_true", help="Docker 실행만 수행")
    parser.add_argument("--attack",  nargs=2, metavar=("attack_name", "column_name"), help="공격 생성 + 포매터 + Docker 실행")
    parser.add_argument("--evaluate",nargs=1, metavar="log_folder", help="평가 실행")
    parser.add_argument("--dynamic", action="store_true", help="Dynamic Attack 실행")
    parser.add_argument("--all", nargs=2, metavar=("attack_name", "column_name"), help="전체 파이프라인 실행")

    args = parser.parse_args()
    
    if args.attack_gen:
        run_attack_generation(args.attack_gen[0], args.attack_gen[1])

    if args.formatter:
        run_formatter(args.formatter[0], args.formatter[1])

    if args.docker_run:
            run_docker_run()

    if args.attack:
        run_attack(args.formatter[0], args.formatter[1])

    if args.evaluate:
        run_evaluation(args.evaluate[0])

    if args.dynamic:
        run_dynamic_attack()

    if args.all:
        run_attack(args.all[0], args.all[1]) 
        run_evaluation(args.all[0]) # subprocess.run -> docker 종료 직후 시작
        run_dynamic_attack()

if __name__ == "__main__":
    main()
