# SUDO rm -rf Agentic_Security

## Attack Generation

## Automatic attack
아직 옮기는 건 직접해야 함.
1. 공격 json 파일에 scene change task를 중간에 끼워넣기(Aimagent 폴더)
2. computer-use-demo/computer_use_demo/data 위치에 공격 json 파일 옮기기
3. docker run
### Docker command

docker run \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $(pwd)/computer_use_demo:/home/computeruse/computer_use_demo/ \
    -v /home/jiankim/project/aim/sudo/ClaudeAgenticSecurity/computer-use-demo/computer_use_demo/data:/home/computeruse/computer_use_demo/data \
    -v /home/jiankim/project/aim/sudo/ClaudeAgenticSecurity/computer-use-demo/computer_use_demo/log:/home/computeruse/computer_use_demo/log \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it sudo-cua:local

4. log 폴더에 attack result log json이 생김

## Evaluation
1. Evaluation log 폴더로 옮기기
2. 평가
3. 수치 자동 계산

## Dynamic Attack Generation
1. 결과가 Dynamic attack으로 이어지게 하기.