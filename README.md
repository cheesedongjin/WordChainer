# WordChainer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[English README](README.en.md)

## 소개
WordChainer는 한국어 끝말잇기를 인공지능 봇과 함께 즐길 수 있는 프로젝트입니다. Tkinter 기반의 데스크톱 앱과 GitHub Pages로 배포된 웹 버전을 동시에 제공하여, 사용자는 어디서든 간편하게 게임을 시작할 수 있습니다. [웹 버전 바로가기](https://cheesedongjin.github.io/WordChainer/)

## 주요 특징
- **다양한 난이도**: 1단계부터 5단계까지 봇의 난이도를 조절하여 실력에 맞게 도전할 수 있습니다.
- **실시간 타이머**: 각 턴마다 남은 시간을 직관적인 게이지로 확인할 수 있어 긴장감 있는 플레이가 가능합니다.
- **단어 정보 탐색**: 대화창의 단어를 클릭하면 사전에서 가져온 발음, 뜻풀이, 용례 등을 바로 확인할 수 있습니다.
- **전적 기록**: 게임 결과는 난이도별로 자동 저장되어 장기적인 실력 향상을 추적할 수 있습니다.
- **추천 단어 안내**: 규칙 위반 등으로 패배했을 때, 사용자가 말할 수 있었던 단어 예시를 시스템 메시지로 알려 줍니다.
- **두음법칙 처리**: 단어 끝 글자와 두음 변환 글자를 함께 고려하여 자연스러운 한국어 끝말잇기 경험을 제공합니다.

## 일반 사용자 가이드

### 1. 웹에서 즐기기
1. 웹 브라우저에서 [https://cheesedongjin.github.io/WordChainer/](https://cheesedongjin.github.io/WordChainer/) 로 이동합니다.
2. 좌측 패널의 "게임 시작" 버튼을 눌러 봇과의 게임을 시작합니다.
3. "봇 난이도" 슬라이더로 난이도를 조정하고, 입력창에 단어를 입력해 봇과 번갈아 끝말잇기를 진행합니다.
4. 우측 패널의 "단어 정보" 영역에서 클릭한 단어의 의미와 용례를 확인하며 어휘력을 키워 보세요.

### 2. 데스크톱 앱 실행하기
1. Python 3.10 이상이 설치되어 있는지 확인합니다.
2. 프로젝트를 다운로드한 후 다음 명령을 실행해 필요한 의존성을 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```
   > `requirements.txt`에 별도 패키지가 명시되어 있지 않은 경우, 기본 Python 표준 라이브러리만으로 실행됩니다.
3. Tkinter GUI 앱을 실행합니다.
   ```bash
   python main.py
   ```
4. 앱이 실행되면 "게임 시작" 버튼을 눌러 플레이를 시작하고, 입력창에 단어를 입력하거나 Enter 키로 제출합니다.
5. 게임 결과는 `game_stats.json` 파일에 자동 저장됩니다. 필요 시 해당 파일을 삭제하여 전적을 초기화할 수 있습니다.

## 개발자 가이드

### 프로젝트 구조
```
WordChainer/
├── index.html          # GitHub Pages용 웹 앱
├── main.py             # Tkinter 기반 데스크톱 앱
├── words.json          # 끝말잇기용 단어 데이터베이스
├── dev/
│   ├── extract_words_to_json.py  # 원천 데이터에서 words.json을 생성하는 스크립트
│   └── requirements-dev.txt      # 개발 환경용 의존성 목록
├── requirements.txt    # 실행에 필요한 Python 패키지 목록
└── README.md
```

### 로컬 개발 환경 구축
1. 가상 환경을 권장합니다.
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\Activate.ps1  # Windows PowerShell
   pip install -r dev/requirements-dev.txt
   ```
2. Tkinter UI를 수정할 경우 `main.py`를 직접 실행하여 변경 사항을 즉시 확인할 수 있습니다.
3. 웹 클라이언트를 개발하려면 `index.html`을 로컬 서버에서 열어야 합니다.
   ```bash
   python -m http.server 8000
   ```
   이후 브라우저에서 `http://localhost:8000/index.html`로 접속합니다.

### 단어 데이터 갱신
- `dev/extract_words_to_json.py` 스크립트는 여러 개의 엑셀(`.xls`) 파일에서 명사 데이터를 추출하여 `words.json`을 생성합니다.
- 스크립트 실행 전 `dev/input_xls/` 디렉터리에 원천 데이터를 배치하고, `dev/output/` 폴더가 없으면 생성합니다.
  ```bash
  cd dev
  python extract_words_to_json.py
  ```
- 스크립트는 두음법칙을 고려한 "이음 수"를 계산하여 단어별 난도를 측정하고, 게임 중 추천 단어 로직에 활용합니다.

### 배포
- 웹 버전은 `index.html`을 GitHub Pages에 배포하여 제공됩니다. 정적 자산만으로 구성되어 별도의 빌드 과정이 필요 없습니다.
- 데스크톱 버전은 `main.py`와 `words.json` 파일을 포함하여 배포하면 됩니다. 필요 시 PyInstaller 등으로 패키징할 수 있습니다.

## 라이선스
이 프로젝트는 [MIT License](LICENSE)를 따릅니다. 자유롭게 수정 및 배포하되, 라이선스 조건을 준수해 주세요.
