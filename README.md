### 설치 방법 (둘중 하나 선택하시면 됩니다.)
1. pip install uv 한뒤 실행 명령어를 입력하면 됩니다. (간단한 버전)
2. direnv 및 nix 설치 후 프로젝트 루트에서 direnv allow . 입력하고 실행 명령어를 입력하면 됩니다.
3. 1번이나 2번 후, sh setup.sh 를 실행합니다.
### 실행 명령어
```python
uv run app.py
```

### playwright 오픈소스 수정 내역
playwright-dev/playwright/_impl/_driver.py 의 내용을 수정하여, playwright-python에서 playwright editorble 을 바라보도록 수정하였습니다.

playwright-dev/playwright/packages/injected/src/recorder/recorder.ts 에서 _updateModelForHoveredElement 함수 수정

playwright-dev/playwright/packages/injected/src/selectorGenerator.ts 에서 fullPathSelector 함수 추가 및 기존 generateSelector 함수에서 호출

### 팁
playwright js 수정 시 재빌드가 필요하기 때문에 npm run watch 실행해 놓고 개발 진행하면 됩니다.
