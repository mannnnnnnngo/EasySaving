# Easy Saving — PDF 한 장씩 잘라 저장하기 + PowerPoint 로 바꾸기

124페이지짜리 PDF도 버튼 한 번이면 끝. 인쇄 창을 띄워 한 장씩 저장할 필요가 없습니다.

```
기안.pdf (2쪽)  →  바탕 화면 / 기안 저장 / 기안 - 1.pdf
                                        / 기안 - 2.pdf
```

화면에 떠 있는 작은 **`저장하기` ▾** 버튼으로 동작하며, 다른 프로그램 위에 항상 떠 있습니다.

---

## 1. 윈도우용 .exe 만들기 (개발자가 한 번만)

윈도우 PC에서 **`build\build_windows.bat`** 을 더블클릭하세요. 파이썬 3.9 이상만 있으면 됩니다
(설치할 때 *Add Python to PATH* 체크 필수).

배치 파일이 알아서 다 합니다:

| 단계 | 하는 일 |
|---|---|
| 1 | 파이썬 확인 |
| 2 | 빌드용 가상환경 `.venv-build` 생성 |
| 3 | `pypdf`, `pyinstaller` 설치 |
| 4 | 앱 아이콘 `assets\easysaving.ico` 생성 |
| 5 | **`dist\EasySaving.exe`** 빌드 (콘솔 창 없는 단일 실행 파일) |

빌드가 끝나면 배포용 폴더가 함께 만들어집니다:

```
dist\EasySaving_설치\
   ├── EasySaving.exe
   ├── 설치하기.bat      ← 받는 사람은 이것만 더블클릭
   ├── 제거하기.bat
   ├── easysaving.ico
   └── 사용법.txt
```

이 폴더를 압축해서 전달하면 됩니다. **받는 사람은 파이썬을 깔 필요가 없습니다.**

### 설치 마법사(Setup.exe)로 만들고 싶다면

[Inno Setup 6](https://jrsoftware.org/isdl.php) 설치 후 **`build\build_installer.bat`** 실행 →
**`dist\EasySaving_Setup.exe`** 파일 하나가 나옵니다. 더블클릭 → 다음 → 설치 완료 방식입니다.

---

## 1-B. 파이썬 방식 설치 (스마트 앱 컨트롤 우회)

윈도우 11의 **스마트 앱 컨트롤(Smart App Control)** 이 켜져 있으면 서명되지 않은 `.exe`는
아예 실행이 차단됩니다. 이때는 exe를 만들지 말고 **`build\설치하기_파이썬방식.bat`** 을 쓰세요.

서명된 `pythonw.exe`로 실행되므로 차단되지 않습니다. 바탕 화면 · 시작 메뉴 바로가기까지
똑같이 만들어지고, 콘솔 창도 뜨지 않습니다. (파이썬 3.9 이상 필요)

---

## 2. 설치 (사용자)

`설치하기.bat` 더블클릭 → `Y` → 끝.

* 설치 위치: `%LOCALAPPDATA%\Programs\EasySaving` — **관리자 권한 불필요**
* 바탕 화면 + 시작 메뉴 바로가기 자동 생성
* *설정 > 앱 > 설치된 앱* 목록에 등록되어 일반 프로그램처럼 제거 가능
* 설치 중 "윈도우 켤 때 자동 실행" 여부를 물어봅니다
* 서명되지 않은 파일이라 SmartScreen 파란 창이 뜰 수 있음 → **추가 정보 › 실행**

제거: *설정 > 앱*에서 제거하거나 설치 폴더의 `제거하기.bat` 실행.

---

## 3. 사용법

| 조작 | 결과 |
|---|---|
| **저장하기** 클릭 | 파일 창(윈도우/맥 기본)이 바로 열립니다 → PDF 하나 선택 |
| **▾** 클릭 | 여러 파일 저장하기 · 설정 · 튜토리얼 다시 보기 · 종료 |
| **Alt + 마우스 우클릭 드래그** | 버튼 위치 이동 (조합키는 설정에서 변경) |

**여러 파일 저장하기**: 파일 창에서 여러 개 선택 후 두 가지 중 선택
* *따로 저장* — 파일마다 `[이름] 저장` 폴더 하나씩
* *한 폴더에 모아서* — 상위 폴더 이름을 직접 정하고 그 안에 파일별 폴더

**저장 전 미리보기**: 실제로 나누기 전에 *이렇게 저장할까요?* 창이 떠서
어떤 폴더에 `기안 - 1.pdf … 기안 - 12.pdf` 같은 파일이 몇 개 생기는지 보여줍니다.
비밀번호가 걸렸거나 손상된 PDF도 **저장을 시작하기 전에** 여기서 알려 줍니다.
창 안의 *다음부터 건너뛰기* 또는 설정에서 끌 수 있습니다.

**설정**: 이동 조합키(녹화 방식) · 버튼 색 · 글자 색 · 버튼 글자 · 크기 · 모서리 둥글기 ·
투명도 · 항상 위 · 저장 위치 · 폴더 이름 접미사 · 번호 자릿수(01, 02) ·
저장 전 미리보기 · 완료 후 폴더 열기

**튜토리얼**: 8단계(다음/이전). 필요한 권한을 안내하고, **권한 확인 체크박스를 누르기 전까지는
앱을 켤 때마다** 자동으로 뜹니다.

---

## 3-B. 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| bat 실행 시 모든 줄이 `내부 또는 외부 명령이 아닙니다` | 한글이 든 배치 파일에 `chcp`를 쓰면 cmd가 파일을 다시 읽으며 줄이 어긋납니다. 이 저장소의 `.bat`는 **CP949 인코딩 + chcp 없음**으로 되어 있으니 그대로 쓰세요. 수정할 때도 CP949로 저장해야 합니다 |
| 스마트 앱 컨트롤이 exe를 차단 | 위 **1-B 파이썬 방식**을 사용 (권장). 또는 *Windows 보안 > 앱 및 브라우저 컨트롤 > 스마트 앱 컨트롤*을 끄기 — 단, **한 번 끄면 윈도우 재설치 없이는 다시 못 켭니다** |
| 파란 창 "Windows의 PC 보호" | 서명 없는 파일이라 뜹니다. **추가 정보 › 실행** |
| `파이썬을 찾을 수 없습니다` | python.org에서 설치할 때 **Add Python to PATH** 체크 |
| 백신이 exe 삭제 | PyInstaller 산출물의 흔한 오탐. 예외 등록 후 재빌드, 또는 파이썬 방식 사용 |

---

## 3-C. PDF → PowerPoint 로 바꾸기 (1.1.0)

**▾ 메뉴 › PowerPoint 로 바꾸기** → PDF 하나 또는 여러 개 선택 → 저장 위치(기본: 바탕 화면)에
`[이름].pptx` 가 생깁니다.

| 방식 (설정에서 선택) | 결과 |
|---|---|
| **글자 편집 가능** (기본) | 페이지에서 글자만 지운 배경 그림 + 원래 자리에 편집 가능한 텍스트 상자 (글꼴·크기·색·굵게·기울임·위첨자 유지). 그림·도형·표 선은 배경에 그대로 |
| **그림 그대로** | 페이지를 통째로 한 장의 그림으로 (모양 100% 동일, 편집 불가). 글자는 발표자 노트에 |

PDF 에 쓰인 폰트가 컴퓨터에 없으면 비슷한 기본 폰트(세리프 → Georgia, 나머지 → Arial)로 바꿉니다.
명령줄로도 됩니다: `EasySaving.exe --to-pptx 입력.pdf [출력.pptx] [--image]`

---

## 3-D. 자동 업데이트

새 버전은 GitHub Releases(<https://github.com/mannnnnnnngo/EasySaving/releases>)에 올라갑니다.
앱은 켤 때 하루 한 번 확인하고(설정에서 끌 수 있음), **▾ 메뉴 › 업데이트 확인** 으로 직접 확인할 수도 있습니다.

| 설치 방식 | 업데이트 방법 |
|---|---|
| `EasySaving.exe` | 새 exe 를 받아 바꿔 끼우고 다시 켬 (배치 파일·관리자 권한 없이) |
| `git clone` 한 폴더 (맥 포함) | `git pull` + 라이브러리 설치 후 다시 켬 |
| 파이썬 방식 설치 | 소스 zip 을 받아 프로그램 파일만 덮어쓰고 다시 켬 |

설정 파일은 사용자 폴더에 따로 있어서 업데이트해도 그대로입니다.

### 새 버전 내보내기 (개발자)

1. `easysaving/__init__.py` 의 `APP_VERSION` 을 올린다 (예: `1.2.0`)
2. 윈도우에서 `builduild_windows.bat` → `dist\EasySaving.exe`
3. 커밋·푸시 후 릴리스 만들기:
   ```bash
   gh release create v1.2.0 dist/EasySaving.exe --title "Easy Saving 1.2.0" --notes "바뀐 점…"
   ```
   태그는 `v` + 버전, 첨부 파일 이름은 반드시 `EasySaving.exe`.

### 맥에서

```bash
git clone https://github.com/mannnnnnnngo/EasySaving.git && cd EasySaving
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```
이후에는 앱의 *업데이트 확인* 이 `git pull` 로 최신 버전을 받아옵니다.

---

## 3-E. 파란 창 / 백신(Windows Defender) 경고

| 증상 | 원인 | 이번 버전에서 한 일 |
|---|---|---|
| 켤 때마다 파란 **"Windows의 PC 보호"** 창 | SmartScreen 이 *인터넷에서 받은 서명 없는 exe* 에 띄움 | 설치할 때 exe 의 '인터넷에서 받음' 표시(Mark of the Web)를 지워 **설치 후에는 안 뜸**. Setup.exe(Inno) 로 설치해도 안 뜸 |
| 켤 때 검은/파란 **터미널 창**이 같이 뜸 | `run.py` 를 더블클릭하거나 `.bat` 으로 실행 | python.exe 로 켜지면 창 없는 pythonw 로 다시 켜고 콘솔을 닫음. `실행하기.bat` → 창 없는 `실행하기.vbs`, 더블클릭용 `EasySaving.pyw` 추가 |
| Defender 가 exe 를 지우거나 막음 | PyInstaller exe 흔한 오탐 | 숨은 cmd 로 exe 를 바꿔 끼우던 업데이트 방식 제거, `-ExecutionPolicy Bypass` 제거, exe 에 회사·버전 정보 추가. 1.1.0 exe 는 Defender 검사 결과 **위협 없음** |

**완전히 없애는 유일한 방법은 코드 서명**입니다 (받자마자 첫 실행의 SmartScreen 경고, Smart App Control 차단까지).
인증서가 생기면 `set SIGN_ARGS=...` 후 `build_windows.bat` 을 실행하면 자동으로 서명합니다.
저렴한 선택지: Azure Trusted Signing (월 약 $10, 개인 신원 확인 필요).
서명 전까지는 오탐이 생기면 <https://www.microsoft.com/wdsi/filesubmission> 에 exe 를 '오탐(Incorrectly detected)'으로 제출하면 보통 며칠 안에 풀립니다.
스마트 앱 컨트롤이 켜진 PC 는 **1-B 파이썬 방식**을 쓰세요 (서명된 pythonw.exe 로 실행되어 차단되지 않음).

---

## 4. 구조 (레이어)

상위 레이어만 하위 레이어를 의존합니다.

```
easysaving/
├── core/                 ① 순수 도메인 — OS·UI 의존 없음
│   ├── models.py           설정·작업 데이터 모델
│   ├── naming.py           '기안 저장' / '기안 - 1.pdf' 이름 규칙
│   ├── splitter.py         PDF 분할 엔진 (pypdf 지연 임포트)
│   ├── pdf_to_pptx.py      PDF → PowerPoint 변환 엔진 (pymupdf + python-pptx 지연 임포트)
│   └── errors.py
├── platform_layer/       ② OS 추상화
│   ├── paths.py            바탕 화면·설정 폴더·폴더 열기
│   ├── permissions.py      OS별 권한 확인 + 설정 화면 열기
│   └── memory.py           메모리 사용량 측정
├── services/             ③ 애플리케이션 서비스
│   ├── config_service.py   설정 저장/복구 (원자적 쓰기)
│   ├── split_service.py    워커 스레드 + 진행률 큐 + 저장 전 미리보기 계산
│   ├── convert_service.py  PowerPoint 변환 워커 스레드
│   ├── update_service.py   GitHub Releases 업데이트 확인·설치
│   └── combo.py            이동 조합키 판정 (OS별 마스크)
├── ui/                   ④ Tkinter 프레젠테이션
│   ├── floating_button.py  떠 있는 알약 버튼
│   ├── menu.py, theme.py, widgets.py
│   └── dialogs/            튜토리얼·설정·미리보기·진행·완료
└── main.py               composition root (레이어 조립)
```

---

## 5. 메모리 100MB 제약

요구사항이 **100MB 이하**여서 UI 프레임워크를 실측으로 골랐습니다.

| 후보 | 실측 | 결과 |
|---|---|---|
| PySide6 (Qt) | 112.7 MB | ❌ 탈락 |
| **Tkinter + pypdf** | **23.7 MB** (패키징된 실행 파일 기준) | ✅ 채택 |

추가로 지킨 것:
* `pypdf`는 실제로 분할할 때만 import (시작 시 ~20MB 절약)
* 페이지를 모아 두지 않고 1장씩 만들어 즉시 파일로 기록, 25페이지마다 GC
* PyInstaller에서 numpy/PIL 등 대형 모듈 제외
* 설정 창 하단에 현재 메모리 사용량 표시

---

## 6. 개발·테스트

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # 준비
.venv/bin/python run.py                                # 실행
.venv/bin/python -m tests.test_core                    # 로직 테스트 (창 없음)
.venv/bin/python -m tests.test_convert                 # PowerPoint 변환 + 업데이트 로직
.venv/bin/python -m tests.smoke_ui                     # 화면 테스트
```

### 검증 상태

| 항목 | 상태 |
|---|---|
| 124페이지 분할 · 폴더/파일 이름 · 여러 파일 · 이름 충돌 · 손상 PDF · 설정 복구 · 조합키 | ✅ `tests/test_core.py` 전체 통과 (0.03초, 24.5MB) |
| 화면 10종 — 버튼 그리기·클릭영역·실시간 스타일 반영·드롭다운·튜토리얼 8단계(왕복)·설정(조합키 녹화)·저장 방식·저장 전 미리보기·진행 창·완료/오류 | ✅ `tests/smoke_ui.py` 전체 통과 |
| PyInstaller spec | ✅ 실제 빌드로 검증 (4.4MB 단일 실행 파일, 정상 실행, RSS 23.6MB) |
| 윈도우 `.exe` / `설치하기.bat` | ⏳ 윈도우 PC에서 `build\build_windows.bat` 실행 필요 (여기선 맥이라 미실행) |

> **macOS 개발 시 주의** — 시스템 파이썬의 Tk 8.5에는 갓 만든 다이얼로그에 `.update()`를 부르면
> 멈추는 버그가 있습니다. 앱 본체는 `update_idletasks()` + `wait_window()` 경로만 사용하므로
> 영향이 없고, 윈도우(Tk 8.6)에도 해당하지 않습니다. 테스트에서만 `.update()`를 피합니다.
> 같은 이유로 루트 창은 숨겨 두고(`withdraw`) 플로팅 버튼을 자식 창으로 띄웁니다 —
> `overrideredirect` 루트의 자식 다이얼로그가 macOS에서 뜨지 않는 문제를 함께 피합니다.
