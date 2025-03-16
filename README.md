# sudo rm -rf agentic_security

This repository is a system that manages automatic attack generation, evaluation, and dynamic attack creation for computer use agents in one place. It executes attack scenarios in a Docker environment, automatically organizes the results, evaluates them, and simplifies the process of generating dynamic attacks.

![SUDO Attack Framework Architecture](sudo_figure.png)
---

## Table of Contents

1. [Overview](#overview)  
2. [Folder Structure](#folder-structure)  
3. [Prerequisites](#prerequisites)  
4. [Usage](#usage)  
5. [Detailed Workflow](#detailed-workflow)  
6. [Notes](#notes)  

---

## Overview

- **Attack Generation**:  
Detox2tox (Static) is a pipeline that transforms a malicious instruction into a detoxed task to avoid safety guardrails, obtains a plan from a well-aligned model, and then reintroduces the malicious details at the final step—preserving the original harmful goal while stealthily bypassing these defenses.

  Generates attack JSON files and inserts the **Scene Change Task**.  
  The resulting files are copied to the `./claude-cua/.../data/` folder.  
  Subsequently, attacks are executed using **Docker** to generate logs.

- **Evaluation**:  
  Moves generated logs to `./eval/logs/` for evaluation.  
  Performs numeric calculations and evaluations.

- **Dynamic Attack**:  
  Generates additional **Dynamic Attacks** based on evaluation results.

All steps are automated using a single script: **`main.py`**.

---

## Folder Structure (needs revision)

```plaintext
sudo
├── main.py                # Main script managing the entire pipeline
├── attack
│   ├── attack_generation.py
│   └── result.json        # Attack result logs generated after Docker execution
├── claude-cua
│   └── computer-use-demo
│       └── computer_use_demo
│           ├── data       # Folder where attack JSON files are moved
│           └── log        # Logs generated within Docker
├── eval
│   ├── evaluation_json.py # Evaluation logic (log files → extract scores)
│   ├── calculate_score.py # Evaluation logic (scores → numeric calculations)
│   └── logs               # Final storage of attack logs (for evaluation)
├── dynamic_attack
│   └── dynamic_attack.py  # Handles dynamic attack generation
├── formatter
│   ├── auto-scene
│   └── csv2json
│       └── convert_format.py
├── .env                   
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md              # This file
```

**Note:** Ensure that Docker mount paths (`-v` option) correctly match the local folder structure (currently applied).

## Prerequisites
0. `conda create -n sudo python=3.10`
1. Install required packages:
```bash
pip install -r requirements.txt
```
2. Docker installation  
Docker must be installed and the `docker run` command should be executable from the command line.
3. Environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`)  
Set API keys for use within `.env` file:
4. Run the file "./formatter/auto-scene/harmGUI_scnchg.json" using claude-cua, capture screenshots of each task's starting point, and place them in the "./attack/screenshot/" directory. Each screenshot filename should match the corresponding task's identifier.(c.f. `formatter/origin_img2url.py`)
5. Before attacking the computer use agent, create a Victim account and log in as Attacker.

## Usage
The `main.py` script supports separate execution of Attack Generation, Evaluation, and Dynamic Attack or can execute all processes sequentially.

Main arguments:
```python
attack_name = f"{model_name}_{tactic}"  # e.g., o1_static, o1_dynamic-r1
```

1. Execute only Static Attack:

* Integrated command (includes all steps below):
```bash
python main.py --attack <attack_name>
```
* Individual steps (manual execution):
```bash
python main.py --attack-gen <attack_name>
python main.py --formatter <attack_name>  
python main.py --docker-run 
```
- Generate attack JSON (with Scene Change Task inserted).
- Move the generated JSON to `computer_use_demo/data`.
- Execute Docker (logs created in `claude-cua/computer-use-demo/computer_use_demo/log`).

2. Execute only Evaluation:
```bash
python main.py --evaluate <attack_name> 
```
- Move Docker results (`attack/result.json`) to `eval/logs`.
- Run `evaluation_json.py` script for numeric calculations.

3. Execute only Dynamic Attack:
```bash
python3 main.py --dynamic <attack_name> 
```
- Generate Dynamic Attacks based on evaluation results (`eval/logs`).

4. Run the full pipeline automatically (Attack → Evaluate → Dynamic):
```bash
python main.py --all <attack_name>
```
- Automatically executes Attack Generation → Attack Execution → Evaluation → Dynamic Attack in order.

## Detailed Workflow
1. **Attack Generation**
   - `attack_generation.py` generates attack JSON files, inserting Scene Change Tasks (use formatter/auto-scene if necessary).
   - Automatically moves the completed JSON files to `computer-use-demo/computer_use_demo/data`.

2. **Docker Container Execution**
   - Docker execution is handled by `main.py` in the `run_attack()` step.
   - Performs actual attack simulations based on the JSON files.
   - Attack logs (`result.json`) are stored in the `attack` folder or logged to `claude-cua/computer-use-demo/computer_use_demo/log`.

3. **Evaluation**
   - Triggered by `main.py` with the evaluation step (`--evaluate`).
   - Automatically moves `attack/result.json` to `eval/logs`.
   - Runs `evaluation_json.py` to perform evaluations and numeric calculations.

4. **Dynamic Attack**
   - `dynamic_attack/dynamic_attack.py` creates dynamic attacks based on evaluation results.

## Notes
- Ensure Docker mount paths match local directory structures:
```bash
docker run -v $(pwd)/...:/home/...
```
- Confirm that the `ANTHROPIC_API_KEY` is properly passed. If necessary, pass environment variables directly to `subprocess.run()` instead of using `shell=True`.

## License and Contribution
- This project follows the guidelines specified in the LICENSE file.
- Feel free to submit bug reports, feature requests, or pull requests.