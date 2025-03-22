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
ATTACK_SCRIPT = "./attack/static_attack.py"
EVALUATION_SCRIPT = "./eval/evaluation_json.py"
CALCULATE_SCORE_SCRIPT = "./eval/calculate_score.py"
DYNAMIC_ATTACK_SCRIPT = "./attack/dynamic_attack.py"
AUTO_SCENECHG_SCRIPT = "./formatter/auto-scene/auto_scnchg.py"
CONVERT_FORMAT_SCRIPT = "./formatter/csv2json/convert_format.py"

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
    os.makedirs(dest_folder, exist_ok=True)
    
    dest_path = os.path.join(dest_folder, os.path.basename(src))

    if os.path.exists(src):
        if os.path.exists(dest_path):
            os.remove(dest_path)
            print(f"[!] Existing file deleted: {dest_path}")

        shutil.copy2(src, dest_folder)
        print(f"[+] {src} → {dest_folder} Copy completed")
    else:
        print(f"[!] File not found: {src}")

def copy_all_files(src_folder, dest_folder, extension=".json"):
 
    if not os.path.exists(src_folder):
        print(f"[!] Original folder not found: {src_folder}")
        return

    os.makedirs(dest_folder, exist_ok=True)

    copied = False
    for file in os.listdir(src_folder):
        if file.endswith(extension):
            src_file = os.path.join(src_folder, file)
            dest_file = os.path.join(dest_folder, file)

            if os.path.exists(dest_file):
                os.remove(dest_file)
                print(f"[!] Existing file deleted: {dest_file}")

            shutil.copy2(src_file, dest_file)
            print(f"[+] {src_file} → {dest_file} Copy completed")
            copied = True

    if not copied:
        print(f"[!] No '{extension}' files to copy in {src_folder}.")

def get_attack_response_path(attack_name: str) -> str:
    if "static" in attack_name:
        return "static_response"
    match = re.search(r"dynamic-r(\d+)", attack_name)
    if match:
        dynamic_num = match.group(1)  #
        return f"dynamic_response_round_{dynamic_num}"
    return "unknown_attack_type"

def run_attack_generation(attack_name):

    print("[+] Generating attack JSON...")
    model_name = "_".join(attack_name.split("_")[:-1])
    subprocess.run(["python3", ATTACK_SCRIPT,attack_name, model_name], check=True)

def run_formatter(attack_name):
    attack_result_folder = "./attack/result"
    formatter_csv_folder = "./formatter/csv2json/csv"
    formatter_json_folder = "./formatter/csv2json/json"
    before_auto_folder = "./formatter/auto-scene/before_auto_scnchg"
    after_auto_folder = "./formatter/auto-scene/after_auto_scnchg"
    data_folder = "./claude-cua/computer-use-demo/computer_use_demo/data/"
    
    column_name = get_attack_response_path(attack_name)

    print("[+] Running formatter...")

    copy_file(f"{attack_result_folder}/{attack_name}.csv", formatter_csv_folder)
    subprocess.run([
        "python3", CONVERT_FORMAT_SCRIPT, attack_name, column_name
    ], check=True)

    generated_json = os.path.join(formatter_json_folder, attack_name + ".json")

    copy_file(generated_json, before_auto_folder)

    subprocess.run([
        "python3", AUTO_SCENECHG_SCRIPT, attack_name
    ], check=True)

    automatic_json = os.path.join(after_auto_folder, attack_name + "_auto.json")

    copy_file(automatic_json, data_folder)


def run_docker_run():

    print("[+] Running Docker...")
    docker_cmd_str = " ".join(DOCKER_COMMAND)
    subprocess.run(docker_cmd_str, shell=True, check=True)

def run_attack(attack_name):
    column_name = get_attack_response_path(attack_name)
    run_attack_generation()
    run_formatter(attack_name, column_name)
    run_docker_run()

def run_evaluation(attack_name):
    print("[+] Evaluation started...")
    attack_log_folder = f"./claude-cua/computer-use-demo/computer_use_demo/log/{attack_name}"
    eval_log_folder = f"./eval/logs/{attack_name}"
    
    copy_all_files(attack_log_folder, eval_log_folder, extension=".json")

    subprocess.run(["python3", EVALUATION_SCRIPT, attack_name], check=True)
    subprocess.run(["python3", CALCULATE_SCORE_SCRIPT, attack_name], check=True)

def get_next_dynamic_name(model_name: str) -> str:
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
        return max_n, f"{model_name}_dynamic-r1"
    else:
        return max_n, f"{model_name}_dynamic-r{max_n + 1}"

def run_dynamic_attack(attack_name):
    eval_log_folder = f"./eval/results/{attack_name}/scores"
    feedback_folder = f"./attack/feedback/{attack_name}" 
    
    copy_all_files(eval_log_folder, feedback_folder, extension=".json")

    csv_file_path =  f"./attack/result/{attack_name}.csv"
    model_name = "_".join(attack_name.split("_")[:-1])

    dynamic_num, current_attack_name = get_next_dynamic_name(model_name)
    output_csv_path = f"./attack/result/{current_attack_name}.csv"
    
    print("[+] Generating Dynamic Attack...")
    subprocess.run(["python3", DYNAMIC_ATTACK_SCRIPT,csv_file_path, output_csv_path, feedback_folder, str(int(dynamic_num))], check=True)

def main():
    parser = argparse.ArgumentParser(description="Main Controller for Attack / Docker / Evaluation / Dynamic")
    parser.add_argument("--attack-gen", nargs=1, metavar=("attack_name"), help="Static attack JSON generation")
    parser.add_argument("--formatter", nargs=1, metavar=("attack_name"), help="Run formatter")
    parser.add_argument("--docker-run", action="store_true", help="Just run Docker")
    parser.add_argument("--attack",  nargs=1, metavar=("attack_name"), help="Create attack + formatter + run Docker")
    parser.add_argument("--evaluate",nargs=1, metavar="attack_name", help="Evaluation execution")
    parser.add_argument("--dynamic", nargs=1, metavar=("attack_name"), help="Dynamic attack JSON generation")
    parser.add_argument("--all", nargs=1, metavar=("attack_name"), help="Run the entire pipeline")

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
        run_evaluation(args.all[0]) 
        run_dynamic_attack(args.all[0])
        current_attack_name = get_next_dynamic_name(args.all[0])
        run_formatter(current_attack_name)
        run_docker_run()
        run_evaluation(current_attack_name)
if __name__ == "__main__":
    main()
