import argparse
import subprocess
import shutil
import os
import re
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
"""
<attack_name> = <model_name>_<tactic>
"""
# ===== 경로 설정 =====
ATTACK_SCRIPT = "./attack/static_attack.py"
EVALUATION_SCRIPT = "./eval/evaluation_json.py"
CALCULATE_SCORE_SCRIPT = "./eval/calculate_score.py"
DYNAMIC_ATTACK_SCRIPT = "./attack/dynamic_attack.py"
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

def copy_file(src, dest_folder):
    """
    src 경로의 파일을 dest_folder로 복사합니다.
    목적지에 동일한 이름의 파일이 있을 경우 삭제 후 새로 복사합니다.
    """
    # 존재하지 않으면 자동 생성
    os.makedirs(dest_folder, exist_ok=True)
    
    dest_path = os.path.join(dest_folder, os.path.basename(src))

    if os.path.exists(src):
        if os.path.exists(dest_path):
            os.remove(dest_path)
            print(f"[!] 기존 파일을 삭제했습니다: {dest_path}")

        shutil.copy2(src, dest_folder)
        print(f"[+] {src} → {dest_folder} 복사 완료")
    else:
        print(f"[!] 파일을 찾지 못했습니다: {src}")

def copy_all_files(src_folder, dest_folder, extension=".json"):
    """
    src_folder 내부에 있는 특정 확장자(extension) 파일들을
    dest_folder에 동일한 이름으로 복사한다.
    목적지에 동일한 파일이 이미 존재하면 삭제한 뒤 새로 복사한다.
    """
    if not os.path.exists(src_folder):
        print(f"[!] 원본 폴더를 찾지 못했습니다: {src_folder}")
        return

    # 목적지 폴더 생성 (없으면 생성)
    os.makedirs(dest_folder, exist_ok=True)

    copied = False
    for file in os.listdir(src_folder):
        if file.endswith(extension):
            src_file = os.path.join(src_folder, file)
            dest_file = os.path.join(dest_folder, file)

            if os.path.exists(dest_file):
                os.remove(dest_file)
                print(f"[!] 기존 파일 삭제: {dest_file}")

            shutil.copy2(src_file, dest_file)
            print(f"[+] {src_file} → {dest_file} 복사 완료")
            copied = True

    if not copied:
        print(f"[!] {src_folder}에 복사할 '{extension}' 파일이 없습니다.")

def get_attack_response_path(attack_name: str) -> str:
    if "static" in attack_name:
        return "attack_result_new"
    elif "dynamic" in attack_name:
        return "dynamic_response_round_1"
    else:
        return "unknown_attack_type"

def run_attack_generation(attack_name):
    """
    1) 공격 JSON 생성 (Scene Change Task 삽입 포함)
    """
    print("[+] 공격 JSON 생성 중...")
    model_name = "_".join(attack_name.split("_")[:-1])
    subprocess.run(["python3", ATTACK_SCRIPT,attack_name, model_name], check=True)

def run_formatter(attack_name):
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
    
    column_name = get_attack_response_path(attack_name)

    print("[+] formatter 실행 중...")

    # 1. CSV 파일 이동
    copy_file(f"{attack_result_folder}/{attack_name}.csv", formatter_csv_folder)

    #base_name = os.path.splitext(os.path.basename(generated_csv))[0]

    # 2. CSV → JSON 변환 (명시적 파일명 및 컬럼 전달)
    subprocess.run([
        "python3", CONVERT_FORMAT_SCRIPT, attack_name, column_name
    ], check=True)

    generated_json = os.path.join(formatter_json_folder, attack_name + ".json")

    # 3. JSON 파일을 자동화 전 폴더로 이동
    copy_file(generated_json, before_auto_folder)

    # 4. 자동화 가능한 JSON(_auto.json)으로 변환 (명시적 파일명 전달)
    subprocess.run([
        "python3", AUTO_SCENECHG_SCRIPT, attack_name
    ], check=True)

    automatic_json = os.path.join(after_auto_folder, attack_name + "_auto.json")

    # 5. 최종 JSON을 claude-cua data 폴더로 이동
    copy_file(automatic_json, data_folder)


def run_docker_run():
    """
    claude-cua/computer-use-demo 폴더로 이동한 뒤, Docker 명령 실행
    """
    print("[+] Docker 실행 중...")
    docker_cmd_str = " ".join(DOCKER_COMMAND)
    # shell=True 로 서브셸에서 docker run ...을 실행
    subprocess.run(docker_cmd_str, shell=True, check=True)

def run_attack(attack_name):
    """
    (기존 Attack 단계처럼)
    1) 공격 JSON 생성
    2) 자동화
    3) Docker 실행
    """
    column_name = get_attack_response_path(attack_name)
    run_attack_generation()
    run_formatter(attack_name, column_name)
    run_docker_run()

def run_evaluation(attack_name):
    """
    Input: attack_log_folder - 
    평가 시작:
    1) attack_log_folder 내 JSON 결과 로그 파일들을 eval/logs/[폴더명]으로 이동
    2) 평가 및 점수 계산 스크립트 실행
    """
    print("[+] 평가 시작...")
    attack_log_folder = f"./claude-cua/computer-use-demo/computer_use_demo/log/{attack_name}"
    eval_log_folder = f"./eval/logs/{attack_name}"
    
    copy_all_files(attack_log_folder, eval_log_folder, extension=".json")

    subprocess.run(["python3", EVALUATION_SCRIPT, attack_name], check=True)
    subprocess.run(["python3", CALCULATE_SCORE_SCRIPT, attack_name], check=True)

def get_next_dynamic_name(model_name: str) -> str:
    """
    ./attack/result/ 디렉터리에 model_name_dynamic(n).csv 형태로 저장된 파일 중
    가장 큰 n 값을 찾아 n+1이 된 파일명를 반환한다.
    만약 해당 형태의 파일이 없다면 n=1을 사용한다.
    """
    dir_path = "./attack/result"
    pattern = re.compile(rf"^{re.escape(model_name)}_dynamic-r(\d+)\.csv$")

    max_n = 0
    for filename in os.listdir(dir_path):
        match = pattern.match(filename)
        if match:
            current_n = int(match.group(1))
            if current_n > max_n:
                max_n = current_n
    if max_n == 0:
        return f"{model_name}_dynamic-r1"
    else:
        return f"{model_name}_dynamic-r{max_n + 1}"

def run_dynamic_attack(attack_name):
    """
    평가 결과를 기반으로 동적 공격 생성 (dynamic_attack.py)
    """
    eval_log_folder = f"./eval/results/{attack_name}/scores"
    feedback_folder = f"./attack/feedback/{attack_name}" 
    
    copy_all_files(eval_log_folder, feedback_folder, extension=".json")

    csv_file_path =  f"./attack/result/{attack_name}.csv"
    model_name = "_".join(attack_name.split("_")[:-1])

    current_attack_name = get_next_dynamic_name(model_name)
    output_csv_path = f"./attack/result/{current_attack_name}.csv"
    
    print("[+] Dynamic Attack 생성 중...")
    subprocess.run(["python3", DYNAMIC_ATTACK_SCRIPT,csv_file_path, output_csv_path, feedback_folder], check=True)

def main():
    parser = argparse.ArgumentParser(description="Main Controller for Attack / Docker / Evaluation / Dynamic")
    # action="store_true" 추가적인 값을 받을 수 있는 파라미터,nargs와 함께 쓸 수 없음.
    parser.add_argument("--attack-gen", nargs=1, metavar=("attack_name"), help="공격 JSON 생성만 수행")
    parser.add_argument("--formatter", nargs=1, metavar=("attack_name"), help="포맷터 실행")
    parser.add_argument("--docker-run", action="store_true", help="Docker 실행만 수행")
    parser.add_argument("--attack",  nargs=1, metavar=("attack_name"), help="공격 생성 + 포매터 + Docker 실행")
    parser.add_argument("--evaluate",nargs=1, metavar="attack_name", help="평가 실행")
    parser.add_argument("--dynamic", nargs=1, metavar=("attack_name"), help="Dynamic Attack 실행")
    parser.add_argument("--all", nargs=1, metavar=("attack_name"), help="전체 파이프라인 실행")

    args = parser.parse_args()
    
    if args.attack_gen:
        run_attack_generation(args.attack_gen[0])

    if args.formatter:
        run_formatter(args.formatter[0])

    if args.docker_run:
            run_docker_run()

    if args.attack:
        run_attack(args.formatter[0])

    if args.evaluate:
        run_evaluation(args.evaluate[0])

    if args.dynamic:
        run_dynamic_attack(args.dynamic[0])

    if args.all:
        run_attack(args.all[0]) 
        run_evaluation(args.all[0]) # subprocess.run -> docker 종료 직후 시작
        run_dynamic_attack(args.all[0])
        current_attack_name = get_next_dynamic_name(args.all[0])
        run_formatter(current_attack_name)
        #run_docker_run()
        #run_evaluation(current_attack_name)
if __name__ == "__main__":
    main()
